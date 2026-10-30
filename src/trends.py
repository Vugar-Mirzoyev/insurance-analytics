"""Simple trend, anomaly and forecast tools for a monthly series.

Everything here is deliberately basic, so each number can be explained in a sentence:
- moving average: the mean of the last k months, to see the trend without the noise;
- rolling z-score: how many standard deviations a month is from the 12 months
  before it (only past months, so a spike cannot hide itself by raising the mean);
- IQR rule on year-over-year growth: comparing a month with the same month a year
  earlier removes the seasonal pattern (January is always big), then growth rates
  far outside the middle half of all growth rates are flagged;
- forecasts: moving average, simple exponential smoothing and seasonal naive
  (same month last year), compared on the last 12 months before one is trusted.
"""

import numpy as np
import pandas as pd


def moving_average(series, window=3):
    """Mean of the current and previous window-1 months."""
    return series.rolling(window, min_periods=window).mean()


def rolling_zscore(series, window=12, min_periods=6):
    """(value - mean of previous months) / std of previous months."""
    past = series.shift(1).rolling(window, min_periods=min_periods)
    return (series - past.mean()) / past.std()


def yoy_growth(series, season=12):
    """Growth against the same month a year earlier."""
    return series / series.shift(season) - 1


def iqr_bounds(values, k=1.5):
    """(low, high) fences: Q1 - k*IQR and Q3 + k*IQR, ignoring empty values."""
    q1, q3 = np.nanpercentile(values, [25, 75])
    return q1 - k * (q3 - q1), q3 + k * (q3 - q1)


def flag_anomalies(series, z_limit=3.0, k=1.5):
    """Table with the trend and both anomaly flags for every month.

    Args:
        series: Monthly values indexed by month (a missing month is NaN).

    Returns:
        DataFrame with columns value, ma_3, ma_12, rolling_z, z_flag, yoy, iqr_flag.
    """
    out = pd.DataFrame({"value": series})
    out["ma_3"] = moving_average(series, 3)
    out["ma_12"] = moving_average(series, 12)
    out["rolling_z"] = rolling_zscore(series)
    out["z_flag"] = out["rolling_z"].abs() >= z_limit
    out["yoy"] = yoy_growth(series)
    low, high = iqr_bounds(out["yoy"].to_numpy(), k)
    out["iqr_flag"] = (out["yoy"] < low) | (out["yoy"] > high)
    return out


def ma_forecast(history, horizon=3, window=3):
    """Every future month = mean of the last `window` months."""
    return np.repeat(np.mean(history[-window:]), horizon)


def ses_levels(history, alpha):
    """Simple exponential smoothing: level = alpha * value + (1 - alpha) * level."""
    levels = [history[0]]
    for value in history[1:]:
        levels.append(alpha * value + (1 - alpha) * levels[-1])
    return np.array(levels)


def best_alpha(history, grid=np.round(np.arange(0.05, 1.0, 0.05), 2)):
    """Alpha with the smallest one-step-ahead squared error on the history."""
    def error(alpha):
        levels = ses_levels(history, alpha)
        return np.mean((history[1:] - levels[:-1]) ** 2)
    return min(grid, key=error)


def ses_forecast(history, horizon=3, alpha=None):
    """Every future month = the last smoothed level."""
    alpha = best_alpha(history) if alpha is None else alpha
    return np.repeat(ses_levels(history, alpha)[-1], horizon)


def seasonal_naive_forecast(history, horizon=3, season=12):
    """Each future month = the same month one season earlier."""
    return np.array([history[len(history) - season + h] for h in range(horizon)])


METHODS = {
    "moving_average_3": ma_forecast,
    "exp_smoothing": ses_forecast,
    "seasonal_naive": seasonal_naive_forecast,
}


def backtest(history, test_months=12):
    """One-step-ahead test: for each of the last test_months months, forecast it
    from the months before it and compare with what happened.

    Returns:
        DataFrame with one row per method: mae, mape (mean absolute % error).
    """
    history = np.asarray(history, dtype=float)
    rows = []
    for name, method in METHODS.items():
        errors, pct = [], []
        for t in range(len(history) - test_months, len(history)):
            prediction = method(history[:t], horizon=1)[0]
            errors.append(abs(history[t] - prediction))
            pct.append(abs(history[t] - prediction) / abs(history[t]))
        rows.append({"method": name, "mae": np.mean(errors), "mape": np.mean(pct)})
    return pd.DataFrame(rows).sort_values("mae").reset_index(drop=True)


def forecast(history, horizon=3, test_months=12):
    """Forecast with every method and mark the one with the lowest backtest error.

    Returns:
        (forecasts, scores): forecasts has one row per method and future step;
        scores is the backtest table.
    """
    history = np.asarray(history, dtype=float)
    scores = backtest(history, test_months)
    best = scores.iloc[0]["method"]
    rows = []
    for name, method in METHODS.items():
        for step, value in enumerate(method(history, horizon=horizon), start=1):
            rows.append({"method": name, "step": step, "forecast": value,
                         "chosen": name == best})
    return pd.DataFrame(rows), scores
