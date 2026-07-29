"""
Step 6 - generate_clickstream.py
------------------------------------
Generates a large synthetic clickstream dataset -- page views, product
views, add-to-carts, and purchases -- tied to the SAME customer_id /
product_id keys used everywhere else in this repo. This is what makes
it TechMart's browsing behavior instead of a generic demo dataset.

Deliberately includes some invalid/messy records (bad timestamps, an
unknown event_type, orphaned product_ids) so the Spark job in
spark_pipeline.py has real cleaning work to do, matching the roadmap's
"remove invalid records" step.

Usage:
    python3 step6_spark_clickstream/generate_clickstream.py --sessions 40000
"""
import argparse
import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(2026)

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = Path(__file__).resolve().parent / "clickstream_raw.csv"

EVENT_FLOW = ["page_view", "view_product", "add_to_cart", "purchase"]
DEVICE_TYPES = ["desktop", "mobile", "tablet"]


def load_ids():
    import csv as _csv
    with open(ROOT / "data" / "master" / "customers.csv", newline="", encoding="utf-8") as f:
        customer_ids = [row["customer_id"] for row in _csv.DictReader(f)]
    with open(ROOT / "data" / "master" / "products.csv", newline="", encoding="utf-8") as f:
        product_ids = [row["product_id"] for row in _csv.DictReader(f)]
    return customer_ids, product_ids


def generate_session(session_id, customer_ids, product_ids, start_dt, writer):
    is_known_customer = random.random() > 0.35  # ~35% of sessions are anonymous browsing
    customer_id = random.choice(customer_ids) if is_known_customer else ""
    device = random.choice(DEVICE_TYPES)

    # Each session walks forward through the funnel with some drop-off at each stage
    t = start_dt
    depth = 1
    if random.random() < 0.75:
        depth = 2
    if depth == 2 and random.random() < 0.45:
        depth = 3
    if depth == 3 and random.random() < 0.30:
        depth = 4

    product_id = random.choice(product_ids)
    n_events_this_session = random.randint(1, 3) if depth == 1 else 1

    for stage in range(depth):
        event_type = EVENT_FLOW[stage]
        for _ in range(n_events_this_session if stage == 0 else 1):
            t += timedelta(seconds=random.randint(5, 240))
            row = {
                "event_id": str(uuid.uuid4()),
                "session_id": session_id,
                "customer_id": customer_id,
                "event_type": event_type,
                "product_id": product_id if event_type != "page_view" else "",
                "event_timestamp": t.strftime("%Y-%m-%dT%H:%M:%S"),
                "device_type": device,
            }
            writer.writerow(row)
    return t


def inject_dirty_records(writer, product_ids, n=400):
    """A handful of deliberately broken rows: bad timestamp, unknown event
    type, and an orphaned product_id not in the catalog."""
    for i in range(n):
        kind = i % 3
        row = {
            "event_id": str(uuid.uuid4()),
            "session_id": f"dirty-{i}",
            "customer_id": "",
            "event_type": "view_product",
            "product_id": random.choice(product_ids),
            "event_timestamp": "2026-13-45T99:99:99",  # invalid
            "device_type": "desktop",
        }
        if kind == 1:
            row["event_type"] = "click_banner_ad_unknown_type"
            row["event_timestamp"] = "2026-03-01T10:00:00"
        elif kind == 2:
            row["product_id"] = "99999"  # doesn't exist in the product catalog
            row["event_timestamp"] = "2026-03-01T10:00:00"
        writer.writerow(row)


def main(n_sessions: int):
    customer_ids, product_ids = load_ids()
    start = datetime(2026, 1, 1)
    fieldnames = ["event_id", "session_id", "customer_id", "event_type", "product_id", "event_timestamp", "device_type"]

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(n_sessions):
            session_id = f"sess-{i:07d}"
            session_start = start + timedelta(
                days=random.randint(0, 209), seconds=random.randint(0, 86399)
            )
            generate_session(session_id, customer_ids, product_ids, session_start, writer)

        inject_dirty_records(writer, product_ids)

    print(f"Wrote clickstream for {n_sessions} sessions (+ 400 dirty records) -> {OUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=40000)
    args = parser.parse_args()
    main(args.sessions)
