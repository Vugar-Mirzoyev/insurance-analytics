"""Unit tests for reading the CBAR tables and turning year-to-date into periods."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cbar_loader import CLASS_TREE, read_classes, read_insurers, to_monthly, to_quarterly


@pytest.fixture
def insurers(raw_dir):
    ins, total = read_insurers(str(raw_dir / "cbar" / "cbar_6_1_test.xlsx"))
    return ins, total


def value(df, insurer, month, col="premiums"):
    return df.loc[(df["insurer"] == insurer) & (df["month"] == month), col].iloc[0]


class TestReadInsurers:
    """Tests for read_insurers."""

    def test_names_and_flags(self, insurers):
        """Verify short names, the life flag and the licence-revoked section."""
        ins, _ = insurers
        flags = ins.drop_duplicates("insurer").set_index("insurer")
        assert set(flags.index) == {"Alfa Sığorta", "Beta Həyat", "Qamma Sığorta"}
        assert flags.loc["Beta Həyat", "is_life"] == 1
        assert flags.loc["Alfa Sığorta", "is_life"] == 0
        assert flags.loc["Qamma Sığorta", "licence_revoked"] == 1

    def test_missing_month_is_kept_empty(self, insurers):
        """Verify an unpublished month is a row with empty values, not a gap."""
        ins, total = insurers
        assert sorted(ins["month"].unique()) == [1, 2, 3, 4, 5, 6]
        assert pd.isna(value(ins, "Alfa Sığorta", 4))
        assert total.loc[total["month"] == 4, "premiums"].isna().all()

    def test_dash_means_zero(self, insurers):
        """Verify '-' (no business) is read as 0 and a blank cell as empty."""
        ins, _ = insurers
        assert value(ins, "Qamma Sığorta", 1, "claims_paid") == 0
        assert pd.isna(value(ins, "Beta Həyat", 1))


class TestToMonthly:
    """Tests for to_monthly."""

    def test_differences_of_ytd(self, insurers):
        """Verify January is its YTD value and later months are differences."""
        monthly = to_monthly(insurers[0], ["insurer"])
        assert value(monthly, "Alfa Sığorta", 1) == 100
        assert value(monthly, "Alfa Sığorta", 2) == 110
        assert value(monthly, "Alfa Sığorta", 3) == 120

    def test_month_after_a_missing_month_stays_empty(self, insurers):
        """Verify May cannot be separated when April was not published."""
        monthly = to_monthly(insurers[0], ["insurer"])
        assert pd.isna(value(monthly, "Alfa Sığorta", 4))
        assert pd.isna(value(monthly, "Alfa Sığorta", 5))
        assert value(monthly, "Alfa Sığorta", 6) == 140

    def test_new_insurer_counts_from_zero(self, insurers):
        """Verify an insurer with no January business keeps its February premiums."""
        monthly = to_monthly(insurers[0], ["insurer"])
        assert value(monthly, "Beta Həyat", 2) == 50

    def test_ytd_correction_gives_negative_month(self, insurers):
        """Verify a falling YTD value shows up as a negative month."""
        monthly = to_monthly(insurers[0], ["insurer"])
        assert value(monthly, "Alfa Sığorta", 6, "claims_paid") == -10


class TestToQuarterly:
    """Tests for to_quarterly."""

    def test_quarters_across_missing_month(self, insurers):
        """Verify Q2 = June YTD - March YTD even though April is missing."""
        q = to_quarterly(insurers[0], ["insurer"]).set_index(["insurer", "period"])
        assert q.loc[("Alfa Sığorta", "2025-Q1"), "premiums"] == 330
        assert q.loc[("Alfa Sığorta", "2025-Q2"), "premiums"] == 370
        assert q.loc[("Alfa Sığorta", "2025-Q2"), "claims_paid"] == 100


class TestReadClasses:
    """Tests for read_classes."""

    def test_tree_codes_and_leaves(self, raw_dir):
        """Verify every class line gets its code and the leaves add up to the total."""
        classes = read_classes(str(raw_dir / "cbar" / "cbar_6_2_test.xlsx"))
        jan = classes[classes["month"] == 1].set_index("line_code")
        assert len(jan) == len([c for c, _, _ in CLASS_TREE if c])
        leaves = jan[jan["is_leaf"] == 1]["premiums"].sum()
        assert leaves == pytest.approx(jan.loc["TOTAL", "premiums"])
