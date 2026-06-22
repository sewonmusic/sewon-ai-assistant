import time
import logging
from .api_client import fetch_all_products, normalize_product
from .db import init_db, upsert_products, deactivate_missing, get_stats
from .notifier import send_telegram
from .config import MAX_RETRY

logger = logging.getLogger(__name__)


def run_sync():
    init_db()

    raw_products = None
    last_error = None

    for attempt in range(1, MAX_RETRY + 1):
        try:
            logger.info(f"이카운트 품목 조회 시도 {attempt}/{MAX_RETRY}")
            raw_products = fetch_all_products()
            break
        except Exception as e:
            last_error = e
            logger.warning(f"시도 {attempt} 실패: {e}")
            if attempt < MAX_RETRY:
                time.sleep(2 ** attempt)  # 지수 백오프

    if raw_products is None:
        msg = f"[Ecount Sync 실패] {MAX_RETRY}회 재시도 후 최종 실패.\n오류: {last_error}\n마지막 DB 스냅샷 유지."
        logger.error(msg)
        send_telegram(msg)
        return False

    products = [normalize_product(r) for r in raw_products]
    products = [p for p in products if p["ecount_sku"]]  # 빈 SKU 제외

    upsert_products(products)
    active_skus = {p["ecount_sku"] for p in products}
    deactivated = deactivate_missing(active_skus)

    stats = get_stats()
    logger.info(
        f"동기화 완료 — 전체: {stats['total']}개, 활성: {stats['active']}개, "
        f"비활성: {stats['inactive']}개, 이번에 비활성 처리: {deactivated}개"
    )
    return True
