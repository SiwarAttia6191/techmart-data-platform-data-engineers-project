# Step 6 — Spark & Distributed Processing

**Roadmap mini-project:** large-scale clickstream pipeline — read with
Spark, parse timestamps/events, remove invalid records, calculate
sessions, aggregate views/conversions, partition output by date, save as
Parquet, and compare performance with a Pandas version.

The clickstream events are tied to the same `customer_id` / `product_id`
keys as every other step — this is TechMart shoppers browsing before
(maybe) buying.

## Run

```bash
python3 step6_spark_clickstream/generate_clickstream.py --sessions 40000
python3 step6_spark_clickstream/spark_pipeline.py
python3 step6_spark_clickstream/pandas_comparison.py
```

Requires a JVM (PySpark needs one) — `pip install pyspark` alone isn't
enough; see the root `README.md` for setup.

## What actually happened when we ran this

On this single-core, ~4GB sandbox, against ~98K raw events:

| | Spark | Pandas |
|---|---|---|
| Runtime | ~44s | ~27s |
| Sessions computed | 40,000 | 40,000 |
| Invalid records removed | 400 | 400 |

Both produced **identical row counts** — a good sanity check that the
transformation logic matches between the two implementations. Pandas
was faster here, and that's the point, not a bug: on a single machine
with data this size, Spark's cluster-coordination overhead (JVM
startup, task scheduling, shuffle bookkeeping) costs more than it
saves. That overhead starts paying off once data no longer fits in one
machine's memory or you have real multi-node parallelism to spread the
work across — exactly the "Pandas vs. Spark" tradeoff the roadmap asks
you to internalize at this stage.

## Files

- `generate_clickstream.py` — synthetic browsing events (+ deliberately dirty records)
- `spark_pipeline.py` — read → clean → session → aggregate → partitioned Parquet, in PySpark
- `pandas_comparison.py` — the same logic in Pandas, timed the same way
