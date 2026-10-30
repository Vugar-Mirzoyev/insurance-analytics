-- Policy-year view: one row per policy (id) and annual period (date_last_renewal).
-- Every portfolio query builds on this view, so exposure, earned premium and
-- renewal are defined in one place.
--
-- Valuation date: the data ends on 2018-12-31. A period still running on that day
--   is only partly earned: its premium is written in full, but only the elapsed
--   part has been exposed to claims.
-- On-risk end: the next renewal date, the lapse date when the policy was cancelled
--   during its last period, or the valuation date, whichever comes first. A lapse
--   date is ignored when the policy renewed afterwards or when it falls before the
--   period started; both are data errors counted in data_quality.py.
-- Earned premium: written premium x share of the period on risk (pro rata; this
--   assumes the premium of a cancelled policy is refunded pro rata).
-- Renewal due: the period ended on or before the last renewal date in the data
--   (2018-11-30). A policy due later has not had the chance to renew, so it is
--   neither renewed nor lost.

DROP VIEW IF EXISTS policy_year;

CREATE VIEW policy_year AS
WITH params AS (
    SELECT '2018-12-31' AS valuation_date,
           (SELECT MAX(date_last_renewal) FROM policy_years) AS last_renewal_seen
),
periods AS (
    SELECT p.*,
           LEAD(p.date_last_renewal) OVER (
               PARTITION BY p.id ORDER BY p.date_last_renewal) AS next_period_start
    FROM policy_years p
),
on_risk AS (
    SELECT pe.*,
           MIN(CASE WHEN pe.next_period_start IS NULL
                     AND pe.date_lapse > pe.date_last_renewal
                     AND pe.date_lapse < pe.date_next_renewal
                    THEN pe.date_lapse
                    ELSE pe.date_next_renewal END,
               pa.valuation_date)   AS on_risk_end,
           pa.last_renewal_seen,
           julianday(pe.date_next_renewal) - julianday(pe.date_last_renewal) AS period_days
    FROM periods pe
    CROSS JOIN params pa
)
SELECT
    id,
    date_last_renewal                       AS period_start,
    date_next_renewal                       AS period_end,
    on_risk_end,
    strftime('%Y', date_last_renewal)       AS uw_year,
    strftime('%Y-%m', date_last_renewal)    AS uw_month,
    strftime('%Y-%m', date_next_renewal)    AS due_month,
    type_risk,
    area,
    distribution_channel,
    premium                                 AS written_premium,
    MAX(julianday(on_risk_end) - julianday(date_last_renewal), 0) / period_days
                                            AS exposure_years,
    premium * MAX(julianday(on_risk_end) - julianday(date_last_renewal), 0) / period_days
                                            AS earned_premium,
    n_claims_year                           AS claim_count,
    cost_claims_year                        AS claims_cost,
    CASE WHEN date_next_renewal <= last_renewal_seen THEN 1 ELSE 0 END
                                            AS renewal_due,
    CASE WHEN date_next_renewal <= last_renewal_seen
              AND next_period_start IS NOT NULL THEN 1 ELSE 0 END
                                            AS renewed
FROM on_risk;
