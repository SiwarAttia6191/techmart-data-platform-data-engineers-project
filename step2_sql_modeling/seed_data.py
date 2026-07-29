"""
Step 2 - seed_data.py
----------------------
Builds db/techmart.db: applies schema.sql, loads the shared master
customers/products, then generates orders / order_items / payments /
returns. This is the SAME database that Step 4 (incremental ETL) and
Step 5 (warehouse build) read from later -- it's the OLTP source of
truth for the whole repo.

Usage:
    python3 step2_sql_modeling/seed_data.py
"""
import csv
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

random.seed(99)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "techmart.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

N_ORDERS = 4000
RETURN_REASONS = ["defective", "wrong_item", "no_longer_needed", "better_price_found", "damaged_in_shipping"]
PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "gift_card"]
CHANNELS = ["web", "mobile_app", "marketplace"]


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    customers = load_csv(ROOT / "data" / "master" / "customers.csv")
    products = load_csv(ROOT / "data" / "master" / "products.csv")

    conn.executemany(
        "INSERT INTO customers VALUES (:customer_id, :first_name, :last_name, :email, :country, :city, :signup_date)",
        customers,
    )
    conn.executemany(
        "INSERT INTO products VALUES (:product_id, :product_name, :category, :unit_price, :unit_cost, :active)",
        products,
    )

    customer_ids = [int(c["customer_id"]) for c in customers]
    active_products = [p for p in products if p["active"] == "1"]

    # Skew: 20% of customers place ~60% of orders (realistic repeat-buyer pattern)
    loyal = random.sample(customer_ids, k=int(len(customer_ids) * 0.2))

    order_rows, item_rows, payment_rows, return_rows = [], [], [], []
    order_item_id = 1
    payment_id = 1
    return_id = 1
    start = datetime(2025, 1, 1)

    for order_id in range(1, N_ORDERS + 1):
        cust = random.choice(loyal) if random.random() < 0.6 else random.choice(customer_ids)
        # Capped ~5 weeks before "today" on purpose, so Step 4's incremental
        # pipeline has clean room to land genuinely new orders after this
        # historical backfill without any date-range overlap.
        order_dt = start + timedelta(days=random.randint(0, 540), seconds=random.randint(0, 86399))
        status = random.choices(
            ["completed", "shipped", "pending", "cancelled"], weights=[55, 25, 10, 10]
        )[0]
        channel = random.choice(CHANNELS)
        order_rows.append((order_id, cust, order_dt.isoformat(), status, channel))

        n_items = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
        order_total = 0.0
        for _ in range(n_items):
            product = random.choice(active_products)
            qty = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
            price = float(product["unit_price"])
            item_rows.append((order_item_id, order_id, int(product["product_id"]), qty, price))
            order_total += qty * price

            # ~4% of items get returned, only if the order wasn't cancelled
            if status != "cancelled" and random.random() < 0.04:
                return_dt = order_dt + timedelta(days=random.randint(2, 21))
                return_rows.append(
                    (return_id, order_item_id, return_dt.isoformat(), random.choice(RETURN_REASONS))
                )
                return_id += 1
            order_item_id += 1

        if status != "pending":
            pay_status = "refunded" if status == "cancelled" else random.choices(
                ["paid", "failed"], weights=[97, 3]
            )[0]
            payment_rows.append(
                (
                    payment_id,
                    order_id,
                    (order_dt + timedelta(minutes=random.randint(1, 90))).isoformat(),
                    round(order_total, 2),
                    random.choice(PAYMENT_METHODS),
                    pay_status,
                )
            )
            payment_id += 1

    conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", order_rows)
    conn.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", item_rows)
    conn.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?)", payment_rows)
    conn.executemany("INSERT INTO returns VALUES (?,?,?,?)", return_rows)
    conn.commit()

    counts = {
        "customers": len(customers),
        "products": len(products),
        "orders": len(order_rows),
        "order_items": len(item_rows),
        "payments": len(payment_rows),
        "returns": len(return_rows),
    }
    for table, n in counts.items():
        print(f"{table:<12} {n:>6} rows")
    print(f"\nDatabase ready -> {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
