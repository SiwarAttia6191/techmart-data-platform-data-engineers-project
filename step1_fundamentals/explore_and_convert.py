"""
Step 1 - Data Engineering Fundamentals
========================================
Mini project from the roadmap:
  1. Download/receive a raw CSV dataset               -> data/raw/raw_orders_export.csv
  2. Inspect its columns and data types                -> inspect()
  3. Clean incorrect values                             -> clean()
  4. Convert it to JSON and Parquet                     -> to_json() / to_parquet()
  5. Document how each format differs                   -> FORMAT_NOTES.md (generated)

Run:
    python3 step1_fundamentals/explore_and_convert.py
"""
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "raw_orders_export.csv"
OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)

VALID_STATUSES = {"completed", "shipped", "cancelled", "pending"}


def inspect(df: pd.DataFrame) -> None:
    print("=== Shape ===")
    print(df.shape)
    print("\n=== Dtypes (before cleaning) ===")
    print(df.dtypes)
    print("\n=== Null counts ===")
    print(df.isna().sum())
    print("\n=== Exact duplicate rows ===")
    print(df.duplicated().sum())
    print("\n=== Distinct 'status' values (shows the mess) ===")
    print(df["status"].value_counts(dropna=False))


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Drop exact duplicate rows (real-world export artifact)
    df = df.drop_duplicates()

    # 2. Drop rows missing a customer_id or order_date -- can't be trusted downstream
    df["customer_id"] = df["customer_id"].replace("", pd.NA)
    df["order_date"] = df["order_date"].replace("", pd.NA)
    df = df.dropna(subset=["customer_id", "order_date"])

    # 3. Normalize order_date: the raw export mixes YYYY-MM-DD, DD/MM/YYYY,
    #    MM-DD-YYYY and YYYY/MM/DD. We try each known format per value.
    def parse_date(value):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d"):
            try:
                return pd.to_datetime(value, format=fmt)
            except (ValueError, TypeError):
                continue
        return pd.NaT

    df["order_date"] = df["order_date"].apply(parse_date)
    df = df.dropna(subset=["order_date"])

    # 4. quantity arrives as a mix of int, string, and null -> coerce to nullable Int64,
    #    fill missing with 1 (business rule: assume a single unit if unspecified)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype("int64")

    # 5. status has inconsistent casing and blanks -> lowercase + fill unknown
    df["status"] = df["status"].str.lower().where(df["status"].str.lower().isin(VALID_STATUSES), "unknown")

    # 6. channel has real nulls -> fill with 'unknown' rather than dropping the row
    df["channel"] = df["channel"].fillna("unknown")

    # 7. correct dtypes
    df["customer_id"] = df["customer_id"].astype("int64")
    df["product_id"] = df["product_id"].astype("int64")

    return df.reset_index(drop=True)


def to_json(df: pd.DataFrame, path: Path) -> None:
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)


def to_parquet(df: pd.DataFrame, path: Path) -> None:
    df.to_parquet(path, engine="pyarrow", index=False)


def write_format_notes(csv_size, json_size, parquet_size, row_count) -> None:
    notes = f"""# Format comparison notes (generated)

Source: `data/raw/raw_orders_export.csv` ({row_count} clean rows after Step 1 processing)

| Format  | File size | Notes |
|---------|-----------|-------|
| CSV     | {csv_size:,} bytes | Row-oriented, human-readable, no embedded schema/types -- every consumer has to re-infer dtypes. Cheapest to produce, most fragile to consume. |
| JSON    | {json_size:,} bytes | Largest on disk (repeats field names every row). Good for APIs and nested/semi-structured data, poor for large analytical scans. |
| Parquet | {parquet_size:,} bytes | Column-oriented + compressed + carries its own schema (dtypes travel with the file). Smallest on disk here and the fastest to scan a subset of columns from, which is why it's the default for analytical (OLAP) workloads. |

Takeaway: CSV/JSON are fine for small interchange and APIs; Parquet is the
right choice once data lands in a lake/warehouse and gets queried repeatedly.
"""
    (OUT_DIR / "FORMAT_NOTES.md").write_text(notes, encoding="utf-8")


def main():
    df_raw = pd.read_csv(RAW_PATH, dtype=str)  # read as str first to see the real mess
    inspect(df_raw)

    df_clean = clean(df_raw)
    print(f"\nRows: {len(df_raw)} raw -> {len(df_clean)} clean "
          f"({len(df_raw) - len(df_clean)} dropped as unrecoverable)")

    csv_out = OUT_DIR / "orders_clean.csv"
    json_out = OUT_DIR / "orders_clean.json"
    parquet_out = OUT_DIR / "orders_clean.parquet"

    df_clean.to_csv(csv_out, index=False)
    to_json(df_clean, json_out)
    to_parquet(df_clean, parquet_out)

    write_format_notes(
        csv_size=os.path.getsize(csv_out),
        json_size=os.path.getsize(json_out),
        parquet_size=os.path.getsize(parquet_out),
        row_count=len(df_clean),
    )
    print(f"\nWrote cleaned CSV/JSON/Parquet + FORMAT_NOTES.md -> {OUT_DIR}")


if __name__ == "__main__":
    main()
