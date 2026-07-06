from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


def download_price_history(
    ticker: str,
    start: str | None,
    end: str | None,
    raw_dir: Path,
    interval: str = "1d",
    period: str | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Download adjusted close prices and cache them as CSV.

    yfinance with auto_adjust=True returns prices adjusted for dividends and splits, which is
    what we want for return calculations.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_ticker = ticker.replace("^", "").replace(".", "_")
    date_part = period or f"{start}_{end or 'latest'}"
    cache_file = raw_dir / f"{safe_ticker}_{interval}_{date_part}.csv"

    if cache_file.exists() and not force:
        prices = pd.read_csv(cache_file, parse_dates=["date"], index_col="date")
        return prices

    downloaded = yf.download(
        ticker,
        start=start,
        end=end,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        group_by="column",
        prepost=False,
    )
    if downloaded.empty:
        raise ValueError(f"No data returned for ticker {ticker!r}.")

    if isinstance(downloaded.columns, pd.MultiIndex):
        downloaded.columns = downloaded.columns.get_level_values(0)

    close_column = "Close" if "Close" in downloaded.columns else "Adj Close"
    prices = downloaded[[close_column]].rename(columns={close_column: "close"}).dropna()
    prices.index.name = "date"
    prices = prices[~prices.index.duplicated(keep="last")]
    prices.to_csv(cache_file)
    return prices
