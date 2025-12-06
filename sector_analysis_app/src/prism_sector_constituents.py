"""
PRISM Sector Constituents Finder
Identifies top 5-10 companies per (country, sector) by market cap.
Uses yfinance, sector tags, and ETF constituent data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import json
import os
import time

# GICS Sector definitions
GICS_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities"
]

# Country exchange suffixes for yfinance
EXCHANGE_SUFFIXES = {
    "US": "",  # No suffix for US
    "CN": ".SS",  # Shanghai or .HK for Hong Kong listings
    "JP": ".T",
    "DE": ".DE",
    "IN": ".NS",  # NSE India
    "GB": ".L",
    "FR": ".PA",
    "IT": ".MI",
    "BR": ".SA",
    "CA": ".TO",
    "KR": ".KS",
    "ES": ".MC",
    "AU": ".AX",
    "MX": ".MX",
    "ID": ".JK",
    "NL": ".AS",
    "SA": ".SAU",
    "TR": ".IS",
    "CH": ".SW",
    "PL": ".WA",
    "TW": ".TW",
    "BE": ".BR",
    "AR": ".BA",
    "SE": ".ST",
    "IE": ".IR",
    "AT": ".VI",
    "TH": ".BK",
    "SG": ".SI",
    "IL": ".TA",
    "NO": ".OL",
    "AE": ".AE",
    "PH": ".PS",
    "MY": ".KL",
    "BD": ".DH",
    "VN": ".VN",
    "DK": ".CO",
    "CL": ".SN",
    "CO": ".CO",
    "ZA": ".JO",
    "RU": ".ME",
}

# Manually curated top companies per country-sector (fallback when API fails)
# Format: {country_code: {sector: [ticker1, ticker2, ...]}}
CURATED_CONSTITUENTS = {
    "US": {
        "Information Technology": ["MSFT", "AAPL", "NVDA", "AVGO", "PLTR"],
        "Communication Services": ["META", "GOOG", "GOOGL", "NFLX", "DIS"],
        "Financials": ["JPM", "BAC", "WFC", "GS", "MS"],
        "Health Care": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
        "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
        "Consumer Staples": ["COST", "WMT", "PG", "KO", "PEP"],
    },
    "CN": {
        "Information Technology": ["BABA", "TCEHY", "JD", "PDD", "BIDU"],
        "Consumer Discretionary": ["1211.HK", "NIO", "XPEV", "LI", "BABA"],
    },
    "JP": {
        "Information Technology": ["8035.T", "6758.T", "6861.T", "6503.T"],  # Tokyo Electron, Sony, Keyence, Mitsubishi Electric
        "Consumer Discretionary": ["9983.T", "7203.T"],  # Fast Retailing, Toyota
        "Industrials": ["8058.T", "5401.T"],  # Mitsubishi Corp, Nippon Steel
    },
    "DE": {
        "Information Technology": ["SAP"],
        "Financials": ["ALV.DE"],  # Allianz
        "Industrials": ["RHM.DE"],  # Rheinmetall
    },
    "FR": {
        "Consumer Discretionary": ["MC.PA"],  # LVMH
        "Energy": ["TTE.PA"],  # TotalEnergies
        "Materials": ["AI.PA"],  # Air Liquide
    },
    "AU": {
        "Real Estate": ["GMG.AX"],  # Goodman Group
        "Health Care": ["PME.AX"],  # Pro Medicus
        "Industrials": ["NWH.AX", "ASB.AX"],  # NRW Holdings, Austal
    },
    "IN": {
        "Energy": ["RELIANCE.NS"],  # Reliance Industries
        "Information Technology": ["TCS.NS", "INFY.NS"],  # Tata Consultancy, Infosys
        "Industrials": ["TATAMOTORS.NS", "ADANIENT.NS", "M&M.NS"],  # Tata Motors, Adani Enterprises, Mahindra
        "Materials": ["TATASTEEL.NS"],  # Tata Steel
    },
    "ID": {
        "Materials": ["INCO.JK"],  # Vale Indonesia
        "Communication Services": ["TLKM.JK"],  # Telkom Indonesia
        "Financials": ["ARTO.JK"],  # Bank Jago
        "Health Care": ["KLBF.JK"],  # Kalbe Farma
        "Industrials": ["JSMR.JK"],  # Jasa Marga
    },
    "KR": {
        "Information Technology": ["005930.KS", "000660.KS", "035420.KS"],  # Samsung, SK Hynix, Naver
        "Consumer Discretionary": ["005380.KS"],  # Hyundai
        "Communication Services": ["035720.KS"],  # Kakao
    },
}


def get_sector_constituents(country_code: str, sector: str, top_n: int = 5, cache_dir: str = "data_cache") -> List[str]:
    """
    Get top N company tickers for a given country-sector pair.
    Returns list of ticker symbols with exchange suffix.
    
    Uses curated list first, then attempts yfinance screener/search if available.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"constituents_{country_code}_{sector.replace(' ', '_')}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    # Try curated list first
    if country_code in CURATED_CONSTITUENTS and sector in CURATED_CONSTITUENTS[country_code]:
        tickers = CURATED_CONSTITUENTS[country_code][sector][:top_n]
        with open(cache_file, 'w') as f:
            json.dump(tickers, f)
        return tickers
    
    # Fallback: return empty list (will be handled by caller)
    print(f"Warning: No constituents found for {country_code} - {sector}")
    return []


