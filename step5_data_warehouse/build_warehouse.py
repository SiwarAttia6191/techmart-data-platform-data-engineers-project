"""
Step 5 - build_warehouse.py
------------------------------
ETL that reads the OLTP tables built in Steps 2-4 (db/techmart.db) and
populates the star schema defined in warehouse_schema.sql
(db/warehouse.db):

  DimDate, DimCustomer (Type 2), DimProduct (Type 1), DimStore,
  DimPromotion  ->  FactSales, FactReturns

DimPromotion doesn't exist in the OLTP source -- it's enriched here to
demonstrate how a warehouse build often has to attach dimensions that
live in a different system (here: a small deterministic marketing
calendar stand-in). See dimensional_model.md for the full design notes.

Usage:
    python3 step5_data_warehouse/build_warehouse.py
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "db" / "techmart.db"
WAREHOUSE_DB = ROOT / "db" / "warehouse.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "warehouse_schema.sql"

STORE_MAP = {
    "web": ("TechMart Web Storefront", "direct"),
    "mobile_app": ("TechMart Mobile App", "direct"),
    "marketplace": ("Third-Party Marketplace", "third_party"),
}

PROMOTIONS = [
    (1, "SPRING10", "Spring Sale 10%", 10.0),
    (2, "FLASH20", "Flash Sale 20%", 20.0),
    (3, "WELCOME15", "New Customer 15%", 15.0),
]


def build_dim_date(conn, start: date, end: date):
    rows = []
    d = start
    while d <= end:
        rows.append(
            (
                int(d.strftime("%Y%m%d")),
                d.isoformat(),
                d.year,
                (d.month - 1) // 3 + 1,
                d.month,
                d.strftime("%B"),
                d.day,
                d.strftime("%A"),
                1 if d.weekday() >= 5 else 0,
            )
        )
        d += timedelta(days=1)
    conn.executemany("INSERT INTO dim_date VALUES (?,?,?,?,?,?,?,?,?)", rows)


def build_dim_customer(src, conn):
    customers = src.execute("SELECT * FROM customers").fetchall()
    cols = [d[0] for d in src.execute("SELECT * FROM customers LIMIT 1").description]
    rows = []
    for c in customers:
        r = dict(zip(cols, c))
        rows.append(
            (r["customer_id"], r["first_name"], r["last_name"], r["email"],
             r["country"], r["city"], r["signup_date"], r["signup_date"], None, 1)
        )
    conn.executemany(
        """INSERT INTO dim_customer
           (customer_id, first_name, last_name, email, country, city, signup_date, valid_from, valid_to, is_current)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )


def build_dim_product(src, conn):
    products = src.execute("SELECT product_id, product_name, category, unit_price, unit_cost, active FROM products").fetchall()
    conn.executemany("INSERT INTO dim_product VALUES (?,?,?,?,?,?)", products)


def build_dim_store(conn):
    rows = [(i + 1, code, name, ctype) for i, (code, (name, ctype)) in enumerate(STORE_MAP.items())]
    conn.executemany("INSERT INTO dim_store VALUES (?,?,?,?)", rows)
    return {code: key for key, code, *_ in rows}


def build_dim_promotion(conn):
    conn.execute("INSERT INTO dim_promotion VALUES (0, 'NONE', 'No Promotion', 0.0)")
    conn.executemany("INSERT INTO dim_promotion VALUES (?,?,?,?)", PROMOTIONS)


def promotion_for_order(order_id: int) -> int:
    """Deterministic pseudo-random promo assignment (~15% of orders), so
    reruns are reproducible without depending on shared random state."""
    r = random.Random(order_id)
    if r.random() < 0.15:
        return r.choice([1, 2, 3])
    return 0


