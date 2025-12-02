import pandas as pd


ETF_METADATA = {
    "XLK": {
        "name": "Technology Select Sector SPDR Fund",
        "description": "Tracks technology sector companies.",
        "category": "Cyclical",
        "life_cycle": "Growth",
    },
    "XLF": {
        "name": "Financial Select Sector SPDR Fund",
        "description": "Tracks financial sector companies.",
        "category": "Cyclical",
        "life_cycle": "Mature",
    },
    "XLY": {
        "name": "Consumer Discretionary Select Sector SPDR Fund",
        "description": "Tracks consumer discretionary sector companies.",
        "category": "Cyclical",
        "life_cycle": "Growth",
    },
    "XLP": {
        "name": "Consumer Staples Select Sector SPDR Fund",
        "description": "Tracks consumer staples sector companies.",
        "category": "Defensive",
        "life_cycle": "Mature",
    },
    "XLE": {
        "name": "Energy Select Sector SPDR Fund",
        "description": "Tracks energy sector companies.",
        "category": "Cyclical",
        "life_cycle": "Shakeout",
    },
    "XLV": {
        "name": "Health Care Select Sector SPDR Fund",
        "description": "Tracks health care sector companies.",
        "category": "Defensive",
        "life_cycle": "Mature",
    },
    "XLI": {
        "name": "Industrial Select Sector SPDR Fund",
        "description": "Tracks industrial sector companies.",
        "category": "Cyclical",
        "life_cycle": "Mature",
    },
    "XLU": {
        "name": "Utilities Select Sector SPDR Fund",
        "description": "Tracks utilities sector companies.",
        "category": "Defensive",
        "life_cycle": "Mature",
    },
}


def get_etf_list():
    return list(ETF_METADATA.keys())


def get_etf_metadata(ticker: str) -> dict:
    base = ETF_METADATA.get(ticker, {})
    return {
        "ticker": ticker,
        "name": base.get("name", ticker),
        "description": base.get("description", ""),
        "category": base.get("category", "Cyclical"),
        "life_cycle": base.get("life_cycle", "Mature"),
    }