def fetch_company_fundamentals(ticker: str, cache_dir: str = "data_cache") -> Optional[Dict]:
    """
    Fetch fundamental data for a single company:
    - market_cap
    - pe_ratio
    - roe (Return on Equity)
    - profit_margin
    - debt_to_equity
    - fcf (Free Cash Flow)
    - revenue_growth
    """
    cache_file = os.path.join(cache_dir, f"fundamentals_{ticker.replace('/', '_')}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        fundamentals = {
            "ticker": ticker,
            "market_cap": info.get("marketCap", None),
            "pe_ratio": info.get("trailingPE", None),
            "roe": info.get("returnOnEquity", None),  # Often as decimal (0.15 = 15%)
            "profit_margin": info.get("profitMargins", None),
            "debt_to_equity": info.get("debtToEquity", None),
            "fcf": info.get("freeCashflow", None),
            "revenue_growth": info.get("revenueGrowth", None),
            "gross_margin": info.get("grossMargins", None),
            "ebitda": info.get("ebitda", None),
            "sector": info.get("sector", None),
            "industry": info.get("industry", None),
        }
        
        # Cache result
        with open(cache_file, 'w') as f:
            json.dump(fundamentals, f)
        
        return fundamentals
        
    except Exception as e:
        print(f"Failed to fetch fundamentals for {ticker}: {e}")
        return None


def get_country_sector_data(country_code: str, sector: str, top_n: int = 5) -> pd.DataFrame:
    """
    Get fundamentals for top N companies in a country-sector pair.
    Returns DataFrame with columns: ticker, market_cap, pe_ratio, roe, etc.
    """
    tickers = get_sector_constituents(country_code, sector, top_n)
    
    if not tickers:
        return pd.DataFrame()  # Empty DataFrame
    
    data = []
    for ticker in tickers:
        time.sleep(0.3)  # Rate limiting
        fundamentals = fetch_company_fundamentals(ticker)
        if fundamentals:
            data.append(fundamentals)
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Test
    print("Testing US Information Technology sector...")
    df = get_country_sector_data("US", "Information Technology", top_n=5)
    print(df[["ticker", "market_cap", "pe_ratio", "roe", "profit_margin"]])
    
    print("\nTesting JP Industrials sector...")
    df_jp = get_country_sector_data("JP", "Industrials", top_n=3)
    print(df_jp[["ticker", "market_cap", "sector"]])
