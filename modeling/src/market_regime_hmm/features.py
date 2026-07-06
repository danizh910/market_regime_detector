from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass


FEATURE_COLUMNS = [
    "rolling_return_short",
    "realized_vol_short",
    "realized_vol_medium",
    "momentum_medium",
    "drawdown",
]


@dataclass(frozen=True)
class FeatureConfig:
    short_window: int = 21
    medium_window: int = 63
    drawdown_window: int = 126
    periods_per_year: int = 252


def engineer_features(prices: pd.DataFrame, config: FeatureConfig | None = None) -> pd.DataFrame:
    """Create regime features from an adjusted close price series.

    The features intentionally mix direction, risk, and loss-from-peak information:
    returns and momentum capture trend, volatility captures uncertainty, and drawdown
    captures whether losses are shallow or persistent.
    """
    if "close" not in prices.columns:
        raise ValueError("Expected a DataFrame with a 'close' column.")

    config = config or FeatureConfig()
    features = prices.copy()
    features["log_return"] = np.log(features["close"]).diff()
    features["rolling_return_short"] = features["close"].pct_change(config.short_window)
    features["realized_vol_short"] = (
        features["log_return"].rolling(config.short_window).std() * np.sqrt(config.periods_per_year)
    )
    features["realized_vol_medium"] = (
        features["log_return"].rolling(config.medium_window).std() * np.sqrt(config.periods_per_year)
    )
    features["momentum_medium"] = features["close"].pct_change(config.medium_window)

    min_periods = max(2, min(config.short_window, config.drawdown_window // 3))
    rolling_peak = features["close"].rolling(config.drawdown_window, min_periods=min_periods).max()
    features["drawdown"] = features["close"] / rolling_peak - 1.0

    return features.dropna(subset=FEATURE_COLUMNS).copy()
