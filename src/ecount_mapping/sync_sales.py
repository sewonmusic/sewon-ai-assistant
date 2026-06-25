"""이카운트 전일판매현황 자동 수집 및 DB 적재 파이프라인.

실행: venv/bin/python -m src.ecount_mapping.sync_sales
"""

import imaplib
import email
import re
import os
import sys
from email.header import decode_header
from pathlib import Path
from dotenv import load_dotenv

_BASE = Path(__file__).parent.parent.parent
load_dotenv(_BASE / ".env")

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
ECOUNT_WEB_PASSWORD = os.environ["ECOUNT_WEB_PASSWORD"]

MAX_ERRORS = 3
_error_count = 0


def _fail(msg: str):
    global _error_count
    _error_count += 1
    print(f"[ERROR #{_error_count}] {msg}", file=sys.stderr)
    if _error_count >= MAX_ERRORS:
        print(f"\n연속 {MAX_ERRORS}회 에러 발생 — 작업을 중단합니다.", file=sys.stderr)
        sys.exit(1)
    raise RuntimeError(msg)


# ──────────────────────────────────────────
# Module 1. Gmail IMAP 수집기
# ──────────────────────────────────────────

def fetch_ecount_link() -> str:
    """Gmail에서 이카운트 판매현황 메일을 찾아 수신문서보기 링크를 반환."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    except Exception as e:
        _fail(f"Gmail IMAP 접속 실패: {e}")

    try:
        mail.select("INBOX")
        # IMAP은 한글 SUBJECT 검색을 지원하지 않으므로 발신자로만 1차 필터링
        _, data = mail.search(None, '(FROM "ecountnotice@ecount.com")')
        msg_ids = data[0].split()
        if not msg_ids:
            _fail("이카운트 발신 메일을 찾을 수 없습니다.")

        # 최신 순으로 순회하며 제목 필터링
        target_id = None
        for mid in reversed(msg_ids):
            _, hdr = mail.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT)])")
            raw_subj = hdr[0][1].decode("utf-8", errors="replace")
            subject = _decode_header_val(raw_subj.replace("Subject:", "").strip())
            if "판매현황" in subject:
                target_id = mid
                break

        if not target_id:
            _fail("제목에 '판매현황'이 포함된 메일을 찾을 수 없습니다.")

        _, raw = mail.fetch(target_id, "(RFC822)")
        msg = email.message_from_bytes(raw[0][1])
    except RuntimeError:
        raise
    except Exception as e:
        _fail(f"메일 조회 실패: {e}")
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    html_body = _extract_html(msg)
    if not html_body:
        _fail("메일 HTML 본문을 파싱할 수 없습니다.")

    # 20자리 해시가 포함된 l.ecount.com 링크 추출
    pattern = r'https?://l\.ecount\.com/[^\s"\'<>]+'
    links = re.findall(pattern, html_body)
    if not links:
        _fail("수신문서보기 링크를 찾을 수 없습니다.")

    print(f"[Module 1] 링크 추출 완료: {links[0][:60]}...")
    return links[0]


def _decode_header_val(val: str) -> str:
    """RFC2047 인코딩된 헤더 값을 디코딩하여 유니코드 문자열로 반환."""
    parts = decode_header(val)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_html(msg) -> str:
    """email.message에서 HTML 파트를 꺼내 반환."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


# ──────────────────────────────────────────
# Module 2. Playwright 스크래퍼
# ──────────────────────────────────────────

