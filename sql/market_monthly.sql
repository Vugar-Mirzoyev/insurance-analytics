-- Azerbaijan insurance market by month: premiums and claims paid (thousand AZN).
-- Input for the trend, anomaly and forecast checks in src/trends.py.
--
-- CBAR publishes year-to-date figures; insurer_monthly already holds single months.
-- When a year-to-date column is missing (2022: no January-August), the month after
-- it cannot be separated either, so both stay empty here (SUM over only NULLs is NULL).

WITH market AS (                    -- grain: month
    SELECT year, month,
           SUM(premiums)    AS premiums,
           SUM(claims_paid) AS claims_paid
    FROM insurer_monthly
    GROUP BY year, month
)
SELECT
    printf('%04d-%02d-01', year, month)     AS month_start,
    year, month,
    ROUND(premiums, 1)                      AS premiums,
    ROUND(claims_paid, 1)                   AS claims_paid,
    ROUND(claims_paid / premiums, 4)        AS payout_ratio
FROM market
ORDER BY year, month;
