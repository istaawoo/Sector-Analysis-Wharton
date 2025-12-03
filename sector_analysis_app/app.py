import streamlit as st
import pandas as pd
from sector_analysis_app.src import data, scoring, plots, utils


st.set_page_config(page_title="Sector Risk Analysis", layout="wide")

st.title("Sector Risk Analysis")

st.markdown("This app computes a sector-level risk score (0-100) using price data and a top-down model.")

# Sidebar
st.sidebar.header("Settings")
etf_choice = st.sidebar.selectbox("Choose sector ETF", utils.get_etf_list())
run_button = st.sidebar.button("Refresh Data")

meta = utils.get_etf_metadata(etf_choice)

st.header(f"{meta['name']} ({etf_choice})")
st.write(meta["description"])

with st.spinner("Fetching data..."):
    etf_df, spy_df = data.get_spy_and_etf(etf_choice)

metrics = {}
metrics["volatility"] = scoring.compute_volatility_factors(etf_df, spy_df)
metrics["performance"] = scoring.compute_performance_factors(etf_df)
metrics["behavior"] = scoring.compute_market_behavior(etf_df, spy_df)
metrics["fundamentals"] = {"cyclical": True if meta.get("category", "Cyclical") == "Cyclical" else False,
                              "topdown_score": None}

# Top-down inputs (editable)
st.subheader("Top-Down Model (Porter / Life Cycle / SWOT)")
col1, col2, col3 = st.columns(3)
with col1:
    regulation = st.selectbox("Regulation (0=no,1=yes)", [0, 1], index=0)
    r_and_d = st.number_input("R&D intensity (% revenue)", value=2.0, step=0.1)
    hhi = st.number_input("HHI concentration (0-10000)", value=1500.0, step=10.0)
with col2:
    switching = st.slider("Switching costs (1 low - 5 high)", 1, 5, 3)
    lifecycle = st.selectbox("Industry Life Cycle", ["Intro", "Growth", "Shakeout", "Mature", "Decline"], index=["Intro","Growth","Shakeout","Mature","Decline"].index(meta.get("life_cycle","Mature")))
with col3:
    s_strength = st.slider("SWOT - Strengths (1-5)", 1, 5, 3)
    s_weakness = st.slider("SWOT - Weaknesses (1-5)", 1, 5, 3)
    s_opportunity = st.slider("SWOT - Opportunities (1-5)", 1, 5, 3)
    s_threat = st.slider("SWOT - Threats (1-5)", 1, 5, 3)

porter_s = scoring.porter_score(regulation, r_and_d, hhi, switching)
life_s = scoring.lifecycle_score(lifecycle)
swot_s = scoring.swot_score(s_strength, s_weakness, s_opportunity, s_threat)
topdown = scoring.combine_topdown(porter_s, life_s, swot_s)

st.markdown(f"**Top-Down Combined Score (1-5):** {topdown:.2f} — Porter {porter_s:.2f}, LifeCycle {life_s:.2f}, SWOT {swot_s:.2f}")

metrics["fundamentals"]["topdown_score"] = topdown

# Compute actual score
result = scoring.compute_final_score(metrics)

# Show factor table and user-editable overrides
st.subheader("Factors & Contributions")
factors = []

# Volatility factors
v = metrics["volatility"]
factors.append(("1y volatility (ann)", round(v.get("1y_vol", 0), 4), scoring.normalize(v.get("1y_vol", 0), 0.0, 0.8), 0.40 * (1/3)))
factors.append(("Beta vs SPY", round(v.get("beta", 0), 3), scoring.normalize(v.get("beta", 0), 0.0, 3.0), 0.40 * (1/3)))
factors.append(("1y max drawdown", round(v.get("max_drawdown", 0), 4), scoring.normalize(v.get("max_drawdown", 0), 0.0, 1.0), 0.40 * (1/3)))

# Performance factors
p = metrics["performance"]
factors.append(("6m return", round(p.get("6m", 0), 4), scoring.normalize(p.get("6m", 0), -1.0, 1.0, invert=True), 0.30 * (1/3)))
factors.append(("12m return", round(p.get("12m", 0), 4), scoring.normalize(p.get("12m", 0), -1.0, 1.0, invert=True), 0.30 * (1/3)))
factors.append(("Sharpe (1y)", round(p.get("sharpe", 0), 3), scoring.normalize(p.get("sharpe", 0), -3.0, 3.0, invert=True), 0.30 * (1/3)))

# Behavior factors
b = metrics["behavior"]
factors.append(("Correlation with SPY", round(b.get("corr_spy", 0), 3), scoring.normalize(b.get("corr_spy", 0), -1.0, 1.0, invert=False), 0.20 * (1/2)))
factors.append(("Volume growth YoY (approx)", round(b.get("volume_growth", 0) if b.get("volume_growth") is not None else 0, 3), scoring.normalize(b.get("volume_growth", 0) if b.get("volume_growth") is not None else 0, -1.0, 2.0, invert=False), 0.20 * (1/2)))

# Fundamentals
fund_score = result["breakdown"].get("fundamentals", 0.0)
factors.append(("Fundamentals baseline (cyclical/defensive + top-down)", round(fund_score, 2), fund_score, 0.10))

df_table = pd.DataFrame(factors, columns=["Factor", "Raw Value", "Normalized (0-100)", "Category Weight Portion"])
st.dataframe(df_table)

# Display final scores side-by-side
st.subheader("Sector Risk Score")
colA, colB = st.columns(2)
with colA:
    st.metric("Actual Sector Risk Score (0-100)", f"{result['final_score']:.2f}")
with colB:
    # User modifications: allow overriding key raw values
    st.write("User overrides — adjust raw values to see new score")
    overrides = {}
    overrides["1y_vol"] = st.number_input("Override 1y vol (ann)", value=float(v.get("1y_vol", 0)), format="%.6f")
    overrides["beta"] = st.number_input("Override Beta", value=float(v.get("beta", 0)), format="%.3f")
    overrides["max_drawdown"] = st.number_input("Override Max Drawdown", value=float(v.get("max_drawdown", 0)), format="%.6f")
    overrides["6m"] = st.number_input("Override 6m return", value=float(p.get("6m", 0)), format="%.6f")
    overrides["12m"] = st.number_input("Override 12m return", value=float(p.get("12m", 0)), format="%.6f")
    overrides["sharpe"] = st.number_input("Override Sharpe", value=float(p.get("sharpe", 0)), format="%.3f")
    overrides["corr_spy"] = st.number_input("Override Correlation", value=float(b.get("corr_spy", 0)), format="%.3f")
    overrides["volume_growth"] = st.number_input("Override Volume Growth", value=float(b.get("volume_growth") if b.get("volume_growth") is not None else 0.0), format="%.3f")
    user_result = scoring.compute_final_score(metrics, overrides=overrides)
    st.metric("User-Modified Sector Risk Score (0-100)", f"{user_result['final_score']:.2f}")

# Charts
st.subheader("Charts")
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(plots.price_chart(etf_df, title=f"{etf_choice} — 2y Price"), use_container_width=True)
    st.plotly_chart(plots.rolling_volatility_chart(etf_df, window=21), use_container_width=True)
with col2:
    st.plotly_chart(plots.drawdown_chart(etf_df, title=f"{etf_choice} — Drawdown"), use_container_width=True)

st.markdown("---")
st.write("Methodology: Volatility (40%), Performance (30%), Market Behavior (20%), Fundamentals (10%). Scores are normalized to 0-100 where higher = more risk. Top-down model (Porter/Lifecycle/SWOT) feeds fundamentals.")
