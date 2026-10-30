"""Read the Central Bank of Azerbaijan (CBAR) insurance tables into tidy form.

CBAR publishes two Excel tables on https://www.cbar.az/page-189/insurance:
- Table 6.1: premiums written and claims paid by insurer, from January 2016;
- Table 6.2: the same by insurance class, from January 2017.

Both tables are wide (one pair of columns per period) and year-to-date: the
"yanvar-mart" column holds January to March together, not March alone. Values are
in thousand AZN. The readers return one row per entity, year and month with the
year-to-date values; to_monthly() and to_quarterly() turn them into single periods.

A month CBAR did not publish stays in the result with empty values, so it can be
seen and counted (2022 has no January-August column in Table 6.1).
"""

import re

import numpy as np
import pandas as pd

MONTHS_AZ = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avqust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}
METRICS = {"Premiums": "premiums", "Claims Paid": "claims_paid"}

# Table 6.2 rows in sheet order: (code, parent code, is_leaf).
# A parent's premiums are the sum of its leaf rows. "Including" rows that only
# show part of a leaf (rows 33-34, 46, 48 in the sheet) are kept as memo lines:
# they are not leaves, so summing leaves never counts them twice.
CLASS_TREE = [
    ("V", "TOTAL", False),          # voluntary, total
    (None, None, None),             # "o cümlədən:" (including:)
    ("V_LIFE", "V", False),
    ("V_LIFE_ENDOWMENT", "V_LIFE", True),
    ("V_LIFE_DEATH", "V_LIFE", True),
    ("V_LIFE_WORK_CAPACITY", "V_LIFE", True),
    ("V_LIFE_CRITICAL_ILLNESS", "V_LIFE", True),
    ("V_NONLIFE", "V", False),
    ("V_PERSONAL", "V_NONLIFE", False),
    ("V_MEDICAL", "V_PERSONAL", True),
    ("V_TRAVEL", "V_PERSONAL", True),
    ("V_PERSONAL_ACCIDENT", "V_PERSONAL", True),
    ("V_PROPERTY_CLASS", "V_NONLIFE", False),
    ("V_PROPERTY", "V_PROPERTY_CLASS", False),
    ("V_AIRCRAFT", "V_PROPERTY", True),
    ("V_FIRE", "V_PROPERTY", True),
    ("V_MOTOR_KASKO", "V_PROPERTY", True),
    ("V_CARGO", "V_PROPERTY", True),
    ("V_LIVESTOCK", "V_PROPERTY", True),
    ("V_MARINE_HULL", "V_PROPERTY", True),
    ("V_RAILWAY", "V_PROPERTY", True),
    ("V_CROP", "V_PROPERTY", True),
    ("V_OTHER_PROPERTY", "V_PROPERTY", True),
    ("V_FIDELITY", "V_OTHER_PROPERTY", False),
    ("V_COUNTERFEIT", "V_OTHER_PROPERTY", False),
    ("V_LIABILITY", "V_PROPERTY_CLASS", False),
    ("V_AIRCRAFT_LIABILITY", "V_LIABILITY", True),
    ("V_GENERAL_LIABILITY", "V_LIABILITY", True),
    ("V_MOTOR_TPL_VOLUNTARY", "V_LIABILITY", True),
    ("V_PROFESSIONAL", "V_LIABILITY", True),
    ("V_EMPLOYER", "V_LIABILITY", True),
    ("V_CARRIER", "V_LIABILITY", True),
    ("V_MARINE_LIABILITY", "V_LIABILITY", True),
    ("V_RAILWAY_LIABILITY", "V_LIABILITY", True),
    ("V_CONTRACTUAL", "V_LIABILITY", True),
    ("V_CREDIT_CLASS", "V_PROPERTY_CLASS", True),
    ("V_CREDIT", "V_CREDIT_CLASS", False),
    ("V_FINANCIAL", "V_PROPERTY_CLASS", True),
    ("V_BUSINESS_INTERRUPTION", "V_FINANCIAL", False),
    ("C", "TOTAL", False),          # compulsory, total
    (None, None, None),             # "o cümlədən:"
    ("C_LIFE", "C", False),
    ("C_WORK_ACCIDENT", "C_LIFE", True),
    ("C_NONLIFE", "C", False),
    ("C_MOTOR_TPL", "C_NONLIFE", True),
    ("C_REAL_ESTATE", "C_NONLIFE", True),
    ("C_REAL_ESTATE_LIABILITY", "C_NONLIFE", True),
    ("C_PASSENGER_ACCIDENT", "C_NONLIFE", True),
    ("C_OTHER", "C_NONLIFE", True),
    ("TOTAL", None, False),
]


