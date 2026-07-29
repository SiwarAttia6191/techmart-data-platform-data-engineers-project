"""
Step 4 - simulate_new_orders.py
----------------------------------
Stands in for "the business keeps running": appends a fresh batch of
orders (+ order_items + payments) to db/techmart.db with order_date
timestamps at/after 'now', so that each time incremental_pipeline.py
runs afterward, there is genuinely new data past the current watermark.

Usage:
    python3 step4_incremental_etl/simulate_new_orders.py --n 25
"""
import argparse
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "techmart.db"


def main(n: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    max_order_id = cur.execute("SELECT COALESCE(MAX(order_id), 0) FROM orders").fetchone()[0]
    max_item_id = cur.execute("SELECT COALESCE(MAX(order_item_id), 0) FROM order_items").fetchone()[0]
    max_payment_id = cur.execute("SELECT COALESCE(MAX(payment_id), 0) FROM payments").fetchone()[0]
    customer_ids = [r[0] for r in cur.execute("SELECT customer_id FROM customers").fetchall()]
    product_rows = cur.execute("SELECT product_id, unit_price FROM products WHERE active = 1").fetchall()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_orders, new_items, new_payments = [], [], []

    for i in range(1, n + 1):
        order_id = max_order_id + i
        order_dt = now + timedelta(seconds=random.randint(0, 3600))
        status = random.choices(["completed", "shipped", "pending"], weights=[70, 20, 10])[0]
        channel = random.choice(["web", "mobile_app", "marketplace"])
        new_orders.append((order_id, random.choice(customer_ids), order_dt.isoformat(), status, channel))

        item_id = max_item_id + 1
        product_id, price = random.choice(product_rows)
        qty = random.choice([1, 1, 2])
        new_items.append((item_id, order_id, product_id, qty, price))
        max_item_id = item_id

        if status != "pending":
            payment_id = max_payment_id + 1
            new_payments.append(
                (payment_id, order_id, order_dt.isoformat(), round(qty * price, 2), "credit_card", "paid")
            )
            max_payment_id = payment_id

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", new_orders)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", new_items)
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?)", new_payments)
    conn.commit()
    conn.close()

    print(f"Simulated {len(new_orders)} new orders (order_id {max_order_id + 1}..{max_order_id + n}), "
          f"{len(new_items)} items, {len(new_payments)} payments -> {DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25, help="number of new orders to simulate")
    args = parser.parse_args()
    main(args.n)
