# TechMart Warehouse — Dimensional Model

Built by `build_warehouse.py` from the OLTP tables in `db/techmart.db`
(Steps 2-4) into `db/warehouse.db`.

## Grain

| Table | Grain (what one row represents) |
|---|---|
| `fact_sales` | **One row per product per order** (i.e. one row per `order_item`). |
| `fact_returns` | **One row per return event** (one product being returned from one order). |

Defining this up front matters: if `fact_sales` were instead grained at
"one row per order," multi-item orders would force choosing a single
product per row and silently corrupt product-level revenue.

## Keys

- **Surrogate keys** (`customer_key`, `sales_key`, `return_key`, ...) are
  warehouse-generated integers, independent of the source system's IDs.
  They exist so `dim_customer` can hold multiple historical versions of
  the same real-world customer (see SCD below) without a key collision.
- **Natural/business keys** (`customer_id`, `product_id`, `order_id`)
  are also kept on the tables so you can always trace a warehouse row
  back to its OLTP source.
- `order_id` on `fact_sales` is a **degenerate dimension** — there's no
  `dim_order` table because an order has no descriptive attributes of
  its own beyond what's already in the fact row and `dim_date`/`dim_customer`.

## Slowly Changing Dimension strategy

| Dimension | Strategy | Why |
|---|---|---|
| `dim_customer` | **Type 2** (`valid_from`/`valid_to`/`is_current`) | Country/city can change after signup, and historical sales should still report against the customer attributes *as they were at the time of the sale*. This build inserts one current version per customer since the OLTP source has no change history yet — see "Maintaining Type 2 incrementally" below for how a production job would extend this. |
| `dim_product` | **Type 1** (overwrite) | TechMart doesn't need to know what a product used to cost for reporting — current price/category is enough, so `product_key = product_id` with no versioning. |
| `dim_date`, `dim_store`, `dim_promotion` | Static / rebuilt in full each run | Small reference dimensions with no meaningful "history" to preserve. |

### Maintaining Type 2 incrementally (design note, not yet implemented)

A production version of `build_warehouse.py` would, on each run:
1. Compare each source customer row to its current `dim_customer` version
   (e.g. hash the tracked columns: `country`, `city`, `email`).
2. If unchanged, do nothing.
3. If changed: set `valid_to = today`, `is_current = 0` on the old
   version, then insert a new row with `valid_from = today`,
   `valid_to = NULL`, `is_current = 1`.
4. Any *new* `fact_sales` rows join to the customer's *current* version
   at load time; historical fact rows keep pointing at whichever
   `customer_key` they were originally loaded against — that's what
   preserves "the attributes as they were at the time of sale."

## `dim_promotion` — an enrichment, not a direct copy

Unlike the other dimensions, promotions don't exist in the Step 2 OLTP
schema. `build_warehouse.py` attaches a small deterministic marketing
calendar to ~15% of orders to demonstrate a very common real pipeline
situation: a fact table needing a dimension that lives in a *different*
system (here, a marketing platform) and has to be joined in during the
warehouse build rather than pulled straight from the OLTP source.

## Expected business queries this model supports

- Revenue / margin by category, store (channel), month, or promotion
- Customer lifetime value and repeat-purchase rate (join `fact_sales` → `dim_customer`)
- Return rate by product / category / reason
- Which promotions actually moved margin, not just volume
- Any of Step 2's six analysis questions, but attributable to a
  channel or promotion, which the flat OLTP schema alone can't do
  without repeating that same join logic in every query
