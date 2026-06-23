# 📋 [PRD] 이카운트 전일판매현황 자동 수집 및 DB 적재 파이프라인

## 1. 프로젝트 개요
* **목표:** 매일 아침 Gmail로 수신되는 이카운트 "전일판매현황" 이메일을 자동으로 읽고, 첨부된 동적 링크(JS/SPA)에 가상 브라우저로 접속하여 데이터를 스크래핑한 뒤 로컬 DB(`database/sewon_mapping.db`)에 적재한다.
* **실행 주체:** 클로드 코드(Claude Code)가 본 문서를 기반으로 터미널 환경에서 Python 코드를 작성하고 테스트를 완료한다.

---

## 2. 사전 환경 설정 (.env)
다음 환경 변수들이 프로젝트 루트의 `.env`에 등록되어 있어야 한다. (이미 등록된 값들은 활용하고, 없는 값은 스크립트 작성 시 예외 처리를 추가할 것)
```env
# Gmail IMAP 연동
GMAIL_USER=sewonmusic@gmail.com
GMAIL_APP_PASSWORD=**** (16자리 앱 비밀번호)

# 이카운트 웹 뷰어 로그인 계정
ECOUNT_WEB_ID=sewonmusic
ECOUNT_WEB_PASSWORD=dltlqdhdlf1!
```

---

## 3. 핵심 개발 모듈 및 요구사항

### Module 1. Gmail IMAP 수집기 (Email Fetcher)
* Python 내장 `imaplib`를 사용하여 `.env`의 `GMAIL_USER` 계정으로 IMAP 접속.
* 발신자가 `ecountnotice@ecount.com` 이고, 메일 제목에 `"자동알림 > 판매현황"`이 포함된 가장 최근 메일을 찾는다.
* 메일 본문의 HTML을 파싱하여 **"수신문서보기"** 버튼의 20자리 고유 해시값이 포함된 링크(예: `https://l.ecount.com/...`)를 추출하여 반환한다.

### Module 2. Playwright 스크래퍼 (Ecount Web Scraper)
* 이카운트 뷰어는 동적 렌더링(SPA) 페이지이므로 `playwright` 라이브러리를 사용해 스크래핑한다.
* `headless=True` 모드로 크롬(Chromium) 브라우저를 띄워 Module 1에서 추출한 링크로 접속.
* **로그인 처리 로직:** 
  - 링크 접속 시 아이디는 `SEWONMUSIC`으로 채워져 있을 수 있다.
  - 비밀번호 입력창을 찾아 `.env`의 `ECOUNT_WEB_PASSWORD`(`dltlqdhdlf1!`)를 입력하고 로그인/확인 버튼을 클릭.
* **테이블 렌더링 대기 및 데이터 추출:**
  - 판매현황 표(`table`)가 렌더링될 때까지 대기(`page.wait_for_selector`).
  - 컬럼 헤더(`일자-No.`, `품목명[규격]`, `수량`, `단가`, `공급가액`, `부가세`, `합계`, `거래처명`)를 식별.
  - 각 행(row)을 순회하며 텍스트 데이터를 추출. 숫자 데이터의 콤마(,) 등은 제거 후 형변환(int/float) 처리.

### Module 3. 데이터 정제 및 DB 적재 (Data Processor & DB Upsert)
* **대상 DB:** `database/sewon_mapping.db`
* **신규 테이블 정의:** `ecount_sales_history`
  ```sql
  CREATE TABLE IF NOT EXISTS ecount_sales_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sale_date TEXT,          -- 일자
      sale_no TEXT,            -- No.
      ecount_sku TEXT,         -- 매핑된 품목코드
      product_name TEXT,       -- 품목명[규격]
      quantity INTEGER,        -- 수량
      unit_price REAL,         -- 단가
      supply_value REAL,       -- 공급가액
      vat REAL,                -- 부가세
      total_amount REAL,       -- 합계
      customer_name TEXT,      -- 거래처명
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(sale_date, sale_no, product_name) -- 중복 방지
  );
  ```
* **데이터 정제 핵심 비즈니스 로직 (주의 사항):**
  1. **품목코드 매핑 (가장 중요):** 이메일 표에는 품목코드가 없음. 따라서 스크래핑한 `품목명[규격]` 값을 기존 `product_master` 테이블의 `product_name`과 조인(또는 매핑 검색)하여 `ecount_sku`를 추출해 함께 저장해야 함.
  2. **단가 누락 예외 처리:** 일부 거래처의 경우 표에서 `단가` 항목이 비어있음. `수량`과 `공급가액`이 존재하므로 스크립트 상에서 `(공급가액 / 수량)`으로 역산하여 `unit_price`에 입력하거나, 역산이 불가능할 경우 `0` 또는 `NULL`로 안전하게 캐스팅할 것.

---

## 4. 실행 및 배포 지침 (For Claude Code)
1. **패키지 설치:** `requirements.txt`에 `playwright`, `python-dotenv` 추가. (실행 전 `venv/bin/pip install playwright` 및 `venv/bin/playwright install chromium` 반드시 수행)
2. **코드 작성 위치:** 기존 프로젝트 구조를 따라 `src/ecount_mapping/sync_sales.py` (또는 적절한 모듈명) 파일에 메인 로직 작성.
3. **DB 연동:** DB 연결은 가급적 기존 `src/ecount_mapping/db.py` 의 패턴(`_conn()` 컨텍스트 매니저 등)을 재사용하여 일관성을 유지할 것.
4. **최종 테스트:** 메인 로직 개발 완료 후 스크립트를 직접 1회 실행시켜 실제 `sewon_mapping.db`의 `ecount_sales_history` 테이블에 데이터가 에러 없이 완벽하게 적재되는지 최종 검증하고 작업을 마칠 것.

---

## 5. 구현 결과 및 실제 동작 명세 (2026-06-23 완료)

### 실제 구현 파일
- `src/ecount_mapping/sync_sales.py` — 메인 파이프라인
- `src/ecount_mapping/db.py` — `init_sales_table`, `upsert_sales`, `lookup_sku` 추가
- cron 등록: `0 9 * * *` 매일 오전 9시 자동 실행, 로그 → `logs/sync_sales.log`

### PRD 대비 실제 구현 차이점

| 항목 | PRD 가정 | 실제 구현 |
|------|----------|-----------|
| Gmail IMAP 검색 | FROM + SUBJECT 한글 조건 | FROM만 IMAP 필터 후 Python에서 제목 2차 필터 (IMAP 한글 미지원) |
| 이카운트 링크 접속 | 단순 goto 후 로그인 폼 | S3 랜딩 → ecount 3단계 JS 리다이렉트 후 V5 SPA 로그인 폼 도달 |
| 로그인 처리 | 비밀번호 입력 후 버튼 클릭 | 로그인 후 "새로운 기기 알림" 모달 자동 해제(`등록안함`) 필요 |
| 테이블 대기 | `table` 셀렉터 대기 | `th:has-text('품목명')` 대기 (SPA 마운트 타이밍 이슈) |
| `일자` / `No.` 컬럼 | 별도 컬럼으로 가정 | `"일자-No."` 단일 컬럼 (`"2026/06/22 -1"` 형태로 분리 처리) |
| 품목명 매핑 | 품목명 그대로 조회 | `[규격명]` 제거 후 조회 (원본은 DB에 보존) |
| 소계 행 | 언급 없음 | "합계", "2026/06 계" 등 소계 행을 날짜 패턴으로 자동 제외 |
