# TechMart Data Platform

A single, connected project covering Steps 1–6 of the *Complete Data
Engineering Roadmap for 2026* — instead of six disconnected exercises,
every step reads or extends the **same fictional e-commerce store**
("TechMart"), so the repo reads like one continuous, real project.

| Step | Roadmap topic | What it is here |
|---|---|---|
| 1 | Fundamentals | Clean a messy raw orders export, convert CSV → JSON/Parquet |
| 2 | SQL | Model + query TechMart's OLTP database (customers, products, orders, payments, returns) |
| 3 | Python pipeline | Extract/transform/load a marketplace API integration (paginated, retried, logged) |
| 4 | ETL / pipelines | Watermark-based incremental load of new orders, idempotent and resumable |
| 5 | Data modeling | Star-schema warehouse (facts + dimensions) built from the Step 2 data |
| 6 | Spark | Distributed clickstream processing, benchmarked against Pandas |

Everything downstream of Step 1 keys off the same `customer_id` /
`product_id` values generated once in `data/generate_master_data.py`, so
a customer or product means the same thing whether you're looking at a
SQL join, a warehouse fact table, or a clickstream session.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

PySpark also needs a JVM (Java 11+) on your machine — install a JDK if
`java -version` doesn't already work.

Run everything, in order:

```bash
bash scripts/run_all.sh
```

Or work through it step by step — each `stepN_.../README.md` has the
exact commands and explains what that step is doing and why.

## Repo layout

```
data/                     shared master data + raw messy export generators
db/                       SQLite databases (gitignored, rebuilt by the scripts)
step1_fundamentals/       CSV inspection, cleaning, format conversion
step2_sql_modeling/       OLTP schema, seed data, 6 business-question queries
step3_python_pipeline/    API pipeline + local mock API
step4_incremental_etl/    watermark-based incremental loading
step5_data_warehouse/     star schema + dimensional modeling docs
step6_spark_clickstream/  PySpark session/aggregation job + Pandas comparison
scripts/run_all.sh        runs the whole thing end to end
```

Generated data, databases, and pipeline outputs are gitignored on
purpose — every one of them is fully reproducible (fixed random seeds
throughout), so the repo only tracks the actual engineering: schemas,
pipeline code, and documentation.

## Where the roadmap continues from here

The source email this repo is based on was truncated after the intro to
Step 7 (choosing a cloud platform), so Steps 7–10 (Cloud, Data Quality,
Production Workflows, capstone Projects) aren't built out here yet. If
you can share the rest of that roadmap, this repo can be extended the
same way — e.g. Step 7 could deploy Step 5's warehouse build to a real
cloud data warehouse, Step 8 could add data-quality checks on top of
Step 4's incremental loads, and so on.
