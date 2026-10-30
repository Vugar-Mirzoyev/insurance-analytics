-- Main insurance classes by quarter: premiums, claims paid, payout ratio, share of
-- all premiums and year-over-year growth (values in thousand AZN, from 2017).
--
-- CBAR Table 6.2 lists subtotals and their parts in one column ("Non-life
-- insurance, including: ..."). Summing every line counts the same premium two or
-- three times, so only the lines below are reported; the share uses the grand total.

WITH lines AS (                     -- grain: class line x quarter
    SELECT line_code, line_name_en, year, quarter, period, premiums, claims_paid
    FROM class_quarterly
    WHERE line_code IN ('C_MOTOR_TPL', 'V_MOTOR_KASKO', 'V_MEDICAL', 'V_FIRE',
                        'C_REAL_ESTATE', 'V_TRAVEL', 'V_LIFE', 'C_WORK_ACCIDENT',
                        'V_NONLIFE', 'C_NONLIFE', 'TOTAL')
),
total_q AS (                        -- grain: quarter
    SELECT period, premiums AS total_premiums
    FROM class_quarterly
    WHERE line_code = 'TOTAL'
)
SELECT
    l.line_code,
    l.line_name_en,
    CASE l.line_code
        WHEN 'C_MOTOR_TPL'     THEN 'Motor TPL (C)'
        WHEN 'V_MOTOR_KASKO'   THEN 'KASKO'
        WHEN 'V_MEDICAL'       THEN 'Medical'
        WHEN 'V_FIRE'          THEN 'Fire and perils'
        WHEN 'C_REAL_ESTATE'   THEN 'Real estate (C)'
        WHEN 'V_TRAVEL'        THEN 'Travel'
        WHEN 'V_LIFE'          THEN 'Life'
        WHEN 'C_WORK_ACCIDENT' THEN 'Work accident (C)'
        WHEN 'V_NONLIFE'       THEN 'Non-life'
        WHEN 'C_NONLIFE'       THEN 'Non-life (C)'
        WHEN 'TOTAL'           THEN 'Total'
    END                                                     AS line_label,     -- short chart label, C = compulsory
    l.period, l.year, l.quarter,
    ROUND(l.premiums, 1)                                    AS premiums,
    ROUND(l.claims_paid, 1)                                 AS claims_paid,
    ROUND(l.claims_paid / NULLIF(l.premiums, 0), 4)         AS payout_ratio,
    ROUND(l.premiums / t.total_premiums, 4)                 AS share_of_premiums,
    ROUND(l.premiums / NULLIF(LAG(l.premiums) OVER (
        PARTITION BY l.line_code, l.quarter ORDER BY l.year), 0) - 1, 4) AS premiums_yoy
FROM lines l
JOIN total_q t ON t.period = l.period
ORDER BY l.year, l.quarter, l.line_code;