def build_fact_sales(src, conn, store_key_map, customer_key_map):
    query = """
        SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.quantity, oi.unit_price,
               o.customer_id, o.order_date, o.status, o.channel,
               p.unit_cost
        FROM order_items oi
        JOIN orders o   ON o.order_id = oi.order_id
        JOIN products p ON p.product_id = oi.product_id
    """
    rows = []
    for r in src.execute(query).fetchall():
        (order_item_id, order_id, product_id, qty, unit_price,
         customer_id, order_date, status, channel, unit_cost) = r

        date_key = int(order_date[:10].replace("-", ""))
        customer_key = customer_key_map[customer_id]
        store_key = store_key_map[channel]
        promo_key = promotion_for_order(order_id)
        extended_price = round(qty * unit_price, 2)
        gross_margin = round(extended_price - (qty * unit_cost), 2)

        rows.append(
            (order_id, order_item_id, date_key, customer_key, product_id, store_key, promo_key,
             status, qty, unit_price, extended_price, unit_cost, gross_margin)
        )

    conn.executemany(
        """INSERT INTO fact_sales
           (order_id, order_item_id, date_key, customer_key, product_key, store_key, promotion_key,
            order_status, quantity, unit_price, extended_price, unit_cost, gross_margin)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    return len(rows)


def build_fact_returns(src, conn, customer_key_map):
    query = """
        SELECT r.return_id, r.order_item_id, r.return_date, r.reason,
               oi.product_id, oi.quantity, oi.unit_price, o.customer_id
        FROM returns r
        JOIN order_items oi ON oi.order_item_id = r.order_item_id
        JOIN orders o       ON o.order_id = oi.order_id
    """
    rows = []
    for r in src.execute(query).fetchall():
        return_id, order_item_id, return_date, reason, product_id, qty, unit_price, customer_id = r
        date_key = int(return_date[:10].replace("-", ""))
        customer_key = customer_key_map[customer_id]
        refund_amount = round(qty * unit_price, 2)
        rows.append((return_id, order_item_id, date_key, customer_key, product_id, reason, qty, refund_amount))

    conn.executemany(
        """INSERT INTO fact_returns
           (return_id, order_item_id, date_key, customer_key, product_key, reason, returned_quantity, refund_amount)
           VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    return len(rows)


def main():
    if WAREHOUSE_DB.exists():
        WAREHOUSE_DB.unlink()

    src = sqlite3.connect(SOURCE_DB)
    conn = sqlite3.connect(WAREHOUSE_DB)
    conn.executescript(SCHEMA_PATH.read_text())

    build_dim_date(conn, date(2025, 1, 1), date(2026, 12, 31))
    build_dim_customer(src, conn)
    build_dim_product(src, conn)
    store_key_map = build_dim_store(conn)
    build_dim_promotion(conn)
    conn.commit()

    customer_key_map = {
        row[0]: row[1] for row in conn.execute("SELECT customer_id, customer_key FROM dim_customer WHERE is_current = 1")
    }

    n_sales = build_fact_sales(src, conn, store_key_map, customer_key_map)
    n_returns = build_fact_returns(src, conn, customer_key_map)
    conn.commit()

    print(f"dim_date       {conn.execute('SELECT COUNT(*) FROM dim_date').fetchone()[0]:>6} rows")
    print(f"dim_customer   {conn.execute('SELECT COUNT(*) FROM dim_customer').fetchone()[0]:>6} rows")
    print(f"dim_product    {conn.execute('SELECT COUNT(*) FROM dim_product').fetchone()[0]:>6} rows")
    print(f"dim_store      {conn.execute('SELECT COUNT(*) FROM dim_store').fetchone()[0]:>6} rows")
    print(f"dim_promotion  {conn.execute('SELECT COUNT(*) FROM dim_promotion').fetchone()[0]:>6} rows")
    print(f"fact_sales     {n_sales:>6} rows")
    print(f"fact_returns   {n_returns:>6} rows")
    print(f"\nWarehouse ready -> {WAREHOUSE_DB}")

    src.close()
    conn.close()


if __name__ == "__main__":
    main()
