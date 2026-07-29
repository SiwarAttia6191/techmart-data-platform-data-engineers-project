"""
generate_raw_export.py
-----------------------
Simulates the messy, denormalized CSV a data engineer would actually
receive on day one -- a flat export from TechMart's order system,
BEFORE anyone has modeled it properly. This is the intentionally dirty
input for Step 1 (Fundamentals): missing values, inconsistent date
formats, duplicate rows, and mixed types in numeric columns.

Usage:
    python3 data/generate_raw_export.py
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(7)

BASE_DIR = Path(__file__).resolve().parent
MASTER_DIR = BASE_DIR / "master"
OUT_PATH = BASE_DIR / "raw" / "raw_orders_export.csv"

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d"]


def load_ids(path, id_col):
    with open(path, newline="", encoding="utf-8") as f:
        return [row[id_col] for row in csv.DictReader(f)]


def messy_date(dt):
    fmt = random.choice(DATE_FORMATS)
    return dt.strftime(fmt)


def main():
    customer_ids = load_ids(MASTER_DIR / "customers.csv", "customer_id")
    product_ids = load_ids(MASTER_DIR / "products.csv", "product_id")

    rows = []
    start = datetime(2025, 1, 1)
    for i in range(1, 2001):
        order_date = start + timedelta(days=random.randint(0, 545), hours=random.randint(0, 23))
        qty = random.choice([1, 1, 1, 2, 2, 3, "2", None])  # mixed types on purpose
        row = {
            "order_row_id": i,
            "customer_id": random.choice(customer_ids) if random.random() > 0.01 else "",
            "product_id": random.choice(product_ids),
            "order_date": messy_date(order_date) if random.random() > 0.03 else "",
            "quantity": qty,
            "status": random.choice(["completed", "COMPLETED", "shipped", "cancelled", "pending", ""]),
            "channel": random.choice(["web", "mobile_app", "web", "marketplace", None]),
        }
        rows.append(row)

    # Inject ~2% exact duplicate rows, a very common real-world artifact
    dupes = random.sample(rows, k=int(len(rows) * 0.02))
    rows.extend(dupes)
    random.shuffle(rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows (incl. {len(dupes)} intentional dupes) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
