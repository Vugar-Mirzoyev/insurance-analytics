"""Shared sample files and database for the tests.

The sample files have the same layout as the real ones (CBAR Excel sheets and the
semicolon-separated portfolio CSV), so the loaders are tested too. They carry the
same traps as the real data, so the tests fail if a query handles them wrong.

CBAR Table 6.1 sample (thousand AZN, year-to-date):
- April 2025 is not published, so May 2025 cannot be separated either;
- "Beta Həyat" is a life insurer that starts in February 2025;
- "Qamma Sığorta" has its licence revoked, writes '-' for no business, and is left
  out of the sheet's own total row;
- Alfa's claims YTD goes down in June 2025 (a correction).

Portfolio sample (policy years, valuation date 2018-12-31, last renewal 2018-11-30):
- policy 1: renewed once, then ended without a lapse date;
- policy 2: still running on the valuation date (183 of 365 days earned);
- policy 3: cancelled inside its last period (184 of 365 days on risk);
- policy 4: due on 2018-12-15, after the last renewal date: not yet due;
- policy 5: zero premium (its start date is the last renewal date);
- policy 6: lapse date inside a period that renewed, and before the next period;
- policy 7: the same policy year twice;
- policy 8: missing next renewal date;
- policy 9: contract start after the period start;
- policy 10: claim cost without a claim count, vehicle power 0;
- claim types: one row for an unknown policy, one total that does not add up.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cbar_loader import CLASS_TREE  # noqa: E402
from src.database import InsuranceDB  # noqa: E402

MONTH_LABELS = {1: "yanvar", 2: "yanvar-fevral", 3: "yanvar-mart", 4: "yanvar-aprel",
                5: "yanvar-may", 6: "yanvar-iyun"}
PERIODS = [(2025, 1), (2025, 2), (2025, 3), (2025, 5), (2025, 6)]  # no April

# YTD (premiums, claims) per insurer and period, in PERIODS order. None = blank cell.
INSURERS = {
    "“Alfa Sığorta” Açıq Səhmdar Cəmiyyəti":
        [(100, 40), (210, 90), (330, 150), (560, 260), (700, 250)],
    "“Beta Həyat” Sığorta Şirkəti Açıq Səhmdar Cəmiyyəti":
        [(None, None), (50, 10), (80, 30), (150, 70), (200, 100)],
}
REVOKED = {"“Qamma Sığorta” Açıq Səhmdar Cəmiyyəti":
           [(5, "-"), (9, 2), (9, 3), (9, 3), (9, 4)]}


def _sheet_frame(period_cols, n_rows):
    """Empty grid with the CBAR header rows filled in; returns (frame, first data row)."""
    width = 2 + 2 * len(period_cols) + 1
    raw = pd.DataFrame(np.full((n_rows + 14, width), None, dtype=object))
    for k, (year, month) in enumerate(period_cols):
        j = 2 + 2 * k
        raw.iat[6, j] = year
        raw.iat[7, j] = MONTH_LABELS[month]
        raw.iat[9, j], raw.iat[9, j + 1] = "Sığorta Haqları", "Sığorta Ödənişləri"
        raw.iat[10, j], raw.iat[10, j + 1] = "Premiums", "Claims Paid"
    return raw, 11


def write_insurer_sheet(path):
    raw, row = _sheet_frame(PERIODS, 6)
    total = [[0.0, 0.0] for _ in PERIODS]
    for n, (name, values) in enumerate(INSURERS.items(), start=1):
        raw.iat[row, 0], raw.iat[row, 1], raw.iat[row, -1] = n, name, f"Insurer {n}"
        for k, (p, c) in enumerate(values):
            raw.iat[row, 2 + 2 * k], raw.iat[row, 3 + 2 * k] = p, c
            total[k][0] += p or 0
            total[k][1] += c or 0
        row += 1
    raw.iat[row, 1] = "Lisenziyası ləğv edilmiş sığortaçılar"
    row += 1
    for name, values in REVOKED.items():
        raw.iat[row, 0], raw.iat[row, 1], raw.iat[row, -1] = 3, name, "Revoked insurer"
        for k, (p, c) in enumerate(values):
            raw.iat[row, 2 + 2 * k], raw.iat[row, 3 + 2 * k] = p, c
        row += 1
    raw.iat[row, 1] = "YEKUN"                 # leaves out the revoked insurer
    for k, (p, c) in enumerate(total):
        raw.iat[row, 2 + 2 * k], raw.iat[row, 3 + 2 * k] = p, c
    raw.to_excel(path, header=False, index=False)


def class_values():
    """Premium per class line: every leaf 10, memo lines 1, parents the sum of leaves.

    A memo line is a non-leaf whose parent is a leaf ("including:" detail lines).
    """
    parents = {code: parent for code, parent, _ in CLASS_TREE if code}
    is_leaf = {code: leaf for code, _, leaf in CLASS_TREE if code}
    values = {}
    for code, leaf in is_leaf.items():
        memo = not leaf and is_leaf.get(parents[code], False)
        values[code] = 10.0 if leaf else (1.0 if memo else 0.0)
    for code, leaf in is_leaf.items():         # add every leaf to all its ancestors
        p = parents[code] if leaf else None
        while p:
            values[p] += 10.0
            p = parents[p]
    return values


def write_class_sheet(path, break_line=None):
    periods = [(2025, 1), (2025, 2)]
    raw, row = _sheet_frame(periods, len(CLASS_TREE))
    raw.iat[6, 0] = None
    values = class_values()
    for code, _, _ in CLASS_TREE:
        raw.iat[row, 0] = code or "o cümlədən:"
        raw.iat[row, -1] = code or "including:"
        if code:
            v = values[code] + (5.0 if code == break_line else 0.0)
            for k in range(len(periods)):
                raw.iat[row, 2 + 2 * k] = v * (k + 1)
                raw.iat[row, 3 + 2 * k] = v * (k + 1) / 2
        row += 1
    raw.iat[row, 0] = "Mənbə: test"
    # Table 6.2 has no number/name split: labels are in column 0, so move data left.
    raw = raw.drop(columns=1)
    raw.columns = range(raw.shape[1])
    raw.to_excel(path, header=False, index=False)


PORTFOLIO_COLUMNS = [
    "ID", "Date_start_contract", "Date_last_renewal", "Date_next_renewal", "Date_birth",
    "Date_driving_licence", "Distribution_channel", "Seniority", "Policies_in_force",
    "Max_policies", "Max_products", "Lapse", "Date_lapse", "Payment", "Premium",
    "Cost_claims_year", "N_claims_year", "N_claims_history", "R_Claims_history",
    "Type_risk", "Area", "Second_driver", "Year_matriculation", "Power",
    "Cylinder_capacity", "Value_vehicle", "N_doors", "Type_fuel", "Length", "Weight",
]

# id, start, last renewal, next renewal, lapse, premium, cost, claims, type_risk, power
POLICY_ROWS = [
    (1, "01/06/2016", "01/06/2016", "01/06/2017", "", 100.0, 50.0, 1, 3, 90),
    (1, "01/06/2016", "01/06/2017", "01/06/2018", "", 100.0, 0.0, 0, 3, 90),
    (2, "01/07/2018", "01/07/2018", "01/07/2019", "", 365.0, 100.0, 1, 3, 90),
    (3, "01/03/2017", "01/03/2017", "01/03/2018", "01/09/2017", 200.0, 0.0, 0, 2, 90),
    (4, "15/12/2017", "15/12/2017", "15/12/2018", "", 100.0, 0.0, 0, 1, 90),
    (5, "30/11/2018", "30/11/2018", "30/11/2019", "", 0.0, 0.0, 0, 3, 90),
    (6, "01/02/2016", "01/02/2016", "01/02/2017", "01/05/2016", 150.0, 0.0, 0, 3, 90),
    (6, "01/02/2016", "01/02/2017", "01/02/2018", "01/05/2016", 150.0, 0.0, 0, 3, 90),
    (7, "01/05/2017", "01/05/2017", "01/05/2018", "01/05/2018", 120.0, 0.0, 0, 3, 90),
    (7, "01/05/2017", "01/05/2017", "01/05/2018", "01/05/2018", 120.0, 0.0, 0, 3, 90),
    (8, "01/04/2017", "01/04/2017", "", "01/04/2018", 100.0, 0.0, 0, 3, 90),
    (9, "10/08/2017", "01/08/2017", "01/08/2018", "01/08/2018", 100.0, 0.0, 0, 3, 90),
    (10, "01/01/2017", "01/01/2017", "01/01/2018", "01/01/2018", 100.0, 30.0, 0, 3, 0),
]

CLAIM_TYPE_ROWS = [
    (1, 50.0, 30.0, "theft"),
    (1, 50.0, 20.0, "fire"),
    (2, 100.0, 60.0, "broken windows"),     # parts add up to 60, total says 100
    (99, 10.0, 10.0, "other"),              # no such policy
]


def write_portfolio(directory):
    rows = []
    for pid, start, last, nxt, lapse, prem, cost, n, risk, power in POLICY_ROWS:
        rows.append([pid, start, last, nxt, "01/01/1980", "01/01/2000", pid % 2, 3, 1, 1, 1,
                     int(bool(lapse)), lapse, 0, prem, cost, n, n, 0.0, risk, pid % 2, 0,
                     2010, power, 1400, 15000.0, 5, "P", 4.2, 1200])
    pd.DataFrame(rows, columns=PORTFOLIO_COLUMNS).to_csv(
        os.path.join(directory, "Motor vehicle insurance data.csv"), sep=";", index=False)
    pd.DataFrame(CLAIM_TYPE_ROWS, columns=["ID", "Cost_claims_year", "Cost_claims_by_type",
                                           "Claims_type"]).to_csv(
        os.path.join(directory, "sample type claim.csv"), sep=";", index=False)


@pytest.fixture
def raw_dir(tmp_path):
    """Directory with sample CBAR sheets and portfolio CSVs."""
    cbar = tmp_path / "cbar"
    portfolio = tmp_path / "portfolio"
    cbar.mkdir()
    portfolio.mkdir()
    write_insurer_sheet(cbar / "cbar_6_1_test.xlsx")
    write_class_sheet(cbar / "cbar_6_2_test.xlsx")
    write_portfolio(portfolio)
    return tmp_path


@pytest.fixture
def sample_db(raw_dir, tmp_path):
    """InsuranceDB loaded from the sample files, with the policy_year view."""
    db = InsuranceDB(db_path=str(tmp_path / "test.db"))
    db.load_portfolio(str(raw_dir / "portfolio"))
    db.load_market(str(raw_dir / "cbar"))
    db.create_views()
    yield db
    db.close()
