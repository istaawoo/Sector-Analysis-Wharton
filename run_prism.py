"""
PRISM CLI - Main orchestration script
Runs the full PRISM analysis pipeline and generates output files.

Usage:
    python run_prism.py --output_dir output/
"""

import argparse
import os
import sys
import json
import pandas as pd
from datetime import datetime
import time

# Add src to path for imports
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sector_analysis_app", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Import PRISM modules (now Pylance can resolve these)
from sector_analysis_app.src.prism_country_data import get_top40_countries, get_country_metadata
from sector_analysis_app.src.prism_sector_constituents import get_sector_constituents, get_country_sector_data, GICS_SECTORS
from sector_analysis_app.src.prism_scoring import compute_prism_score
from sector_analysis_app.src.prism_allocation import parse_allocations, compute_alignment_score, generate_justification, backsolve_parameters


def run_prism_analysis(output_dir: str = "output", top_n_firms: int = 5, cache_dir: str = "data_cache"):
    """
    Run complete PRISM analysis pipeline.
    
    Steps:
    1. Fetch top 40 countries
    2. For each (country, sector) pair, compute PRISM score
    3. Generate prism_country_sector_scores.csv
    4. Compute allocation alignment
    5. Generate justification_report.md and methodology.md
    6. Perform parameter backsolving if needed
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    
    print("=" * 80)
    print("PRISM: Portfolio Risk & Investment Scoring Model")
    print("=" * 80)
    print(f"Output directory: {output_dir}")
    print(f"Cache directory: {cache_dir}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Get countries
    print("[1/6] Fetching top 40 economies...")
    countries_df = get_top40_countries()
    print(f"  Loaded {len(countries_df)} countries")
    
    # Step 2: Compute PRISM scores for all (country, sector) pairs
    print("\n[2/6] Computing PRISM scores for country-sector pairs...")
    print(f"  Processing {len(countries_df)} countries × {len(GICS_SECTORS)} sectors = {len(countries_df) * len(GICS_SECTORS)} pairs")
    print("  (This may take 10-30 minutes depending on API rate limits)")
    
    prism_results = []
    total_pairs = len(countries_df) * len(GICS_SECTORS)
    processed = 0
    
    for _, country_row in countries_df.iterrows():
        country_code = country_row["code"]
        country_meta = country_row.to_dict()
        
        for sector in GICS_SECTORS:
            processed += 1
            if processed % 10 == 0:
                print(f"    Progress: {processed}/{total_pairs} ({100*processed/total_pairs:.1f}%)")
            
            try:
                # Get sector constituents and fundamentals
                firms_df = get_country_sector_data(country_code, sector, top_n=top_n_firms)
                
                # Compute PRISM score
                prism_result = compute_prism_score(
                    country_code=country_code,
                    country_meta=country_meta,
                    sector=sector,
                    firms_df=firms_df,
                )
                
                prism_results.append(prism_result)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    Error processing {country_code}-{sector}: {e}")
                continue
    
    print(f"  Completed {len(prism_results)} country-sector scores")
    
    # Step 3: Save prism_country_sector_scores.csv
    print("\n[3/6] Saving PRISM scores to CSV...")
    prism_df = pd.DataFrame(prism_results)
    csv_path = os.path.join(output_dir, "prism_country_sector_scores.csv")
    prism_df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")
    
    # Also save JSON version
    json_path = os.path.join(output_dir, "prism_sector_scores.json")
    prism_by_country = {}
    for _, row in prism_df.iterrows():
        country = row["country"]
        sector = row["sector"]
        if country not in prism_by_country:
            prism_by_country[country] = {}
        prism_by_country[country][sector] = row.to_dict()
    
    with open(json_path, 'w') as f:
        json.dump(prism_by_country, f, indent=2)
    print(f"  Saved: {json_path}")
    
    # Step 4: Compute allocation alignment
    print("\n[4/6] Computing allocation alignment...")
    allocations_df = parse_allocations()
    alignment_df = compute_alignment_score(allocations_df, prism_df)
    
    alignment_path = os.path.join(output_dir, "allocation_alignment.csv")
    alignment_df.to_csv(alignment_path, index=False)
    print(f"  Saved: {alignment_path}")
    
    # Generate justifications
    alignment_with_justifications = []
    for _, row in alignment_df.iterrows():
        # Find detailed PRISM data if available
        if not pd.isna(row["prism_score"]):
            prism_detail = prism_df[
                (prism_df["country"] == row["country"]) & 
                (prism_df["sector"] == row["sector"])
            ]
            if not prism_detail.empty:
                prism_detail_dict = prism_detail.iloc[0].to_dict()
            else:
                prism_detail_dict = None
        else:
            prism_detail_dict = None
        
        justification = generate_justification(row, prism_detail_dict)
        
        alignment_with_justifications.append({
            "ticker": row["ticker"],
            "country": row["country"],
            "sector": row["sector"],
            "amount": row["amount"],
            "prism_score": row["prism_score"],
            "alignment_score": row["alignment_score"],
            "tier": row["tier"],
            "justification": justification,
        })
    
    alignment_json_path = os.path.join(output_dir, "allocation_alignment.json")
    with open(alignment_json_path, 'w') as f:
        json.dump(alignment_with_justifications, f, indent=2)
    print(f"  Saved: {alignment_json_path}")
    
    # Step 5: Generate justification_report.md
    print("\n[5/6] Generating justification report...")
    report_path = os.path.join(output_dir, "justification_report.md")
    generate_justification_report(
        alignment_df=alignment_df,
        alignment_with_justifications=alignment_with_justifications,
        prism_df=prism_df,
        output_path=report_path,
    )
    print(f"  Saved: {report_path}")
    
    # Step 6: Backsolve parameters if needed
    print("\n[6/6] Performing parameter backsolving...")
    backsolve_result = backsolve_parameters(
        allocated_tickers=allocations_df["ticker"].tolist(),
        prism_scores=prism_df,
        target_percentile=0.70,
    )
    
    backsolve_path = os.path.join(output_dir, "backsolve_changes.json")
    with open(backsolve_path, 'w', encoding='utf-8') as f:
        json.dump(backsolve_result, f, indent=2)
    print(f"  Saved: {backsolve_path}")
    print(f"  {backsolve_result['message']}")
    
    # Generate methodology.md
    print("\n[7/6] Generating methodology documentation...")
    methodology_path = os.path.join(output_dir, "methodology.md")
    generate_methodology(output_path=methodology_path)
    print(f"  Saved: {methodology_path}")
    
    print("\n" + "=" * 80)
    print("PRISM analysis complete!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"\nOutputs generated in: {output_dir}/")
    print("  - prism_country_sector_scores.csv")
    print("  - prism_sector_scores.json")
    print("  - allocation_alignment.csv")
    print("  - allocation_alignment.json")
    print("  - justification_report.md")
    print("  - methodology.md")
    print("  - backsolve_changes.json")
    print()


def generate_justification_report(
    alignment_df: pd.DataFrame,
    alignment_with_justifications: list,
    prism_df: pd.DataFrame,
    output_path: str
):
    """Generate human-readable justification report in Markdown."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# PRISM Portfolio Justification Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("This report analyzes the alignment between our portfolio allocations and the PRISM ")
        f.write("(Portfolio Risk & Investment Scoring Model) recommendations. PRISM evaluates country-sector ")
        f.write("pairs on a 0-100 scale using structural factors (Porter's 5 Forces, Industry Life Cycle), ")
        f.write("fundamental quality metrics, market behavior, and top-down macro analysis.\n\n")
        
        total_amount = alignment_df["amount"].sum()
        overweight = alignment_df[alignment_df["tier"] == "Overweight"]["amount"].sum()
        neutral = alignment_df[alignment_df["tier"] == "Neutral"]["amount"].sum()
        underweight = alignment_df[alignment_df["tier"] == "Underweight"]["amount"].sum()
        not_scored = alignment_df[alignment_df["tier"] == "Not Scored"]["amount"].sum()
        
        f.write(f"**Portfolio Summary:**\n")
        f.write(f"- Total Allocation: ${total_amount:,.2f}\n")
        f.write(f"- Overweight Tier: ${overweight:,.2f} ({100*overweight/total_amount:.1f}%)\n")
        f.write(f"- Neutral Tier: ${neutral:,.2f} ({100*neutral/total_amount:.1f}%)\n")
        f.write(f"- Underweight Tier: ${underweight:,.2f} ({100*underweight/total_amount:.1f}%)\n")
        f.write(f"- Not Scored (ETFs): ${not_scored:,.2f} ({100*not_scored/total_amount:.1f}%)\n\n")
        
        avg_prism = alignment_df[alignment_df["prism_score"].notna()]["prism_score"].mean()
        f.write(f"**Average PRISM Score (individual stocks):** {avg_prism:.1f}/100\n\n")
        
        f.write("---\n\n")
        f.write("## Top 10 Country-Sector Opportunities (by PRISM Score)\n\n")
        top10 = prism_df.nlargest(10, "prism_score")[["country_name", "sector", "prism_score", "top_firms"]]
        f.write("| Rank | Country | Sector | PRISM Score | Top Firms |\n")
        f.write("|------|---------|--------|-------------|----------|\n")
        for i, (_, row) in enumerate(top10.iterrows(), 1):
            firms = ", ".join(row["top_firms"][:3]) if row["top_firms"] else "N/A"
            f.write(f"| {i} | {row['country_name']} | {row['sector']} | {row['prism_score']:.1f} | {firms} |\n")
        f.write("\n---\n\n")
        
        f.write("## Allocation-by-Allocation Justifications\n\n")
        
        # Group by tier
        for tier in ["Overweight", "Neutral", "Underweight", "Not Scored"]:
            tier_allocations = [a for a in alignment_with_justifications if a["tier"] == tier]
            if not tier_allocations:
                continue
            
            f.write(f"### {tier} Tier\n\n")
            
            for alloc in tier_allocations:
                ticker = alloc["ticker"]
                country = alloc["country"]
                sector = alloc["sector"]
                amount = alloc["amount"]
                prism_score = alloc["prism_score"]
                justification = alloc["justification"]
                
                f.write(f"**{ticker}** (${amount:,.2f}) — {country} / {sector}\n\n")
                if prism_score:
                    f.write(f"*PRISM Score: {prism_score:.1f}/100*\n\n")
                f.write(f"{justification}\n\n")
                f.write("---\n\n")
        
        f.write("## Methodology Notes\n\n")
        f.write("PRISM scores are computed as:\n")
        f.write("- **Structural (35%)**: Porter's 5 Forces + Industry Life Cycle\n")
        f.write("- **Fundamentals (30%)**: Market-cap weighted firm metrics (ROE, margins, FCF, debt)\n")
        f.write("- **Market Behavior (20%)**: Returns, volatility, drawdown, beta\n")
        f.write("- **Top-Down (15%)**: Country GDP growth, GDP per capita, SWOT analysis\n\n")
        f.write("Tier definitions:\n")
        f.write("- **Overweight**: PRISM ≥ 70 — Strong opportunity, recommended overweight\n")
        f.write("- **Neutral**: PRISM 55-69 — Moderate opportunity, neutral weight\n")
        f.write("- **Underweight**: PRISM < 55 — Lower opportunity, consider underweight\n")
        f.write("- **Not Scored**: ETFs and diversified holdings\n\n")


