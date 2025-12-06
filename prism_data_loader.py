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
    """Convert PRISM score to tier label"""
    if pd.isna(prism_score):
        return "Not Scored"
    elif prism_score >= 70:
        return "Overweight"
    elif prism_score >= 55:
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
