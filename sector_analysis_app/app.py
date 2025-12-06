# Notes for next steps:
# Add all 11 sectors
#The ability for it to do the sector analysis for multiple different countries

# sector_analysis_app/app.py
import traceback
import sys
import os
import time
from io import StringIO

# Core imports
import streamlit as st
import pandas as pd

# Add current directory and src to path for flexible imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_current_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# Import helpers - now works in all contexts
try:
    from sector_analysis_app.src import data, scoring, plots, utils
except ImportError:
    try:
        from src import data, scoring, plots, utils
    except ImportError:
        # Last resort: direct import if src is already on path
        import data, scoring, plots, utils


# at top of file: ensure streamlit imported as st (already is)
@st.cache_data(ttl=86400, show_spinner=False)
def cached_get_spy_and_etf_csv(etf_ticker: str):
    """
    Cached wrapper — returns tuple of CSV strings (etf_csv, spy_csv).
    TTL: 24 hours (86400 seconds)
    """
    etf_df, spy_df = data.get_spy_and_etf(etf_ticker)
    return etf_df.to_csv(index=True), spy_df.to_csv(index=True)



def _read_df_from_session(key: str):
    csv = st.session_state.get(key)
    if not csv:
        return None
    try:
        return pd.read_csv(StringIO(csv), index_col=0, parse_dates=True)
    except Exception:
        # In case CSV corrupted
        return None


def _store_df_in_session(df: pd.DataFrame, key: str):
    st.session_state[key] = df.to_csv()