def generate_methodology(output_path: str):
    """Generate detailed methodology.md file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# PRISM Methodology\n\n")
        f.write(f"**Version:** 1.0  \n")
        f.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("---\n\n")
        
        f.write("## Overview\n\n")
        f.write("PRISM (Portfolio Risk & Investment Scoring Model) is a quantitative framework ")
        f.write("for evaluating country-sector investment opportunities on a 0-100 scale. ")
        f.write("It combines top-down strategic frameworks (Porter's 5 Forces, Industry Life Cycle, SWOT) ")
        f.write("with bottom-up fundamental and market behavior analysis.\n\n")
        
        f.write("## Data Sources\n\n")
        f.write("1. **Country Macro Data**: Top 40 economies by nominal GDP (World Bank / IMF 2023)\n")
        f.write("2. **Company Fundamentals**: Yahoo Finance API (yfinance)\n")
        f.write("3. **Price Data**: Yahoo Finance historical prices (2-year lookback)\n")
        f.write("4. **Sector Constituents**: Curated lists of top 5-10 companies per country-sector by market cap\n\n")
        
        f.write("## PRISM Score Components\n\n")
        f.write("### 1. Structural Score (35% weight)\n\n")
        f.write("Combines Porter's 5 Forces and Industry Life Cycle analysis:\n\n")
        f.write("**Porter's 5 Forces** (1-5 scale each, then normalized to 0-100):\n")
        f.write("- **Barriers to Entry**: Based on R&D intensity (% revenue) and regulation flag\n")
        f.write("- **Threat of Substitutes**: Sector-specific heuristic (e.g., Tech=4, Utilities=2)\n")
        f.write("- **Supplier Power**: HHI (Herfindahl-Hirschman Index) concentration proxy\n")
        f.write("- **Buyer Power**: Higher for consumer-facing sectors\n")
        f.write("- **Rivalry**: Inverse of HHI (lower concentration = higher rivalry)\n\n")
        f.write("**Industry Life Cycle** (1-5 mapping):\n")
        f.write("- Intro: 2.0, Growth: 4.0, Shakeout: 3.0, Mature: 3.5, Decline: 2.5\n\n")
        f.write("*Formula*: `Structural = 0.70 × Porter + 0.30 × Lifecycle`\n\n")
        
        f.write("### 2. Fundamental Quality Score (30% weight)\n\n")
        f.write("Market-cap weighted average of firm-level fundamental scores.\n\n")
        f.write("**Firm Score Components**:\n")
        f.write("- ROE (Return on Equity): 25% — normalized -10% to 40%, higher = better\n")
        f.write("- Profit Margin: 20% — normalized -10% to 50%, higher = better\n")
        f.write("- Revenue Growth (YoY): 15% — normalized -20% to 50%, higher = better\n")
        f.write("- FCF/Market Cap: 15% — normalized -5% to 15%, higher = better\n")
        f.write("- Debt/Equity: 15% — normalized 0 to 300, lower = better (inverted)\n")
        f.write("- Gross Margin: 10% — normalized 0% to 80%, higher = better\n\n")
        f.write("*Missing data defaults to 50 (neutral).*\n\n")
        
        f.write("### 3. Market Behavior Score (20% weight)\n\n")
        f.write("Uses price data from the largest firm (by market cap) in the sector as proxy.\n\n")
        f.write("**Components**:\n")
        f.write("- 12-month return: 20% — normalized -50% to 100%, higher = better\n")
        f.write("- 6-month return: 20% — normalized -50% to 100%, higher = better\n")
        f.write("- Annualized volatility: 25% — normalized 10% to 80%, lower = better (inverted)\n")
        f.write("- Max drawdown (1y): 20% — normalized 0% to 60%, lower = better (inverted)\n")
        f.write("- Beta vs SPY: 15% — normalized 0.5 to 2.0, lower = better (inverted)\n\n")
        
        f.write("### 4. Top-Down Mission-Fit Score (15% weight)\n\n")
        f.write("Combines country-level macro indicators and SWOT analysis.\n\n")
        f.write("**Components**:\n")
        f.write("- GDP Growth: 40% — normalized -2% to 8%, higher = better\n")
        f.write("- GDP Per Capita: 30% — normalized $1k to $100k, higher = better\n")
        f.write("- SWOT Net Score: 30% — (Strengths - Weaknesses) + (Opportunities - Threats), normalized -8 to 8\n\n")
        
        f.write("## Final PRISM Score\n\n")
        f.write("```\n")
        f.write("PRISM = 0.35 × Structural + 0.30 × Fundamentals + 0.20 × Behavior + 0.15 × TopDown\n")
        f.write("```\n\n")
        
        f.write("## Tier Definitions\n\n")
        f.write("- **Overweight**: PRISM ≥ 70\n")
        f.write("- **Neutral**: 55 ≤ PRISM < 70\n")
        f.write("- **Underweight**: PRISM < 55\n\n")
        
        f.write("## Limitations & Caveats\n\n")
        f.write("1. **Data Availability**: Some emerging market firms lack complete fundamental data; ")
        f.write("defaults to neutral scores (50).\n")
        f.write("2. **Exchange Closure**: Non-US exchanges may have delayed or limited API access.\n")
        f.write("3. **Proxy Assumptions**: Sector behavior proxied by largest firm; may not represent entire sector.\n")
        f.write("4. **Static Weights**: PRISM uses fixed component weights; customization may improve fit.\n")
        f.write("5. **HHI Proxies**: True HHI calculation requires detailed market share data; we use heuristics.\n\n")
        
        f.write("## Backsolving & Parameter Tuning\n\n")
        f.write("If allocations do not align with top PRISM picks, the model can suggest minimal weight adjustments ")
        f.write("(±10% per component) to improve alignment. This ensures transparency and avoids overfitting.\n\n")


def main():
    parser = argparse.ArgumentParser(description="Run PRISM country-sector analysis")
    parser.add_argument("--output_dir", default="output", help="Output directory for results")
    parser.add_argument("--top_n", type=int, default=5, help="Top N firms per sector to analyze")
    parser.add_argument("--cache_dir", default="data_cache", help="Cache directory for API data")
    
    args = parser.parse_args()
    
    run_prism_analysis(
        output_dir=args.output_dir,
        top_n_firms=args.top_n,
        cache_dir=args.cache_dir,
    )


if __name__ == "__main__":
    main()
