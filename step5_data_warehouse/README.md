# Step 5 — Data Warehouse

**Roadmap mini-project:** design a star schema (FactSales, FactReturns,
DimCustomer, DimProduct, DimDate, DimStore, DimPromotion) for the same
e-commerce data.

See **[dimensional_model.md](dimensional_model.md)** for grain, key, and
SCD-strategy documentation — that's the actual "design deliverable" here,
`build_warehouse.py` just implements it.

## Run

```bash
python3 step5_data_warehouse/build_warehouse.py   # reads db/techmart.db, writes db/warehouse.db
```

## Files

- `warehouse_schema.sql` — the star schema DDL
- `build_warehouse.py` — ETL from the OLTP tables into the star schema
- `dimensional_model.md` — grain / keys / SCD strategy / supported queries

## Try it

```sql
-- Revenue and margin by category and channel
SELECT p.category, s.channel_name, ROUND(SUM(f.extended_price),2) AS revenue
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
JOIN dim_store s ON s.store_key = f.store_key
WHERE f.order_status != 'cancelled'
GROUP BY p.category, s.channel_name
ORDER BY revenue DESC;
```
