from __future__ import annotations

import argparse
from pathlib import Path

from market_regime_hmm.pipeline import PipelineConfig, run_pipeline
from market_regime_hmm.timeframes import TIMEFRAMES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect market regimes from index prices with a Gaussian Hidden Markov Model."
    )
    parser.add_argument("--ticker", default="^GSPC", help="Yahoo Finance ticker, e.g. ^GSPC or ^SSMI.")
    parser.add_argument("--start", default=None, help="Optional start date in YYYY-MM-DD format.")
    parser.add_argument("--end", default=None, help="Optional end date in YYYY-MM-DD format.")
    parser.add_argument(
        "--timeframe",
        default="1d",
        choices=sorted(TIMEFRAMES),
        help="Bar timeframe / sampling interval.",
    )
    parser.add_argument("--state-min", type=int, default=2, help="Minimum number of HMM states.")
    parser.add_argument("--state-max", type=int, default=4, help="Maximum number of HMM states.")
    parser.add_argument("--force-download", action="store_true", help="Ignore cached raw price data.")
    parser.add_argument(
        "--project-root",
        default=".",
        type=Path,
        help="Project root where data/ and reports/ will be written.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.state_min < 2 or args.state_max < args.state_min:
        raise SystemExit("--state-min must be >= 2 and --state-max must be >= --state-min.")

    artifacts = run_pipeline(
        PipelineConfig(
            ticker=args.ticker,
            start=args.start,
            end=args.end,
            timeframe=args.timeframe,
            project_root=args.project_root,
            force_download=args.force_download,
            state_min=args.state_min,
            state_max=args.state_max,
        )
    )
    print("Generated artifacts:")
    for name, path in artifacts.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
