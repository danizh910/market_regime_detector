from __future__ import annotations

import numpy as np
import pandas as pd


def trend_following_by_regime(
    df: pd.DataFrame,
    labels: np.ndarray,
    window: int = 200,
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """Evaluate a simple trend-following rule conditional on detected regimes.

    The signal is long the index when yesterday's close was above its moving average,
    otherwise in cash. This is illustrative only; transaction costs and slippage are ignored.
    """
    data = df.copy()
    data["regime"] = labels
    data["sma"] = data["close"].rolling(window).mean()
    data["signal"] = (data["close"] > data["sma"]).astype(float).shift(1).fillna(0.0)
    data["buy_hold_return"] = np.exp(data["log_return"]) - 1.0
    data["trend_return"] = data["signal"] * data["buy_hold_return"]

    rows = []
    for regime, group in data.dropna(subset=["sma"]).groupby("regime"):
        rows.append(
            {
                "regime": int(regime),
                "observations": int(len(group)),
                "buy_hold_ann_return": (1.0 + group["buy_hold_return"].mean())
                ** periods_per_year
                - 1.0,
                "trend_ann_return": (1.0 + group["trend_return"].mean()) ** periods_per_year
                - 1.0,
                "trend_exposure_pct": group["signal"].mean(),
            }
        )

    return pd.DataFrame(rows).sort_values("regime").reset_index(drop=True)
