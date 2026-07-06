from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modeling" / "src"))

from market_regime_hmm.timeframes import TIMEFRAMES  # noqa: E402
from market_regime_hmm.universe import ASSET_UNIVERSE, get_asset  # noqa: E402


PUBLIC = ROOT / "public"
PUBLIC_REPORTS = PUBLIC / "reports"


def _safe_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace(".", "_")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _copy_reports() -> None:
    if PUBLIC_REPORTS.exists():
        shutil.rmtree(PUBLIC_REPORTS)
    PUBLIC_REPORTS.mkdir(parents=True, exist_ok=True)

    for folder in ["figures", "tables"]:
        source = ROOT / "reports" / folder
        target = PUBLIC_REPORTS / folder
        target.mkdir(parents=True, exist_ok=True)
        for file in source.glob("*"):
            if file.is_file():
                shutil.copy2(file, target / file.name)


def _known_symbols_by_safe_name() -> dict[str, str]:
    symbols = {asset.symbol for asset in ASSET_UNIVERSE}
    symbols.update({"^GSPC", "^SSMI", "^HSI"})
    return {_safe_ticker(symbol): symbol for symbol in symbols}


def _parse_stem(stats_file: Path) -> tuple[str, str, str]:
    suffix = "_regime_stats"
    base = stats_file.stem.removesuffix(suffix)
    for timeframe in sorted(TIMEFRAMES, key=len, reverse=True):
        timeframe_suffix = f"_{timeframe}"
        if base.endswith(timeframe_suffix):
            safe_symbol = base[: -len(timeframe_suffix)]
            symbol = _known_symbols_by_safe_name().get(safe_symbol, safe_symbol)
            return base, symbol, timeframe
    raise ValueError(f"Cannot parse report stem from {stats_file.name}")


def _float_or_none(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _latest_regime(stem: str, stats: list[dict[str, str]]) -> dict[str, object] | None:
    labelled_path = ROOT / "data" / "processed" / f"{stem}_labelled_regimes.csv"
    if not labelled_path.exists() or not stats:
        return None

    labelled = _read_csv(labelled_path)
    latest = labelled[-1]
    latest_regime = latest["regime"]
    regime_row = next((row for row in stats if row["regime"] == latest_regime), stats[0])
    return {
        "date": latest["date"],
        "regime": int(latest_regime),
        "regimeName": regime_row["regime_name"],
        "annualizedReturn": _float_or_none(regime_row.get("annualized_return")),
        "annualizedVolatility": _float_or_none(regime_row.get("annualized_volatility")),
        "frequency": _float_or_none(regime_row.get("frequency_pct")),
    }


def build_manifest() -> dict[str, object]:
    runs = []
    for stats_file in sorted((ROOT / "reports" / "tables").glob("*_regime_stats.csv")):
        stem, symbol, timeframe = _parse_stem(stats_file)
        asset = get_asset(symbol)
        stats = _read_csv(stats_file)
        model_selection = _read_csv(ROOT / "reports" / "tables" / f"{stem}_model_selection.csv")
        best_model = min(model_selection, key=lambda row: float(row["bic"]))
        runs.append(
            {
                "id": stem,
                "symbol": symbol,
                "safeSymbol": _safe_ticker(symbol),
                "assetName": asset.name,
                "region": asset.region,
                "assetClass": asset.asset_class,
                "description": asset.description,
                "timeframe": timeframe,
                "timeframeLabel": TIMEFRAMES[timeframe].label,
                "latest": _latest_regime(stem, stats),
                "bestModel": {
                    "states": int(best_model["n_states"]),
                    "bic": float(best_model["bic"]),
                    "aic": float(best_model["aic"]),
                },
                "paths": {
                    "priceChart": f"/reports/figures/{stem}_price_regimes.png",
                    "transitionChart": f"/reports/figures/{stem}_transition_matrix.png",
                    "strategyChart": f"/reports/figures/{stem}_strategy_by_regime.png",
                    "modelSelectionChart": f"/reports/figures/{stem}_model_selection.png",
                    "regimeStats": f"/reports/tables/{stem}_regime_stats.csv",
                    "transitionMatrix": f"/reports/tables/{stem}_transition_matrix.csv",
                    "strategy": f"/reports/tables/{stem}_strategy_by_regime.csv",
                    "modelSelection": f"/reports/tables/{stem}_model_selection.csv",
                },
            }
        )

    return {
        "generatedAt": "2026-07-06",
        "project": "Market Regime Detector",
        "method": "Gaussian Hidden Markov Model with BIC state selection",
        "assets": [asset.__dict__ for asset in ASSET_UNIVERSE],
        "timeframes": {key: config.__dict__ for key, config in TIMEFRAMES.items()},
        "runs": runs,
    }


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    _copy_reports()
    manifest = build_manifest()
    (PUBLIC / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Exported {len(manifest['runs'])} dashboard runs to {PUBLIC}")


if __name__ == "__main__":
    main()
