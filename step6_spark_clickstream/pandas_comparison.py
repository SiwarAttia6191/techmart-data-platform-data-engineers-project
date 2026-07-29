"""
Step 6 - pandas_comparison.py
---------------------------------
The same clickstream cleaning + session calculation + daily aggregation
logic as spark_pipeline.py, written in plain Pandas, timed the same
way -- so you can see directly where Pandas is perfectly fine (this
dataset size) and reason about the point where Spark's overhead starts
paying for itself (much larger data / a real multi-node cluster).

Usage:
    python3 step6_spark_clickstream/pandas_comparison.py
"""
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = Path(__file__).resolve().parent / "clickstream_raw.csv"
OUT_DIR = Path(__file__).resolve().parent / "output_pandas"
VALID_EVENT_TYPES = {"page_view", "view_product", "add_to_cart", "purchase"}


def main():
    t0 = time.time()

    # 1. Read
    df = pd.read_csv(RAW_PATH, dtype={"customer_id": str, "product_id": str})

    # 2. Parse timestamps and types
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], format="%Y-%m-%dT%H:%M:%S", errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df["event_date"] = df["event_timestamp"].dt.date

    valid_products = set(
        pd.read_csv(ROOT / "data" / "master" / "products.csv")["product_id"].astype(int)
    )

    # 3. Remove invalid records
    n_before = len(df)
    df = df[df["event_timestamp"].notna()]
    df = df[df["event_type"].isin(VALID_EVENT_TYPES)]
    has_product = df["product_id"].notna()
    df = df[~has_product | df["product_id"].isin(valid_products)]
    n_after = n_before - len(df)
    print(f"Removed {n_after} invalid records out of {n_before} ({n_after/n_before:.1%})")

    # 4. Sessions
    sessions = (
        df.groupby("session_id")
        .agg(
            customer_id=("customer_id", lambda s: next((x for x in s if pd.notna(x) and x != ""), None)),
            device_type=("device_type", "first"),
            session_start=("event_timestamp", "min"),
            session_end=("event_timestamp", "max"),
            event_count=("event_id", "count"),
            event_date=("event_date", "min"),
        )
        .reset_index()
    )
    sessions["converted"] = sessions["session_id"].isin(
        df.loc[df["event_type"] == "purchase", "session_id"]
    ).astype(int)
    sessions["duration_seconds"] = (sessions["session_end"] - sessions["session_start"]).dt.total_seconds()

    # 5. Daily aggregation
    daily_agg = (
        df.groupby("event_date")
        .apply(
            lambda g: pd.Series(
                {
                    "page_views": (g["event_type"] == "page_view").sum(),
                    "product_views": (g["event_type"] == "view_product").sum(),
                    "add_to_carts": (g["event_type"] == "add_to_cart").sum(),
                    "purchases": (g["event_type"] == "purchase").sum(),
                    "sessions": g["session_id"].nunique(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    daily_agg["conversion_rate_pct"] = (100 * daily_agg["purchases"] / daily_agg["sessions"]).round(2)

    product_agg = (
        df[df["product_id"].notna()]
        .groupby(["event_date", "product_id"])
        .apply(
            lambda g: pd.Series(
                {
                    "views": (g["event_type"] == "view_product").sum(),
                    "add_to_carts": (g["event_type"] == "add_to_cart").sum(),
                    "purchases": (g["event_type"] == "purchase").sum(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )

    # 6 & 7. Write partitioned output (Pandas has no native partitioned
    # writer, so we partition manually by event_date to match Spark's layout)
    OUT_DIR.mkdir(exist_ok=True)
    for date_val, group in sessions.groupby("event_date"):
        part_dir = OUT_DIR / "sessions" / f"event_date={date_val}"
        part_dir.mkdir(parents=True, exist_ok=True)
        group.drop(columns=["event_date"]).to_parquet(part_dir / "part.parquet", index=False)
    daily_agg.to_parquet(OUT_DIR / "daily_summary.parquet", index=False)
    for date_val, group in product_agg.groupby("event_date"):
        part_dir = OUT_DIR / "product_daily" / f"event_date={date_val}"
        part_dir.mkdir(parents=True, exist_ok=True)
        group.drop(columns=["event_date"]).to_parquet(part_dir / "part.parquet", index=False)

    elapsed = time.time() - t0
    print(f"\nSessions computed: {len(sessions)}")
    print(f"Daily summary rows: {len(daily_agg)}")
    print(f"Product-daily rows: {len(product_agg)}")
    print(f"Pandas pipeline finished in {elapsed:.2f}s")
    print(f"Output written to {OUT_DIR}")
    return elapsed


if __name__ == "__main__":
    main()
