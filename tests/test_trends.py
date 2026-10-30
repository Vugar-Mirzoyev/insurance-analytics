"""Unit tests for the trend, anomaly and forecast tools."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import trends  # noqa: E402


def seasonal_series(years=4, spike_at=None):
    """Monthly series: slow growth, every January twice as big, optional spike."""
    values = []
    for i in range(12 * years):
        v = 100 + i
        if i % 12 == 0:
            v *= 2
        values.append(float(v))
    s = pd.Series(values, index=pd.period_range("2022-01", periods=12 * years, freq="M"))
    if spike_at is not None:
        s.iloc[spike_at] *= 3
    return s


class TestAnomalies:
    """Tests for the z-score and IQR flags."""

    def test_zscore_flags_spike(self):
        """Verify a month three times its usual size is flagged."""
        flags = trends.flag_anomalies(seasonal_series(spike_at=30))
        assert flags["z_flag"].iloc[30]

    def test_zscore_uses_only_past_months(self):
        """Verify the z-score of a month does not change when later months change."""
        s = seasonal_series()
        before = trends.rolling_zscore(s).iloc[20]
        s.iloc[21:] = 10_000
        assert trends.rolling_zscore(s).iloc[20] == pytest.approx(before)

    def test_yoy_iqr_ignores_seasonality(self):
        """Verify regular Januaries are not flagged by the IQR rule on YoY growth,
        while the spike is."""
        flags = trends.flag_anomalies(seasonal_series(spike_at=30))
        januaries = flags.iloc[[12, 24, 36]]
        assert not januaries["iqr_flag"].any()
        assert flags["iqr_flag"].iloc[30]

    def test_iqr_bounds(self):
        """Verify the fences are Q1 - 1.5 IQR and Q3 + 1.5 IQR."""
        low, high = trends.iqr_bounds(np.array([1, 2, 3, 4, 5, np.nan]))
        assert (low, high) == (-1.0, 7.0)


class TestForecasts:
    """Tests for the forecast methods and the backtest."""

    def test_moving_average(self):
        """Verify the forecast is the mean of the last three months."""
        assert trends.ma_forecast(np.array([1.0, 2, 3, 4, 5]), horizon=2).tolist() == [4, 4]

    def test_exp_smoothing_alpha_one_is_last_value(self):
        """Verify alpha = 1 keeps only the last value."""
        assert trends.ses_forecast(np.array([5.0, 7, 9]), horizon=1, alpha=1.0)[0] == 9

    def test_seasonal_naive(self):
        """Verify each future month repeats the same month a year earlier."""
        history = np.arange(24, dtype=float)
        assert trends.seasonal_naive_forecast(history, horizon=3).tolist() == [12, 13, 14]

    def test_backtest_prefers_seasonal_method_on_seasonal_data(self):
        """Verify the backtest ranks seasonal naive first on a strongly seasonal series."""
        scores = trends.backtest(seasonal_series().to_numpy())
        assert scores.iloc[0]["method"] == "seasonal_naive"
        assert set(scores["method"]) == set(trends.METHODS)

    def test_forecast_marks_one_method(self):
        """Verify exactly one method is marked as chosen, for every step."""
        fc, _ = trends.forecast(seasonal_series().to_numpy(), horizon=3)
        assert fc.groupby("step")["chosen"].sum().eq(1).all()
