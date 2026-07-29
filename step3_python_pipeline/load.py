"""
Step 3 - load.py
-------------------
Loads the cleaned marketplace orders into db/techmart.db as their own
table (marketplace_orders) -- kept separate from the direct-channel
`orders` table from Step 2 since it's a distinct source system, which
is exactly how you'd handle a second sales channel in a real warehouse.

Usage:
    python3 step3_python_pipeline/load.py
"""
import logging
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "techmart.db"
PROCESSED_PATH = Path(__file__).resolve().parent / "output" / "processed" / "marketplace_orders_clean.parquet"

logger = logging.getLogger("load")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS marketplace_orders (
    source_order_id  TEXT PRIMARY KEY,
    customer_email    TEXT NOT NULL,
    product_id        INTEGER NOT NULL REFERENCES products(product_id),
    quantity           INTEGER NOT NULL,
    order_ts           TEXT NOT NULL,
    amount_usd         NUMERIC(10,2) NOT NULL,
    loaded_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not PROCESSED_PATH.exists():
        raise SystemExit("No processed data found -- run transform.py first.")

    df = pd.read_parquet(PROCESSED_PATH)
    df["order_ts"] = df["order_ts"].astype(str)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)

    # Upsert-style load: INSERT OR REPLACE keyed on source_order_id keeps
    # this step idempotent -- rerunning the pipeline on the same data
    # doesn't create duplicate rows.
    rows = df.to_dict("records")
    conn.executemany(
        """INSERT OR REPLACE INTO marketplace_orders
           (source_order_id, customer_email, product_id, quantity, order_ts, amount_usd)
           VALUES (:source_order_id, :customer_email, :product_id, :quantity, :order_ts, :amount_usd)""",
        rows,
    )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM marketplace_orders").fetchone()[0]
    logger.info(f"Loaded {len(rows)} records (table now has {total} total rows) -> {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
