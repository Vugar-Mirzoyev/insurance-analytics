"""Data quality checks behind the market tables and the portfolio KPIs.

Each check counts the rows that break an assumption a query could easily make.
A non-zero count is not always an error in the data, but the query has to handle it.

Run from the project root:  python -m src.data_quality
"""

import pandas as pd

CHECKS = [
    # --- CBAR market tables -------------------------------------------------------
    (
        "market",
        "Months missing from the CBAR year-to-date series",
        "SELECT COUNT(*) FROM cbar_total_ytd WHERE premiums IS NULL",
        "Table 6.1 has no January-August 2022 column. August and September 2022 "
        "cannot be separated, so both stay empty by month; Q3 2022 is still exact.",
    ),
    (
        "market",
        "Months where CBAR's total row is not the sum of the insurers",
        """SELECT COUNT(*) FROM cbar_total_ytd t
           JOIN (SELECT year, month, SUM(premiums) AS premiums
                 FROM insurer_ytd GROUP BY year, month) s
             ON s.year = t.year AND s.month = t.month
           WHERE ABS(s.premiums - t.premiums) > 1""",
        "The 6.1 total row leaves out AtaSığorta (licence revoked) up to 2024. The "
        "market is the sum of the insurers, which equals the 6.2 grand total in 113 of "
        "116 months (the other 3 differ by at most 51 thousand AZN).",
    ),
    (
        "market",
        "Insurer-months where a year-to-date value goes down",
        """SELECT COUNT(*) FROM insurer_monthly
           WHERE premiums < -0.01 OR claims_paid < -0.01""",
        "Later corrections make the single-month value negative. Kept as published; "
        "the market total of those months stays positive.",
    ),
    (
        "market",
        "Class subtotals that are not the sum of their parts",
        """SELECT COUNT(*) FROM class_ytd p
           JOIN (SELECT parent_code, year, month, SUM(premiums) AS premiums
                 FROM class_ytd
                 WHERE parent_code <> ''
                   AND line_code NOT IN ('V_FIDELITY', 'V_COUNTERFEIT',
                                         'V_CREDIT', 'V_BUSINESS_INTERRUPTION')
                 GROUP BY parent_code, year, month) c
             ON c.parent_code = p.line_code AND c.year = p.year AND c.month = p.month
           WHERE ABS(c.premiums - p.premiums) > 1""",
        "Must be 0: class shares and the leaf-level sums assume the tree adds up.",
    ),
    # --- Portfolio -----------------------------------------------------------------
    (
        "portfolio",
        "Duplicate policy-year rows",
        """SELECT COUNT(*) - COUNT(DISTINCT id || '|' || date_last_renewal)
           FROM policy_years""",
        "Must be 0: every premium and claim sum assumes one row per policy and year.",
    ),
    (
        "portfolio",
        "Claim-type rows without a matching policy year",
        """SELECT COUNT(*) FROM claim_types c
           WHERE NOT EXISTS (SELECT 1 FROM policy_years p
                             WHERE p.id = c.id
                               AND ABS(p.cost_claims_year - c.cost_claims_year) < 0.01)""",
        "A claim with no policy has no premium or exposure to be measured against.",
    ),
    (
        "portfolio",
        "Policy years with zero or negative premium",
        "SELECT COUNT(*) FROM policy_years WHERE premium IS NULL OR premium <= 0",
        "Would divide by zero in the loss ratio, or make it negative.",
    ),
    (
        "portfolio",
        "Policy years with a missing period date",
        """SELECT COUNT(*) FROM policy_years
           WHERE date_start_contract IS NULL OR date_last_renewal IS NULL
              OR date_next_renewal IS NULL""",
        "Exposure and earned premium cannot be computed without the period dates.",
    ),
    (
        "portfolio",
        "Contracts that start after the period they belong to",
        "SELECT COUNT(*) FROM policy_years WHERE date_start_contract > date_last_renewal",
        "Not used in any metric (the period dates are), but the dates contradict.",
    ),
    (
        "portfolio",
        "Lapse date before the period started",
        "SELECT COUNT(*) FROM policy_years WHERE date_lapse < date_last_renewal",
        "A period cannot follow its own cancellation. The lapse date is ignored, "
        "so the period keeps its full exposure.",
    ),
    (
        "portfolio",
        "Renewed policies with a lapse date inside the period",
        """SELECT COUNT(*) FROM policy_year py
           JOIN policy_years p ON p.id = py.id AND p.date_last_renewal = py.period_start
           WHERE py.renewed = 1
             AND p.date_lapse > p.date_last_renewal AND p.date_lapse < p.date_next_renewal""",
        "The policy renewed, so the lapse date is ignored and exposure is not cut.",
    ),
    (
        "portfolio",
        "Policies that ended without a lapse date",
        """SELECT COUNT(*) FROM policy_year py
           JOIN policy_years p ON p.id = py.id AND p.date_last_renewal = py.period_start
           WHERE py.renewal_due = 1 AND py.renewed = 0 AND p.date_lapse IS NULL""",
        "Not renewed but no lapse recorded. The renewal rate uses the next row, not "
        "the lapse date, so these still count as lost.",
    ),
    (
        "portfolio",
        "Policy years not yet ended on the valuation date",
        "SELECT COUNT(*) FROM policy_years WHERE date_next_renewal > '2018-12-31'",
        "Premium is written in full but only partly earned. The loss ratio of these "
        "years uses earned premium, and is still too low because of late claims.",
    ),
    (
        "portfolio",
        "Policy years due after the last renewal in the data",
        """SELECT COUNT(*) FROM policy_years
           WHERE date_next_renewal > (SELECT MAX(date_last_renewal) FROM policy_years)""",
        "They have not had the chance to renew. Counting them as lost would show a "
        "0% renewal rate for December 2018.",
    ),
    (
        "portfolio",
        "Claim counts and claim costs that disagree",
        """SELECT COUNT(*) FROM policy_years
           WHERE (n_claims_year = 0 AND cost_claims_year > 0)
              OR (n_claims_year > 0 AND cost_claims_year = 0)""",
        "Severity (cost per claim) assumes cost and count describe the same claims.",
    ),
    (
        "portfolio",
        "Claim-type costs that do not add up to the policy-year total",
        """SELECT COUNT(*) FROM (
               SELECT id, cost_claims_year FROM claim_types
               GROUP BY id, cost_claims_year
               HAVING ABS(SUM(cost_claims_by_type) - cost_claims_year) > 0.01)""",
        "The claim-type file is a sample used for the claim mix only; totals always "
        "come from the policy table.",
    ),
    (
        "portfolio",
        "Vehicles with power recorded as 0",
        "SELECT COUNT(*) FROM policy_years WHERE power = 0",
        "0 means unknown, not a vehicle without an engine. Not used in the KPIs.",
    ),
]


def run_checks(db):
    """Run every check against the database behind db.

    Args:
        db: An InsuranceDB (or anything with a query(sql) method).

    Returns:
        DataFrame with columns: area, check, rows, why.
    """
    rows = []
    for area, name, sql, why in CHECKS:
        count = int(db.query(sql).iloc[0, 0])
        rows.append({"area": area, "check": name, "rows": count, "why": why})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from src.database import InsuranceDB

    db = InsuranceDB()
    with pd.option_context("display.max_colwidth", 80, "display.width", 180):
        print(run_checks(db).to_string(index=False))
    db.close()
