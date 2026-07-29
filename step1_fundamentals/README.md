# Step 1 — Fundamentals

**Roadmap mini-project:** download a raw CSV, inspect it, clean it, convert
to JSON + Parquet, document the format differences.

`data/raw/raw_orders_export.csv` stands in for "the messy file you'd
actually receive" — it has missing values, four different date formats,
mixed-type quantities, and duplicate rows on purpose.

## Run

```bash
python3 data/generate_master_data.py      # only needed once, shared by every step
python3 data/generate_raw_export.py       # only needed once
python3 step1_fundamentals/explore_and_convert.py
```

## Output

- `output/orders_clean.{csv,json,parquet}` — the same cleaned data in all three formats
- `output/FORMAT_NOTES.md` — generated file size / tradeoff comparison
