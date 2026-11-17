"""Run the data quality checks inside PostgreSQL, as a procedure that logs every run.

The SQLite pipeline counts each check's exceptions when it is rebuilt and keeps
only the latest numbers. Here the same checks become rows of a rule table, the
procedure run_dq_checks() runs them all and writes one result row per check and
run, and the view dq_latest puts each count next to the previous run's. A check
whose SQL fails is logged as an error and the run carries on.

Steps:
1. copy the tables the checks read from the SQLite database (CREATE TABLE, INSERT);
2. create the PostgreSQL version of the policy_year view;
3. create the audit tables and the procedure (kept between runs, so history stays);
4. load the checks of src/data_quality.py into dq_rule;
5. CALL run_dq_checks() and compare every count with the SQLite result.

Run from the project root, after run_pipeline.py has built data/insurance.db:

    docker compose up -d
    python -m src.postgres_audit

The connection string is read from INSURANCE_PG_DSN; without it the local
database from docker-compose.yml is used.
"""

import logging
import os
import sys

import pandas as pd

from src.data_quality import CHECKS, run_checks
from src.database import DATE_COLUMNS, SQL_DIR, InsuranceDB

logger = logging.getLogger(__name__)

DEFAULT_DSN = "postgresql://audit:audit@127.0.0.1:5433/insurance"
PG_SQL_DIR = os.path.join(SQL_DIR, "postgres")

#: The tables the checks read. The rest of the SQLite database stays in SQLite.
TABLES = ("cbar_total_ytd", "insurer_ytd", "insurer_monthly", "class_ytd",
          "policy_years", "claim_types")


def column_type(name, dtype):
    """PostgreSQL type for a column read back from SQLite.

    SQLite stores the portfolio dates as ISO text; here they become real dates,
    so the checks compare dates rather than strings.
    """
    if name in DATE_COLUMNS:
        return "date"
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "bigint"
    if pd.api.types.is_float_dtype(dtype):
        return "double precision"
    return "text"


def create_table_sql(table, df):
    """CREATE TABLE statement for a DataFrame, one column per DataFrame column."""
    columns = ",\n    ".join(f'"{c}" {column_type(c, df[c].dtype)}' for c in df.columns)
    return f'CREATE TABLE "{table}" (\n    {columns}\n)'


def insert_sql(table, columns):
    """Parameterised INSERT for the given columns."""
    names = ", ".join(f'"{c}"' for c in columns)
    marks = ", ".join(["%s"] * len(columns))
    return f'INSERT INTO "{table}" ({names}) VALUES ({marks})'


def _rows(df):
    """Rows as tuples of plain Python values, with None for missing."""
    out = df.astype(object).where(df.notna(), None)
    for col in df.columns:
        if col in DATE_COLUMNS:
            out[col] = [None if v is None else pd.Timestamp(v).date() for v in out[col]]
    return list(out.itertuples(index=False, name=None))


def copy_table(sqlite_conn, pg_conn, table):
    """Recreate one SQLite table in PostgreSQL and insert its rows. Returns the row count."""
    df = pd.read_sql_query(f'SELECT * FROM "{table}"', sqlite_conn)
    with pg_conn.cursor() as cur:
        cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        cur.execute(create_table_sql(table, df))
        cur.executemany(insert_sql(table, list(df.columns)), _rows(df))
    logger.info("%s copied - %s rows", table, f"{len(df):,}")
    return len(df)


def run_sql_file(pg_conn, name):
    """Run sql/postgres/<name>.sql as one script."""
    with open(os.path.join(PG_SQL_DIR, f"{name}.sql"), encoding="utf-8") as f:
        pg_conn.execute(f.read())


def setup(sqlite_conn, pg_conn):
    """Copy the data, then create the view, the audit tables and the procedure."""
    for table in TABLES:
        copy_table(sqlite_conn, pg_conn, table)
    for name in ("policy_year", "audit_schema", "run_dq_checks"):
        run_sql_file(pg_conn, name)


def load_rules(pg_conn, checks=CHECKS):
    """Write the checks into dq_rule. A check no longer in the list is deactivated, not deleted,
    so its past results keep their rule."""
    with pg_conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO dq_rule (area, rule_name, check_sql, why)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (rule_name) DO UPDATE
               SET area = EXCLUDED.area, check_sql = EXCLUDED.check_sql,
                   why = EXCLUDED.why, active = true""",
            [(area, name, sql, why) for area, name, sql, why in checks],
        )
        cur.execute("UPDATE dq_rule SET active = false WHERE NOT (rule_name = ANY(%s))",
                    ([name for _, name, _, _ in checks],))


def run_checks_pg(pg_conn):
    """CALL run_dq_checks() and return (run_id, results of that run)."""
    run_id = pg_conn.execute("CALL run_dq_checks(NULL)").fetchone()[0]
    rows = pg_conn.execute(
        """SELECT ru.area, ru.rule_name AS check, r.exception_rows AS rows,
                  r.status, r.error_message
           FROM dq_result r JOIN dq_rule ru USING (rule_id)
           WHERE r.run_id = %s ORDER BY ru.rule_id""",
        (run_id,),
    ).fetchall()
    return run_id, pd.DataFrame(rows, columns=["area", "check", "rows", "status", "error"])


def compare(sqlite_results, pg_results):
    """Checks whose count differs between SQLite and PostgreSQL (empty when they agree)."""
    merged = sqlite_results[["check", "rows"]].merge(
        pg_results[["check", "rows", "status"]], on="check", how="outer",
        suffixes=("_sqlite", "_postgres"))
    return merged[(merged["rows_sqlite"] != merged["rows_postgres"])
                  | (merged["status"] == "error")]


def main():
    import psycopg

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    dsn = os.environ.get("INSURANCE_PG_DSN", DEFAULT_DSN)
    db = InsuranceDB()
    with psycopg.connect(dsn) as pg:
        setup(db.conn, pg)
        load_rules(pg)
        run_id, results = run_checks_pg(pg)
        pg.commit()
        latest = pd.DataFrame(
            pg.execute("SELECT rule_name, status, exception_rows, previous_rows, change "
                       "FROM dq_latest").fetchall(),
            columns=["check", "status", "rows", "previous", "change"])
    sqlite_results = run_checks(db)
    db.close()

    with pd.option_context("display.max_colwidth", 70, "display.width", 180):
        print(f"run {run_id}")
        print(latest.to_string(index=False))
    differences = compare(sqlite_results, results)
    if not differences.empty:
        print("\nPostgreSQL and SQLite disagree:")
        print(differences.to_string(index=False))
        sys.exit(1)
    print(f"\nAll {len(results)} checks match the SQLite pipeline.")


if __name__ == "__main__":
    main()
