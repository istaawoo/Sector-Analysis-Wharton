"""
PRISM Data Loader for Streamlit App
Handles caching and loading of PRISM scores and portfolio data
"""

import pandas as pd
import streamlit as st
import os
import sys

# Add src to path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sector_analysis_app", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from sector_analysis_app.src.prism_allocation import ALLOCATIONS


@st.cache_data(ttl=3600)
def load_prism_scores():
    """
    Load PRISM country-sector scores.
    If output/prism_country_sector_scores.csv exists, load it.
    Otherwise, compute a sample for demo purposes.
    """
    output_file = "output/prism_country_sector_scores.csv"
    
    if os.path.exists(output_file):
        df = pd.read_csv(output_file)
        return df
    else:
        # Return None - will trigger "Run PRISM first" message
        return None


@st.cache_data
def get_portfolio_allocations():
    """Get portfolio allocations from prism_allocation.py"""
    data = []
    for ticker, info in ALLOCATIONS.items():
        data.append({
            "ticker": ticker,
            "amount": info["amount"],
            "country": info["country"],
            "sector": info["sector"],
        })
    return pd.DataFrame(data)


@st.cache_data
def get_allocation_summary():
    """Get summary stats for portfolio"""
    df = get_portfolio_allocations()
    
    total = df["amount"].sum()
    
    # Count by country
    by_country = df.groupby("country")["amount"].sum().sort_values(ascending=False)
    
    # Count by sector
    by_sector = df.groupby("sector")["amount"].sum().sort_values(ascending=False)
    
    return {
        "total": total,
        "num_holdings": len(df),
        "by_country": by_country,
        "by_sector": by_sector,
        "countries": df["country"].nunique(),
        "sectors": df["sector"].nunique(),
    }


@st.cache_data
def get_country_summary(prism_df):
    """Aggregate PRISM scores by country"""
    if prism_df is None:
        return None
    
    country_summary = prism_df.groupby(["country", "country_name"]).agg({
        "prism_score": ["mean", "max", "min"],
        "sector": "count"
    }).reset_index()
    
    country_summary.columns = ["country", "country_name", "avg_score", "max_score", "min_score", "num_sectors"]
    country_summary = country_summary.sort_values("avg_score", ascending=False)
    
    return country_summary


@st.cache_data
def get_sector_summary(prism_df):
    """Aggregate PRISM scores by sector (global)"""
    if prism_df is None:
        return None
    
    sector_summary = prism_df.groupby("sector").agg({
        "prism_score": ["mean", "max", "min"],
        "country": "count"
    }).reset_index()
    
    sector_summary.columns = ["sector", "avg_score", "max_score", "min_score", "num_countries"]
    sector_summary = sector_summary.sort_values("avg_score", ascending=False)
    
    return sector_summary


def get_tier(prism_score):
    """Convert PRISM score to tier label. Adjusted thresholds for flexibility."""
    if pd.isna(prism_score):
        return "Not Scored"
    elif prism_score >= 65:  # Lowered from 70
        return "Overweight"
    elif prism_score >= 45:  # Lowered from 55
        return "Neutral"
    else:
        return "Underweight"


def get_tier_color(tier):
    """Get color for tier badges"""
    colors = {
        "Overweight": "green",
        "Neutral": "blue",
        "Underweight": "orange",
        "Not Scored": "gray"
    }
    return colors.get(tier, "gray")


def compute_portfolio_weighted_score(portfolio_df, prism_df=None):
    """
    Compute portfolio-level weighted average PRISM score.
    This shows the overall portfolio balance: Overweight/Neutral/Underweight.
    """
    total_value = portfolio_df["amount"].sum()
    
    if total_value == 0:
        return {
            "weighted_score": 50,
            "tier": "Neutral",
            "interpretation": "No allocations",
            "total_allocation": 0
        }
    
    # Merge portfolio with PRISM scores
    if prism_df is not None:
        merged = portfolio_df.merge(
            prism_df[["country", "sector", "prism_score"]],
            on=["country", "sector"],
            how="left"
        )
        # Use PRISM score, or 50 (neutral) if not available
        merged["prism_score"] = merged["prism_score"].fillna(50)
    else:
        merged = portfolio_df.copy()
        merged["prism_score"] = 50
    
    # Compute weighted average
    weighted_score = (merged["prism_score"] * merged["amount"]).sum() / total_value
    
    # Determine portfolio tier
    if weighted_score >= 65:
        tier = "Overweight"
        interpretation = "Portfolio is positioned for growth; overweight high-opportunity sectors and countries"
    elif weighted_score >= 45:
        tier = "Neutral"
        interpretation = "Portfolio is balanced across opportunities and risk; neither aggressive nor conservative"
    else:
        tier = "Underweight"
        interpretation = "Portfolio is positioned conservatively; underweight high-opportunity sectors"
    
    return {
        "weighted_score": round(weighted_score, 1),
        "tier": tier,
        "interpretation": interpretation,
        "total_allocation": total_value
    }
