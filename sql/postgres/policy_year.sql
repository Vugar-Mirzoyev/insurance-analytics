-- PostgreSQL version of sql/policy_year.sql: same definitions, PostgreSQL date
-- arithmetic. See that file for what each column means.
--
-- Two differences in behaviour had to be written out by hand:
-- - LEAST ignores NULL, while SQLite's two-argument MIN returns NULL. A period
--   with no end date must stay without an on-risk end, so NULL is kept explicitly.
-- - Dividing by a zero-day period is an error here and NULL in SQLite; NULLIF
--   keeps the SQLite result.

DROP VIEW IF EXISTS policy_year;

CREATE VIEW policy_year AS
WITH params AS (
    SELECT DATE '2018-12-31' AS valuation_date,
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
           CASE WHEN pe.date_next_renewal IS NULL THEN NULL
                ELSE LEAST(CASE WHEN pe.next_period_start IS NULL
                                 AND pe.date_lapse > pe.date_last_renewal
                                 AND pe.date_lapse < pe.date_next_renewal
                                THEN pe.date_lapse
                                ELSE pe.date_next_renewal END,
                           pa.valuation_date)
           END                                                  AS on_risk_end,
           pa.last_renewal_seen,
           pe.date_next_renewal - pe.date_last_renewal          AS period_days
    FROM periods pe
    CROSS JOIN params pa
)
SELECT
    id,
    date_last_renewal                       AS period_start,
    date_next_renewal                       AS period_end,
    on_risk_end,
    to_char(date_last_renewal, 'YYYY')      AS uw_year,
    to_char(date_last_renewal, 'YYYY-MM')   AS uw_month,
    to_char(date_next_renewal, 'YYYY-MM')   AS due_month,
    type_risk,
    area,
    distribution_channel,
    premium                                 AS written_premium,
    GREATEST(on_risk_end - date_last_renewal, 0)::double precision
        / NULLIF(period_days, 0)            AS exposure_years,
    premium * GREATEST(on_risk_end - date_last_renewal, 0)::double precision
        / NULLIF(period_days, 0)            AS earned_premium,
    n_claims_year                           AS claim_count,
    cost_claims_year                        AS claims_cost,
    CASE WHEN date_next_renewal <= last_renewal_seen THEN 1 ELSE 0 END
                                            AS renewal_due,
    CASE WHEN date_next_renewal <= last_renewal_seen
              AND next_period_start IS NOT NULL THEN 1 ELSE 0 END
                                            AS renewed
FROM on_risk;
