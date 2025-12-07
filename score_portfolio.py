"""
Quick script to compute PRISM scores for your specific portfolio holdings.
Much faster than running all 440 country-sector pairs.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sector_analysis_app", "src"))

from prism_scoring import compute_prism_score
from prism_country_data import get_country_metadata
from prism_sector_constituents import get_country_sector_data
import pandas as pd

# Your portfolio holdings (country-sector pairs)
portfolio_holdings = [
    ("US", "Information Technology"),  # MSFT, NVDA, AAPL, AVGO, PLTR, RGTI
    ("US", "Communication Services"),  # META, GOOG
    ("US", "Consumer Staples"),        # COST
    ("US", "Health Care"),              # LLY
    ("US", "Financials"),               # JPM
    ("TW", "Information Technology"),  # TSM
    ("DE", "Information Technology"),  # SAP
    ("DE", "Financials"),               # ALV
    ("DE", "Industrials"),              # RHM
    ("FR", "Consumer Discretionary"),  # LVMH (MC.PA)
    ("FR", "Energy"),                   # TTE
    ("FR", "Materials"),                # AI (Air Liquide)
    ("JP", "Information Technology"),  # Tokyo Electron, Fujikura
    ("JP", "Consumer Discretionary"),  # Sony, Fast Retailing
    ("JP", "Industrials"),              # Mitsubishi Corp
    ("CN", "Communication Services"),  # Tencent
    ("CN", "Consumer Discretionary"),  # BABA, JD, PDD
    ("IN", "Financials"),               # Indian banks
    ("BR", "Diversified"),              # ETF
]

print("=" * 90)
print("YOUR PORTFOLIO SCORING - PRISM with Optimized Weights")
print("Weights: 30% TopDown | 35% Structural | 20% Fundamentals | 15% Behavior")
print("=" * 90)
print()

results = []

for country, sector in portfolio_holdings:
    try:
        print(f"Scoring {country:3s} - {sector:25s}...", end=" ")
        
        country_meta = get_country_metadata(country)
        firms_df = get_country_sector_data(country, sector, top_n=5)
        
        result = compute_prism_score(country, country_meta, sector, firms_df)
        prism = result["prism_score"]
        
        # Tier classification
        if prism >= 62:
            tier = "AGGRESSIVE (62+)"
            tier_label = "[AGG]"
        elif prism >= 55:
            tier = "MOD. AGGRESSIVE (55-61)"
            tier_label = "[MA] "
        elif prism >= 48:
            tier = "MODERATE (48-54)"
            tier_label = "[MOD]"
        else:
            tier = "CONSERVATIVE (<48)"
            tier_label = "[CON]"
        
        print(f"{tier_label} {prism:5.1f}/100 - {tier}")
        
        results.append({
            "Country": country,
            "Sector": sector,
            "PRISM Score": prism,
            "Structural": result["structural_score"],
            "Fundamentals": result["fundamentals_score"],
            "TopDown": result["topdown_score"],
            "Behavior": result["behavior_score"],
            "Tier": tier
        })
        
    except Exception as e:
        print(f"ERROR - {str(e)[:60]}")

# Print summary
print()
print("=" * 90)
print("PORTFOLIO SUMMARY")
print("=" * 90)
if results:
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print()
    avg_score = df["PRISM Score"].mean()
    print(f"Average PRISM Score: {avg_score:.1f}/100")
    if avg_score >= 55:
        print(f"RESULT: Portfolio scores as MODERATELY AGGRESSIVE ({avg_score:.1f}) - justified!")
    elif avg_score >= 48:
        print(f"RESULT: Portfolio scores as MODERATE ({avg_score:.1f}) - needs tuning")
    else:
        print(f"RESULT: Portfolio scores as CONSERVATIVE ({avg_score:.1f}) - too low")
    print()
    print("Breakdown by Tier:")
    for tier in ["AGGRESSIVE (62+)", "MOD. AGGRESSIVE (55-61)", "MODERATE (48-54)", "CONSERVATIVE (<48)"]:
        count = len(df[df["Tier"] == tier])
        if count > 0:
            total_score = df[df["Tier"] == tier]["PRISM Score"].sum()
            avg = df[df["Tier"] == tier]["PRISM Score"].mean()
            print(f"  {tier:25s}: {count:2d} holdings, avg {avg:5.1f}/100")
