# Step 3 — Python Pipeline

**Roadmap mini-project:** collect data from a public API with pagination,
validate the response, clean/transform records, save raw JSON + processed
Parquet, load into SQL, log errors.

Narratively, this is TechMart's **marketplace integration** — a
third-party sales channel accessed through an API, landing in its own
`marketplace_orders` table (distinct from the direct-channel `orders`
table from Step 2).

A small local Flask app (`mock_api/app.py`) stands in for the real
external API so the whole pipeline runs offline and deterministically —
it requires an API key, paginates, and randomly rate-limits (429) so
`extract.py` has real retry logic to exercise. Point `extract.py` at a
real API later by changing `API_BASE`.

## Run

```bash
# terminal 1
python3 step3_python_pipeline/mock_api/app.py

# terminal 2
python3 step3_python_pipeline/pipeline.py
```

`pipeline.py` orchestrates `extract.py` → `transform.py` → `load.py` and
writes `pipeline.log` alongside console output.

## Files

- `mock_api/app.py` — local stand-in API (auth, pagination, rate limiting)
- `extract.py` — paginated fetch with exponential-backoff retries
- `transform.py` — validation, dedup, type coercion → Parquet
- `load.py` — idempotent load into `db/techmart.db` (`INSERT OR REPLACE`)
- `pipeline.py` — orchestrator with end-to-end logging
