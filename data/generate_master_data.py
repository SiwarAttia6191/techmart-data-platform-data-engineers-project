"""
generate_master_data.py
------------------------
Generates the ONE shared dataset that every step of the roadmap builds on:
a fictional e-commerce store called "TechMart".

Running this script creates:
  data/master/customers.csv
  data/master/products.csv

Every other step (SQL modeling, the Python pipeline, incremental ETL,
the warehouse, and the Spark clickstream job) reads or extends these
same customer_id / product_id keys, so the whole repo reads as ONE
continuous project instead of six disconnected exercises.

Usage:
    python3 data/generate_master_data.py
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

random.seed(42)
fake = Faker()
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "master"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 500
N_PRODUCTS = 120

CATEGORIES = {
    "Laptops": (450, 2200),
    "Phones": (200, 1500),
    "Audio": (15, 350),
    "Monitors": (100, 900),
    "Accessories": (5, 120),
    "Smart Home": (20, 400),
    "Wearables": (30, 600),
    "Gaming": (40, 1200),
}

COUNTRIES = ["US", "UK", "DE", "ES", "FR", "CA", "IN", "BR", "AU", "NL"]


def generate_customers(n):
    rows = []
    start = datetime(2022, 1, 1)
    end = datetime(2026, 7, 1)
    for i in range(1, n + 1):
        signup = start + timedelta(days=random.randint(0, (end - start).days))
        rows.append(
            {
                "customer_id": i,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "country": random.choice(COUNTRIES),
                "city": fake.city(),
                "signup_date": signup.strftime("%Y-%m-%d"),
            }
        )
    return rows


def generate_products(n):
    rows = []
    for i in range(1, n + 1):
        category = random.choice(list(CATEGORIES.keys()))
        low, high = CATEGORIES[category]
        price = round(random.uniform(low, high), 2)
        cost = round(price * random.uniform(0.45, 0.75), 2)
        rows.append(
            {
                "product_id": i,
                "product_name": f"{category[:-1] if category.endswith('s') else category} {fake.word().capitalize()} {random.choice(['Pro','Lite','X','Max','Plus',''])}".strip(),
                "category": category,
                "unit_price": price,
                "unit_cost": cost,
                "active": 1 if random.random() > 0.05 else 0,
            }
        )
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows):>4} rows -> {path}")


if __name__ == "__main__":
    customers = generate_customers(N_CUSTOMERS)
    products = generate_products(N_PRODUCTS)
    write_csv(customers, OUT_DIR / "customers.csv")
    write_csv(products, OUT_DIR / "products.csv")
