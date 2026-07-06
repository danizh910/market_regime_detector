from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from market_regime_hmm.pipeline import PipelineConfig, run_pipeline
from market_regime_hmm.timeframes import TIMEFRAMES
from market_regime_hmm.universe import ASSET_UNIVERSE, assets_by_region, get_asset


PROJECT_ROOT = Path.cwd()


def _safe_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace(".", "_")


@st.cache_data(show_spinner=False)
def _run_cached_pipeline(
    ticker: str,
    timeframe: str,
    state_min: int,
    state_max: int,
    force_download: bool,
) -> dict[str, str]:
    artifacts = run_pipeline(
        PipelineConfig(
            ticker=ticker,
            timeframe=timeframe,
            project_root=PROJECT_ROOT,
            force_download=force_download,
            state_min=state_min,
            state_max=state_max,
        )
    )
    return {key: str(path) for key, path in artifacts.items()}


def _format_percent_columns(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    percent_columns = [
        "frequency_pct",
        "mean_daily_return",
        "annualized_return",
        "annualized_volatility",
        "avg_drawdown",
        "buy_hold_ann_return",
        "trend_ann_return",
        "trend_exposure_pct",
    ]
    for column in percent_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.1%}")
    return formatted


def _asset_options(region: str) -> list[str]:
    if region == "All":
        return [asset.symbol for asset in ASSET_UNIVERSE]
    return [asset.symbol for asset in assets_by_region().get(region, [])]


def _render_single_analysis() -> None:
    regions = ["All", *sorted(assets_by_region())]
    region = st.sidebar.selectbox("Region / market", regions, index=0)
    options = _asset_options(region)
    selected_symbol = st.sidebar.selectbox("Instrument", options, index=0)
    custom_ticker = st.sidebar.text_input("Custom Yahoo ticker", value="")
    ticker = custom_ticker.strip() or selected_symbol
    timeframe = st.sidebar.selectbox(
        "Timeframe",
        list(TIMEFRAMES),
        index=list(TIMEFRAMES).index("1d"),
        format_func=lambda key: TIMEFRAMES[key].label,
    )
    state_min, state_max = st.sidebar.slider("HMM state range", 2, 6, (2, 4))
    force_download = st.sidebar.checkbox("Refresh market data", value=False)

    asset = get_asset(ticker)
    st.title("Market Regime Dashboard")
    st.caption(f"{asset.name} | {asset.region} | {asset.asset_class} | {TIMEFRAMES[timeframe].label}")

    if st.sidebar.button("Run analysis", type="primary", use_container_width=True):
        with st.spinner("Fitting HMM regimes and generating charts..."):
            artifacts = _run_cached_pipeline(ticker, timeframe, state_min, state_max, force_download)
        st.session_state["latest_artifacts"] = artifacts
        st.session_state["latest_ticker"] = ticker
        st.session_state["latest_timeframe"] = timeframe

    artifacts = st.session_state.get("latest_artifacts")
    if not artifacts:
        st.info("Choose an instrument and timeframe, then run the analysis.")
        return

    col_chart, col_meta = st.columns([2, 1])
    with col_chart:
        st.image(artifacts["price_chart"], use_container_width=True)
    with col_meta:
        selection = pd.read_csv(artifacts["model_selection"])
        best = selection.sort_values("bic").iloc[0]
        st.metric("Selected states", int(best["n_states"]))
        st.metric("Best BIC", f"{best['bic']:,.0f}")
        st.dataframe(selection, hide_index=True, use_container_width=True)

    stats = pd.read_csv(artifacts["regime_stats"])
    transitions = pd.read_csv(artifacts["transition_matrix"], index_col=0)
    strategy = pd.read_csv(artifacts["strategy_by_regime"])

    tab_stats, tab_transition, tab_strategy, tab_files = st.tabs(
        ["Regime stats", "Transitions", "Strategy", "Files"]
    )
    with tab_stats:
        st.dataframe(_format_percent_columns(stats), hide_index=True, use_container_width=True)
    with tab_transition:
        st.image(artifacts["transition_chart"], use_container_width=True)
        st.dataframe(transitions.style.format("{:.1%}"), use_container_width=True)
    with tab_strategy:
        st.image(artifacts["strategy_chart"], use_container_width=True)
        st.dataframe(_format_percent_columns(strategy), hide_index=True, use_container_width=True)
    with tab_files:
        st.json(artifacts)


def _render_snapshot() -> None:
    st.title("Multi-Asset Snapshot")
    st.caption("Run the same regime model across selected assets and timeframes.")

    default_assets = ["BTC-USD", "ETH-USD", "^GSPC", "^SSMI", "000300.SS", "^HSI"]
    symbols = st.multiselect(
        "Assets",
        [asset.symbol for asset in ASSET_UNIVERSE],
        default=[symbol for symbol in default_assets if symbol in [asset.symbol for asset in ASSET_UNIVERSE]],
    )
    timeframes = st.multiselect(
        "Timeframes",
        list(TIMEFRAMES),
        default=["1h", "1d", "1wk", "1mo"],
        format_func=lambda key: TIMEFRAMES[key].label,
    )

    if not st.button("Run snapshot", type="primary"):
        st.info("Select assets and timeframes, then run the snapshot.")
        return

    rows = []
    progress = st.progress(0)
    total = max(1, len(symbols) * len(timeframes))
    completed = 0

    for symbol in symbols:
        for timeframe in timeframes:
            completed += 1
            progress.progress(completed / total)
            try:
                artifacts = _run_cached_pipeline(symbol, timeframe, 2, 4, False)
                labelled = pd.read_csv(artifacts["labelled_data"])
                stats = pd.read_csv(artifacts["regime_stats"])
                latest_regime = int(labelled["regime"].iloc[-1])
                latest_stats = stats.loc[stats["regime"] == latest_regime].iloc[0]
                rows.append(
                    {
                        "symbol": symbol,
                        "asset": get_asset(symbol).name,
                        "region": get_asset(symbol).region,
                        "timeframe": TIMEFRAMES[timeframe].label,
                        "latest_regime": latest_stats["regime_name"],
                        "ann_return": latest_stats["annualized_return"],
                        "ann_volatility": latest_stats["annualized_volatility"],
                        "avg_duration": latest_stats["avg_duration_days"],
                    }
                )
            except Exception as exc:  # noqa: BLE001
                rows.append(
                    {
                        "symbol": symbol,
                        "asset": get_asset(symbol).name,
                        "region": get_asset(symbol).region,
                        "timeframe": TIMEFRAMES[timeframe].label,
                        "latest_regime": f"Error: {exc}",
                        "ann_return": None,
                        "ann_volatility": None,
                        "avg_duration": None,
                    }
                )

    snapshot = pd.DataFrame(rows)
    st.dataframe(_format_percent_columns(snapshot), hide_index=True, use_container_width=True)


def render_dashboard() -> None:
    st.set_page_config(page_title="Market Regime Dashboard", layout="wide")
    st.sidebar.title("Controls")
    page = st.sidebar.radio("View", ["Single analysis", "Multi-asset snapshot"])
    if page == "Single analysis":
        _render_single_analysis()
    else:
        _render_snapshot()


def main() -> None:
    from streamlit.web import cli as stcli

    dashboard_file = Path(__file__).resolve()
    sys.argv = ["streamlit", "run", str(dashboard_file), "--server.port", "8501"]
    stcli.main()


if __name__ == "__main__":
    render_dashboard()
