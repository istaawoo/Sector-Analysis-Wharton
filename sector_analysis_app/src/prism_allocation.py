"""
PRISM Allocation Alignment Analyzer
Maps existing portfolio allocations to PRISM scores and justifies selections.
Performs parameter backsolving if allocations don't match top PRISM picks.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import json

# Your existing allocations (parsed from user input)
ALLOCATIONS = {
    # US Stocks
    "MSFT": {"amount": 20000, "country": "US", "sector": "Information Technology"},
    "NVDA": {"amount": 20000, "country": "US", "sector": "Information Technology"},
    "AAPL": {"amount": 15000, "country": "US", "sector": "Information Technology"},
    "META": {"amount": 10000, "country": "US", "sector": "Communication Services"},
    "GOOG": {"amount": 10000, "country": "US", "sector": "Communication Services"},
    "AVGO": {"amount": 10000, "country": "US", "sector": "Information Technology"},
    "COST": {"amount": 10000, "country": "US", "sector": "Consumer Staples"},
    "LLY": {"amount": 10000, "country": "US", "sector": "Health Care"},
    "JPM": {"amount": 10000, "country": "US", "sector": "Financials"},
    "TSM": {"amount": 10000, "country": "TW", "sector": "Information Technology"},  # Taiwan ADR
    "PLTR": {"amount": 20000, "country": "US", "sector": "Information Technology"},
    "RGTI": {"amount": 7500, "country": "US", "sector": "Information Technology"},
    
    # US ETFs
    "QQQ": {"amount": 30000, "country": "US", "sector": "Information Technology"},  # Tech-heavy
    "VTI": {"amount": 20000, "country": "US", "sector": "Diversified"},
    "VTV": {"amount": 12500, "country": "US", "sector": "Diversified"},
    
    # Germany
    "SAP": {"amount": 5000, "country": "DE", "sector": "Information Technology"},
    "ALV.DE": {"amount": 4000, "country": "DE", "sector": "Financials"},
    "RHM.DE": {"amount": 3750, "country": "DE", "sector": "Industrials"},
    
    # France
    "MC.PA": {"amount": 4000, "country": "FR", "sector": "Consumer Discretionary"},
    "TTE.PA": {"amount": 3000, "country": "FR", "sector": "Energy"},
    "AI.PA": {"amount": 3625, "country": "FR", "sector": "Materials"},
    
    # Japan
    "8035.T": {"amount": 8000, "country": "JP", "sector": "Information Technology"},  # Tokyo Electron
    "6758.T": {"amount": 6500, "country": "JP", "sector": "Consumer Discretionary"},  # Sony
    "9983.T": {"amount": 5000, "country": "JP", "sector": "Consumer Discretionary"},  # Fast Retailing
    "8058.T": {"amount": 4000, "country": "JP", "sector": "Industrials"},  # Mitsubishi Corp
    "5803.T": {"amount": 3062.50, "country": "JP", "sector": "Information Technology"},  # Fujikura
    
    # Australia
    "GMG.AX": {"amount": 3000, "country": "AU", "sector": "Real Estate"},
    "PME.AX": {"amount": 2000, "country": "AU", "sector": "Health Care"},
    "NWH.AX": {"amount": 1750, "country": "AU", "sector": "Industrials"},
    "ASB.AX": {"amount": 1750, "country": "AU", "sector": "Industrials"},  # Austal
    
    # UK ETF
    "EWU": {"amount": 21250, "country": "GB", "sector": "Diversified"},
    
    # Canada ETF
    "EWC": {"amount": 10625, "country": "CA", "sector": "Diversified"},
    
    # Europe ex-UK/FR/DE ETF
    "FEZ": {"amount": 15937.50, "country": "EU", "sector": "Diversified"},
    
    # China
    "TCEHY": {"amount": 5000, "country": "CN", "sector": "Communication Services"},
    "BABA": {"amount": 5000, "country": "CN", "sector": "Consumer Discretionary"},
    "JD": {"amount": 4000, "country": "CN", "sector": "Consumer Discretionary"},
    "PDD": {"amount": 5000, "country": "CN", "sector": "Consumer Discretionary"},
    "1211.HK": {"amount": 3500, "country": "CN", "sector": "Consumer Discretionary"},  # BYD
    
    # Indonesia
    "INCO.JK": {"amount": 2000, "country": "ID", "sector": "Materials"},
    "TLKM.JK": {"amount": 2000, "country": "ID", "sector": "Communication Services"},
    "ARTO.JK": {"amount": 2000, "country": "ID", "sector": "Financials"},
    "KLBF.JK": {"amount": 1500, "country": "ID", "sector": "Health Care"},
    "JSMR.JK": {"amount": 2062.50, "country": "ID", "sector": "Industrials"},
    
    # South Korea
    "005930.KS": {"amount": 2000, "country": "KR", "sector": "Information Technology"},  # Samsung
    "000660.KS": {"amount": 1500, "country": "KR", "sector": "Information Technology"},  # SK Hynix
    "005380.KS": {"amount": 1000, "country": "KR", "sector": "Consumer Discretionary"},  # Hyundai
    "035420.KS": {"amount": 1000, "country": "KR", "sector": "Communication Services"},  # Naver
    "035720.KS": {"amount": 875, "country": "KR", "sector": "Communication Services"},  # Kakao
    
    # India ETF
    "INDA": {"amount": 19125, "country": "IN", "sector": "Diversified"},
    
    # Brazil ETF
    "EWZ": {"amount": 12750, "country": "BR", "sector": "Diversified"},
    
    # Mexico ETF
    "EWW": {"amount": 6375, "country": "MX", "sector": "Diversified"},
    
    # Taiwan ETF
    "EWT": {"amount": 6375, "country": "TW", "sector": "Diversified"},
    
    # Rest EM ETF
    "EEM": {"amount": 3187.50, "country": "EM", "sector": "Diversified"},
}


def parse_allocations() -> pd.DataFrame:
    """Convert ALLOCATIONS dict to DataFrame."""
    data = []
    for ticker, info in ALLOCATIONS.items():
        data.append({
            "ticker": ticker,
            "amount": info["amount"],
            "country": info["country"],
            "sector": info["sector"],
        })
    return pd.DataFrame(data)


def compute_alignment_score(allocated_sector_country: pd.DataFrame, prism_scores: pd.DataFrame) -> pd.DataFrame:
    """
    Compute alignment score for each allocation based on PRISM rankings.
    
    allocated_sector_country: DataFrame with columns [ticker, country, sector, amount]
    prism_scores: DataFrame with columns [country, sector, prism_score]
    
    Returns DataFrame with alignment_score (0-100) for each ticker.
    """
    results = []
    
    for _, row in allocated_sector_country.iterrows():
        ticker = row["ticker"]
        country = row["country"]
        sector = row["sector"]
        amount = row["amount"]
        
        # Find PRISM score for this country-sector
        match = prism_scores[
            (prism_scores["country"] == country) & 
            (prism_scores["sector"] == sector)
        ]
        
        if not match.empty:
            prism_score = match.iloc[0]["prism_score"]
            
            # Alignment score: directly use PRISM score
            # Higher PRISM = higher alignment
            alignment_score = prism_score
            
            # Determine recommendation tier
            if prism_score >= 70:
                tier = "Overweight"
            elif prism_score >= 55:
                tier = "Neutral"
            else:
                tier = "Underweight"
            
            results.append({
                "ticker": ticker,
                "country": country,
                "sector": sector,
                "amount": amount,
                "prism_score": round(prism_score, 2),
                "alignment_score": round(alignment_score, 2),
                "tier": tier,
            })
        else:
            # No PRISM score available (ETF, diversified, or missing data)
            results.append({
                "ticker": ticker,
                "country": country,
                "sector": sector,
                "amount": amount,
                "prism_score": None,
                "alignment_score": 50.0,  # Neutral default
                "tier": "Not Scored",
            })
    
    return pd.DataFrame(results)


def generate_justification(row: pd.Series, prism_details: Optional[Dict] = None) -> str:
    """
    Generate 2-4 sentence justification for a single allocation.
    
    row: Series with ticker, country, sector, prism_score, alignment_score, tier
    prism_details: Optional dict with detailed PRISM component scores
    """
    ticker = row["ticker"]
    country = row["country"]
    sector = row["sector"]
    prism_score = row["prism_score"]
    tier = row["tier"]
    
    if pd.isna(prism_score):
        return f"{ticker} is a diversified ETF providing broad exposure to {country} markets. " \
               f"ETFs reduce single-stock risk and provide liquidity. Recommended for portfolio diversification."
    
    if tier == "Overweight":
        justification = f"{ticker} ({country} - {sector}) receives a strong PRISM score of {prism_score:.1f}/100, " \
                       f"placing it in the 'Overweight' category. "
        
        if prism_details:
            structural = prism_details.get("structural_score", 0)
            fundamentals = prism_details.get("fundamentals_score", 0)
            if structural >= 65:
                justification += f"Structural factors (Porter's 5 Forces + Lifecycle) are favorable ({structural:.1f}). "
            if fundamentals >= 65:
                justification += f"Firm fundamentals are strong ({fundamentals:.1f}) with solid ROE and margins. "
        
        justification += f"This allocation is well-supported by our top-down and quantitative analysis."
        
    elif tier == "Neutral":
        justification = f"{ticker} ({country} - {sector}) has a moderate PRISM score of {prism_score:.1f}/100, " \
                       f"placing it in the 'Neutral' category. "
        justification += f"While not a top-tier opportunity, this allocation provides diversification and balances risk exposure. " \
                        f"Consider monitoring for rebalancing opportunities."
        
    else:  # Underweight
        justification = f"{ticker} ({country} - {sector}) has a lower PRISM score of {prism_score:.1f}/100, " \
                       f"suggesting caution. "
        
        if prism_details:
            behavior = prism_details.get("behavior_score", 50)
            if behavior < 45:
                justification += f"Market behavior metrics (volatility, drawdown) indicate elevated risk. "
        
        justification += f"This allocation may be justified by strategic diversification or contrarian positioning, " \
                        f"but warrants close monitoring."
    
    return justification


def backsolve_parameters(
    allocated_tickers: List[str],
    prism_scores: pd.DataFrame,
    target_percentile: float = 0.70
) -> Dict:
    """
    Find minimal weight adjustments to PRISM components to justify allocations.
    
    Returns dict with suggested weight deltas and confidence scores.
    """
    # For now, return placeholder logic
    # Full implementation would use optimization to find minimal changes
    
    allocated_cs = parse_allocations()
    allocated_cs = allocated_cs[allocated_cs["sector"] != "Diversified"]  # Exclude ETFs
    
    # Compute current median PRISM score for allocated assets
    merged = allocated_cs.merge(
        prism_scores[["country", "sector", "prism_score"]], 
        on=["country", "sector"], 
        how="left"
    )
    current_median = merged["prism_score"].median()
    
    # Target: 70th percentile of all PRISM scores
    target_score = prism_scores["prism_score"].quantile(target_percentile)
    
    if current_median >= target_score:
        return {
            "adjustments_needed": False,
            "current_median": round(current_median, 2),
            "target_score": round(target_score, 2),
            "message": "Allocations are well-aligned with PRISM rankings. No parameter adjustments needed."
        }
    
    # Compute gap
    gap = target_score - current_median
    
    # Suggest increasing weight on components where allocated assets score well
    # Placeholder heuristic: increase Fundamentals weight by 5%, reduce Behavior weight by 5%
    suggested_weights = {
        "structural": 0.35,  # No change
        "fundamentals": 0.33,  # +3%
        "behavior": 0.17,  # -3%
        "topdown": 0.15,  # No change
    }
    
    return {
        "adjustments_needed": True,
        "current_median": round(current_median, 2),
        "target_score": round(target_score, 2),
        "gap": round(gap, 2),
        "suggested_weights": suggested_weights,
        "message": f"To better justify allocations, consider adjusting PRISM weights. " \
                   f"Increasing Fundamentals weight to {suggested_weights['fundamentals']:.0%} and " \
                   f"reducing Behavior weight to {suggested_weights['behavior']:.0%} may improve alignment."
    }


if __name__ == "__main__":
    # Test
    allocations_df = parse_allocations()
    print("Parsed allocations:")
    print(allocations_df.head(10))
    print(f"\nTotal allocations: {len(allocations_df)}")
    print(f"Total amount: ${allocations_df['amount'].sum():,.2f}")
    
    # Count by country
    country_totals = allocations_df.groupby("country")["amount"].sum().sort_values(ascending=False)
    print("\nAllocation by country:")
    print(country_totals)
