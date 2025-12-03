import streamlit as st
import pandas as pd
# Top of sector_analysis_app/app.py
from .src import data, scoring, plots, utils


@st.cache_data(ttl=300)
def cached_get_spy_and_etf(etf_ticker: str):
    """Cached wrapper around data.get_spy_and_etf to reduce repeated network calls.
       Returns tuple (etf_df, spy_df) or raises RuntimeError with message.
    """
    return data.get_spy_and_etf(etf_ticker)



st.set_page_config(page_title="Sector Risk Analysis", layout="wide")

st.title("Sector Risk Analysis")

st.markdown("This app computes a sector-level risk score (0-100) using price data and a top-down model.")

with st.sidebar.expander("Debug / Session"):
    st.write("data_loaded:", st.session_state.get("data_loaded"))
    st.write("last_ticker:", st.session_state.get("last_ticker"))
    st.write("etf_df rows:", None if st.session_state.get("etf_df") is None else len(st.session_state.get("etf_df")))
    st.write("spy_df rows:", None if st.session_state.get("spy_df") is None else len(st.session_state.get("spy_df")))


# Sidebar
st.sidebar.header("Settings")
etf_choice = st.sidebar.selectbox("Choose sector ETF", utils.get_etf_list())
# Let user choose whether to auto-fetch when changing ticker. Default: manual to avoid blocking on interaction.
auto_fetch = st.sidebar.checkbox("Auto-fetch on ticker change", value=True)
run_button = st.sidebar.button("Refresh Data")

# Initialize session state for data caching and last ticker
if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False
if "etf_df" not in st.session_state:
    st.session_state["etf_df"] = None
if "spy_df" not in st.session_state:
    st.session_state["spy_df"] = None
if "last_ticker" not in st.session_state:
    st.session_state["last_ticker"] = None

meta = utils.get_etf_metadata(etf_choice)

st.header(f"{meta['name']} ({etf_choice})")
st.write(meta["description"])

# Fetch data only when requested:
# - Always fetch on first app load (last_ticker is None) so the homepage shows the default ticker
# - Fetch when user clicks Refresh
# - If auto_fetch enabled, fetch when ticker changes
do_fetch = False
if st.session_state.get("last_ticker") is None:
    do_fetch = True  # first load: pull default ETF
elif run_button:
    do_fetch = True
elif auto_fetch and st.session_state.get("last_ticker") != etf_choice:
    do_fetch = True


if do_fetch:
    with st.spinner("Fetching data..."):
        try:
            etf_df, spy_df = cached_get_spy_and_etf(etf_choice)
            # sanity checks
            if etf_df is None or etf_df.empty:
                st.error(f"Fetched {etf_choice} returned no price rows.")
                st.session_state["data_loaded"] = False
            elif spy_df is None or spy_df.empty:
                st.error("Fetched SPY returned no price rows.")
                st.session_state["data_loaded"] = False
            else:
                st.session_state["etf_df"] = etf_df
                st.session_state["spy_df"] = spy_df
                st.session_state["data_loaded"] = True
                st.session_state["last_ticker"] = etf_choice
        except Exception as e:
            # show human-readable error and keep UI alive (don't crash to a blank page)
            st.error("Failed to fetch price data for the selected ETF. See details below.")
            st.exception(e)
            st.session_state["data_loaded"] = False
    # ensure local variables are defined after fetch attempt
    etf_df = st.session_state.get("etf_df")
    spy_df = st.session_state.get("spy_df")
else:
    etf_df = st.session_state.get("etf_df")
    spy_df = st.session_state.get("spy_df")


# If no data has been loaded yet, prompt the user and stop further heavy computation
if not st.session_state.get("data_loaded", False):
    st.info("No market data loaded. Click 'Refresh Data' or enable 'Auto-fetch on ticker change' to load data for the selected ETF.")
    st.stop()

