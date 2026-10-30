"""Unit tests for the market queries (window functions over quarters)."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import InsuranceDB  # noqa: E402


@pytest.fixture
def quarters_db(tmp_path):
    """Two insurers over two years: one non-life, one life."""
    rows = []
    for year in (2024, 2025):
        for quarter in (1, 2, 3, 4):
            base = 100 * quarter + (50 if year == 2025 else 0)
            rows.append(("Alfa", 0, 0, year, quarter, f"{year}-Q{quarter}", base, base / 2))
            rows.append(("Beta", 1, 0, year, quarter, f"{year}-Q{quarter}", 100.0, 80.0))
    df = pd.DataFrame(rows, columns=["insurer", "is_life", "licence_revoked", "year",
                                     "quarter", "period", "premiums", "claims_paid"])
    db = InsuranceDB(db_path=str(tmp_path / "q.db"))
    df.to_sql("insurer_quarterly", db.conn, index=False)
    yield db
    db.close()


class TestMarketQuarterly:
    """Tests for sql/market_quarterly.sql."""

    def test_qoq_and_yoy(self, quarters_db):
        """Verify QoQ compares with the previous quarter and YoY with a year earlier."""
        m = quarters_db.run_file("market_quarterly").set_index("period")
        q1 = m.loc["2025-Q1"]
        assert q1["premiums"] == 250                       # 150 + 100
        assert q1["premiums_yoy"] == pytest.approx(250 / 200 - 1, abs=1e-4)
        assert q1["premiums_qoq"] == pytest.approx(250 / 500 - 1, abs=1e-4)
        assert pd.isna(m.loc["2024-Q1", "premiums_yoy"])

    def test_payout_ratio(self, quarters_db):
        """Verify payout ratio = claims paid / premiums of the same quarter."""
        m = quarters_db.run_file("market_quarterly").set_index("period")
        assert m.loc["2024-Q1", "payout_ratio"] == pytest.approx(130 / 200)


class TestInsurerQuarterly:
    """Tests for sql/insurer_quarterly.sql."""

    def test_shares(self, quarters_db):
        """Verify market shares add up to 1 and each insurer's segment share uses its
        own segment (life or non-life)."""
        i = quarters_db.run_file("insurer_quarterly")
        assert i.groupby("period")["market_share"].sum().round(4).eq(1).all()
        assert i["segment_share"].eq(1).all()           # one insurer per segment
        alfa = i[(i["insurer"] == "Alfa") & (i["period"] == "2025-Q2")].iloc[0]
        assert alfa["premiums_yoy"] == pytest.approx(250 / 200 - 1, abs=1e-4)
