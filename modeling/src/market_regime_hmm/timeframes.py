from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeframeConfig:
    key: str
    label: str
    interval: str
    period: str | None
    start: str | None
    short_window: int
    medium_window: int
    drawdown_window: int
    strategy_window: int
    trading_periods_per_year: int
    crypto_periods_per_year: int


TIMEFRAMES: dict[str, TimeframeConfig] = {
    "15m": TimeframeConfig(
        key="15m",
        label="Short-term 15 minute",
        interval="15m",
        period="60d",
        start=None,
        short_window=16,
        medium_window=64,
        drawdown_window=192,
        strategy_window=96,
        trading_periods_per_year=26 * 252,
        crypto_periods_per_year=96 * 365,
    ),
    "1h": TimeframeConfig(
        key="1h",
        label="Short-term 1 hour",
        interval="1h",
        period="730d",
        start=None,
        short_window=24,
        medium_window=72,
        drawdown_window=240,
        strategy_window=160,
        trading_periods_per_year=7 * 252,
        crypto_periods_per_year=24 * 365,
    ),
    "1d": TimeframeConfig(
        key="1d",
        label="Daily",
        interval="1d",
        period=None,
        start="2000-01-01",
        short_window=21,
        medium_window=63,
        drawdown_window=126,
        strategy_window=200,
        trading_periods_per_year=252,
        crypto_periods_per_year=365,
    ),
    "1wk": TimeframeConfig(
        key="1wk",
        label="Weekly",
        interval="1wk",
        period=None,
        start="2000-01-01",
        short_window=4,
        medium_window=13,
        drawdown_window=26,
        strategy_window=40,
        trading_periods_per_year=52,
        crypto_periods_per_year=52,
    ),
    "1mo": TimeframeConfig(
        key="1mo",
        label="Monthly",
        interval="1mo",
        period=None,
        start="2000-01-01",
        short_window=3,
        medium_window=6,
        drawdown_window=12,
        strategy_window=10,
        trading_periods_per_year=12,
        crypto_periods_per_year=12,
    ),
}


def get_timeframe(key: str) -> TimeframeConfig:
    try:
        return TIMEFRAMES[key]
    except KeyError as exc:
        valid = ", ".join(TIMEFRAMES)
        raise ValueError(f"Unknown timeframe {key!r}. Valid values: {valid}.") from exc
