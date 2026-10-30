# run_pipeline.py
"""Build everything from the raw files: database, checks, KPI tables, trends.

Run from the project root:  python run_pipeline.py
Outputs go to data/processed/ (CSV files for Power BI) and docs/images/ (charts).
"""

import logging
import os

import pandas as pd

from src import trends
from src.data_quality import run_checks
from src.database import InsuranceDB

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

OUT = "data/processed"
SQL_OUTPUTS = {
    "market_monthly": "market_monthly",
    "market_quarterly": "market_quarterly",
    "insurer_quarterly": "insurer_quarterly",
    "class_quarterly": "class_quarterly",
    "portfolio_uw_year": "kpi_by_uw_year",
    "portfolio_monthly": "portfolio_monthly",
    "portfolio_segments": "kpi_by_segment",
    "fact_portfolio": "fact_portfolio",
    "fact_renewal": "fact_renewal",
}
FORECAST_START = "2023-01-01"   # first January after the missing 2022 months


def market_trends(market_monthly):
    """Anomaly flags for the whole series, forecasts from 2023 on."""
    monthly = market_monthly.set_index("month_start")
    flags, forecasts, scores = [], [], []
    for metric in ("premiums", "claims_paid"):
        f = trends.flag_anomalies(monthly[metric])
        flags.append(f.reset_index().assign(metric=metric))

        history = monthly.loc[monthly.index >= FORECAST_START, metric]
        fc, sc = trends.forecast(history.to_numpy(), horizon=3)
        last = pd.Period(history.index[-1], freq="M")
        fc["month_start"] = [str((last + s).start_time.date()) for s in fc["step"]]
        forecasts.append(fc.assign(metric=metric))
        scores.append(sc.assign(metric=metric))
    return pd.concat(flags), pd.concat(forecasts), pd.concat(scores)


def main():
    os.makedirs(OUT, exist_ok=True)
    db = InsuranceDB()
    db.load_portfolio()
    db.load_market()
    db.create_views()

    checks = run_checks(db)
    checks.to_csv(f"{OUT}/data_quality.csv", index=False)
    with pd.option_context("display.max_colwidth", 70, "display.width", 180):
        print(checks[["area", "check", "rows"]].to_string(index=False))

    tables = {}
    for name, sql_file in SQL_OUTPUTS.items():
        tables[name] = db.run_file(sql_file)
        tables[name].to_csv(f"{OUT}/{name}.csv", index=False)
    db.close()

    flags, forecasts, scores = market_trends(tables["market_monthly"])
    flags.to_csv(f"{OUT}/market_anomalies.csv", index=False)
    forecasts.to_csv(f"{OUT}/market_forecast.csv", index=False)
    scores.to_csv(f"{OUT}/market_forecast_backtest.csv", index=False)

    from src.charts import make_charts
    make_charts(tables, flags, forecasts)
    print("Pipeline completed!")


if __name__ == "__main__":
    main()
