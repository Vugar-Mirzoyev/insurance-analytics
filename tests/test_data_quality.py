"""Unit tests for the data quality checks."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import write_class_sheet  # noqa: E402
from src.data_quality import CHECKS, run_checks  # noqa: E402
from src.database import InsuranceDB  # noqa: E402


class TestDataQuality:
    """Tests for run_checks."""

    def test_one_row_per_check(self, sample_db):
        """Verify every check is reported with its explanation."""
        df = run_checks(sample_db)
        assert list(df.columns) == ["area", "check", "rows", "why"]
        assert len(df) == len(CHECKS)
        assert df["why"].str.len().gt(0).all()

    def test_counts_match_sample_data(self, sample_db):
        """Verify each check finds exactly the traps planted in the sample data."""
        counts = run_checks(sample_db).set_index("check")["rows"].to_dict()
        assert counts == {
            "Months missing from the CBAR year-to-date series": 1,
            "Months where CBAR's total row is not the sum of the insurers": 5,
            "Insurer-months where a year-to-date value goes down": 1,
            "Class subtotals that are not the sum of their parts": 0,
            "Duplicate policy-year rows": 1,
            "Claim-type rows without a matching policy year": 1,
            "Policy years with zero or negative premium": 1,
            "Policy years with a missing period date": 1,
            "Contracts that start after the period they belong to": 1,
            "Lapse date before the period started": 1,
            "Renewed policies with a lapse date inside the period": 1,
            "Policies that ended without a lapse date": 1,
            "Policy years not yet ended on the valuation date": 2,
            "Policy years due after the last renewal in the data": 3,
            "Claim counts and claim costs that disagree": 1,
            "Claim-type costs that do not add up to the policy-year total": 1,
            "Vehicles with power recorded as 0": 1,
        }

    def test_broken_class_subtotal_is_found(self, raw_dir, tmp_path):
        """Verify a subtotal that no longer matches its parts is counted, along with
        its own parent (2 lines x 2 months)."""
        write_class_sheet(raw_dir / "cbar" / "cbar_6_2_test.xlsx", break_line="V_PERSONAL")
        db = InsuranceDB(db_path=str(tmp_path / "broken.db"))
        db.load_portfolio(str(raw_dir / "portfolio"))
        db.load_market(str(raw_dir / "cbar"))
        db.create_views()
        counts = run_checks(db).set_index("check")["rows"]
        db.close()
        assert counts["Class subtotals that are not the sum of their parts"] == 4
