import numpy as np
import pandas as pd

from market_regime_hmm.regimes import consecutive_durations, summarize_regimes


def test_consecutive_durations_counts_segments():
    labels = pd.Series([0, 0, 1, 1, 1, 0], index=pd.bdate_range("2024-01-01", periods=6))

    durations = consecutive_durations(labels)

    assert durations["duration_days"].tolist() == [2, 3, 1]
    assert durations["regime"].tolist() == [0, 1, 0]


def test_summarize_regimes_includes_duration_and_frequency():
    dates = pd.bdate_range("2024-01-01", periods=8)
    df = pd.DataFrame(
        {
            "close": np.linspace(100, 108, 8),
            "log_return": [0.0, 0.01, 0.01, -0.02, -0.01, 0.0, 0.01, 0.01],
            "drawdown": [0.0, 0.0, 0.0, -0.02, -0.03, -0.01, 0.0, 0.0],
        },
        index=dates,
    )
    labels = np.array([0, 0, 0, 1, 1, 1, 0, 0])

    stats = summarize_regimes(df, labels)

    assert stats.loc[stats["regime"] == 0, "frequency_pct"].iloc[0] == 5 / 8
    assert stats.loc[stats["regime"] == 1, "avg_duration_days"].iloc[0] == 3
