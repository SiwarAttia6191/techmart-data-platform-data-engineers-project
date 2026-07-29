"""
Step 3 - extract.py
---------------------
Pulls every page of marketplace orders from the (mock) API, handling:
  - pagination (follows has_next until exhausted)
  - authentication (X-API-Key header)
  - rate limiting (429 -> exponential backoff retry)
  - transient failures (retry with backoff, then give up and log)

Saves the raw, unmodified API response records as JSON -- this is the
"landing zone" copy you always keep before any transformation, so you
can always replay a bad transform without re-hitting the source.

Usage:
    python3 step3_python_pipeline/extract.py
"""
import json
import logging
import time
from pathlib import Path

import requests

API_BASE = "http://127.0.0.1:5055"
API_KEY = "demo-key-techmart-2026"
OUT_DIR = Path(__file__).resolve().parent / "output" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 0.5

logger = logging.getLogger("extract")


def fetch_page(page: int) -> dict:
    """Fetch one page, retrying on 429 / 5xx with exponential backoff."""
    url = f"{API_BASE}/orders"
    headers = {"X-API-Key": API_KEY}

    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, headers=headers, params={"page": page}, timeout=10)

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(f"Page {page}: rate limited (429). Retry {attempt}/{MAX_RETRIES} in {wait:.1f}s")
            time.sleep(wait)
            continue

        if resp.status_code >= 500:
            wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(f"Page {page}: server error {resp.status_code}. Retry {attempt}/{MAX_RETRIES} in {wait:.1f}s")
            time.sleep(wait)
            continue

        resp.raise_for_status()  # auth errors / anything else -> fail loudly, don't retry

    raise RuntimeError(f"Page {page}: exceeded {MAX_RETRIES} retries")


def extract_all() -> list[dict]:
    all_records = []
    page = 1
    while True:
        data = fetch_page(page)
        all_records.extend(data["results"])
        logger.info(f"Fetched page {page} ({len(data['results'])} records, "
                    f"{len(all_records)}/{data['total_records']} total)")
        if not data["has_next"]:
            break
        page += 1
    return all_records


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    records = extract_all()

    out_path = OUT_DIR / "marketplace_orders_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    logger.info(f"Extracted {len(records)} raw records -> {out_path}")
    return out_path


if __name__ == "__main__":
    main()