def _period_columns(raw):
    """Map each data column of a CBAR sheet to (year, month, metric).

    The English metric row ("Premiums" / "Claims Paid") is found first; the
    Azerbaijani period row is 3 rows above it and the year row 4 rows above.
    """
    metric_row = next(i for i in range(len(raw))
                      if raw.iloc[i].astype(str).str.strip().eq("Premiums").any())
    years = pd.to_numeric(raw.iloc[metric_row - 4], errors="coerce").ffill()
    periods = raw.iloc[metric_row - 3].ffill()

    columns = {}
    for j, label in raw.iloc[metric_row].items():
        if not isinstance(label, str) or label.strip() not in METRICS:
            continue
        period = str(periods[j]).strip().lower()
        if not period.startswith("yanvar"):
            raise ValueError(f"Column {j}: expected a year-to-date period, got {period!r}")
        month = MONTHS_AZ[period.split("-")[-1].strip()]
        columns[j] = (int(years[j]), month, METRICS[label.strip()])
    return metric_row, columns


def _to_number(value):
    """CBAR writes '-' for no business; blank cells stay empty."""
    if isinstance(value, str):
        return 0.0 if value.strip() == "-" else np.nan
    return float(value) if pd.notna(value) else np.nan


def _melt(raw, rows, columns):
    """Turn the chosen sheet rows into one row per entity, year and month."""
    records = {}
    for i, attrs in rows:
        for j, (year, month, metric) in columns.items():
            key = (i, year, month)
            records.setdefault(key, {**attrs, "year": year, "month": month})
            records[key][metric] = _to_number(raw.iat[i, j])
    wide = pd.DataFrame(list(records.values()))
    return _add_missing_months(wide, list(rows[0][1]))


def _add_missing_months(df, entity_cols):
    """Add a row with empty values for every month CBAR did not publish."""
    last_year = df["year"].max()
    last_month = df.loc[df["year"] == last_year, "month"].max()
    months = pd.DataFrame(
        [(y, m) for y in range(df["year"].min(), last_year + 1) for m in range(1, 13)
         if (y, m) <= (last_year, last_month)],
        columns=["year", "month"],
    )
    entities = df[entity_cols].drop_duplicates()
    grid = entities.merge(months, how="cross")
    full = grid.merge(df, on=entity_cols + ["year", "month"], how="left")
    return full.sort_values(entity_cols + ["year", "month"]).reset_index(drop=True)


def _short_name(name):
    """'“Paşa Sığorta” Açıq Səhmdar Cəmiyyəti' -> 'Paşa Sığorta'."""
    quoted = re.search(r'[“"]([^”"]+)[”"]', name)
    return (quoted.group(1) if quoted else name).strip()


