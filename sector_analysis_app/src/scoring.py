import numpy as np
import pandas as pd
from scipy.stats import zscore


def annualize_volatility(daily_std: float) -> float:
    return daily_std * np.sqrt(252)


def normalize(value, vmin, vmax, invert=False):
    """Min-max normalize to 0-100 and clip. If invert=True, higher raw -> lower normalized.
    Missing or invalid values return neutral 50.0.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 50.0
    vmin = float(vmin)
    vmax = float(vmax)
    if vmax == vmin:
        return 50.0
    val = (float(value) - vmin) / (vmax - vmin)
    val = np.clip(val, 0.0, 1.0)
    if invert:
        val = 1.0 - val
    return float(val * 100.0)


def minmax_scale_series(series: pd.Series, vmin=None, vmax=None, invert=False):
    if vmin is None:
        vmin = series.min()
    if vmax is None:
        vmax = series.max()
    return series.apply(lambda x: normalize(x, vmin, vmax, invert=invert))


def compute_volatility_factors(etf_df: pd.DataFrame, spy_df: pd.DataFrame) -> dict:
    # Use last 1 year window
    if etf_df is None or etf_df.empty:
        return {"1y_vol": np.nan, "beta": np.nan, "max_drawdown": np.nan}
    end = etf_df.index.max()
    start = end - pd.DateOffset(years=1)
    etf_1y = etf_df.loc[start:end].copy()
    spy_1y = spy_df.loc[start:end].copy() if (spy_df is not None and not spy_df.empty) else pd.DataFrame()

    etf_1y["ret"] = etf_1y["Close"].pct_change()
    if not spy_1y.empty:
        spy_1y["ret"] = spy_1y["Close"].pct_change()

    daily_std = etf_1y["ret"].std()
    ann_vol = annualize_volatility(daily_std) if not np.isnan(daily_std) else np.nan

    cov = np.nan
    var_spy = np.nan
    beta = np.nan
    if not spy_1y.empty:
        cov = etf_1y["ret"].cov(spy_1y["ret"])
        var_spy = spy_1y["ret"].var()
    if not np.isnan(cov) and not np.isnan(var_spy) and var_spy > 0:
        beta = cov / var_spy

    # max drawdown (positive fraction)
    max_dd = compute_max_drawdown(etf_1y["Close"]) if not etf_1y.empty else np.nan

    return {"1y_vol": ann_vol, "beta": beta, "max_drawdown": float(max_dd)}


def compute_performance_factors(etf_df: pd.DataFrame) -> dict:
    if etf_df is None or etf_df.empty:
        return {"6m": np.nan, "12m": np.nan, "sharpe": np.nan}
    end = etf_df.index.max()
    six_m = end - pd.DateOffset(months=6)
    twelve_m = end - pd.DateOffset(months=12)
    price_now = float(etf_df["Close"].iloc[-1])

    def _closest_price_before(df: pd.DataFrame, target_date):
        # returns the price on the nearest index <= target_date, otherwise first available
        if df is None or df.empty:
            return np.nan
        idx = df.index.searchsorted(target_date, side="right") - 1
        if idx < 0:
            return float(df["Close"].iloc[0])
        return float(df["Close"].iloc[idx])

    p_6m = _closest_price_before(etf_df, six_m)
    p_12m = _closest_price_before(etf_df, twelve_m)

    ret_6m = (price_now / p_6m - 1.0) if (p_6m and not np.isnan(p_6m) and p_6m != 0) else np.nan
    ret_12m = (price_now / p_12m - 1.0) if (p_12m and not np.isnan(p_12m) and p_12m != 0) else np.nan

    df = etf_df.copy()
    df["ret"] = df["Close"].pct_change()
    mean_daily = df["ret"].mean()
    std_daily = df["ret"].std()
    rf_annual = 0.04
    rf_daily = rf_annual / 252
    sharpe = np.nan
    if std_daily and not np.isnan(std_daily) and std_daily != 0:
        sharpe = (mean_daily - rf_daily) / std_daily * np.sqrt(252)

    return {"6m": ret_6m, "12m": ret_12m, "sharpe": sharpe}


def compute_market_behavior(etf_df: pd.DataFrame, spy_df: pd.DataFrame) -> dict:
    if etf_df is None or etf_df.empty:
        return {"corr_spy": np.nan, "volume_growth": np.nan}
    end = etf_df.index.max()
    start = end - pd.DateOffset(years=1)
    etf_1y = etf_df.loc[start:end].copy()
    spy_1y = spy_df.loc[start:end].copy() if (spy_df is not None and not spy_df.empty) else pd.DataFrame()
    etf_1y["ret"] = etf_1y["Close"].pct_change()
    if not spy_1y.empty:
        spy_1y["ret"] = spy_1y["Close"].pct_change()

    corr = np.nan
    if not spy_1y.empty:
        corr = etf_1y["ret"].corr(spy_1y["ret"]) if not etf_1y["ret"].isna().all() else np.nan

    mid = end - pd.DateOffset(months=6)
    vol_recent = etf_df.loc[etf_df.index >= mid]["Volume"].mean()
    vol_prior = etf_df.loc[(etf_df.index < mid) & (etf_df.index >= (mid - pd.DateOffset(months=6)))]["Volume"].mean()
    vol_growth = (vol_recent - vol_prior) / vol_prior if vol_prior and not np.isnan(vol_prior) and vol_prior != 0 else np.nan

    return {"corr_spy": corr, "volume_growth": vol_growth}


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
        try:
            td = float(topdown)
            # Map 1->0 risk, 5->100 risk then blend with cyc baseline
            topdown_risk = ((td - 1.0) / 4.0) * 100.0
            fundamentals_score = float(np.mean([cyc_baseline, topdown_risk]))
        except Exception:
            fundamentals_score = float(cyc_baseline)
    else:
        fundamentals_score = float(cyc_baseline)

    # Category weights
    w_vol = 0.40
    w_perf = 0.30
    w_beh = 0.20
    w_fund = 0.10

    final = (
        volatility_score * w_vol
        + performance_score * w_perf
        + behavior_score * w_beh
        + fundamentals_score * w_fund
    )

    # ensure final is numeric
    if np.isnan(final):
        final = 50.0

    return {
        "breakdown": {
            "volatility": float(volatility_score),
            "performance": float(performance_score),
            "behavior": float(behavior_score),
            "fundamentals": float(fundamentals_score),
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
    """Return maximum drawdown as a positive fraction (e.g., 0.25 == 25%)."""
    if prices is None or prices.empty:
        return 0.0
    roll_max = prices.cummax()
    drawdown = (roll_max - prices) / roll_max
    max_dd = drawdown.max()
    return float(max_dd if not pd.isna(max_dd) else 0.0)


# --- Top-down model (Porter + LifeCycle + SWOT) ---
def porter_score(regulation_binary: int, r_and_d_pct: float, hhi: float, switching_costs: int, other_force: int = 3) -> float:
        """Return average 1-5 score where higher is more attractive (lower risk).
        Inputs expected as:
            regulation_binary: 0 or 1 (1 = heavy regulation -> worse)
            r_and_d_pct: percent of revenue (higher -> stronger defensibility -> better)
            hhi: concentration measure (higher -> more concentrated -> better)
            switching_costs: 1-5 qualitative where higher = higher switching costs -> better
        """
        reg_score = 5.0 if int(regulation_binary) == 0 else 2.0

        def to_1_5(raw, vmin, vmax, invert=False):
                # normalize -> 0-1 -> map to 1-5
                norm100 = normalize(raw, vmin, vmax, invert=invert)
                norm01 = norm100 / 100.0
                return 1.0 + norm01 * 4.0

        rscore = to_1_5((r_and_d_pct / 100.0) if r_and_d_pct is not None else 0.0, 0.0, 0.10, invert=False)
        hhi_score = to_1_5(hhi if hhi is not None else 0.0, 0.0, 10000.0, invert=False)
        sc_score = float(np.clip(switching_costs if switching_costs is not None else 3, 1, 5))
        other = float(np.clip(other_force if other_force is not None else 3, 1, 5))

        forces = [reg_score, rscore, hhi_score, sc_score, other]
        return float(np.mean(forces))


def lifecycle_score(stage: str) -> float:
    mapping = {"intro": 1.0, "growth": 5.0, "shakeout": 3.0, "mature": 3.0, "decline": 1.0}
    if stage is None:
        return 3.0
    key = stage.strip().lower()
    return float(mapping.get(key, 3.0))


def swot_score(strengths: int, weaknesses: int, opportunities: int, threats: int) -> float:
    # Inputs expected 1-5. Produce net 1-5 where higher -> stronger (less risky)
    s = float(np.clip(strengths if strengths is not None else 3, 1, 5))
    w = float(np.clip(weaknesses if weaknesses is not None else 3, 1, 5))
    o = float(np.clip(opportunities if opportunities is not None else 3, 1, 5))
    t = float(np.clip(threats if threats is not None else 3, 1, 5))
    net = (s + o) - (w + t)
    norm = (net + 8.0) / 16.0
    return float(1.0 + norm * 4.0)


def combine_topdown(porter_s: float, lifecycle_s: float, swot_s: float, weights=(0.4, 0.35, 0.25)) -> float:
    p, l, s = float(porter_s), float(lifecycle_s), float(swot_s)
    w1, w2, w3 = weights
    combined_1_5 = (p * w1 + l * w2 + s * w3) / (w1 + w2 + w3)
    return float(combined_1_5)
