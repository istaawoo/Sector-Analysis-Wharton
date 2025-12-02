import numpy as np
import pandas as pd
from scipy.stats import zscore


def annualize_volatility(daily_std: float) -> float:
    return daily_std * np.sqrt(252)


def normalize(value, vmin, vmax, invert=False):
    """Min-max normalize to 0-100 and clip. If invert=True, higher raw -> lower normalized.
    """
    if np.isnan(value):
        return 50.0
    vmin = float(vmin)
    vmax = float(vmax)
    if vmax == vmin:
        return 50.0
    val = (value - vmin) / (vmax - vmin)
    val = np.clip(val, 0.0, 1.0)
    if invert:
        val = 1.0 - val
    return float(val * 100)


def minmax_scale_series(series: pd.Series, vmin=None, vmax=None, invert=False):
    if vmin is None:
        vmin = series.min()
    if vmax is None:
        vmax = series.max()
    return series.apply(lambda x: normalize(x, vmin, vmax, invert=invert))


def compute_volatility_factors(etf_df: pd.DataFrame, spy_df: pd.DataFrame) -> dict:
    # Use last 1 year window
    end = etf_df.index.max()
    start = end - pd.DateOffset(years=1)
    etf_1y = etf_df.loc[start:end].copy()
    spy_1y = spy_df.loc[start:end].copy()

    etf_1y["ret"] = etf_1y["Close"].pct_change()
    spy_1y["ret"] = spy_1y["Close"].pct_change()

    daily_std = etf_1y["ret"].std()
    ann_vol = annualize_volatility(daily_std)
    # beta
    cov = etf_1y["ret"].cov(spy_1y["ret"])
    var_spy = spy_1y["ret"].var()
    beta = cov / var_spy if var_spy > 0 else np.nan
    # max drawdown
    max_dd = compute_max_drawdown(etf_1y["Close"]) if not etf_1y.empty else np.nan

    return {
        "1y_vol": ann_vol,
        "beta": beta,
        "max_drawdown": abs(max_dd),
    }


def compute_performance_factors(etf_df: pd.DataFrame) -> dict:
    end = etf_df.index.max()
    six_m = end - pd.DateOffset(months=6)
    twelve_m = end - pd.DateOffset(months=12)
    # last price
    price_now = etf_df["Close"].iloc[-1]
    # find values closest to dates
    p_6m = etf_df.loc[etf_df.index >= six_m]["Close"].iloc[0] if any(etf_df.index >= six_m) else etf_df["Close"].iloc[0]
    p_12m = etf_df.loc[etf_df.index >= twelve_m]["Close"].iloc[0] if any(etf_df.index >= twelve_m) else etf_df["Close"].iloc[0]

    ret_6m = price_now / p_6m - 1.0
    ret_12m = price_now / p_12m - 1.0

    # Sharpe: use 1y daily returns
    df = etf_df.copy()
    df["ret"] = df["Close"].pct_change()
    mean_daily = df["ret"].mean()
    std_daily = df["ret"].std()
    rf_annual = 0.04
    rf_daily = rf_annual / 252
    sharpe = (mean_daily - rf_daily) / std_daily * np.sqrt(252) if std_daily and not np.isnan(std_daily) else np.nan

    return {
        "6m": ret_6m,
        "12m": ret_12m,
        "sharpe": sharpe,
    }


def compute_market_behavior(etf_df: pd.DataFrame, spy_df: pd.DataFrame) -> dict:
    end = etf_df.index.max()
    start = end - pd.DateOffset(years=1)
    etf_1y = etf_df.loc[start:end].copy()
    spy_1y = spy_df.loc[start:end].copy()
    etf_1y["ret"] = etf_1y["Close"].pct_change()
    spy_1y["ret"] = spy_1y["Close"].pct_change()

    corr = etf_1y["ret"].corr(spy_1y["ret"])
    # volume growth: compare last 6 months avg volume to prior 6 months avg
    mid = end - pd.DateOffset(months=6)
    vol_recent = etf_df.loc[etf_df.index >= mid]["Volume"].mean()
    vol_prior = etf_df.loc[(etf_df.index < mid) & (etf_df.index >= (mid - pd.DateOffset(months=6)))]["Volume"].mean()
    vol_growth = (vol_recent - vol_prior) / vol_prior if vol_prior and not np.isnan(vol_prior) else np.nan

    return {
        "corr_spy": corr,
        "volume_growth": vol_growth,
    }


