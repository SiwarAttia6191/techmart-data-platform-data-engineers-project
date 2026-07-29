-- Step 5 - TechMart analytical warehouse (star schema)
-- Populated from db/techmart.db (the OLTP tables from Steps 2-4) by build_warehouse.py.
-- See dimensional_model.md for grain, key, and SCD documentation.

DROP TABLE IF EXISTS fact_returns;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_promotion;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;

-- ---------------------------------------------------------------------
-- DimCustomer -- Type 2 SCD (tracks history). Surrogate key so a fact
-- row always points at the customer version that was true *at the time
-- of the sale*, even if the customer's country/city changes later.
-- ---------------------------------------------------------------------
CREATE TABLE dim_customer (
    customer_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    INTEGER NOT NULL,        -- natural/business key from the OLTP source
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT NOT NULL,
    country        TEXT NOT NULL,
    city           TEXT,
    signup_date    DATE NOT NULL,
    valid_from     TEXT NOT NULL,
    valid_to       TEXT,                    -- NULL = current version
    is_current     INTEGER NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------
-- DimProduct -- Type 1 SCD (overwrite in place). TechMart doesn't need
-- historical price/category tracking for reporting, so the natural key
-- doubles as the surrogate key here.
-- ---------------------------------------------------------------------
CREATE TABLE dim_product (
    product_key    INTEGER PRIMARY KEY,     -- = product_id, Type 1 (no history)
    product_name   TEXT NOT NULL,
    category       TEXT NOT NULL,
    unit_price     NUMERIC(10,2) NOT NULL,
    unit_cost      NUMERIC(10,2) NOT NULL,
    active         INTEGER NOT NULL
);

-- ---------------------------------------------------------------------
-- DimDate -- standard conformed date dimension, one row per calendar day.
-- ---------------------------------------------------------------------
CREATE TABLE dim_date (
    date_key       INTEGER PRIMARY KEY,     -- YYYYMMDD
    full_date      DATE NOT NULL,
    year           INTEGER NOT NULL,
    quarter        INTEGER NOT NULL,
    month          INTEGER NOT NULL,
    month_name     TEXT NOT NULL,
    day_of_month   INTEGER NOT NULL,
    day_of_week    TEXT NOT NULL,
    is_weekend     INTEGER NOT NULL
);

-- ---------------------------------------------------------------------
-- DimStore -- TechMart is online-only, so "store" = sales channel
-- (web storefront / mobile app / marketplace). Degenerate but still a
-- conformed dimension other facts could join to later.
-- ---------------------------------------------------------------------
CREATE TABLE dim_store (
    store_key      INTEGER PRIMARY KEY,
    channel_code   TEXT NOT NULL UNIQUE,
    channel_name   TEXT NOT NULL,
    channel_type   TEXT NOT NULL            -- 'direct' vs 'third_party'
);

-- ---------------------------------------------------------------------
-- DimPromotion -- marketing calendar, not present in the OLTP source;
-- derived/enriched during the warehouse build (see build_warehouse.py).
-- Row 0 is the required "no promotion applied" member.
-- ---------------------------------------------------------------------
CREATE TABLE dim_promotion (
    promotion_key   INTEGER PRIMARY KEY,
    promotion_code  TEXT NOT NULL UNIQUE,
    promotion_name  TEXT NOT NULL,
    discount_pct    NUMERIC(5,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- FactSales -- grain: ONE ROW PER PRODUCT PER ORDER (i.e. one row per
-- order_item). Defining the grain here explicitly, per the roadmap's
-- warning that an unclear grain causes duplicate metrics.
-- ---------------------------------------------------------------------
CREATE TABLE fact_sales (
    sales_key        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id          INTEGER NOT NULL,      -- degenerate dimension (no separate DimOrder)
    order_item_id     INTEGER NOT NULL,
    date_key           INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_key        INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key          INTEGER NOT NULL REFERENCES dim_product(product_key),
    store_key             INTEGER NOT NULL REFERENCES dim_store(store_key),
    promotion_key           INTEGER NOT NULL REFERENCES dim_promotion(promotion_key),
    order_status              TEXT NOT NULL,
    quantity                    INTEGER NOT NULL,
    unit_price                   NUMERIC(10,2) NOT NULL,
    extended_price                 NUMERIC(10,2) NOT NULL,  -- quantity * unit_price
    unit_cost                        NUMERIC(10,2) NOT NULL,
    gross_margin                       NUMERIC(10,2) NOT NULL  -- extended_price - (quantity*unit_cost)
);

-- ---------------------------------------------------------------------
-- FactReturns -- grain: ONE ROW PER RETURN EVENT.
-- ---------------------------------------------------------------------
CREATE TABLE fact_returns (
    return_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id        INTEGER NOT NULL,
    order_item_id      INTEGER NOT NULL,
    date_key             INTEGER NOT NULL REFERENCES dim_date(date_key),  -- return date
    customer_key           INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key              INTEGER NOT NULL REFERENCES dim_product(product_key),
    reason                     TEXT NOT NULL,
    returned_quantity            INTEGER NOT NULL,
    refund_amount                  NUMERIC(10,2) NOT NULL
);

CREATE INDEX idx_fact_sales_date     ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_product  ON fact_sales(product_key);
CREATE INDEX idx_fact_returns_date   ON fact_returns(date_key);
CREATE INDEX idx_fact_returns_product ON fact_returns(product_key);
