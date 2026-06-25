import sqlite3
from contextlib import contextmanager
from datetime import datetime
from .config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS product_master (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ecount_sku  TEXT    NOT NULL UNIQUE,
                product_name TEXT   NOT NULL,
                purchase_price REAL,
                sale_price  REAL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                sync_source TEXT    NOT NULL DEFAULT 'API',
                updated_at  TEXT    NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def upsert_products(products: list[dict]):
    """products: list of dicts with keys ecount_sku, product_name, purchase_price, sale_price"""
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO product_master (ecount_sku, product_name, purchase_price, sale_price, is_active, sync_source, updated_at)
            VALUES (:ecount_sku, :product_name, :purchase_price, :sale_price, 1, 'API', :updated_at)
            ON CONFLICT(ecount_sku) DO UPDATE SET
                product_name   = excluded.product_name,
                purchase_price = excluded.purchase_price,
                sale_price     = excluded.sale_price,
                is_active      = 1,
                sync_source    = 'API',
                updated_at     = excluded.updated_at
            """,
            [{**p, "updated_at": now} for p in products],
        )
        conn.commit()


def deactivate_missing(active_skus: set[str]):
    """Mark SKUs no longer returned by API as inactive (soft delete)."""
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        rows = conn.execute("SELECT ecount_sku FROM product_master WHERE is_active = 1").fetchall()
        db_skus = {r["ecount_sku"] for r in rows}
        to_deactivate = db_skus - active_skus
        if to_deactivate:
            conn.executemany(
                "UPDATE product_master SET is_active = 0, updated_at = ? WHERE ecount_sku = ?",
                [(now, sku) for sku in to_deactivate],
            )
            conn.commit()
        return len(to_deactivate)


def get_stats() -> dict:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM product_master").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM product_master WHERE is_active = 1").fetchone()[0]
        return {"total": total, "active": active, "inactive": total - active}


def init_sales_table():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ecount_sales_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT,
                sale_no TEXT,
                ecount_sku TEXT,
                product_name TEXT,
                quantity INTEGER,
                unit_price INTEGER,
                total_amount INTEGER,
                customer_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sale_date, sale_no, product_name)
            )
        """)
        conn.commit()


def upsert_sales(rows: list[dict]) -> int:
    """Insert sales rows, skipping duplicates. Returns inserted count."""
    with _conn() as conn:
        result = conn.executemany(
            """
            INSERT OR IGNORE INTO ecount_sales_history
                (sale_date, sale_no, ecount_sku, product_name, quantity,
                 unit_price, total_amount, customer_name)
            VALUES
                (:sale_date, :sale_no, :ecount_sku, :product_name, :quantity,
                 :unit_price, :total_amount, :customer_name)
            """,
            rows,
        )
        conn.commit()
        return result.rowcount


def lookup_sku(product_name: str) -> str | None:
    """Find ecount_sku by exact or partial product_name match in product_master."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT ecount_sku FROM product_master WHERE product_name = ? AND is_active = 1 LIMIT 1",
            (product_name,),
        ).fetchone()
        if row:
            return row["ecount_sku"]
        row = conn.execute(
            "SELECT ecount_sku FROM product_master WHERE product_name LIKE ? AND is_active = 1 LIMIT 1",
            (f"%{product_name}%",),
        ).fetchone()
        return row["ecount_sku"] if row else None
