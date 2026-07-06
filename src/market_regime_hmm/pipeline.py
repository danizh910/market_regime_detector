from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_regime_hmm.data import download_price_history
from market_regime_hmm.features import FEATURE_COLUMNS, FeatureConfig, engineer_features
from market_regime_hmm.model import fit_hmm_with_bic_selection
from market_regime_hmm.regimes import assign_regime_names, summarize_regimes, transition_matrix
from market_regime_hmm.reporting import (
    plot_model_selection,
    plot_price_with_regimes,
    plot_strategy_by_regime,
    plot_transition_matrix,
)
from market_regime_hmm.strategy import trend_following_by_regime
from market_regime_hmm.timeframes import get_timeframe
from market_regime_hmm.universe import is_crypto


@dataclass(frozen=True)
class PipelineConfig:
    ticker: str = "^GSPC"
    start: str | None = None
    end: str | None = None
    timeframe: str = "1d"
    project_root: Path = Path(".")
    force_download: bool = False
    state_min: int = 2
    state_max: int = 4


def run_pipeline(config: PipelineConfig) -> dict[str, Path]:
    """Run the full market-regime pipeline and write reproducible artifacts."""
    root = config.project_root
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    figures_dir = root / "reports" / "figures"
    tables_dir = root / "reports" / "tables"
    processed_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    timeframe = get_timeframe(config.timeframe)
    periods_per_year = (
        timeframe.crypto_periods_per_year if is_crypto(config.ticker) else timeframe.trading_periods_per_year
    )
    start = config.start or timeframe.start

    prices = download_price_history(
        ticker=config.ticker,
        start=start,
        end=config.end,
        interval=timeframe.interval,
        period=timeframe.period,
        raw_dir=raw_dir,
        force=config.force_download,
    )
    features = engineer_features(
        prices,
        FeatureConfig(
            short_window=timeframe.short_window,
            medium_window=timeframe.medium_window,
            drawdown_window=timeframe.drawdown_window,
            periods_per_year=periods_per_year,
        ),
    )
    minimum_rows = max(60, config.state_max * 20)
    if len(features) < minimum_rows:
        raise ValueError(
            f"Only {len(features)} feature rows for {config.ticker} at {timeframe.key}. "
            "Choose a longer period or a higher timeframe."
        )

    selection = fit_hmm_with_bic_selection(
        features=features,
        feature_columns=FEATURE_COLUMNS,
        state_candidates=range(config.state_min, config.state_max + 1),
    )

    labelled = features.copy()
    labelled["regime"] = selection.labels
    stats = summarize_regimes(labelled, selection.labels, periods_per_year=periods_per_year)
    named_stats = assign_regime_names(stats)
    transitions = transition_matrix(selection.model.transmat_, named_stats)
    strategy = trend_following_by_regime(
        labelled,
        selection.labels,
        window=timeframe.strategy_window,
        periods_per_year=periods_per_year,
    )
    strategy = strategy.merge(named_stats[["regime", "regime_name"]], on="regime", how="left")

    safe_ticker = config.ticker.replace("^", "").replace(".", "_")
    artifact_stem = f"{safe_ticker}_{timeframe.key}"
    labelled_path = processed_dir / f"{artifact_stem}_labelled_regimes.csv"
    stats_path = tables_dir / f"{artifact_stem}_regime_stats.csv"
    selection_path = tables_dir / f"{artifact_stem}_model_selection.csv"
    transition_path = tables_dir / f"{artifact_stem}_transition_matrix.csv"
    strategy_path = tables_dir / f"{artifact_stem}_strategy_by_regime.csv"
    chart_path = figures_dir / f"{artifact_stem}_price_regimes.png"
    transition_chart_path = figures_dir / f"{artifact_stem}_transition_matrix.png"
    selection_chart_path = figures_dir / f"{artifact_stem}_model_selection.png"
    strategy_chart_path = figures_dir / f"{artifact_stem}_strategy_by_regime.png"

    labelled.to_csv(labelled_path)
    named_stats.to_csv(stats_path, index=False)
    selection.selection_table.to_csv(selection_path, index=False)
    transitions.to_csv(transition_path)
    strategy.to_csv(strategy_path, index=False)

    label_series = pd.Series(selection.labels, index=labelled.index, name="regime")
    plot_price_with_regimes(
        labelled, label_series, named_stats, config.ticker, timeframe.label, chart_path
    )
    plot_transition_matrix(transitions, transition_chart_path)
    plot_model_selection(selection.selection_table, selection_chart_path)
    plot_strategy_by_regime(strategy, strategy_chart_path)

    return {
        "labelled_data": labelled_path,
        "regime_stats": stats_path,
        "model_selection": selection_path,
        "transition_matrix": transition_path,
        "strategy_by_regime": strategy_path,
        "price_chart": chart_path,
        "transition_chart": transition_chart_path,
        "model_selection_chart": selection_chart_path,
        "strategy_chart": strategy_chart_path,
    }
