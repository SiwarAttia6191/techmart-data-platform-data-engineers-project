-- Step 2 - SQL project: TechMart OLTP schema
-- customers, products, orders, order_items, payments
-- SQLite dialect (portable to Postgres/MySQL with minor type tweaks)

DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    country       TEXT NOT NULL,
    city          TEXT,
    signup_date   DATE NOT NULL
);

CREATE TABLE products (
    product_id    INTEGER PRIMARY KEY,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    unit_price    NUMERIC(10, 2) NOT NULL,
    unit_cost     NUMERIC(10, 2) NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date    TEXT NOT NULL,          -- ISO 8601 timestamp
    status        TEXT NOT NULL CHECK (status IN ('pending','completed','shipped','cancelled')),
    channel       TEXT NOT NULL
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10, 2) NOT NULL   -- price at time of sale (can differ from products.unit_price)
);

CREATE TABLE payments (
    payment_id    INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    payment_date  TEXT NOT NULL,
    amount        NUMERIC(10, 2) NOT NULL,
    method        TEXT NOT NULL CHECK (method IN ('credit_card','paypal','bank_transfer','gift_card')),
    status        TEXT NOT NULL CHECK (status IN ('paid','failed','refunded'))
);

CREATE TABLE returns (
    return_id      INTEGER PRIMARY KEY,
    order_item_id  INTEGER NOT NULL REFERENCES order_items(order_item_id),
    return_date    TEXT NOT NULL,
    reason         TEXT NOT NULL
);

-- Helpful indexes for the analytical queries in analysis_queries.sql
CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_orders_date       ON orders(order_date);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_prod  ON order_items(product_id);
CREATE INDEX idx_payments_order    ON payments(order_id);
CREATE INDEX idx_returns_item      ON returns(order_item_id);
