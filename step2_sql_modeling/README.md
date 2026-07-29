# Step 2 — SQL

**Roadmap mini-project:** build an e-commerce database (customers, products,
orders, order_items, payments) and answer six specific business questions.

This is the OLTP source of truth for the rest of the repo — Steps 4 and 5
both read from the database built here.

## Run

```bash
python3 step2_sql_modeling/seed_data.py     # builds db/techmart.db
python3 step2_sql_modeling/run_analysis.py  # runs & prints all 6 analysis queries
```

Or explore the raw SQL directly:

```bash
sqlite3 db/techmart.db < step2_sql_modeling/analysis_queries.sql
```

## Files

- `schema.sql` — DDL: customers, products, orders, order_items, payments, returns
- `seed_data.py` — generates realistic seed data (500 customers, 120 products, 4000 orders)
- `analysis_queries.sql` — the six business questions, each with reasoning in comments
- `run_analysis.py` — runs each query and prints a formatted result table

## Note on Q4 (declining categories)

The most recent month in the data is always partial (it's "in progress"),
so it will show as a decline versus a full prior month almost by
definition. Handling partial-period comparisons correctly is a real,
common gotcha worth internalizing early.