def compute_final_score(metrics: dict, overrides: dict = None) -> dict:
    """Combine metrics into final 0-100 risk score.

    Metrics expected keys:
      volatility: dict (1y_vol, beta, max_drawdown)
      performance: dict (6m, 12m, sharpe)
      behavior: dict (corr_spy, volume_growth)
      fundamentals: dict (cyclical_flag: bool -> baseline)

    Returns dict with breakdown and final score.
    """
    if overrides is None:
        overrides = {}

    # Normalization bounds (tunable)
    # Volatility: annual vol 0-0.8
    vol = metrics.get("volatility", {})
    perf = metrics.get("performance", {})
    beh = metrics.get("behavior", {})
    fund = metrics.get("fundamentals", {})

    v_1y = overrides.get("1y_vol", vol.get("1y_vol"))
    v_beta = overrides.get("beta", vol.get("beta"))
    v_dd = overrides.get("max_drawdown", vol.get("max_drawdown"))

    p_6m = overrides.get("6m", perf.get("6m"))
    p_12m = overrides.get("12m", perf.get("12m"))
    p_sharpe = overrides.get("sharpe", perf.get("sharpe"))

    b_corr = overrides.get("corr_spy", beh.get("corr_spy"))
    b_volg = overrides.get("volume_growth", beh.get("volume_growth"))

    # Normalize to 0-100 where higher -> more risk
    s_v1 = normalize(v_1y, 0.0, 0.8, invert=False)
    s_beta = normalize(v_beta if v_beta is not None else 1.0, 0.0, 3.0, invert=False)
    s_dd = normalize(v_dd if v_dd is not None else 0.0, 0.0, 1.0, invert=False)

    # For returns and sharpe: better performance -> lower risk, so invert=True
    s_6m = normalize(p_6m if p_6m is not None else 0.0, -1.0, 1.0, invert=True)
    s_12m = normalize(p_12m if p_12m is not None else 0.0, -1.0, 1.0, invert=True)
    s_sharpe = normalize(p_sharpe if p_sharpe is not None else 0.0, -3.0, 3.0, invert=True)

    # Correlation: higher correlation -> more market-driven -> higher risk
    s_corr = normalize(b_corr if b_corr is not None else 0.0, -1.0, 1.0, invert=False)
    s_volg = normalize(b_volg if b_volg is not None else 0.0, -1.0, 2.0, invert=False)

    # CategoryScores
    volatility_score = np.nanmean([s_v1, s_beta, s_dd])
    performance_score = np.nanmean([s_6m, s_12m, s_sharpe])
    behavior_score = np.nanmean([s_corr, s_volg])

    # Fundamentals baseline: use cyclical flag
    cyc_flag = fund.get("cyclical", True)
    cyc_baseline = 60.0 if cyc_flag else 20.0
    # If a top-down score exists (1-5), incorporate it
    topdown = fund.get("topdown_score")
    if topdown is not None:
        # Map 1-5 (higher better) to 0-100 risk (higher worse)
        topdown_risk = 100.0 * (1.0 - ((topdown - 1.0) / 4.0))
        fundamental_score = 0.7 * topdown_risk + 0.3 * cyc_baseline
    else:
        fundamental_score = cyc_baseline

    # Category weights
    w_vol = 0.40
    w_perf = 0.30
    w_beh = 0.20
    w_fund = 0.10

    final = (
        volatility_score * w_vol
        + performance_score * w_perf
        + behavior_score * w_beh
        + fundamental_score * w_fund
    )

    return {
        "breakdown": {
            "volatility": float(volatility_score),
            "performance": float(performance_score),
            "behavior": float(behavior_score),
            "fundamental": float(fundamental_score),
        },
        "final_score": float(final),
        "components": {
            "s_v1": s_v1,
            "s_beta": s_beta,
            "s_dd": s_dd,
            "s_6m": s_6m,
            "s_12m": s_12m,
            "s_sharpe": s_sharpe,
            "s_corr": s_corr,
            "s_volg": s_volg,
        },
    }


def compute_max_drawdown(prices: pd.Series) -> float:
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    return drawdown.min()


# --- Top-down model (Porter + LifeCycle + SWOT) ---
def porter_score(regulation_binary: int, r_and_d_pct: float, hhi: float, switching_costs: int, other_force: int = 3) -> float:
    """Return average 1-5 score where higher is more attractive (lower risk).
    Inputs expected as:
      regulation_binary: 0 or 1 (1 = heavy regulation -> worse)
      r_and_d_pct: percent of revenue (higher -> stronger defensibility -> better)
      hhi: concentration measure (higher -> more concentrated -> better)
      switching_costs: 1-5 qualitative where higher = higher switching costs -> better
    """
    # Map regulation to score
    reg_score = 5.0 if regulation_binary == 0 else 2.0
    # R&D: scale 0-10% -> score
    rscore = normalize(r_and_d_pct / 100.0, 0.0, 0.10, invert=False) / 20.0 * 5.0
    rscore = np.clip(rscore, 1.0, 5.0)
    # HHI: higher is more concentrated (good)
    hhi_score = normalize(hhi, 0.0, 10000.0, invert=False) / 20.0 * 5.0
    hhi_score = np.clip(hhi_score, 1.0, 5.0)
    sc_score = float(np.clip(switching_costs, 1, 5))

    forces = [reg_score, rscore, hhi_score, sc_score, float(other_force)]
    return float(np.mean(forces))


def lifecycle_score(stage: str) -> float:
    mapping = {
        "Intro": 1.0,
        "Growth": 5.0,
        "Shakeout": 3.0,
        "Mature": 3.0,
        "Decline": 1.0,
    }
    return float(mapping.get(stage, 3.0))


def swot_score(strengths: int, weaknesses: int, opportunities: int, threats: int) -> float:
    # All inputs 1-5 where higher strengths/opportunities are good, higher weaknesses/threats are bad
    strengths = np.clip(strengths, 1, 5)
    weaknesses = np.clip(weaknesses, 1, 5)
    opportunities = np.clip(opportunities, 1, 5)
    threats = np.clip(threats, 1, 5)
    # Net: (S + O) - (W + T) mapped to 1-5
    raw = (strengths + opportunities) - (weaknesses + threats)
    # raw range: -8..8 -> map to 1..5
    scaled = (raw + 8) / 16 * 4 + 1
    return float(np.clip(scaled, 1.0, 5.0))


def combine_topdown(porter_s: float, lifecycle_s: float, swot_s: float, weights=(0.4, 0.35, 0.25)) -> float:
    p, l, s = weights
    return float(porter_s * p + lifecycle_s * l + swot_s * s)
