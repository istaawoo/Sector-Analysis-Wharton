"""
PRISM Streamlit App - Country & Sector Investment Analysis
Multi-page app showing PRISM scores, portfolio justifications, and methodology
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# Add src to path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sector_analysis_app", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Import PRISM data loaders
from prism_data_loader import (
    load_prism_scores,
    get_portfolio_allocations,
    get_allocation_summary,
    get_country_summary,
    get_sector_summary,
    get_tier,
    get_tier_color,
    compute_portfolio_weighted_score
)

# Page configuration
st.set_page_config(
    page_title="PRISM - Portfolio Investment Scoring",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🌍 PRISM Navigation")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Select Page:",
    ["🏠 Home", "🌎 Country Rankings", "📊 Sector Analysis", "💼 Our Portfolio", "📖 Methodology"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**PRISM** evaluates 440 country-sector pairs (40 countries × 11 sectors) "
    "using structural factors, fundamentals, market behavior, and macro indicators."
)

# Main content based on selected page
if page == "🏠 Home":
    st.title("🌍 PRISM - Portfolio Risk & Investment Scoring Model")
    st.markdown("### Systematic Country-Sector Investment Analysis")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🔍 What We Analyze")
        st.markdown("""
        - **40 Countries** (top economies by GDP)
        - **11 GICS Sectors** per country
        - **440 Total Opportunities**
        """)
    
    with col2:
        st.markdown("#### 📈 How We Score")
        st.markdown("""
        - Structural Factors (35%)
        - Firm Fundamentals (30%)
        - Market Behavior (20%)
        - Country Macro + SWOT (15%)
        """)
    
    with col3:
        st.markdown("#### 💡 Our Approach")
        st.markdown("""
        - Objective, data-driven
        - Transparent methodology
        - Auditable calculations
        """)
    
    st.markdown("---")
    
    st.markdown("### 🎯 How to Use This App")
    
    st.info("""
    **1. Country Rankings** - See which countries score highest across all sectors
    
    **2. Sector Analysis** - Compare sectors within a specific country or globally
    
    **3. Our Portfolio** - View our $500K allocation with PRISM justifications
    
    **4. Methodology** - Understand how PRISM scores are calculated
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Quick Stats")
    
    # Placeholder stats - will be populated when PRISM data loads
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Countries Analyzed", "40")
    
    with col2:
        st.metric("Sectors per Country", "11")
    
    with col3:
        st.metric("Total Opportunities", "440")
    
    with col4:
        st.metric("Portfolio Allocation", "$500K")
    
    st.markdown("---")
    
    st.success("👈 Use the sidebar to navigate to different sections of the analysis.")

