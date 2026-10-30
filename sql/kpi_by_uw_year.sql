-- Portfolio KPIs by underwriting year (the year the policy period started).
-- Returns written and earned premium, exposure, claims, frequency, severity and
-- the loss ratio on both the written and the earned basis.
--
-- The written-basis loss ratio divides claims by the full annual premium. For a
-- period that is still running, the premium is all there but most claims have not
-- happened yet, so the ratio looks too good. The earned basis divides by the part
-- of the premium that has been on risk. Neither basis adds claims that have
-- happened but are not reported yet (IBNR), so a young year still looks better
-- than it will end up.

WITH year_totals AS (               -- grain: underwriting year
    SELECT uw_year,
           COUNT(*)             AS policy_years,
           SUM(written_premium) AS written_premium,
           SUM(earned_premium)  AS earned_premium,
           SUM(exposure_years)  AS exposure_years,
           SUM(claim_count)     AS claim_count,
           SUM(claims_cost)     AS claims_cost
    FROM policy_year
    GROUP BY uw_year
)
SELECT
    uw_year,
    policy_years,
    ROUND(written_premium, 2)                           AS written_premium,
    ROUND(earned_premium, 2)                            AS earned_premium,
    ROUND(earned_premium / written_premium, 4)          AS earned_share,
    ROUND(exposure_years, 1)                            AS exposure_years,
    claim_count,
    ROUND(claims_cost, 2)                               AS claims_cost,
    ROUND(claim_count / exposure_years, 4)              AS frequency,
    ROUND(claims_cost / NULLIF(claim_count, 0), 2)      AS severity,
    ROUND(claims_cost / written_premium, 4)             AS loss_ratio_written,
    ROUND(claims_cost / earned_premium, 4)              AS loss_ratio_earned
FROM year_totals
ORDER BY uw_year;