metrics = {}
try:
    metrics["volatility"] = scoring.compute_volatility_factors(etf_df, spy_df)
    metrics["performance"] = scoring.compute_performance_factors(etf_df)
    metrics["behavior"] = scoring.compute_market_behavior(etf_df, spy_df)
    metrics["fundamentals"] = {
        "cyclical": True if meta.get("category", "Cyclical") == "Cyclical" else False,
        "topdown_score": None,
    }
except Exception as e:
    st.error("Error computing metrics from fetched data (falling back to safe defaults).")
    st.exception(e)
    # safe fallback so UI can continue instead of terminating
    metrics = {
        "volatility": {"1y_vol": 0.0, "beta": 1.0, "max_drawdown": 0.0},
        "performance": {"6m": 0.0, "12m": 0.0, "sharpe": 0.0},
        "behavior": {"corr_spy": 0.0, "volume_growth": 0.0},
        "fundamentals": {"cyclical": True, "topdown_score": None},
    }


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

try:
    porter_s = scoring.porter_score(regulation, r_and_d, hhi, switching)
    life_s = scoring.lifecycle_score(lifecycle)
    swot_s = scoring.swot_score(s_strength, s_weakness, s_opportunity, s_threat)
    topdown = scoring.combine_topdown(porter_s, life_s, swot_s)

    st.markdown(
        f"**Top-Down Combined Score (1-5):** {topdown:.2f} — Porter {porter_s:.2f}, LifeCycle {life_s:.2f}, SWOT {swot_s:.2f}"
    )

    metrics["fundamentals"]["topdown_score"] = topdown
except Exception as e:
    st.error("Error computing top-down score.")
    st.exception(e)
    # fall back to neutral topdown
    metrics["fundamentals"]["topdown_score"] = 3.0


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
    try:
        if etf_df is None or etf_df.empty:
            st.warning("No price data available to display charts.")
        else:
            # defensive copy and cleanup
            df = etf_df.copy()
            # ensure datetime index and sorted
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                # if index can't convert, try resetting index and using a date column if present
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    df = df.set_index("Date")
            df = df.sort_index()
            # drop rows missing the Close column
            df = df.dropna(subset=["Close"])
            if df.empty:
                st.warning("Price data exists but 'Close' column is empty after dropping NaNs.")
            else:
                # smaller defensive check: ensure numeric Close
                df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
                df = df.dropna(subset=["Close"])
                if df.empty:
                    st.warning("Price 'Close' column cannot be coerced to numeric.")
                else:
                    # plot price and rolling vol using cleaned df
                    st.plotly_chart(plots.price_chart(df, title=f"{etf_choice} — 2y Price"), use_container_width=True)
                    # rolling volatility expects a 'Close' column and percent-change will produce NaNs at start; that's fine
                    st.plotly_chart(plots.rolling_volatility_chart(df, window=21), use_container_width=True)
    except Exception as e:
        st.error("Failed to render charts on left column.")
        st.exception(e)
with col2:
    try:
        if etf_df is None or etf_df.empty:
            st.warning("No price data available to display charts.")
        else:
            # use same defensive cleanup for drawdown chart
            df2 = etf_df.copy()
            try:
                df2.index = pd.to_datetime(df2.index)
            except Exception:
                if "Date" in df2.columns:
                    df2["Date"] = pd.to_datetime(df2["Date"], errors="coerce")
                    df2 = df2.set_index("Date")
            df2 = df2.sort_index()
            df2 = df2.dropna(subset=["Close"])
            df2["Close"] = pd.to_numeric(df2["Close"], errors="coerce")
            df2 = df2.dropna(subset=["Close"])
            if df2.empty:
                st.warning("Price data exists but 'Close' column is empty after cleanup for drawdown.")
            else:
                st.plotly_chart(plots.drawdown_chart(df2, title=f"{etf_choice} — Drawdown"), use_container_width=True)
    except Exception as e:
        st.error("Failed to render drawdown chart.")
        st.exception(e)


st.markdown("---")
st.write("Methodology: Volatility (40%), Performance (30%), Market Behavior (20%), Fundamentals (10%). Scores are normalized to 0-100 where higher = more risk. Top-down model (Porter/Lifecycle/SWOT) feeds fundamentals.")