elif page == "🌎 Country Rankings":
    st.title("🌎 Country Rankings")
    st.markdown("### Top Investment Opportunities by Country")
    
    # Load PRISM data
    prism_df = load_prism_scores()
    
    if prism_df is None:
        st.warning("⚠️ PRISM scores not generated yet. Run `python run_prism.py --output_dir output/` first to generate country-sector scores.")
        st.info("The app will display sample data once PRISM analysis completes (~15-30 minutes).")
    else:
        st.success(f"✅ Loaded {len(prism_df)} country-sector scores")
        
        # Get country summary
        country_summary = get_country_summary(prism_df)
        
        st.markdown("---")
        
        # Top 10 countries by average PRISM score
        st.markdown("#### 🏆 Top 10 Countries by Average PRISM Score")
        
        top10 = country_summary.head(10)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create styled dataframe
            display_df = top10[["country_name", "avg_score", "max_score", "min_score", "num_sectors"]].copy()
            display_df.columns = ["Country", "Avg Score", "Max Score", "Min Score", "Sectors Analyzed"]
            display_df["Avg Score"] = display_df["Avg Score"].round(1)
            display_df["Max Score"] = display_df["Max Score"].round(1)
            display_df["Min Score"] = display_df["Min Score"].round(1)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Interpretation:**")
            st.markdown("""
            - **Avg Score**: Mean PRISM across all sectors
            - **Max Score**: Best sector opportunity
            - **Min Score**: Lowest sector opportunity
            """)
        
        st.markdown("---")
        
        # Filter section
        st.markdown("#### 🔍 Explore Specific Country")
        
        selected_country = st.selectbox(
            "Select a country to view detailed sector breakdown:",
            options=country_summary["country_name"].tolist()
        )
        
        if selected_country:
            country_code = country_summary[country_summary["country_name"] == selected_country]["country"].values[0]
            country_data = prism_df[prism_df["country"] == country_code].copy()
            country_data = country_data.sort_values("prism_score", ascending=False)
            
            st.markdown(f"##### {selected_country} - Sector Breakdown")
            
            # Display table
            display_cols = ["sector", "prism_score", "structural_score", "fundamentals_score", "behavior_score", "topdown_score"]
            display_df = country_data[display_cols].copy()
            display_df.columns = ["Sector", "PRISM", "Structural", "Fundamentals", "Behavior", "Top-Down"]
            
            # Round scores
            for col in ["PRISM", "Structural", "Fundamentals", "Behavior", "Top-Down"]:
                display_df[col] = display_df[col].round(1)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Chart
            import plotly.express as px
            fig = px.bar(
                country_data,
                x="sector",
                y="prism_score",
                title=f"{selected_country} - PRISM Scores by Sector",
                labels={"sector": "Sector", "prism_score": "PRISM Score"},
                color="prism_score",
                color_continuous_scale="RdYlGn"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

elif page == "📊 Sector Analysis":
    st.title("📊 Sector Analysis")
    st.markdown("### Compare Sectors Across Countries")
    
    # Load PRISM data
    prism_df = load_prism_scores()
    
    if prism_df is None:
        st.warning("⚠️ PRISM scores not generated yet. Run `python run_prism.py --output_dir output/` first.")
    else:
        st.success(f"✅ Analyzing 11 GICS sectors across {prism_df['country'].nunique()} countries")
        
        # Get sector summary
        sector_summary = get_sector_summary(prism_df)
        
        st.markdown("---")
        
        # Global sector rankings
        st.markdown("#### 🌍 Global Sector Rankings (Average Across All Countries)")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            display_df = sector_summary[["sector", "avg_score", "max_score", "min_score", "num_countries"]].copy()
            display_df.columns = ["Sector", "Avg Score", "Max Score", "Min Score", "Countries"]
            display_df["Avg Score"] = display_df["Avg Score"].round(1)
            display_df["Max Score"] = display_df["Max Score"].round(1)
            display_df["Min Score"] = display_df["Min Score"].round(1)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Key Insights:**")
            best_sector = sector_summary.iloc[0]["sector"]
            best_score = sector_summary.iloc[0]["avg_score"]
            st.info(f"**Top Sector:** {best_sector} ({best_score:.1f})")
            
            worst_sector = sector_summary.iloc[-1]["sector"]
            worst_score = sector_summary.iloc[-1]["avg_score"]
            st.warning(f"**Lowest Sector:** {worst_sector} ({worst_score:.1f})")
        
        st.markdown("---")
        
        # Sector heatmap
        st.markdown("#### 🔥 Sector Heatmap (Top 20 Countries)")
        
        # Get top 20 countries by avg score
        country_summary = get_country_summary(prism_df)
        top20_countries = country_summary.head(20)["country"].tolist()
        
        # Filter and pivot
        heatmap_data = prism_df[prism_df["country"].isin(top20_countries)].copy()
        heatmap_pivot = heatmap_data.pivot_table(
            values="prism_score",
            index="country_name",
            columns="sector",
            aggfunc="mean"
        )
        
        import plotly.express as px
        fig = px.imshow(
            heatmap_pivot,
            labels=dict(x="Sector", y="Country", color="PRISM Score"),
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            color_continuous_scale="RdYlGn",
            aspect="auto"
        )
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed sector view
        st.markdown("#### 🔍 Detailed Sector View")
        
        selected_sector = st.selectbox(
            "Select a sector to see top countries:",
            options=sector_summary["sector"].tolist()
        )
        
        if selected_sector:
            sector_data = prism_df[prism_df["sector"] == selected_sector].copy()
            sector_data = sector_data.sort_values("prism_score", ascending=False).head(15)
            
            st.markdown(f"##### Top 15 Countries for {selected_sector}")
            
            display_df = sector_data[["country_name", "prism_score", "structural_score", "fundamentals_score", "top_firms"]].copy()
            display_df.columns = ["Country", "PRISM", "Structural", "Fundamentals", "Top Firms"]
            display_df["PRISM"] = display_df["PRISM"].round(1)
            display_df["Structural"] = display_df["Structural"].round(1)
            display_df["Fundamentals"] = display_df["Fundamentals"].round(1)
            display_df["Top Firms"] = display_df["Top Firms"].apply(lambda x: ", ".join(x[:3]) if isinstance(x, list) else "N/A")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)