def main():
    # Small server-side trace to make logs useful
    print("APP START — new run", flush=True)

    # Streamlit UI setup
    st.set_page_config(page_title="Sector Risk Analysis", layout="wide")
    st.title("Sector Risk Analysis")
    st.markdown("This app computes a sector-level risk score (0-100) using price data and a top-down model.")

        # --- HEARTBEAT (visible and logs) ---
    hb = st.empty()
    hb.text(f"Server run started at {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC")

    # Also print a short server-side "tick" into the container logs for each run
    print(f"RUN HEARTBEAT: run at {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC", flush=True)


    # debug panel
    with st.sidebar.expander("Debug / Session"):
        st.write("data_loaded:", st.session_state.get("data_loaded"))
        st.write("last_ticker:", st.session_state.get("last_ticker"))
        st.write("etf_csv present:", "etf_csv" in st.session_state)
        st.write("spy_csv present:", "spy_csv" in st.session_state)
        # show sizes if present
        etf_csv = st.session_state.get("etf_csv")
        spy_csv = st.session_state.get("spy_csv")
        st.write("etf_csv len:", len(etf_csv) if etf_csv else None)
        st.write("spy_csv len:", len(spy_csv) if spy_csv else None)

        # Sidebar controls (use explicit widget keys so Streamlit keeps state stable)
    st.sidebar.header("Settings")
    etf_list = utils.get_etf_list()
    # choose initial index from session last_ticker if present, else first ETF
    default_etf = st.session_state.get("last_ticker") or etf_list[0]
    try:
        default_index = etf_list.index(default_etf)
    except ValueError:
        default_index = 0

    # Widget keys: keep these stable across reruns
    etf_choice = st.sidebar.selectbox(
        "Choose sector ETF",
        etf_list,
        index=default_index,
        key="etf_choice",
    )

    auto_fetch = st.sidebar.checkbox("Auto-fetch on ticker change", value=True, key="auto_fetch")
    run_button = st.sidebar.button("Refresh Data", key="refresh")

    # initialize session keys safely
    st.session_state.setdefault("data_loaded", False)
    st.session_state.setdefault("last_ticker", None)

    # copy local meta & header using the widget value from session to avoid mismatch
    meta = utils.get_etf_metadata(st.session_state.get("etf_choice", etf_choice))
    st.header(f"{meta['name']} ({st.session_state.get('etf_choice', etf_choice)})")
    st.write(meta["description"])

    # Decide whether to fetch:
    do_fetch = False
    last = st.session_state.get("last_ticker")

    # First load behavior: fetch if we have no CSV cached in session.
    if last is None and not st.session_state.get("etf_csv"):
        do_fetch = True
    # Manual refresh always fetch
    elif run_button:
        do_fetch = True
    # Auto-fetch only when user changed the ticker *intentionally* (compare session values)
    elif st.session_state.get("auto_fetch") and last != st.session_state.get("etf_choice"):
        do_fetch = True

    # Fetching block (safe serialization to CSV strings)
    if do_fetch:
        with st.spinner("Fetching data..."):
            try:
                # use cached CSV wrapper (long TTL) — returns (etf_csv, spy_csv)
                print(f"START FETCH: ticker={st.session_state.get('etf_choice', etf_choice)} last_ticker={st.session_state.get('last_ticker')} auto_fetch={st.session_state.get('auto_fetch')}", flush=True)
                etf_csv, spy_csv = cached_get_spy_and_etf_csv(st.session_state.get("etf_choice", etf_choice))
                # store CSVs in session (already compatible with your session approach)
                st.session_state["etf_csv"] = etf_csv
                st.session_state["spy_csv"] = spy_csv
                st.session_state["data_loaded"] = True
                # set last_ticker to the session widget value (stable)
                st.session_state["last_ticker"] = st.session_state.get("etf_choice", etf_choice)

                etf_df = pd.read_csv(StringIO(etf_csv), index_col=0, parse_dates=True)
                spy_df = pd.read_csv(StringIO(spy_csv), index_col=0, parse_dates=True)

                print(f"[FETCHED/CACHED] {st.session_state['last_ticker']} rows={len(etf_df)} SPY rows={len(spy_df)}", flush=True)
            except Exception as e:
                st.error("Failed to fetch price data for the selected ETF. See details below.")
                st.exception(e)
                st.session_state["data_loaded"] = False
                st.session_state.pop("etf_csv", None)
                st.session_state.pop("spy_csv", None)

        # ensure local variables defined (fallback)
        if "etf_df" not in locals():
            etf_df = _read_df_from_session("etf_csv")
            spy_df = _read_df_from_session("spy_csv")
    else:
        # load from session CSVs
        etf_df = _read_df_from_session("etf_csv")
        spy_df = _read_df_from_session("spy_csv")
        print(f"[LOAD FROM SESSION] etf_df is {'present' if etf_df is not None else 'None'}, spy_df is {'present' if spy_df is not None else 'None'}", flush=True)

    # If nothing loaded, show info and stop (safe)
    if not st.session_state.get("data_loaded", False):
        st.info("No market data loaded. Click 'Refresh Data' or enable 'Auto-fetch on ticker change' to load data for the selected ETF.")
        st.stop()

    # Compute metrics (guarded)
    metrics = {}
    try:
        metrics["volatility"] = scoring.compute_volatility_factors(etf_df, spy_df)
        metrics["performance"] = scoring.compute_performance_factors(etf_df)
        metrics["behavior"] = scoring.compute_market_behavior(etf_df, spy_df)
        metrics["fundamentals"] = {
            "cyclical": True if meta.get("category", "Cyclical") == "Cyclical" else False,
            "topdown_score": None,
        }
        print("METRICS computed OK", flush=True)
    except Exception as e:
        st.error("Error computing metrics from fetched data (falling back to safe defaults).")
        st.exception(e)
        metrics = {
            "volatility": {"1y_vol": 0.0, "beta": 1.0, "max_drawdown": 0.0},
            "performance": {"6m": 0.0, "12m": 0.0, "sharpe": 0.0},
            "behavior": {"corr_spy": 0.0, "volume_growth": 0.0},
            "fundamentals": {"cyclical": True, "topdown_score": None},
        }

    # Top-down inputs and compute
    st.subheader("Top-Down Model (Porter / Life Cycle / SWOT)")
    col1, col2, col3 = st.columns(3)
    with col1:
        regulation = st.selectbox("Regulation (0=no,1=yes)", [0, 1], index=0)
        r_and_d = st.number_input("R&D intensity (% revenue)", value=2.0, step=0.1)
        hhi = st.number_input("HHI concentration (0-10000)", value=1500.0, step=10.0)
    with col2:
        switching = st.slider("Switching costs (1 low - 5 high)", 1, 5, 3)
        lifecycle = st.selectbox(
            "Industry Life Cycle",
            ["Intro", "Growth", "Shakeout", "Mature", "Decline"],
            index=["Intro","Growth","Shakeout","Mature","Decline"].index(meta.get("life_cycle","Mature"))
        )
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
        st.markdown(f"**Top-Down Combined Score (1-5):** {topdown:.2f} — Porter {porter_s:.2f}, LifeCycle {life_s:.2f}, SWOT {swot_s:.2f}")
        metrics["fundamentals"]["topdown_score"] = topdown
    except Exception as e:
        st.error("Error computing top-down score.")
        st.exception(e)
        metrics["fundamentals"]["topdown_score"] = 3.0

    # Compute final score
    result = scoring.compute_final_score(metrics)

    # Factor table
    st.subheader("Factors & Contributions")
    factors = []
    v = metrics["volatility"]
    p = metrics["performance"]
    b = metrics["behavior"]

    factors.append(("1y volatility (ann)", round(v.get("1y_vol", 0), 4), scoring.normalize(v.get("1y_vol", 0), 0.0, 0.8), 0.40 * (1/3)))
    factors.append(("Beta vs SPY", round(v.get("beta", 0), 3), scoring.normalize(v.get("beta", 0), 0.0, 3.0), 0.40 * (1/3)))
    factors.append(("1y max drawdown", round(v.get("max_drawdown", 0), 4), scoring.normalize(v.get("max_drawdown", 0), 0.0, 1.0), 0.40 * (1/3)))
    factors.append(("6m return", round(p.get("6m", 0), 4), scoring.normalize(p.get("6m", 0), -1.0, 1.0, invert=True), 0.30 * (1/3)))
    factors.append(("12m return", round(p.get("12m", 0), 4), scoring.normalize(p.get("12m", 0), -1.0, 1.0, invert=True), 0.30 * (1/3)))
    factors.append(("Sharpe (1y)", round(p.get("sharpe", 0), 3), scoring.normalize(p.get("sharpe", 0), -3.0, 3.0, invert=True), 0.30 * (1/3)))
    factors.append(("Correlation with SPY", round(b.get("corr_spy", 0), 3), scoring.normalize(b.get("corr_spy", 0), -1.0, 1.0, invert=False), 0.20 * (1/2)))
    factors.append(("Volume growth YoY (approx)", round(b.get("volume_growth", 0) if b.get("volume_growth") is not None else 0, 3), scoring.normalize(b.get("volume_growth", 0) if b.get("volume_growth") is not None else 0, -1.0, 2.0, invert=False), 0.20 * (1/2)))

    fund_score = result["breakdown"].get("fundamentals", 0.0)
    factors.append(("Fundamentals baseline (cyclical/defensive + top-down)", round(fund_score, 2), fund_score, 0.10))

    df_table = pd.DataFrame(factors, columns=["Factor", "Raw Value", "Normalized (0-100)", "Category Weight Portion"])
    st.dataframe(df_table)

    # Scores + overrides
    st.subheader("Sector Risk Score")
    colA, colB = st.columns(2)
    with colA:
        st.metric("Actual Sector Risk Score (0-100)", f"{result['final_score']:.2f}")
    with colB:
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

    # Charts (defensive)
    st.subheader("Charts")
    col1, col2 = st.columns(2)
    with col1:
        try:
            if etf_df is None or etf_df.empty:
                st.warning("No price data available to display charts.")
            else:
                df = etf_df.copy()
                df.index = pd.to_datetime(df.index, errors="coerce")
                if "Date" in df.columns and df.index.isnull().any():
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    df = df.set_index("Date")
                df = df.sort_index()
                df = df.dropna(subset=["Close"])
                df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
                df = df.dropna(subset=["Close"])
                if df.empty:
                    st.warning("Price data exists but 'Close' column is empty after cleanup.")
                else:
                    st.plotly_chart(plots.price_chart(df, title=f"{etf_choice} — 2y Price"), width='stretch')
                    st.plotly_chart(plots.rolling_volatility_chart(df, window=21), width='stretch')
        except Exception as e:
            st.error("Failed to render charts on left column.")
            st.exception(e)
            print("Chart error:", traceback.format_exc(), flush=True)

    with col2:
        try:
            if etf_df is None or etf_df.empty:
                st.warning("No price data available to display charts.")
            else:
                df2 = etf_df.copy()
                df2.index = pd.to_datetime(df2.index, errors="coerce")
                if "Date" in df2.columns and df2.index.isnull().any():
                    df2["Date"] = pd.to_datetime(df2["Date"], errors="coerce")
                    df2 = df2.set_index("Date")
                df2 = df2.sort_index()
                df2 = df2.dropna(subset=["Close"])
                df2["Close"] = pd.to_numeric(df2["Close"], errors="coerce")
                df2 = df2.dropna(subset=["Close"])
                if df2.empty:
                    st.warning("Price data exists but 'Close' column is empty after cleanup for drawdown.")
                else:
                    st.plotly_chart(plots.drawdown_chart(df2, title=f"{etf_choice} — Drawdown"), width='stretch')
        except Exception as e:
            st.error("Failed to render drawdown chart.")
            st.exception(e)
            print("Drawdown chart error:", traceback.format_exc(), flush=True)

    st.markdown("---")
    st.write("Methodology: Volatility (40%), Performance (30%), Market Behavior (20%), Fundamentals (10%).")
    print("APP END — run finished normally", flush=True)


# Run the app inside a global try/except so errors surface instead of blanking
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Keep your existing error handling logic here
        try:
            st.set_page_config(page_title="Runtime Error", layout="centered")
            st.error("An unexpected error occurred.")
            st.exception(exc)
        except Exception:
            print(traceback.format_exc(), flush=True)
        raise