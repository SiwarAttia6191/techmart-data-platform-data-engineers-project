"""
Step 6 - spark_pipeline.py
------------------------------
The roadmap's "large-scale clickstream pipeline" project:
  1. Read the event dataset with Spark.
  2. Parse timestamps and user events.
  3. Remove invalid records.
  4. Calculate sessions.
  5. Aggregate page views and conversions.
  6. Partition output by date.
  7. Save results as Parquet.
(Step 8, comparing performance with a Pandas version, lives in
pandas_comparison.py -- run both and compare their printed timings.)

Usage:
    python3 step6_spark_clickstream/spark_pipeline.py
"""
import time
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, Window

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = Path(__file__).resolve().parent / "clickstream_raw.csv"
OUT_DIR = Path(__file__).resolve().parent / "output"
VALID_EVENT_TYPES = ["page_view", "view_product", "add_to_cart", "purchase"]


def build_spark():
    return (
        SparkSession.builder.appName("TechMartClickstream")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")  # small cluster -> keep shuffle partitions modest
        .config("spark.driver.memory", "2g")
        .config("spark.sql.ansi.enabled", "false")  # malformed timestamps -> NULL, not a thrown error
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")
        .config("spark.sql.sources.commitProtocolClass", "org.apache.spark.sql.execution.datasources.FileCommitProtocol")
        .getOrCreate()
    )


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")
    t0 = time.time()

    # 1. Read
    df = spark.read.csv(str(RAW_PATH), header=True, inferSchema=False)

    # 2. Parse timestamps and enforce types
    df = df.withColumn("event_timestamp", F.to_timestamp("event_timestamp", "yyyy-MM-dd'T'HH:mm:ss"))
    df = df.withColumn("product_id", F.col("product_id").cast("int"))
    df = df.withColumn("event_date", F.to_date("event_timestamp"))

    # Load the valid product catalog to catch orphaned product_ids
    valid_products = spark.read.csv(str(ROOT / "data" / "master" / "products.csv"), header=True) \
                             .select(F.col("product_id").cast("int").alias("valid_product_id"))

    # 3. Remove invalid records: bad timestamp, unknown event_type,
    #    or a product_id referencing a product that doesn't exist
    n_before = df.count()
    df = df.filter(F.col("event_timestamp").isNotNull())
    df = df.filter(F.col("event_type").isin(VALID_EVENT_TYPES))

    df_with_product = df.filter(F.col("product_id").isNotNull())
    df_without_product = df.filter(F.col("product_id").isNull())
    df_with_product_valid = df_with_product.join(
        valid_products, df_with_product.product_id == valid_products.valid_product_id, "inner"
    ).drop("valid_product_id")
    df = df_with_product_valid.unionByName(df_without_product)

    n_after = n_before - df.count()
    print(f"Removed {n_after} invalid records out of {n_before} ({n_after/n_before:.1%})")

    df.cache()

    # 4. Calculate sessions: one row per session_id with start/end/duration/
    #    event count/whether it converted to a purchase
    session_window = Window.partitionBy("session_id")
    sessions = (
        df.groupBy("session_id")
        .agg(
            F.first("customer_id", ignorenulls=True).alias("customer_id"),
            F.first("device_type").alias("device_type"),
            F.min("event_timestamp").alias("session_start"),
            F.max("event_timestamp").alias("session_end"),
            F.count("*").alias("event_count"),
            F.max(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("converted"),
            F.min("event_date").alias("event_date"),
        )
        .withColumn(
            "duration_seconds",
            F.col("session_end").cast("long") - F.col("session_start").cast("long"),
        )
    )

    # 5. Aggregate page views and conversions by day + device
    daily_agg = (
        df.groupBy("event_date")
        .agg(
            F.sum(F.when(F.col("event_type") == "page_view", 1).otherwise(0)).alias("page_views"),
            F.sum(F.when(F.col("event_type") == "view_product", 1).otherwise(0)).alias("product_views"),
            F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias("add_to_carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.countDistinct("session_id").alias("sessions"),
        )
        .withColumn(
            "conversion_rate_pct",
            F.round(100.0 * F.col("purchases") / F.col("sessions"), 2),
        )
        .orderBy("event_date")
    )

    product_agg = (
        df.filter(F.col("product_id").isNotNull())
        .groupBy("event_date", "product_id")
        .agg(
            F.sum(F.when(F.col("event_type") == "view_product", 1).otherwise(0)).alias("views"),
            F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias("add_to_carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
        )
    )

    # 6 & 7. Write partitioned Parquet
    OUT_DIR.mkdir(exist_ok=True)
    for target in ["sessions", "daily_summary", "product_daily"]:
        (OUT_DIR / target).mkdir(exist_ok=True)
    sessions.write.mode("overwrite").partitionBy("event_date").parquet(str(OUT_DIR / "sessions"))
    daily_agg.write.mode("overwrite").parquet(str(OUT_DIR / "daily_summary"))
    product_agg.write.mode("overwrite").partitionBy("event_date").parquet(str(OUT_DIR / "product_daily"))

    elapsed = time.time() - t0
    print(f"\nSessions computed: {sessions.count()}")
    print(f"Daily summary rows: {daily_agg.count()}")
    print(f"Product-daily rows: {product_agg.count()}")
    print(f"Spark pipeline finished in {elapsed:.2f}s")
    print(f"Output written to {OUT_DIR} (partitioned by event_date)")

    spark.stop()
    return elapsed


if __name__ == "__main__":
    main()
