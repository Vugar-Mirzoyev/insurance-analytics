"""Tests for the PostgreSQL version of the data quality checks.

The first group needs no database: it checks the statements the copy is built
from. The second runs against a real PostgreSQL and is skipped unless
INSURANCE_PG_DSN points at one (docker compose up -d, then set
INSURANCE_PG_DSN=postgresql://audit:audit@127.0.0.1:5433/insurance). Each test
works in its own schema, which is dropped afterwards.
"""

import os
import sys
import uuid

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_quality import CHECKS, run_checks  # noqa: E402
from src.postgres_audit import (  # noqa: E402
    column_type,
    compare,
    create_table_sql,
    insert_sql,
    load_rules,
    run_checks_pg,
    setup,
)


class TestStatements:
    """Tests for the CREATE TABLE and INSERT statements."""

    def test_column_types(self):
        """Verify dates become date and numbers keep their kind."""
        df = pd.DataFrame({"date_lapse": ["2018-01-01"], "id": [1], "premium": [1.5],
                           "area": ["x"]})
        assert [column_type(c, df[c].dtype) for c in df.columns] == [
            "date", "bigint", "double precision", "text"]

    def test_create_table_lists_every_column(self):
        """Verify every column appears once, quoted, with its type."""
        df = pd.DataFrame({"id": [1], "area": ["x"]})
        sql = create_table_sql("policy_years", df)
        assert sql.startswith('CREATE TABLE "policy_years"')
        assert '"id" bigint' in sql and '"area" text' in sql

    def test_insert_has_one_placeholder_per_column(self):
        """Verify the INSERT carries one parameter per column."""
        sql = insert_sql("t", ["a", "b", "c"])
        assert sql == 'INSERT INTO "t" ("a", "b", "c") VALUES (%s, %s, %s)'

    def test_compare_reports_only_differences(self):
        """Verify compare returns the checks whose counts differ."""
        sqlite = pd.DataFrame({"check": ["a", "b"], "rows": [1, 2]})
        pg = pd.DataFrame({"check": ["a", "b"], "rows": [1, 3],
                           "status": ["exceptions", "exceptions"]})
        assert compare(sqlite, pg)["check"].tolist() == ["b"]


DSN = os.environ.get("INSURANCE_PG_DSN")
needs_postgres = pytest.mark.skipif(not DSN, reason="INSURANCE_PG_DSN is not set")


@pytest.fixture
def pg():
    psycopg = pytest.importorskip("psycopg")
    schema = f"test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA {schema}")
        conn.execute(f"SET search_path TO {schema}")
        try:
            yield conn
        finally:
            conn.execute(f"DROP SCHEMA {schema} CASCADE")


@needs_postgres
class TestProcedure:
    """Tests for run_dq_checks() on the sample data and its planted traps."""

    def test_counts_match_sqlite(self, sample_db, pg):
        """Verify every check counts the same rows in PostgreSQL as in SQLite."""
        setup(sample_db.conn, pg)
        load_rules(pg)
        _, results = run_checks_pg(pg)
        assert len(results) == len(CHECKS)
        assert (results["status"] != "error").all()
        assert compare(run_checks(sample_db), results).empty

    def test_a_broken_check_is_logged_and_the_run_continues(self, sample_db, pg):
        """Verify a failing rule gets status error and the other rules still run."""
        setup(sample_db.conn, pg)
        broken = ("portfolio", "Broken check", "SELECT COUNT(*) FROM no_such_table", "test")
        load_rules(pg, CHECKS + [broken])
        run_id, results = run_checks_pg(pg)
        row = results.set_index("check").loc["Broken check"]
        assert row["status"] == "error" and "no_such_table" in row["error"]
        assert (results["status"] != "error").sum() == len(CHECKS)
        totals = pg.execute("SELECT rules_run, rules_failed FROM dq_run WHERE run_id = %s",
                            (run_id,)).fetchone()
        assert totals == (len(CHECKS) + 1, 1)

    def test_latest_view_shows_the_change_since_the_previous_run(self, sample_db, pg):
        """Verify a new duplicate row shows up as +1 against the previous run."""
        setup(sample_db.conn, pg)
        load_rules(pg)
        run_checks_pg(pg)
        pg.execute("INSERT INTO policy_years SELECT * FROM policy_years LIMIT 1")
        run_checks_pg(pg)
        latest = pd.DataFrame(
            pg.execute("SELECT rule_name, previous_rows, change FROM dq_latest").fetchall(),
            columns=["check", "previous", "change"]).set_index("check")
        assert latest.loc["Duplicate policy-year rows", "change"] == 1
        assert latest["previous"].notna().all()

    def test_a_removed_check_is_deactivated_not_deleted(self, sample_db, pg):
        """Verify history keeps its rule when a check leaves src/data_quality.py."""
        setup(sample_db.conn, pg)
        load_rules(pg)
        run_checks_pg(pg)
        load_rules(pg, CHECKS[1:])
        active = pg.execute("SELECT active FROM dq_rule WHERE rule_name = %s",
                            (CHECKS[0][1],)).fetchone()[0]
        assert active is False
        _, results = run_checks_pg(pg)
        assert len(results) == len(CHECKS) - 1
