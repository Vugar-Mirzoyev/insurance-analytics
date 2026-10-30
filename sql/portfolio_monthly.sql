-- Portfolio KPIs by month.
-- Premium, exposure and claims are counted in the month the policy period started
-- (uw_month). Renewals are counted in the month the period ended (due_month), and
-- only for periods that could renew before the data ends.
--
-- The two halves have different month columns, so each is grouped on its own
-- before the join. Grouping both in one query would pair a period's premium with
-- its own renewal and put them in the wrong month.

WITH written AS (                   -- grain: month the period started
    SELECT uw_month             AS month,
           COUNT(*)             AS policy_years,
           SUM(written_premium) AS written_premium,
           SUM(earned_premium)  AS earned_premium,
           SUM(exposure_years)  AS exposure_years,
           SUM(claim_count)     AS claim_count,
           SUM(claims_cost)     AS claims_cost
    FROM policy_year
    GROUP BY uw_month
),
renewals AS (                       -- grain: month the period ended
    SELECT due_month            AS month,
           COUNT(*)             AS policies_due,
           SUM(renewed)         AS policies_renewed
    FROM policy_year
    WHERE renewal_due = 1
    GROUP BY due_month
),
months AS (
    SELECT month FROM written
    UNION
    SELECT month FROM renewals
)
SELECT
    m.month,
    w.policy_years,
    ROUND(w.written_premium, 2)                             AS written_premium,
    ROUND(w.earned_premium, 2)                              AS earned_premium,
    ROUND(w.exposure_years, 2)                              AS exposure_years,
    w.claim_count,
    ROUND(w.claims_cost, 2)                                 AS claims_cost,
    ROUND(w.claim_count / w.exposure_years, 4)              AS frequency,
    ROUND(w.claims_cost / NULLIF(w.claim_count, 0), 2)      AS severity,
    ROUND(w.claims_cost / w.written_premium, 4)             AS loss_ratio_written,
    ROUND(w.claims_cost / w.earned_premium, 4)              AS loss_ratio_earned,
    r.policies_due,
    r.policies_renewed,
    ROUND(1.0 * r.policies_renewed / r.policies_due, 4)     AS renewal_rate
FROM months m
LEFT JOIN written  w ON w.month = m.month
LEFT JOIN renewals r ON r.month = m.month
ORDER BY m.month;
