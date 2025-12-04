import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures
import traceback


def fetch_price_data(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Fetch historical price data for a ticker using yfinance.

    Returns a DataFrame with datetime index and columns: Open, High, Low, Close, Adj Close, Volume
    """
    tk = yf.Ticker(ticker)
    df = tk.history(period=period, interval=interval, actions=False)
    if df is None or df.empty:
        raise RuntimeError(f"No data for {ticker}")
    df.index = pd.to_datetime(df.index)
    return df


def fetch_etf_info(ticker: str) -> dict:
    """Fetch basic ETF metadata. yfinance.info can be flaky; we use available fast_info and fallbacks."""
    tk = yf.Ticker(ticker)
    info = {}
    try:
        info_raw = tk.info
    except Exception:
        info_raw = {}
    # safe pulls
    info["ticker"] = ticker
    info["longName"] = info_raw.get("longName") or info_raw.get("shortName") or ticker
    info["sector"] = info_raw.get("category") or info_raw.get("quoteType") or "ETF"
    info["inceptionDate"] = info_raw.get("fundInceptionDate") or info_raw.get("fund_inception_date")
    info["aum"] = info_raw.get("totalAssets") or info_raw.get("assets") or None
    info["expenseRatio"] = info_raw.get("expenseRatio") or info_raw.get("managementFee") or None
    # fallback to fast_info
    try:
        fi = tk.fast_info
        # fast_info has stable keys like 'lastPrice' and 'total_assets'
        info.setdefault("lastPrice", fi.get("lastPrice"))
        if info.get("aum") is None:
            info["aum"] = fi.get("total_assets") if isinstance(fi, dict) else None
    except Exception:
        pass
    return info


def prepare_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add returns columns to price DataFrame."""
    df = df.copy()
    df["ret"] = df["Close"].pct_change()
    return df


def compute_max_drawdown(prices: pd.Series) -> float:
    """Return maximum drawdown as a positive fraction (e.g., 0.25 == 25%)."""
    if prices is None or prices.empty:
        return 0.0
    roll_max = prices.cummax()
    drawdown = (roll_max - prices) / roll_max
    max_dd = drawdown.max()
    return float(max_dd if not pd.isna(max_dd) else 0.0)

import time
import random
import requests
import concurrent.futures
import traceback

def get_spy_and_etf(etf: str, period: str = "2y", interval: str = "1d"):
    """
    Fetch ETF and SPY price data with robust retries, jittered exponential backoff,
    and polite handling of rate limits.

    Returns (etf_df, spy_df) or raises RuntimeError.
    """
    # per-call timeout for each future/result
    per_call_timeout = 40
    max_attempts = 5
    base_backoff = 2.0

    last_exc = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Strategy: fetch ETF first then SPY shortly after.
            # Fetch ETF
            try:
                etf_df = fetch_price_data(etf, period=period, interval=interval)
            except Exception as e_etf:
                raise RuntimeError(f"Failed fetching {etf}: {e_etf}")

            # tiny polite pause to avoid simultaneous hammering from same container
            time.sleep(0.5 + random.random() * 0.5)

            # Fetch SPY
            try:
                spy_df = fetch_price_data("SPY", period=period, interval=interval)
            except Exception as e_spy:
                raise RuntimeError(f"Failed fetching SPY: {e_spy}")

            if etf_df is None or spy_df is None:
                raise RuntimeError("One of the tickers returned None")

            return etf_df, spy_df

        except Exception as e:
            last_exc = e
            msg = str(e).lower()
            # base backoff, then jitter
            sleep_time = base_backoff ** attempt
            # if we detect rate-limit text, increase backoff
            if "too many requests" in msg or "rate limit" in msg or "429" in msg:
                sleep_time = max(sleep_time, 10 + random.random() * 5)
            else:
                # add modest jitter so multiple processes don't retry in lockstep
                sleep_time = sleep_time + random.random() * 2.0

            # logging (server logs)
            print(f"get_spy_and_etf: attempt {attempt} failed: {e}. backing off ~{sleep_time:.1f}s...", flush=True)
            time.sleep(sleep_time)
            continue

    # all attempts failed
    tb = traceback.format_exc()
    raise RuntimeError(f"Failed fetching {etf} after {max_attempts} attempts. Last error: {last_exc}\n{tb}")