def read_insurers(path):
    """Read Table 6.1 (by insurer).

    Returns:
        (insurers, total): insurers has one row per insurer, year and month with
        columns insurer, name_en, is_life, licence_revoked, year, month,
        premiums, claims_paid (year-to-date, thousand AZN). total holds the
        sheet's own YEKUN (total) row in the same shape, without the insurer columns.
    """
    raw = pd.read_excel(path, header=None)
    metric_row, columns = _period_columns(raw)

    rows, total_row, revoked = [], None, False
    for i in range(metric_row + 1, len(raw)):
        name = raw.iat[i, 1]
        if not isinstance(name, str):
            continue
        name = name.strip()
        if name.startswith("Lisenziyası ləğv"):
            revoked = True
            continue
        if name == "YEKUN":
            total_row = i
            break
        rows.append((i, {
            "insurer": _short_name(name),
            "name_en": str(raw.iat[i, raw.shape[1] - 1]).strip(),
            "is_life": int("Həyat" in name),
            "licence_revoked": int(revoked),
        }))

    insurers = _melt(raw, rows, columns)
    total = _melt(raw, [(total_row, {"entity": "TOTAL"})], columns).drop(columns="entity")
    return insurers, total


def read_classes(path):
    """Read Table 6.2 (by insurance class).

    Returns:
        One row per class line, year and month with columns line_code, parent_code,
        is_leaf, line_name_az, line_name_en, year, month, premiums, claims_paid.
    """
    raw = pd.read_excel(path, header=None)
    metric_row, columns = _period_columns(raw)

    labels = [i for i in range(metric_row + 1, len(raw))
              if isinstance(raw.iat[i, 0], str) and not raw.iat[i, 0].startswith(("Mənbə", "*"))]
    if len(labels) != len(CLASS_TREE):
        raise ValueError(f"Expected {len(CLASS_TREE)} class rows, found {len(labels)}")

    rows = []
    for i, (code, parent, is_leaf) in zip(labels, CLASS_TREE):
        if code is None:
            continue
        rows.append((i, {
            "line_code": code,
            "parent_code": parent or "",
            "is_leaf": int(is_leaf),
            "line_name_az": raw.iat[i, 0].strip(),
            "line_name_en": str(raw.iat[i, raw.shape[1] - 1]).strip(),
        }))
    return _melt(raw, rows, columns)


def published_periods(ytd):
    """(year, month) pairs for which CBAR published a column."""
    has_value = ytd[["premiums", "claims_paid"]].notna().any(axis=1)
    return set(zip(ytd.loc[has_value, "year"], ytd.loc[has_value, "month"]))


def _subtract_previous(df, entity_cols, first_month, step, published):
    """Value minus the entity's value `step` months earlier in the same year.

    An empty earlier value counts as 0 when CBAR published that period (the entity
    had no business yet) and stays empty when the period itself is missing.
    """
    prev = df.groupby(entity_cols + ["year"])[["premiums", "claims_paid"]].shift(1)
    prev_published = [(y, m - step) in published for y, m in zip(df["year"], df["month"])]
    for col in ("premiums", "claims_paid"):
        previous = prev[col].where(prev[col].notna() | ~pd.Series(prev_published, index=df.index), 0.0)
        df[col] = np.where(df["month"] == first_month, df[col], df[col] - previous)
    return df


def to_monthly(ytd, entity_cols):
    """Turn year-to-date values into single-month values.

    January is the January YTD value; any other month is its YTD value minus the
    previous month's. When the previous month was not published, the month cannot
    be separated and stays empty.
    """
    df = ytd.sort_values(entity_cols + ["year", "month"]).copy()
    df = _subtract_previous(df, entity_cols, 1, 1, published_periods(ytd))
    return df.reset_index(drop=True)


def to_quarterly(ytd, entity_cols):
    """Turn year-to-date values into quarters: YTD at the quarter's last month
    minus YTD three months earlier. Works across a missing middle month."""
    published = published_periods(ytd)
    df = ytd[ytd["month"].isin([3, 6, 9, 12])].sort_values(entity_cols + ["year", "month"]).copy()
    df = _subtract_previous(df, entity_cols, 3, 3, published)
    df["quarter"] = df["month"] // 3
    df["period"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)
    return df.drop(columns="month").reset_index(drop=True)
