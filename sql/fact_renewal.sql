-- Fact table for Power BI: policies due for renewal and renewed, by due month and
-- segment. Only periods that could renew before the data ends are included.

WITH fact AS (                      -- grain: due month x vehicle type x area x channel
    SELECT due_month || '-01'   AS month_start,
           type_risk, area, distribution_channel,
           COUNT(*)             AS policies_due,
           SUM(renewed)         AS policies_renewed
    FROM policy_year
    WHERE renewal_due = 1
    GROUP BY due_month, type_risk, area, distribution_channel
)
SELECT
    month_start,
    CASE type_risk WHEN 1 THEN 'Motorbike' WHEN 2 THEN 'Van'
                   WHEN 3 THEN 'Passenger car' WHEN 4 THEN 'Agricultural' END AS vehicle_type,
    CASE area WHEN 0 THEN 'Rural' ELSE 'Urban' END                         AS area,
    CASE distribution_channel WHEN 0 THEN 'Agent' ELSE 'Broker' END        AS channel,
    policies_due,
    policies_renewed
FROM fact
ORDER BY month_start, vehicle_type, area, channel;