def scrape_sales_table(url: str) -> list[dict]:
    """Playwright로 이카운트 판매현황 페이지를 스크래핑하여 행 리스트 반환."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        _fail("playwright 패키지가 설치되지 않았습니다. 'venv/bin/pip install playwright' 후 재시도하세요.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)

            # 비밀번호 입력창이 있으면 로그인 처리
            try:
                pwd_input = page.wait_for_selector("#txtPass", timeout=8000)
                if pwd_input:
                    if not pwd_input.input_value():
                        pwd_input.fill(ECOUNT_WEB_PASSWORD)
                    save_btn = page.query_selector("#save")
                    if save_btn:
                        save_btn.click()
                    else:
                        page.keyboard.press("Enter")
                    # 새로운 기기 로그인 알림 모달 처리
                    try:
                        skip_btn = page.wait_for_selector(
                            "button:has-text('등록안함')", timeout=10000
                        )
                        skip_btn.click()
                    except PWTimeout:
                        pass  # 모달 없으면 계속 진행
                    page.wait_for_load_state("networkidle", timeout=20000)
            except PWTimeout:
                pass  # 비밀번호 창 없으면 이미 로그인 상태

            # 판매현황 테이블 렌더링 대기: 품목명 th가 나타날 때까지
            try:
                page.wait_for_selector("th:has-text('품목명')", timeout=30000)
            except PWTimeout:
                _fail("판매현황 테이블이 30초 내에 렌더링되지 않았습니다.")

            rows = _parse_table(page)
            browser.close()
            print(f"[Module 2] 스크래핑 완료: {len(rows)}행 추출")
            return rows
    except RuntimeError:
        raise
    except Exception as e:
        _fail(f"Playwright 스크래핑 오류: {e}")


def _parse_table(page) -> list[dict]:
    """페이지에서 판매현황 테이블을 파싱하여 dict 리스트 반환.

    실제 구조: th=[일자-No., 품목명[규격], 수량, 단가, 공급가액, 부가세, 합계, 거래처명]
    일자-No. 셀 값 예시: "2026/06/22 -1"  →  date="2026/06/22", no="1"
    """
    # 컬럼명 키워드 → 내부 필드명 매핑
    COL_MAP = {
        "일자": "sale_date_no",   # "일자-No." 합쳐진 컬럼
        "품목명": "product_name",
        "수량": "quantity",
        "합계": "total_amount",
        "거래처명": "customer_name",
    }

    # 판매현황 데이터가 있는 테이블 선택 (가장 많은 데이터 행을 가진 것)
    tables = page.query_selector_all("table")
    best_table = None
    best_score = 0

    for tbl in tables:
        ths = tbl.query_selector_all("th")
        header_texts = [th.inner_text().strip().lower() for th in ths]
        score = sum(1 for h in header_texts if any(k in h for k in COL_MAP))
        # 실 데이터 행 수도 반영
        data_rows = len([tr for tr in tbl.query_selector_all("tr")
                         if tr.query_selector_all("td")])
        if score > best_score or (score == best_score and data_rows > 0):
            best_score = score
            best_table = tbl

    if not best_table or best_score == 0:
        raise RuntimeError("판매현황 테이블을 식별할 수 없습니다.")

    # 헤더 인덱스 확정
    raw_headers = [th.inner_text().strip() for th in best_table.query_selector_all("th")]
    col_idx: dict[str, int] = {}
    for i, h in enumerate(raw_headers):
        hl = h.lower()
        for keyword, field in COL_MAP.items():
            if keyword in hl and field not in col_idx:
                col_idx[field] = i
                break

    def to_num(val: str, cast=float, nullable=False):
        cleaned = re.sub(r"[,\s원]", "", val)
        if not cleaned:
            return None if nullable else cast(0)
        try:
            return cast(cleaned)
        except ValueError:
            return None if nullable else cast(0)

    rows_data = []
    for tr in best_table.query_selector_all("tr"):
        cells = tr.query_selector_all("td")
        if not cells:
            continue

        def cell(field: str) -> str:
            idx = col_idx.get(field)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx].inner_text().strip()

        # "일자-No." 컬럼 분리: "2026/06/22 -1" → date, no
        raw_date_no = cell("sale_date_no")
        sale_date, sale_no = "", ""
        m = re.match(r"^(\S+)\s*-\s*(\d+)$", raw_date_no)
        if m:
            sale_date, sale_no = m.group(1), m.group(2)
        else:
            sale_date = raw_date_no

        qty = to_num(cell("quantity"), int)
        total = to_num(cell("total_amount"), int)
        unit = round(total / qty) if qty else 0

        rows_data.append({
            "sale_date": sale_date,
            "sale_no": sale_no,
            "product_name": cell("product_name"),
            "quantity": qty,
            "unit_price": unit,
            "total_amount": total,
            "customer_name": cell("customer_name"),
        })

    # 소계/합계 행 제거: 날짜가 YYYY/MM/DD 형식이 아닌 행 (예: "합계", "2026/06 계")
    date_pattern = re.compile(r"^\d{4}/\d{2}/\d{2}$")
    return [r for r in rows_data if r["product_name"] and date_pattern.match(r.get("sale_date", ""))]


# ──────────────────────────────────────────
# Module 3. 데이터 정제 및 DB 적재
# ──────────────────────────────────────────

def process_and_save(raw_rows: list[dict]) -> int:
    """품목코드 매핑 후 DB 적재. 삽입된 행 수 반환."""
    from .db import init_sales_table, upsert_sales, lookup_sku

    init_sales_table()

    enriched = []
    for row in raw_rows:
        # "[규격명]" 제거 후 매핑 (원본 product_name은 그대로 저장)
        name_for_lookup = re.sub(r"\s*\[.*?\]\s*$", "", row["product_name"]).strip()
        sku = lookup_sku(name_for_lookup)
        enriched.append({**row, "ecount_sku": sku})

    inserted = upsert_sales(enriched)
    print(f"[Module 3] DB 적재 완료: {inserted}행 신규 삽입 (전체 {len(enriched)}행)")
    return inserted


# ──────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────

def main():
    print("=== 이카운트 전일판매현황 수집 시작 ===")
    try:
        url = fetch_ecount_link()
        rows = scrape_sales_table(url)
        if not rows:
            print("[완료] 스크래핑된 데이터 없음 — DB 적재 스킵.")
            return
        inserted = process_and_save(rows)
        print(f"=== 완료: {inserted}건 신규 적재 ===")
    except SystemExit:
        raise
    except Exception as e:
        _fail(f"예상치 못한 오류: {e}")


if __name__ == "__main__":
    main()
