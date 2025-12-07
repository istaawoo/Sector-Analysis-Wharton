"""
PRISM Scoring Engine
Computes PRISM scores (0-100) for country-sector pairs using:
- Structural Score (35%): Porter's 5 Forces + Industry Life Cycle
- Fundamental Quality Score (30%): Market-cap weighted firm fundamentals
- Market Behavior Score (20%): Recent performance & risk metrics
- Mission-Fit & Top-Down Score (15%): Country macro + top-down frameworks
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def normalize(value: float, min_val: float, max_val: float, invert: bool = False) -> float:
    """
    Normalize value to 0-100 scale.
    If invert=True, higher input values result in lower scores.
    """
    if value is None or np.isnan(value):
        return 50.0  # Neutral default
    
    value = np.clip(value, min_val, max_val)
    normalized = 100 * (value - min_val) / (max_val - min_val) if max_val > min_val else 50.0
    
    if invert:
        normalized = 100 - normalized
    
    return normalized


def compute_firm_score(fundamentals: Dict) -> float:
    """
    Compute normalized firm-level score (0-100) from fundamentals.
    Weights: FCF 25% (cash generation), ROE 25% (profitability), Profit Margin 20%, 
             Gross Margin 15%, Revenue Growth 10%, Debt/Equity 5%
    Emphasizes cash generation and profitability over leverage (tech/growth focus).
    When data is sparse (emerging markets), defaults to 55 (slightly positive) rather than 50.
    """
    if not fundamentals or fundamentals.get("market_cap") is None:
        return 55.0  # Slight positive default (vs 50 neutral) for international stocks
    
    # Extract and normalize each metric
    roe = fundamentals.get("roe", None)
    if roe is not None:
        roe = roe * 100 if roe < 1 else roe  # Convert decimal to percentage
    
    profit_margin = fundamentals.get("profit_margin", None)
    if profit_margin is not None:
        profit_margin = profit_margin * 100 if profit_margin < 1 else profit_margin
    
    revenue_growth = fundamentals.get("revenue_growth", None)
    if revenue_growth is not None:
        revenue_growth = revenue_growth * 100 if abs(revenue_growth) < 5 else revenue_growth
    
    gross_margin = fundamentals.get("gross_margin", None)
    if gross_margin is not None:
        gross_margin = gross_margin * 100 if gross_margin < 1 else gross_margin
    
    debt_to_equity = fundamentals.get("debt_to_equity", None)
    
    fcf = fundamentals.get("fcf", None)
    market_cap = fundamentals.get("market_cap", 1)
    fcf_to_mcap = (fcf / market_cap * 100) if fcf and market_cap else None
    
    # Normalize each component
    roe_score = normalize(roe, -10, 40, invert=False) if roe is not None else 55
    margin_score = normalize(profit_margin, -10, 50, invert=False) if profit_margin is not None else 55
    growth_score = normalize(revenue_growth, -20, 50, invert=False) if revenue_growth is not None else 55
    fcf_score = normalize(fcf_to_mcap, -5, 15, invert=False) if fcf_to_mcap is not None else 55
    debt_score = normalize(debt_to_equity, 0, 300, invert=True) if debt_to_equity is not None else 55
    gross_score = normalize(gross_margin, 0, 80, invert=False) if gross_margin is not None else 55
    
    # Weighted average: FCF (25%), ROE (25%), Profit Margin (20%), Gross Margin (15%), Growth (10%), Debt (5%)
    firm_score = (
        0.25 * fcf_score +
        0.25 * roe_score +
        0.20 * margin_score +
        0.15 * gross_score +
        0.10 * growth_score +
        0.05 * debt_score
    )
    
    return firm_score


def compute_sector_fundamentals(firms_df: pd.DataFrame) -> float:
    """
    Compute market-cap weighted average fundamental score for a sector.
    firms_df must have columns: ticker, market_cap, and other fundamentals.
    """
    if firms_df.empty:
        return 50.0
    
    # Compute firm scores
    firms_df["firm_score"] = firms_df.apply(
        lambda row: compute_firm_score(row.to_dict()), axis=1
    )
    
    # Market-cap weighting
    total_mcap = firms_df["market_cap"].sum()
    if total_mcap == 0 or pd.isna(total_mcap):
        # Equal weight if market cap data missing
        return firms_df["firm_score"].mean()
    
    firms_df["weight"] = firms_df["market_cap"] / total_mcap
    weighted_score = (firms_df["firm_score"] * firms_df["weight"]).sum()
    
    return weighted_score


def compute_structural_score(
    sector: str,
    country_code: str,
    firms_df: pd.DataFrame,
    r_and_d_intensity: float = 5.0,
    hhi: float = 2000,
    regulation_flag: int = 0,
    lifecycle_stage: str = "Mature"
) -> Dict:
    """
    Compute Structural Score (Porter's 5 Forces + Industry Life Cycle).
    Returns dict with component scores and final structural_score (0-100).
    """
    # Porter's 5 Forces (each 1-5, then average and normalize to 0-100)
    
    # 1. Barriers to entry (R&D intensity, regulation)
    barriers = 3.0  # Default medium
    if r_and_d_intensity > 10:
        barriers = 4.5
    elif r_and_d_intensity > 5:
        barriers = 3.5
    else:
        barriers = 2.5
    if regulation_flag == 1:
        barriers += 0.5
    barriers = min(barriers, 5.0)
    
    # 2. Threat of substitutes (sector-specific heuristic)
    substitutes = 3.0
    if sector in ["Information Technology", "Communication Services"]:
        substitutes = 4.0  # High threat
    elif sector in ["Utilities", "Real Estate"]:
        substitutes = 2.0  # Low threat
    
    # 3. Supplier power (HHI proxy)
    supplier_power = normalize(hhi, 0, 5000, invert=False) / 20  # Scale to 1-5
    supplier_power = np.clip(supplier_power, 1, 5)
    
    # 4. Buyer power (assume medium for most, adjust for consumer sectors)
    buyer_power = 3.0
    if sector in ["Consumer Discretionary", "Consumer Staples"]:
        buyer_power = 3.5
    
    # 5. Rivalry (HHI inverse - lower HHI = more rivalry)
    rivalry = normalize(hhi, 0, 5000, invert=True) / 20
    rivalry = np.clip(rivalry, 1, 5)
    
    porter_avg = (barriers + substitutes + supplier_power + buyer_power + rivalry) / 5
    porter_score = normalize(porter_avg, 1, 5, invert=False)
    
    # Lifecycle score
    lifecycle_map = {
        "Intro": 2.0,
        "Growth": 4.0,
        "Shakeout": 3.0,
        "Mature": 3.5,
        "Decline": 2.5
    }
    lifecycle_val = lifecycle_map.get(lifecycle_stage, 3.5)
    lifecycle_score = normalize(lifecycle_val, 1, 5, invert=False)
    
    # Combine: 70% Porter + 30% Lifecycle
    structural_score = 0.70 * porter_score + 0.30 * lifecycle_score
    
    return {
        "porter_score": round(porter_score, 2),
        "lifecycle_score": round(lifecycle_score, 2),
        "structural_score": round(structural_score, 2),
        "barriers": round(barriers, 2),
        "substitutes": round(substitutes, 2),
        "rivalry": round(rivalry, 2),
    }


def fetch_price_data(ticker: str, period: str = "2y") -> Optional[pd.DataFrame]:
    """Fetch historical price data for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception as e:
        print(f"Failed to fetch price data for {ticker}: {e}")
        return None


def compute_market_behavior_score(firms_df: pd.DataFrame, country_code: str) -> Dict:
    """
    Compute Market Behavior Score using price data:
    - 12m return, 6m return
    - Annualized volatility
    - Max drawdown
    - Beta vs SPY (for US) or regional benchmark
    
    Returns dict with component scores and final market_behavior_score (0-100).
    Note: Higher volatility is penalized less heavily for growth stocks (risk-adjusted).
    """
    if firms_df.empty:
        return {"market_behavior_score": 50.0}
    
    # Use largest company as proxy for sector behavior
    firms_sorted = firms_df.sort_values("market_cap", ascending=False)
    representative_ticker = firms_sorted.iloc[0]["ticker"]
    
    price_df = fetch_price_data(representative_ticker, period="2y")
    if price_df is None or price_df.empty:
        return {"market_behavior_score": 50.0}
    
    close_prices = price_df["Close"]
    
    # 12-month and 6-month returns
    if len(close_prices) > 252:
        ret_12m = (close_prices.iloc[-1] / close_prices.iloc[-252] - 1) if len(close_prices) >= 252 else 0
    else:
        ret_12m = (close_prices.iloc[-1] / close_prices.iloc[0] - 1) if len(close_prices) > 0 else 0
    
    if len(close_prices) > 126:
        ret_6m = (close_prices.iloc[-1] / close_prices.iloc[-126] - 1) if len(close_prices) >= 126 else 0
    else:
        ret_6m = ret_12m
    
    # Annualized volatility
    daily_returns = close_prices.pct_change().dropna()
    ann_vol = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 20 else 0.3
    
    # Max drawdown
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.2
    
    # Beta (vs SPY for simplicity)
    try:
        spy = yf.Ticker("SPY").history(period="1y")["Close"]
        if len(spy) > 20 and len(close_prices) > 20:
            # Align dates
            aligned = pd.DataFrame({"asset": close_prices, "spy": spy}).dropna()
            if len(aligned) > 20:
                asset_ret = aligned["asset"].pct_change().dropna()
                spy_ret = aligned["spy"].pct_change().dropna()
                covariance = asset_ret.cov(spy_ret)
                spy_variance = spy_ret.var()
                beta = covariance / spy_variance if spy_variance > 0 else 1.0
            else:
                beta = 1.0
        else:
            beta = 1.0
    except:
        beta = 1.0
    
    # Normalize components (less harsh on volatility for quality stocks)
    ret_12m_score = normalize(ret_12m, -0.5, 1.0, invert=False)  # Higher return = better
    ret_6m_score = normalize(ret_6m, -0.5, 1.0, invert=False)
    vol_score = normalize(ann_vol, 0.1, 1.0, invert=True)  # Higher vol penalty reduced
    dd_score = normalize(max_drawdown, 0, 0.6, invert=True)  # Drawdown still matters
    beta_score = normalize(beta, 0.5, 2.5, invert=True)  # Beta tolerance increased
    
    # Combine: Returns (25% + 25%), Volatility (20%), Drawdown (20%), Beta (10%)
    # Emphasis on returns, less on vol/beta since high-quality growth stocks are naturally volatile
    market_behavior_score = (
        0.25 * ret_12m_score + 
        0.25 * ret_6m_score + 
        0.20 * vol_score + 
        0.20 * dd_score + 
        0.10 * beta_score
    )
    
    return {
        "market_behavior_score": round(market_behavior_score, 2),
        "ret_12m": round(ret_12m, 4),
        "ret_6m": round(ret_6m, 4),
        "ann_vol": round(ann_vol, 4),
        "max_drawdown": round(max_drawdown, 4),
        "beta": round(beta, 3),
    }


def compute_topdown_score(
    country_meta: Dict,
    swot_strength: int = 3,
    swot_weakness: int = 3,
    swot_opportunity: int = 3,
    swot_threat: int = 3,
) -> Dict:
    """
    Compute Top-Down Mission-Fit Score using country macro and SWOT.
    Favors developed markets with institutional strength, rule of law, capital markets.
    Returns dict with component scores and final topdown_score (0-100).
    """
    gdp_growth = country_meta.get("gdp_growth", 2.0)
    gdp_per_capita = country_meta.get("gdp_per_capita", 20000)
    gdp_billions = country_meta.get("gdp_billions", 500)  # Use economic scale
    
    # GDP per capita score (higher = more stable, mature market) - 40% weight
    gdp_pc_score = normalize(gdp_per_capita, 1000, 100000, invert=False)
    
    # Economic scale score (larger economies = more diversified, institutional) - 40% weight
    # Favors US ($25T), Japan ($4T), Germany ($5T) over small economies
    scale_score = normalize(gdp_billions, 100, 30000, invert=False)
    
    # GDP growth score (higher = better opportunity) - 15% weight
    # De-emphasize growth since high-growth small economies lack stability
    growth_score = normalize(gdp_growth, -2, 8, invert=False)
    
    # SWOT score: net strength-weakness + opportunity-threat - 5% weight
    swot_net = (swot_strength - swot_weakness) + (swot_opportunity - swot_threat)
    swot_score = normalize(swot_net, -8, 8, invert=False)
    
    # Combine: 40% GDP per capita (stability), 40% economic scale (institutions/diversification), 15% growth, 5% SWOT
    topdown_score = 0.40 * gdp_pc_score + 0.40 * scale_score + 0.15 * growth_score + 0.05 * swot_score
    
    return {
        "topdown_score": round(topdown_score, 2),
        "growth_score": round(growth_score, 2),
        "gdp_pc_score": round(gdp_pc_score, 2),
        "swot_score": round(swot_score, 2),
    }


def compute_prism_score(
    country_code: str,
    country_meta: Dict,
    sector: str,
    firms_df: pd.DataFrame,
    **kwargs
) -> Dict:
    """
    Compute final PRISM score (0-100) for a country-sector pair.
    
    Components:
    - Fundamentals (40%): Strong firm-level quality drives long-term returns
    - Structural (30%): Industry attractiveness and competitive positioning
    - Top-Down (20%): Country macro stability and growth opportunity
    - Market Behavior (10%): Recent performance; de-weighted to reduce noise
    
    Returns dict with all component scores and final PRISM score.
    """
    # 1. Structural
    structural = compute_structural_score(
        sector=sector,
        country_code=country_code,
        firms_df=firms_df,
        r_and_d_intensity=kwargs.get("r_and_d_intensity", 5.0),
        hhi=kwargs.get("hhi", 2000),
        regulation_flag=kwargs.get("regulation_flag", 0),
        lifecycle_stage=kwargs.get("lifecycle_stage", "Mature"),
    )
    structural_score = structural["structural_score"]
    
    # 2. Fundamentals
    fundamentals_score = compute_sector_fundamentals(firms_df)
    
    # 3. Market Behavior
    behavior = compute_market_behavior_score(firms_df, country_code)
    behavior_score = behavior["market_behavior_score"]
    
    # 4. Top-Down
    topdown = compute_topdown_score(
        country_meta=country_meta,
        swot_strength=kwargs.get("swot_strength", 3),
        swot_weakness=kwargs.get("swot_weakness", 3),
        swot_opportunity=kwargs.get("swot_opportunity", 3),
        swot_threat=kwargs.get("swot_threat", 3),
    )
    topdown_score = topdown["topdown_score"]
    
    # Combine with optimized weights for global portfolio:
    # Fundamentals (35%) - rewards quality, but defaults to 55 for missing intl data
    # Structural (30%) - consistent across countries
    # Top-Down (25%) - favors developed markets with institutional strength  
    # Behavior (10%) - de-emphasizes volatility for growth stocks
    prism_score = (
        0.35 * fundamentals_score +
        0.30 * structural_score +
        0.25 * topdown_score +
        0.10 * behavior_score
    )
    
    return {
        "country": country_code,
        "country_name": country_meta.get("name", country_code),
        "sector": sector,
        "prism_score": round(prism_score, 2),
        "structural_score": round(structural_score, 2),
        "fundamentals_score": round(fundamentals_score, 2),
        "behavior_score": round(behavior_score, 2),
        "topdown_score": round(topdown_score, 2),
        "num_firms": len(firms_df),
        "top_firms": firms_df["ticker"].tolist() if not firms_df.empty else [],
        **structural,
        **behavior,
        **topdown,
    }


if __name__ == "__main__":
    # Test with mock data
    from prism_sector_constituents import get_country_sector_data
    from prism_country_data import get_country_metadata
    
    country = "US"
    sector = "Information Technology"
    
    print(f"Computing PRISM score for {country} - {sector}...")
    country_meta = get_country_metadata(country)
    firms_df = get_country_sector_data(country, sector, top_n=5)
    
    if not firms_df.empty:
        prism_result = compute_prism_score(country, country_meta, sector, firms_df)
        print("\nPRISM Result:")
        for k, v in prism_result.items():
            print(f"  {k}: {v}")
    else:
        print("No firm data available")
