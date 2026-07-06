from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketAsset:
    symbol: str
    name: str
    region: str
    asset_class: str
    description: str


ASSET_UNIVERSE: list[MarketAsset] = [
    MarketAsset("BTC-USD", "Bitcoin", "Crypto", "Crypto", "Large-cap digital asset"),
    MarketAsset("ETH-USD", "Ethereum", "Crypto", "Crypto", "Large-cap smart-contract asset"),
    MarketAsset("^GSPC", "S&P 500", "Global / US", "Equity index", "Broad US equity benchmark"),
    MarketAsset("^IXIC", "Nasdaq Composite", "Global / US", "Equity index", "US growth and technology-heavy benchmark"),
    MarketAsset("ACWI", "iShares MSCI ACWI ETF", "Global", "ETF", "Global developed and emerging equity proxy"),
    MarketAsset("^STOXX50E", "Euro Stoxx 50", "Europe", "Equity index", "Eurozone blue-chip benchmark"),
    MarketAsset("^SSMI", "Swiss Market Index", "Switzerland", "Equity index", "Swiss blue-chip equity benchmark"),
    MarketAsset("CHSPI.SW", "Swiss Performance Index", "Switzerland", "Equity index", "Broad Swiss equity benchmark"),
    MarketAsset("000300.SS", "CSI 300", "China", "Equity index", "Mainland China large-cap A-share benchmark"),
    MarketAsset("000001.SS", "Shanghai Composite", "China", "Equity index", "Broad Shanghai equity benchmark"),
    MarketAsset("^HSI", "Hang Seng Index", "China / Hong Kong", "Equity index", "Hong Kong-listed China and regional benchmark"),
]


def assets_by_region() -> dict[str, list[MarketAsset]]:
    grouped: dict[str, list[MarketAsset]] = {}
    for asset in ASSET_UNIVERSE:
        grouped.setdefault(asset.region, []).append(asset)
    return grouped


def get_asset(symbol: str) -> MarketAsset:
    for asset in ASSET_UNIVERSE:
        if asset.symbol == symbol:
            return asset
    return MarketAsset(symbol, symbol, "Custom", "Unknown", "User supplied ticker")


def is_crypto(symbol: str) -> bool:
    return get_asset(symbol).asset_class.lower() == "crypto" or symbol.upper().endswith("-USD")
