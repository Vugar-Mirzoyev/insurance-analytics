-- Insurers by quarter: premiums, claims paid, payout ratio, market share and
-- year-over-year growth (values in thousand AZN).
--
-- Life insurers (PAŞA Həyat, Atəşgah Həyat, ...) sell savings products whose
-- maturity payments count as claims paid, so their payout ratio means something
-- else. Each insurer therefore also gets a share of its own segment: PAŞA Sığorta
-- is compared with the other non-life insurers, not with PAŞA Həyat.

WITH insurer_q AS (                 -- grain: insurer x quarter
    SELECT insurer, is_life, licence_revoked, year, quarter, period,
           premiums, claims_paid
    FROM insurer_quarterly
    WHERE premiums IS NOT NULL
),
market_q AS (                       -- grain: quarter
    SELECT period, SUM(premiums) AS market_premiums
    FROM insurer_q
    GROUP BY period
),
segment_q AS (                      -- grain: segment (life / non-life) x quarter
    SELECT period, is_life, SUM(premiums) AS segment_premiums
    FROM insurer_q
    GROUP BY period, is_life
)
SELECT
    i.insurer,
    CASE i.is_life WHEN 1 THEN 'Life' ELSE 'Non-life' END   AS segment,
    i.licence_revoked,
    i.period, i.year, i.quarter,
    ROUND(i.premiums, 1)                                    AS premiums,
    ROUND(i.claims_paid, 1)                                 AS claims_paid,
    ROUND(i.claims_paid / NULLIF(i.premiums, 0), 4)         AS payout_ratio,
    ROUND(i.premiums / m.market_premiums, 4)                AS market_share,
    ROUND(i.premiums / s.segment_premiums, 4)               AS segment_share,
    ROUND(i.premiums / NULLIF(LAG(i.premiums) OVER (
        PARTITION BY i.insurer, i.quarter ORDER BY i.year), 0) - 1, 4) AS premiums_yoy
FROM insurer_q i
JOIN market_q  m ON m.period = i.period
JOIN segment_q s ON s.period = i.period AND s.is_life = i.is_life
ORDER BY i.year, i.quarter, i.premiums DESC;
