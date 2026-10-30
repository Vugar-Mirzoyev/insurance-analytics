-- Fact table for Power BI: additive portfolio totals by start month and segment.
-- Only sums are stored. Ratios (loss ratio, frequency, severity) are DAX measures
-- that divide the sums, so they stay correct at any level of filtering. An
-- average of stored ratios would weight a 10-policy segment like a 10,000-policy one.

WITH fact AS (                      -- grain: start month x vehicle type x area x channel
    SELECT uw_month || '-01'        AS month_start,
           type_risk, area, distribution_channel,
           COUNT(*)                 AS policy_years,
           SUM(written_premium)     AS written_premium,
           SUM(earned_premium)      AS earned_premium,
           SUM(exposure_years)      AS exposure_years,
           SUM(claim_count)         AS claim_count,
           SUM(claims_cost)         AS claims_cost
    FROM policy_year
    GROUP BY uw_month, type_risk, area, distribution_channel
)
SELECT
    month_start,
    CASE type_risk WHEN 1 THEN 'Motorbike' WHEN 2 THEN 'Van'
                   WHEN 3 THEN 'Passenger car' WHEN 4 THEN 'Agricultural' END AS vehicle_type,
    CASE area WHEN 0 THEN 'Rural' ELSE 'Urban' END                         AS area,
    CASE distribution_channel WHEN 0 THEN 'Agent' ELSE 'Broker' END        AS channel,
    policy_years,
    ROUND(written_premium, 2)   AS written_premium,
    ROUND(earned_premium, 2)    AS earned_premium,
    ROUND(exposure_years, 4)    AS exposure_years,
    claim_count,
    ROUND(claims_cost, 2)       AS claims_cost
FROM fact
ORDER BY month_start, vehicle_type, area, channel;
