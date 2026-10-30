-- Portfolio KPIs by segment: vehicle type, area and sales channel.
-- Only periods that ended before the valuation date are used, so every segment is
-- compared on fully earned years and a segment with more recent business does not
-- look better just because its claims have not happened yet.

WITH completed AS (                 -- grain: policy year, finished periods only
    SELECT *
    FROM policy_year
    WHERE period_end <= '2018-12-31'
),
segments AS (                       -- grain: segment
    SELECT 'vehicle_type' AS dimension,
           CASE type_risk WHEN 1 THEN 'Motorbike' WHEN 2 THEN 'Van'
                          WHEN 3 THEN 'Passenger car' WHEN 4 THEN 'Agricultural'
                          END AS segment,
           written_premium, earned_premium, exposure_years, claim_count, claims_cost
    FROM completed
    UNION ALL
    SELECT 'area', CASE area WHEN 0 THEN 'Rural' ELSE 'Urban' END,
           written_premium, earned_premium, exposure_years, claim_count, claims_cost
    FROM completed
    UNION ALL
    SELECT 'channel', CASE distribution_channel WHEN 0 THEN 'Agent' ELSE 'Broker' END,
           written_premium, earned_premium, exposure_years, claim_count, claims_cost
    FROM completed
)
SELECT
    dimension,
    segment,
    COUNT(*)                                                AS policy_years,
    ROUND(SUM(earned_premium), 2)                           AS earned_premium,
    ROUND(SUM(earned_premium) / SUM(exposure_years), 2)     AS avg_premium,
    ROUND(SUM(claim_count) / SUM(exposure_years), 4)        AS frequency,
    ROUND(SUM(claims_cost) / NULLIF(SUM(claim_count), 0), 2) AS severity,
    ROUND(SUM(claims_cost) / SUM(earned_premium), 4)        AS loss_ratio_earned
FROM segments
GROUP BY dimension, segment
ORDER BY dimension, loss_ratio_earned DESC;
