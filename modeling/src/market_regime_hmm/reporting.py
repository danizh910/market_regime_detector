from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from market_regime_hmm.regimes import consecutive_durations


def _regime_lookup(regime_names: pd.DataFrame) -> dict[int, dict[str, str]]:
    return {
        int(row.regime): {"name": row.regime_name, "color": row.color}
        for row in regime_names.itertuples()
    }


def plot_price_with_regimes(
    df: pd.DataFrame,
    labels: pd.Series,
    regime_names: pd.DataFrame,
    ticker: str,
    timeframe_label: str,
    output_path: Path,
) -> None:
    """Plot price with shaded backgrounds for each consecutive detected regime."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lookup = _regime_lookup(regime_names)
    segments = consecutive_durations(labels)

    fig, ax = plt.subplots(figsize=(14, 7))
    for segment in segments.itertuples():
        meta = lookup[int(segment.regime)]
        ax.axvspan(segment.start, segment.end, color=meta["color"], alpha=0.15, linewidth=0)

    ax.plot(df.index, df["close"], color="#1f2933", linewidth=1.4, label=f"{ticker} adjusted close")
    ax.set_title(f"{ticker} {timeframe_label} price history with HMM regimes")
    ax.set_ylabel("Adjusted close")
    ax.set_xlabel("")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    handles = []
    for row in regime_names.sort_values("regime").itertuples():
        handles.append(plt.Rectangle((0, 0), 1, 1, color=row.color, alpha=0.25, label=row.regime_name))
    ax.legend(handles=handles, loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_transition_matrix(matrix: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(matrix, annot=True, fmt=".1%", cmap="Blues", vmin=0, vmax=1, ax=ax)
    ax.set_title("HMM regime transition probabilities")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_model_selection(selection_table: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(selection_table["n_states"], selection_table["bic"], marker="o", label="BIC")
    ax.plot(selection_table["n_states"], selection_table["aic"], marker="s", label="AIC", alpha=0.75)
    ax.set_title("HMM model selection")
    ax.set_xlabel("Number of hidden states")
    ax.set_ylabel("Information criterion (lower is better)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_strategy_by_regime(strategy: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plot_data = strategy.set_index("regime")[["buy_hold_ann_return", "trend_ann_return"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    plot_data.plot(kind="bar", ax=ax, color=["#4c78a8", "#f58518"])
    ax.set_title("Illustrative strategy performance by detected regime")
    ax.set_ylabel("Annualized return")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.set_xlabel("Regime")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(["Buy and hold", "Trend following"])
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
