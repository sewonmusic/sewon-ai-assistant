import json
import requests
from .auth import get_session, invalidate_session


def _parse_result(raw) -> list[dict]:
    """Result 필드는 JSON 문자열로 반환되므로 파싱 처리."""
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, list):
        return raw
    return []


def fetch_all_products() -> list[dict]:
    """이카운트 전체 품목 리스트 조회. 세션 만료 시 1회 재로그인."""
    zone, session_id = get_session()
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/InventoryBasic/GetBasicProductsList"

    resp = requests.post(
        url,
        params={"SESSION_ID": session_id},
        json={"PROD_CD": "", "PROD_TYPE": ""},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # 세션 만료 감지 후 1회 재시도
    if str(data.get("Status")) != "200" or data.get("Error"):
        err_code = (data.get("Error") or {}).get("Code")
        if err_code in (20, 21, 99):  # 로그인 관련 오류
            invalidate_session()
            zone, session_id = get_session()
            resp = requests.post(
                url,
                params={"SESSION_ID": session_id},
                json={"PROD_CD": "", "PROD_TYPE": ""},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

    if str(data.get("Status")) != "200":
        raise RuntimeError(f"품목 조회 실패: {data}")

    raw_result = (data.get("Data") or {}).get("Result", [])
    return _parse_result(raw_result)


def normalize_product(raw: dict) -> dict:
    """API 응답 필드를 product_master 스키마로 변환."""
    def _float(val):
        try:
            return float(val) if val not in (None, "", "0.0000000000") else 0.0
        except (TypeError, ValueError):
            return 0.0

    return {
        "ecount_sku": raw.get("PROD_CD", "").strip(),
        "product_name": raw.get("PROD_DES", "").strip(),
        "purchase_price": _float(raw.get("IN_PRICE")),
        "sale_price": _float(raw.get("OUT_PRICE") or raw.get("OUT_PRICE1")),
    }
