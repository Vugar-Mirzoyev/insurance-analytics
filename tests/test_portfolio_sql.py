"""Unit tests for the policy_year view and the portfolio KPI queries."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def policy_year(db, policy_id):
    return db.query("SELECT * FROM policy_year WHERE id = ? ORDER BY period_start",
                    params=(policy_id,))


class TestPolicyYearView:
    """Tests for exposure, earned premium and renewal in sql/policy_year.sql."""

    def test_running_period_is_partly_earned(self, sample_db):
        """Verify a period running past the valuation date earns only the elapsed days."""
        row = policy_year(sample_db, 2).iloc[0]
        assert row["exposure_years"] == pytest.approx(183 / 365)
        assert row["earned_premium"] == pytest.approx(183.0)
        assert row["written_premium"] == 365.0

    def test_lapse_cuts_exposure_in_last_period(self, sample_db):
        """Verify a cancelled policy is on risk only until its lapse date."""
        row = policy_year(sample_db, 3).iloc[0]
        assert row["on_risk_end"] == "2017-09-01"
        assert row["exposure_years"] == pytest.approx(184 / 365)

    def test_contradicting_lapse_dates_are_ignored(self, sample_db):
        """Verify a lapse inside a renewed period, or before a period, keeps full exposure."""
        rows = policy_year(sample_db, 6)
        assert rows["exposure_years"].tolist() == pytest.approx([1.0, 1.0])

    def test_renewal_only_for_periods_that_could_renew(self, sample_db):
        """Verify a policy due after the last renewal date is neither renewed nor lost."""
        assert policy_year(sample_db, 4).iloc[0]["renewal_due"] == 0
        first, second = policy_year(sample_db, 1).itertuples()
        assert (first.renewal_due, first.renewed) == (1, 1)
        assert (second.renewal_due, second.renewed) == (1, 0)


class TestKpiQueries:
    """Tests for the KPI files in sql/."""

    def test_written_vs_earned_loss_ratio(self, sample_db):
        """Verify the young year's loss ratio is higher on the earned basis."""
        years = sample_db.run_file("kpi_by_uw_year").set_index("uw_year")
        y2018 = years.loc["2018"]
        assert y2018["loss_ratio_written"] == pytest.approx(100 / 365, abs=1e-4)
        assert y2018["loss_ratio_earned"] == pytest.approx(100 / 183, abs=1e-4)
        assert years.loc["2016", "loss_ratio_written"] == pytest.approx(0.2)

    def test_frequency_and_severity(self, sample_db):
        """Verify frequency = claims / exposure and severity = cost / claims."""
        y2016 = sample_db.run_file("kpi_by_uw_year").set_index("uw_year").loc["2016"]
        assert y2016["frequency"] == pytest.approx(1 / 2)
        assert y2016["severity"] == pytest.approx(50.0)

    def test_renewals_counted_in_due_month(self, sample_db):
        """Verify renewals sit in the month a period ended and premium in the month it
        started, and that December 2018 is not shown as a 0% month."""
        monthly = sample_db.run_file("portfolio_monthly").set_index("month")
        june = monthly.loc["2017-06"]
        assert (june["policies_due"], june["policies_renewed"]) == (1, 1)
        assert june["written_premium"] == 100.0
        assert "2018-12" not in monthly.index

    def test_segments_use_finished_periods_only(self, sample_db):
        """Verify periods still running (or without an end date) are left out."""
        seg = sample_db.run_file("kpi_by_segment")
        assert seg.groupby("dimension")["policy_years"].sum().eq(10).all()

    def test_fact_tables_keep_totals(self, sample_db):
        """Verify the Power BI fact tables add up to the policy-year totals."""
        fact = sample_db.run_file("fact_portfolio")
        renewal = sample_db.run_file("fact_renewal")
        totals = sample_db.query(
            "SELECT SUM(written_premium) AS wp, SUM(renewal_due) AS due FROM policy_year")
        assert fact["written_premium"].sum() == pytest.approx(totals["wp"].iloc[0])
        assert renewal["policies_due"].sum() == totals["due"].iloc[0]
