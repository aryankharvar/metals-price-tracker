-- views.sql
-- Reusable views wrapping the analysis logic. Created once; SQLite recomputes
-- the underlying window functions live every time the view is queried, so
-- these always reflect the latest data in metal_prices — no refresh needed.

CREATE VIEW IF NOT EXISTS latest_prices AS
SELECT metal_name, ticker, price_date, close_price
FROM metal_prices mp
WHERE price_date = (
    SELECT MAX(price_date) FROM metal_prices WHERE ticker = mp.ticker
);

CREATE VIEW IF NOT EXISTS daily_pct_change AS
SELECT
    metal_name,
    ticker,
    price_date,
    close_price,
    LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date) AS prev_close,
    ROUND(
        (close_price - LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date))
        / LAG(close_price) OVER (PARTITION BY ticker ORDER BY price_date) * 100, 2
    ) AS pct_change
FROM metal_prices;

CREATE VIEW IF NOT EXISTS rolling_averages AS
SELECT
    metal_name,
    ticker,
    price_date,
    close_price,
    ROUND(AVG(close_price) OVER (
        PARTITION BY ticker ORDER BY price_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 4) AS rolling_7d_avg,
    ROUND(AVG(close_price) OVER (
        PARTITION BY ticker ORDER BY price_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 4) AS rolling_30d_avg
FROM metal_prices;

CREATE VIEW IF NOT EXISTS weekly_volatility AS
WITH weekly_range AS (
    SELECT
        metal_name,
        MAX(close_price) - MIN(close_price) AS price_range,
        MIN(close_price) AS week_low,
        MAX(close_price) AS week_high
    FROM metal_prices
    WHERE price_date >= DATE('now', '-7 days')
    GROUP BY metal_name
)
SELECT
    metal_name,
    week_low,
    week_high,
    price_range,
    RANK() OVER (ORDER BY price_range DESC) AS volatility_rank
FROM weekly_range;
