"""
Step 4 - incremental_pipeline.py
------------------------------------
The roadmap's "incremental sales pipeline" project, implemented against
the same TechMart database from Steps 2-3:

  1. Extract new records from the source `orders` table using an
     order_date WATERMARK (only pulls rows newer than the last run).
  2. Store raw records in a LANDING area (timestamped Parquet file) --
     an audit trail of exactly what each run pulled.
  3. Clean/standardize + DEDUPE against what's already loaded, so
     re-running the same batch twice is safe (idempotent).
  4. Load into `orders_incremental_log`, an append-only analytical table.
  5. Only advance the watermark AFTER a successful load, so a crash
     mid-run doesn't lose or skip data -- the next run just retries.
  6. Retry + failure logging throughout.

Usage:
    python3 step4_incremental_etl/incremental_pipeline.py
    python3 step4_incremental_etl/incremental_pipeline.py --reset   # start over from watermark zero
"""
import argparse
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import watermark

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "techmart.db"
LANDING_DIR = Path(__file__).resolve().parent / "landing"
LANDING_DIR.mkdir(exist_ok=True)

MAX_RETRIES = 3

logger = logging.getLogger("incremental_pipeline")

CREATE_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders_incremental_log (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    order_date   TEXT NOT NULL,
    status       TEXT NOT NULL,
    channel      TEXT NOT NULL,
    loaded_at    TEXT NOT NULL
);
"""


def extract_new(conn: sqlite3.Connection, since: str) -> pd.DataFrame:
    query = """
        SELECT order_id, customer_id, order_date, status, channel
        FROM orders
        WHERE order_date > ?
        ORDER BY order_date
    """
    return pd.read_sql_query(query, conn, params=(since,))


def land(df: pd.DataFrame) -> Path:
    ts = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y%m%dT%H%M%S")
    path = LANDING_DIR / f"orders_batch_{ts}.parquet"
    df.to_parquet(path, engine="pyarrow", index=False)
    return path


def dedupe_against_target(conn: sqlite3.Connection, df: pd.DataFrame) -> pd.DataFrame:
    already_loaded = pd.read_sql_query("SELECT order_id FROM orders_incremental_log", conn)
    before = len(df)
    df = df[~df["order_id"].isin(already_loaded["order_id"])]
    skipped = before - len(df)
    if skipped:
        logger.info(f"Skipped {skipped} rows already present in orders_incremental_log (idempotency check)")
    return df


def load_with_retry(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    rows = df.copy()
    rows["loaded_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    records = rows.to_dict("records")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn.executemany(
                """INSERT INTO orders_incremental_log
                   (order_id, customer_id, order_date, status, channel, loaded_at)
                   VALUES (:order_id, :customer_id, :order_date, :status, :channel, :loaded_at)""",
                records,
            )
            conn.commit()
            return
        except sqlite3.Error as exc:
            logger.warning(f"Load attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            conn.rollback()
            if attempt == MAX_RETRIES:
                raise
            time.sleep(0.5 * attempt)


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_LOG_TABLE_SQL)
    conn.commit()

    since = watermark.get_watermark()
    logger.info(f"Current watermark: {since}")

    df_new = extract_new(conn, since)
    if df_new.empty:
        logger.info("No new records since last watermark -- nothing to do.")
        conn.close()
        return

    landing_path = land(df_new)
    logger.info(f"Landed {len(df_new)} raw rows -> {landing_path}")

    df_clean = dedupe_against_target(conn, df_new)
    if df_clean.empty:
        logger.info("All extracted rows were already loaded (idempotent no-op). Watermark unchanged trigger avoided.")
        conn.close()
        return

    try:
        load_with_retry(conn, df_clean)
    except Exception:
        logger.exception("Load failed after all retries -- watermark NOT advanced, safe to re-run.")
        conn.close()
        raise

    new_watermark = df_clean["order_date"].max()
    watermark.set_watermark(new_watermark)
    logger.info(f"Loaded {len(df_clean)} rows into orders_incremental_log. "
                f"Watermark advanced to {new_watermark}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="reset the watermark and reprocess everything")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.reset:
        watermark.reset_watermark()
        logger.info("Watermark reset.")

    run()
