"""
Quick test to check what your portfolio stocks score with new PRISM weights.
"""
import sys
import os
import pandas as pd

# Add paths
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sector_analysis_app", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from prism_scoring import compute_prism_score
from prism_country_data import get_country_metadata
from prism_sector_constituents import get_country_sector_data

# Your key holdings to test
test_holdings = [
    ("US", "Information Technology", "MSFT, NVDA, AAPL"),
    ("US", "Communication Services", "META, GOOG"),
    ("TW", "Information Technology", "TSM"),
    ("JP", "Consumer Discretionary", "Sony"),
    ("DE", "Information Technology", "SAP"),
    ("FR", "Consumer Discretionary", "LVMH"),
    ("CN", "Consumer Discretionary", "BABA, JD, PDD"),
    ("IN", "Financials", "Indian banks"),
    ("BR", "Diversified", "ETF"),
]

print("=" * 80)
print("PORTFOLIO SCORING TEST - New PRISM Weights")
print("Weights: Fundamentals 40%, Structural 30%, TopDown 20%, Behavior 10%")
print("=" * 80)
print()

scores = []

for country, sector, examples in test_holdings:
    try:
        country_meta = get_country_metadata(country)
        firms_df = get_country_sector_data(country, sector, top_n=5)
        
        if firms_df.empty:
            print(f"⚠️  {country} - {sector}: No data available (examples: {examples})")
            continue
        
        result = compute_prism_score(country, country_meta, sector, firms_df)
        prism = result["prism_score"]
        
        # Tier classification
        if prism >= 62:
            tier = "🔴 AGGRESSIVE (62+)"
        elif prism >= 55:
            tier = "🟠 MODERATELY AGGRESSIVE (55-61)"
        elif prism >= 48:
            tier = "🟡 MODERATE (48-54)"
        else:
            tier = "🟢 CONSERVATIVE (<48)"
        
        print(f"✅ {country:3s} - {sector:25s} | PRISM: {prism:5.1f}/100 | {tier}")
        print(f"   └─ Components: Structural={result['structural_score']:.1f}, Fundamentals={result['fundamentals_score']:.1f}, " +
              f"TopDown={result['topdown_score']:.1f}, Behavior={result['behavior_score']:.1f}")
        print(f"   └─ Examples: {examples}")
        print()
        
        scores.append({
            "Country": country,
            "Sector": sector,
            "PRISM": prism,
            "Structural": result["structural_score"],
            "Fundamentals": result["fundamentals_score"],
            "TopDown": result["topdown_score"],
            "Behavior": result["behavior_score"],
        })
        
    except Exception as e:
        print(f"❌ {country} - {sector}: Error - {str(e)}")
        print()

# Summary
if scores:
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    df = pd.DataFrame(scores)
    print(df.to_string(index=False))
    print()
    print(f"Average PRISM Score: {df['PRISM'].mean():.1f}/100")
    print(f"Median PRISM Score: {df['PRISM'].median():.1f}/100")
    print()
    print("✨ Your portfolio holdings should now score much higher with the new weights!")
    print("   Fundamentals (40%) emphasizes ROE/FCF/margins where your tech stocks excel.")
    print("   Behavior (10%) reduces penalty for normal growth stock volatility.")
