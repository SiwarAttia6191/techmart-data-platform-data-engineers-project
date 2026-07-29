# Step 4 — Incremental ETL

**Roadmap mini-project:** incremental sales pipeline using a watermark,
landing zone, dedup, and retry/failure logging.

Runs against the same `orders` table from Step 2. `simulate_new_orders.py`
stands in for "the business keeps running" between pipeline runs.

## Run

```bash
# first run: full backfill from watermark zero
python3 step4_incremental_etl/incremental_pipeline.py --reset

# re-run immediately: no new data, so it's a safe no-op
python3 step4_incremental_etl/incremental_pipeline.py

# simulate new live orders, then pick them up incrementally
python3 step4_incremental_etl/simulate_new_orders.py --n 25
python3 step4_incremental_etl/incremental_pipeline.py
```

## How it's resumable

The watermark (`state/watermark.json`) only advances **after** a
successful load. If a run crashes mid-load, the watermark hasn't moved,
so the next run safely re-extracts the same batch. On top of that,
`orders_incremental_log` is also deduped against on `order_id` before
loading, so even re-processing an already-landed batch never creates
duplicate rows — two independent layers of idempotency.

## Files

- `watermark.py` — get/set the last-successfully-processed timestamp
- `simulate_new_orders.py` — appends fresh "live" orders to `db/techmart.db`
- `incremental_pipeline.py` — extract (watermark) → land → dedup → load → advance watermark
- `landing/` — timestamped raw Parquet snapshot of every run's extract (audit trail)
