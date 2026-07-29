"""
Mock marketplace API
----------------------
Simulates a real third-party API TechMart integrates with (e.g. selling
through an external marketplace). It deliberately behaves like a real,
slightly annoying external API so extract.py has to handle:
  - API-key auth
  - pagination
  - random 429 rate-limiting
  - occasional 500s

Run:
    python3 step3_python_pipeline/mock_api/app.py
Serves on http://127.0.0.1:5055
"""
import random
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
random.seed(123)

API_KEY = "demo-key-techmart-2026"
PAGE_SIZE = 50

# Generate a fixed pool of "marketplace order" records once at startup
CATEGORIES = ["Laptops", "Phones", "Audio", "Monitors", "Accessories", "Smart Home", "Wearables", "Gaming"]


def _generate_records(n=537):
    records = []
    for i in range(1, n + 1):
        records.append(
            {
                "marketplace_order_id": f"MKT-{10000 + i}",
                "customer_email": f"buyer{i}@marketplace-example.com",
                "product_sku": f"SKU-{random.randint(1, 120)}",
                "quantity": random.choice([1, 1, 2, 3]),
                "order_ts": f"2026-{random.randint(1,7):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:00:00Z",
                "amount_usd": round(random.uniform(15, 1800), 2),
            }
        )
    return records


ALL_RECORDS = _generate_records()


@app.route("/orders")
def get_orders():
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    # ~8% chance of simulated rate limiting, to force extract.py to retry
    if random.random() < 0.08:
        return jsonify({"error": "rate_limited"}), 429

    page = int(request.args.get("page", 1))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_records = ALL_RECORDS[start:end]

    return jsonify(
        {
            "page": page,
            "page_size": PAGE_SIZE,
            "total_records": len(ALL_RECORDS),
            "has_next": end < len(ALL_RECORDS),
            "results": page_records,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055)
