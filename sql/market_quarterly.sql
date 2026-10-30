-- Azerbaijan insurance market by quarter: premiums, claims paid, payout ratio,
-- quarter-over-quarter and year-over-year change (values in thousand AZN).
--
-- The market is the sum of all insurers in CBAR Table 6.1. The table's own total
-- row leaves out AtaSığorta (licence revoked) up to 2024, so it is not used.
-- Year-over-year takes the previous row of the same quarter (LAG partitioned by
-- quarter). Every quarter from 2016-Q1 is present, so that row is one year earlier.
--
-- Payout ratio = claims paid / premiums written in the same quarter. It is not a
-- loss ratio: the loss ratio needs earned premium and the change in claim reserves.

WITH market AS (                    -- grain: quarter
    SELECT year, quarter, period,
           SUM(premiums)    AS premiums,
           SUM(claims_paid) AS claims_paid
    FROM insurer_quarterly
    GROUP BY year, quarter, period
),
with_prior AS (
    SELECT m.*,
           LAG(premiums)    OVER (ORDER BY year, quarter)                   AS premiums_prev_q,
           LAG(claims_paid) OVER (ORDER BY year, quarter)                   AS claims_prev_q,
           LAG(premiums)    OVER (PARTITION BY quarter ORDER BY year)       AS premiums_prev_y,
           LAG(claims_paid) OVER (PARTITION BY quarter ORDER BY year)       AS claims_prev_y
    FROM market m
)
SELECT
    period, year, quarter,
    ROUND(premiums, 1)                              AS premiums,
    ROUND(claims_paid, 1)                           AS claims_paid,
    ROUND(claims_paid / premiums, 4)                AS payout_ratio,
    ROUND(premiums / premiums_prev_q - 1, 4)        AS premiums_qoq,
    ROUND(premiums / premiums_prev_y - 1, 4)        AS premiums_yoy,
    ROUND(claims_paid / claims_prev_q - 1, 4)       AS claims_qoq,
    ROUND(claims_paid / claims_prev_y - 1, 4)       AS claims_yoy
FROM with_prior
ORDER BY year, quarter;
