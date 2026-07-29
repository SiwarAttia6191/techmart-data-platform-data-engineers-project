"""
Step 3 - transform.py
------------------------
Validates and cleans the raw marketplace API records:
  - parses product_sku ("SKU-42") into an int product_id and checks it
    actually exists in TechMart's product catalog (data/master/products.csv)
  - parses order_ts into a real timestamp
  - drops records that fail validation, logging *why* each was dropped
    instead of silently discarding them
  - de-duplicates by marketplace_order_id (APIs sometimes double-send)

Saves cleaned, typed output as Parquet.

Usage:
    python3 step3_python_pipeline/transform.py
"""
import json
import logging
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = Path(__file__).resolve().parent / "output" / "raw" / "marketplace_orders_raw.json"
OUT_DIR = Path(__file__).resolve().parent / "output" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("transform")


def load_valid_product_ids() -> set[int]:
    products = pd.read_csv(ROOT / "data" / "master" / "products.csv")
    return set(products["product_id"].astype(int))


def transform(records: list[dict], valid_product_ids: set[int]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    before = len(df)

    df = df.drop_duplicates(subset="marketplace_order_id")
    logger.info(f"Dropped {before - len(df)} exact-duplicate marketplace_order_ids")

    df["product_id"] = df["product_sku"].str.replace("SKU-", "", regex=False)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")

    invalid_sku_mask = ~df["product_id"].isin(valid_product_ids)
    if invalid_sku_mask.any():
        logger.warning(f"Dropping {invalid_sku_mask.sum()} records with a product_sku "
                        f"not found in the product catalog")
    df = df[~invalid_sku_mask]
    df["product_id"] = df["product_id"].astype(int)

    df["order_ts"] = pd.to_datetime(df["order_ts"], errors="coerce", utc=True)
    bad_ts_mask = df["order_ts"].isna()
    if bad_ts_mask.any():
        logger.warning(f"Dropping {bad_ts_mask.sum()} records with an unparseable order_ts")
    df = df[~bad_ts_mask]

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df = df[df["quantity"] > 0]

    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce")
    df = df[df["amount_usd"] > 0]

    df = df.rename(columns={"marketplace_order_id": "source_order_id"})
    df = df[["source_order_id", "customer_email", "product_id", "quantity", "order_ts", "amount_usd"]]

    return df.reset_index(drop=True)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not RAW_PATH.exists():
        raise SystemExit("No raw extract found -- run extract.py first.")

    records = json.loads(RAW_PATH.read_text())
    valid_ids = load_valid_product_ids()
    df_clean = transform(records, valid_ids)

    out_path = OUT_DIR / "marketplace_orders_clean.parquet"
    df_clean.to_parquet(out_path, engine="pyarrow", index=False)
    logger.info(f"Transformed {len(records)} raw -> {len(df_clean)} clean records -> {out_path}")
    return out_path


if __name__ == "__main__":
    main()
