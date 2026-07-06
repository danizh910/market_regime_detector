from __future__ import annotations

import numpy as np
import pandas as pd


REGIME_COLORS = [
    "#2ca25f",
    "#f0b429",
    "#d95f02",
    "#756bb1",
    "#4c78a8",
]

REGIME_COLOR_BY_NAME = {
    "Calm / bull": "#2ca25f",
    "Calm / low-volatility": "#5abf90",
    "Recovery / risk-on": "#4c78a8",
    "Transition / mixed": "#7b8794",
    "High-volatility / sideways": "#f0b429",
    "Bear / drawdown": "#d95f02",
    "Stress / bear": "#c0392b",
}


def consecutive_durations(labels: pd.Series) -> pd.DataFrame:
    """Return one row per consecutive regime segment."""
    if labels.empty:
        return pd.DataFrame(columns=["regime", "start", "end", "duration_days"])

    groups = labels.ne(labels.shift()).cumsum()
    rows = []
    for _, segment in labels.groupby(groups):
        rows.append(
            {
                "regime": int(segment.iloc[0]),
                "start": segment.index[0],
                "end": segment.index[-1],
                "duration_days": len(segment),
            }
        )
    return pd.DataFrame(rows)


def summarize_regimes(
    df: pd.DataFrame, labels: np.ndarray, periods_per_year: int = 252
) -> pd.DataFrame:
    """Compute per-regime performance, risk, frequency, and duration statistics."""
    labelled = df.copy()
    labelled["regime"] = labels
    durations = consecutive_durations(labelled["regime"])

    rows = []
    for regime, group in labelled.groupby("regime"):
        regime_durations = durations.loc[durations["regime"] == regime, "duration_days"]
        mean_daily_log_return = group["log_return"].mean()
        annualized_return = np.exp(mean_daily_log_return * periods_per_year) - 1.0
        annualized_volatility = group["log_return"].std() * np.sqrt(periods_per_year)

        rows.append(
            {
                "regime": int(regime),
                "observations": int(len(group)),
                "frequency_pct": len(group) / len(labelled),
                "mean_daily_return": np.exp(mean_daily_log_return) - 1.0,
                "annualized_return": annualized_return,
                "annualized_volatility": annualized_volatility,
                "avg_duration_days": regime_durations.mean(),
                "median_duration_days": regime_durations.median(),
                "segments": int(len(regime_durations)),
                "avg_drawdown": group["drawdown"].mean(),
            }
        )

    stats = pd.DataFrame(rows).sort_values("regime").reset_index(drop=True)
    stats["sharpe_like"] = stats["annualized_return"] / stats["annualized_volatility"]
    return stats


def assign_regime_names(stats: pd.DataFrame) -> pd.DataFrame:
    """Attach readable labels to arbitrary HMM state IDs."""
    named = stats.copy()
    named["regime_name"] = "Transition / mixed"

    if named.empty:
        return named

    stress_idx = named.sort_values(
        ["annualized_return", "annualized_volatility"], ascending=[True, False]
    ).index[0]
    calm_idx = named.sort_values(
        ["annualized_volatility", "annualized_return"], ascending=[True, False]
    ).index[0]

    named.loc[stress_idx, "regime_name"] = "Stress / bear"
    calm_label = "Calm / bull"
    if named.loc[calm_idx, "annualized_return"] <= 0:
        calm_label = "Calm / low-volatility"
    named.loc[calm_idx, "regime_name"] = calm_label

    median_volatility = named["annualized_volatility"].median()
    for idx in named.index.difference([stress_idx, calm_idx]):
        annualized_return = named.loc[idx, "annualized_return"]
        annualized_volatility = named.loc[idx, "annualized_volatility"]

        if annualized_return > 0.10:
            label = "Recovery / risk-on"
        elif annualized_volatility >= median_volatility and annualized_return > -0.10:
            label = "High-volatility / sideways"
        elif annualized_return < -0.05 and annualized_volatility < named.loc[stress_idx, "annualized_volatility"]:
            label = "Bear / drawdown"
        elif annualized_volatility >= median_volatility:
            label = "High-volatility / sideways"
        else:
            label = "Transition / mixed"

        named.loc[idx, "regime_name"] = label

    colors = []
    fallback_colors = iter(REGIME_COLORS)
    for regime_name in named["regime_name"]:
        if regime_name in REGIME_COLOR_BY_NAME:
            colors.append(REGIME_COLOR_BY_NAME[regime_name])
        else:
            colors.append(next(fallback_colors))
    named["color"] = colors
    return named


def transition_matrix(model_transitions: np.ndarray, regime_names: pd.DataFrame) -> pd.DataFrame:
    """Return model transition probabilities with readable row/column labels."""
    labels = [
        f"{int(row.regime)}: {row.regime_name}" for row in regime_names.sort_values("regime").itertuples()
    ]
    return pd.DataFrame(model_transitions, index=labels, columns=labels)
