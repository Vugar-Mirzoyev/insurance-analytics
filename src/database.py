"""Load the portfolio CSVs and the CBAR tables into SQLite and run the sql/ files."""

import glob
import logging
import os
import sqlite3

import pandas as pd

from src import cbar_loader

logger = logging.getLogger(__name__)

SQL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sql")
DATE_COLUMNS = ["date_start_contract", "date_last_renewal", "date_next_renewal",
                "date_birth", "date_driving_licence", "date_lapse"]


class InsuranceDB:
    """SQLite database with the policy portfolio and the Azerbaijan market tables."""

    def __init__(self, db_path="data/insurance.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        logger.info("Database connection established")

    def load_portfolio(self, csv_dir="data/raw/portfolio"):
        """Load the Lledó & Pavía motor portfolio (one row per policy and year).

        Column names are lower-cased and dates are stored as ISO text
        (YYYY-MM-DD), so SQLite compares and subtracts them correctly.
        A date that cannot be read is stored as NULL and counted by data_quality.
        """
        policies = pd.read_csv(os.path.join(csv_dir, "Motor vehicle insurance data.csv"), sep=";")
        policies.columns = [c.lower() for c in policies.columns]
        for col in DATE_COLUMNS:
            policies[col] = pd.to_datetime(policies[col], format="%d/%m/%Y",
                                           errors="coerce").dt.strftime("%Y-%m-%d")
        self._write("policy_years", policies)

        claims = pd.read_csv(os.path.join(csv_dir, "sample type claim.csv"), sep=";")
        claims.columns = [c.lower() for c in claims.columns]
        self._write("claim_types", claims)

    def load_market(self, cbar_dir="data/raw/cbar"):
        """Load CBAR Tables 6.1 (by insurer) and 6.2 (by class), newest file of each.

        Stored tables (values in thousand AZN):
            insurer_ytd, cbar_total_ytd, class_ytd: year-to-date, as published;
            insurer_monthly, insurer_quarterly, class_quarterly: single periods.
        """
        insurers, total = cbar_loader.read_insurers(_newest(cbar_dir, "cbar_6_1_*.xlsx"))
        classes = cbar_loader.read_classes(_newest(cbar_dir, "cbar_6_2_*.xlsx"))

        self._write("insurer_ytd", insurers)
        self._write("cbar_total_ytd", total)
        self._write("class_ytd", classes)
        self._write("insurer_monthly", cbar_loader.to_monthly(insurers, ["insurer"]))
        self._write("insurer_quarterly", cbar_loader.to_quarterly(insurers, ["insurer"]))
        self._write("class_quarterly", cbar_loader.to_quarterly(classes, ["line_code"]))

    def create_views(self):
        """Create the policy_year view that every portfolio query builds on."""
        self.conn.executescript(_read_sql("policy_year"))

    def query(self, sql, params=None):
        """Execute a SQL query and return results as a DataFrame."""
        return pd.read_sql_query(sql, self.conn, params=params)

    def run_file(self, name):
        """Run sql/<name>.sql and return the result as a DataFrame."""
        return self.query(_read_sql(name))

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def _write(self, table, df):
        df.to_sql(table, self.conn, if_exists="replace", index=False)
        logger.info("%s table loaded - %s rows", table, f"{len(df):,}")


def _newest(directory, pattern):
    files = sorted(glob.glob(os.path.join(directory, pattern)))
    if not files:
        raise FileNotFoundError(f"No {pattern} in {directory}")
    return files[-1]


def _read_sql(name):
    with open(os.path.join(SQL_DIR, f"{name}.sql"), encoding="utf-8") as f:
        return f.read()
