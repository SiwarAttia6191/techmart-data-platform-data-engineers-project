-- Step 2 - SQL project: answers to the business questions from the roadmap.
-- Run interactively with `sqlite3 db/techmart.db < step2_sql_modeling/analysis_queries.sql`
-- or via run_analysis.py for formatted output.

-- Q1: What is the monthly revenue?
-- (revenue = paid payments only, avoids counting failed/refunded)
SELECT
    strftime('%Y-%m', payment_date) AS month,
    ROUND(SUM(amount), 2)           AS revenue
FROM payments
WHERE status = 'paid'
GROUP BY month
ORDER BY month;


-- Q2: Who are the highest-value customers?
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    ROUND(SUM(p.amount), 2)            AS lifetime_value
FROM payments p
JOIN orders o    ON o.order_id = p.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE p.status = 'paid'
GROUP BY c.customer_id
ORDER BY lifetime_value DESC
LIMIT 10;


-- Q3: Which products are frequently returned?
-- (rate = returns / units sold, not just raw return count, so low-volume
--  products with 1 return don't outrank high-volume ones misleadingly)
SELECT
    pr.product_id,
    pr.product_name,
    COUNT(DISTINCT r.return_id)                          AS total_returns,
    SUM(oi.quantity)                                      AS units_sold,
    ROUND(100.0 * COUNT(DISTINCT r.return_id) / SUM(oi.quantity), 2) AS return_rate_pct
FROM order_items oi
JOIN products pr   ON pr.product_id = oi.product_id
LEFT JOIN returns r ON r.order_item_id = oi.order_item_id
GROUP BY pr.product_id
HAVING total_returns > 0
ORDER BY return_rate_pct DESC
LIMIT 10;


-- Q4: Which categories have declining sales?
-- Compares the most recent full month vs. the prior month per category.
WITH monthly_category_sales AS (
    SELECT
        pr.category,
        strftime('%Y-%m', o.order_date) AS month,
        SUM(oi.quantity * oi.unit_price) AS revenue
    FROM order_items oi
    JOIN orders o     ON o.order_id = oi.order_id
    JOIN products pr  ON pr.product_id = oi.product_id
    WHERE o.status != 'cancelled'
    GROUP BY pr.category, month
),
ranked AS (
    SELECT
        category, month, revenue,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY month DESC) AS rn
    FROM monthly_category_sales
)
SELECT
    curr.category,
    prev.month  AS prior_month,
    prev.revenue AS prior_revenue,
    curr.month  AS latest_month,
    curr.revenue AS latest_revenue,
    ROUND(100.0 * (curr.revenue - prev.revenue) / prev.revenue, 1) AS pct_change
FROM ranked curr
JOIN ranked prev ON prev.category = curr.category AND prev.rn = curr.rn + 1
WHERE curr.rn = 1 AND curr.revenue < prev.revenue
ORDER BY pct_change ASC;


-- Q5: What percentage of revenue comes from repeat customers?
-- (repeat customer = has 2+ orders with a paid payment)
WITH paid_orders AS (
    SELECT o.customer_id, p.amount
    FROM payments p
    JOIN orders o ON o.order_id = p.order_id
    WHERE p.status = 'paid'
),
customer_order_counts AS (
    SELECT customer_id, COUNT(*) AS n_orders, SUM(amount) AS cust_revenue
    FROM paid_orders
    GROUP BY customer_id
)
SELECT
    ROUND(100.0 * SUM(CASE WHEN n_orders >= 2 THEN cust_revenue ELSE 0 END)
          / SUM(cust_revenue), 2) AS pct_revenue_from_repeat_customers
FROM customer_order_counts;


-- Q6: Which customers have not purchased recently?
-- ("recently" = within the last 90 days relative to the most recent order in the data)
WITH last_order_date AS (SELECT MAX(order_date) AS max_date FROM orders)
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    MAX(o.order_date)                   AS last_order,
    CAST(julianday((SELECT max_date FROM last_order_date)) - julianday(MAX(o.order_date)) AS INT) AS days_since_last_order
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id
HAVING days_since_last_order > 90
ORDER BY days_since_last_order DESC
LIMIT 15;