elif page == "💼 Our Portfolio":
    st.title("💼 Our Portfolio")
    st.markdown("### $500K Allocation with PRISM Justifications")
    
    # Load portfolio data
    portfolio_df = get_portfolio_allocations()
    summary = get_allocation_summary()
    prism_df = load_prism_scores()
    
    st.markdown("---")
    
    # Portfolio weighted average (KEY METRIC)
    portfolio_score = compute_portfolio_weighted_score(portfolio_df, prism_df)
    
    st.markdown("#### 🎯 Portfolio-Level PRISM Score")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Weighted Average PRISM",
            f"{portfolio_score['weighted_score']:.1f}/100",
            help="Calculated as sum of (holding_score × holding_amount) / total_allocation"
        )
    
    with col2:
        tier = portfolio_score['tier']
        tier_emoji = {"Overweight": "🟢", "Neutral": "🟡", "Underweight": "🔴"}[tier]
        st.metric("Portfolio Tier", f"{tier_emoji} {tier}")
    
    with col3:
        st.metric("Total Allocation", f"${portfolio_score['total_allocation']:,.0f}")
    
    st.info(f"📊 **Portfolio Interpretation:** {portfolio_score['interpretation']}")
    
    st.markdown("---")
    
    # Portfolio summary
    st.markdown("#### 📊 Portfolio Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Allocation", f"${summary['total']:,.0f}")
    
    with col2:
        st.metric("Holdings", summary['num_holdings'])
    
    with col3:
        st.metric("Countries", summary['countries'])
    
    with col4:
        st.metric("Sectors", summary['sectors'])
    
    st.markdown("---")
    
    # Allocation by country
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Allocation by Country")
        country_alloc = summary['by_country'].head(10)
        
        import plotly.express as px
        fig = px.pie(
            values=country_alloc.values,
            names=country_alloc.index,
            title="Top 10 Countries by Allocation"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("##### Allocation by Sector")
        sector_alloc = summary['by_sector'].head(10)
        
        fig = px.pie(
            values=sector_alloc.values,
            names=sector_alloc.index,
            title="Top 10 Sectors by Allocation"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Holdings table with PRISM scores
    st.markdown("#### 📋 All Holdings with PRISM Scores")
    
    if prism_df is not None:
        # Merge portfolio with PRISM scores
        merged = portfolio_df.merge(
            prism_df[["country", "sector", "prism_score"]],
            on=["country", "sector"],
            how="left"
        )
        
        # Add tier
        merged["tier"] = merged["prism_score"].apply(get_tier)
        
        # Sort by amount descending
        merged = merged.sort_values("amount", ascending=False)
        
        # Count by tier
        tier_counts = merged["tier"].value_counts()
        tier_amounts = merged.groupby("tier")["amount"].sum()
        
        st.markdown("##### Tier Distribution")
        
        tier_cols = st.columns(4)
        
        for i, tier in enumerate(["Overweight", "Neutral", "Underweight", "Not Scored"]):
            with tier_cols[i]:
                count = tier_counts.get(tier, 0)
                amount = tier_amounts.get(tier, 0)
                pct = (amount / summary['total'] * 100) if summary['total'] > 0 else 0
                st.metric(
                    tier,
                    f"{count} holdings",
                    f"${amount:,.0f} ({pct:.1f}%)"
                )
        
        st.markdown("---")
        
        # Display holdings table
        st.markdown("##### Detailed Holdings")
        
        # Add filters
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            country_filter = st.multiselect(
                "Filter by Country:",
                options=sorted(merged["country"].unique()),
                default=[]
            )
        
        with filter_col2:
            tier_filter = st.multiselect(
                "Filter by Tier:",
                options=["Overweight", "Neutral", "Underweight", "Not Scored"],
                default=[]
            )
        
        # Apply filters
        filtered_df = merged.copy()
        if country_filter:
            filtered_df = filtered_df[filtered_df["country"].isin(country_filter)]
        if tier_filter:
            filtered_df = filtered_df[filtered_df["tier"].isin(tier_filter)]
        
        # Display table
        display_df = filtered_df[["ticker", "country", "sector", "amount", "prism_score", "tier"]].copy()
        display_df.columns = ["Ticker", "Country", "Sector", "Amount ($)", "PRISM Score", "Tier"]
        display_df["Amount ($)"] = display_df["Amount ($)"].apply(lambda x: f"${x:,.2f}")
        display_df["PRISM Score"] = display_df["PRISM Score"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Individual justifications
        st.markdown("#### 💡 Individual Holding Justifications")
        
        st.info("Select a holding to see detailed PRISM justification")
        
        selected_ticker = st.selectbox(
            "Select holding:",
            options=merged["ticker"].tolist()
        )
        
        if selected_ticker:
            holding = merged[merged["ticker"] == selected_ticker].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Allocation", f"${holding['amount']:,.2f}")
            
            with col2:
                prism_val = holding['prism_score']
                st.metric("PRISM Score", f"{prism_val:.1f}" if pd.notna(prism_val) else "N/A")
            
            with col3:
                tier_color = get_tier_color(holding['tier'])
                st.markdown(f"**Tier:** :{tier_color}[{holding['tier']}]")
            
            # Get detailed PRISM breakdown if available
            if prism_df is not None and pd.notna(prism_val):
                detail = prism_df[
                    (prism_df["country"] == holding["country"]) &
                    (prism_df["sector"] == holding["sector"])
                ]
                
                if not detail.empty:
                    detail = detail.iloc[0]
                    
                    st.markdown("##### PRISM Component Breakdown")
                    
                    comp_col1, comp_col2, comp_col3, comp_col4 = st.columns(4)
                    
                    with comp_col1:
                        st.metric("Structural (35%)", f"{detail['structural_score']:.1f}")
                    
                    with comp_col2:
                        st.metric("Fundamentals (30%)", f"{detail['fundamentals_score']:.1f}")
                    
                    with comp_col3:
                        st.metric("Behavior (20%)", f"{detail['behavior_score']:.1f}")
                    
                    with comp_col4:
                        st.metric("Top-Down (15%)", f"{detail['topdown_score']:.1f}")
                    
                    # Justification narrative
                    st.markdown("##### Justification")
                    
                    tier = holding['tier']
                    if tier == "Overweight":
                        st.success(
                            f"**{selected_ticker}** ({holding['country']} - {holding['sector']}) receives a strong PRISM score of {prism_val:.1f}/100, "
                            f"placing it in the 'Overweight' category. This allocation is well-supported by our quantitative analysis. "
                            f"Key strengths: Structural score of {detail['structural_score']:.1f} and Fundamentals score of {detail['fundamentals_score']:.1f}."
                        )
                    elif tier == "Neutral":
                        st.info(
                            f"**{selected_ticker}** ({holding['country']} - {holding['sector']}) has a moderate PRISM score of {prism_val:.1f}/100, "
                            f"placing it in the 'Neutral' category. While not a top-tier opportunity, this allocation provides diversification "
                            f"and balances risk exposure across our portfolio."
                        )
                    elif tier == "Underweight":
                        st.warning(
                            f"**{selected_ticker}** ({holding['country']} - {holding['sector']}) has a lower PRISM score of {prism_val:.1f}/100. "
                            f"This allocation may be justified by strategic diversification or contrarian positioning, but warrants close monitoring. "
                            f"Consider rebalancing opportunities as market conditions evolve."
                        )
            else:
                st.info(
                    f"**{selected_ticker}** is a diversified ETF providing broad exposure to {holding['country']} markets. "
                    f"ETFs reduce single-stock risk and provide liquidity. Recommended for portfolio diversification."
                )
    
    else:
        st.warning("⚠️ PRISM scores not available. Run `python run_prism.py --output_dir output/` to generate scores and justifications.")
        
        # Show portfolio without scores
        st.markdown("##### Holdings (PRISM scores pending)")
        display_df = portfolio_df[["ticker", "country", "sector", "amount"]].copy()
        display_df.columns = ["Ticker", "Country", "Sector", "Amount ($)"]
        display_df["Amount ($)"] = display_df["Amount ($)"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

elif page == "📖 Methodology":
    st.title("📖 PRISM Methodology")
    st.markdown("### How We Calculate Investment Scores")
    
    st.markdown("---")
    
    st.markdown("#### PRISM Score Components")
    
    st.markdown("""
    PRISM evaluates country-sector pairs on a **0-100 scale** using four weighted components:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 1. Structural Score (35%)")
        st.markdown("""
        - **Porter's 5 Forces**: Barriers to entry, threat of substitutes, supplier/buyer power, rivalry
        - **Industry Life Cycle**: Intro, Growth, Shakeout, Mature, Decline
        - **What it measures**: Competitive dynamics, industry attractiveness
        """)
        
        st.markdown("##### 2. Fundamental Quality (30%)")
        st.markdown("""
        - **Firm Metrics**: ROE, profit margin, revenue growth, FCF, debt/equity, gross margin
        - **Aggregation**: Market-cap weighted average of top 5-10 firms
        - **What it measures**: Company quality, profitability, financial health
        """)
    
    with col2:
        st.markdown("##### 3. Market Behavior (20%)")
        st.markdown("""
        - **Price Metrics**: 12m/6m returns, volatility, max drawdown, beta
        - **Proxy**: Largest firm by market cap
        - **What it measures**: Recent performance, risk, market stability
        """)
        
        st.markdown("##### 4. Top-Down Mission-Fit (15%)")
        st.markdown("""
        - **Country Macro**: GDP growth, GDP per capita
        - **SWOT**: Strengths, weaknesses, opportunities, threats
        - **What it measures**: Macro environment, strategic fit
        """)
    
    st.markdown("---")
    
    st.markdown("#### Final PRISM Formula")
    
    st.code("""
PRISM = 0.35 × Structural + 0.30 × Fundamentals + 0.20 × Behavior + 0.15 × TopDown
    """)
    
    st.markdown("---")
    
    st.markdown("#### Tier Definitions")
    
    tier_df = pd.DataFrame({
        "Tier": ["Overweight", "Neutral", "Underweight"],
        "PRISM Score Range": ["70-100", "55-69", "0-54"],
        "Recommendation": [
            "Strong opportunity, recommended overweight position",
            "Moderate opportunity, neutral weight",
            "Lower opportunity, consider underweight or avoid"
        ]
    })
    
    st.table(tier_df)
    
    st.markdown("---")
    
    st.markdown("#### Data Sources")
    
    st.markdown("""
    - **Country Macro**: World Bank / IMF (Top 40 economies by GDP)
    - **Company Fundamentals**: Yahoo Finance API
    - **Price Data**: Yahoo Finance (2-year historical)
    - **Sector Constituents**: Top 5-10 companies per country-sector by market cap
    """)

# Footer
st.markdown("---")
st.markdown("*PRISM - Developed for Wharton Sector Analysis Competition 2025*")