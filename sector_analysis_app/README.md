# Sector Risk Analysis Streamlit App

## Summary

This Streamlit app computes a transparent sector-level risk score (0–100) using market data and a simple top-down model. It is intended to be used as the "Sector Analysis" layer inside a larger top-down investment framework.

Features:
- Pulls real-time (yfinance) ETF price data (sector ETFs such as `XLK`, `XLF`, `XLY`, etc.)
- Computes volatility, performance, and market-behavior factors
- Includes a top-down model (Porter, Industry Life Cycle, SWOT) which feeds into fundamentals
- Presents both Actual Score (computed from data) and User-Modified Score (editable inputs)
- Interactive charts: price, drawdown, rolling volatility

## Directory Structure

```
/sector_analysis_app
    /src
        data.py
        scoring.py
        plots.py
        utils.py
    app.py
    requirements.txt
    README.md
```

## Purpose

This app provides a sector-level risk assessment used in top-down investing. The primary output is a Sector Risk Score between 0 (very safe) and 100 (very risky). The score is computed from four layers: Volatility (40%), Performance (30%), Market Behavior (20%), and Fundamentals (10%).

## How the score is calculated

- Volatility factors (40%): 1-year annualized volatility, beta vs SPY, max drawdown.
- Performance factors (30%): 6-month return, 12-month return, 1-year Sharpe ratio (RF=4%).
- Market behavior (20%): correlation with SPY and volume growth YoY.
- Fundamentals (10%): a baseline depending on cyclical/defensive classification and a top-down model score derived from Porter+Industry-LifeCycle+SWOT.

Each factor is normalized to 0–100 using min–max scaling (tunable bounds). Higher normalized values indicate higher risk. Category scores are averaged per category, then combined with the weights above to produce the final 0–100 Sector Risk Score.

Top-Down model (Porter/Life Cycle/SWOT):
- Porter: five forces are scored (1–5) using inputs like regulation (binary), R&D intensity (% revenue), HHI concentration, and switching costs (1–5).
- Industry Life Cycle: mapped to [Intro, Growth, Shakeout, Mature, Decline] and numeric mapping (Growth=5, Mature=3, Decline=1).
- SWOT: user-entered Strengths/Weaknesses/Opportunities/Threats (1–5) combined into a 1–5 score.
- Combined with weights: Porter 40%, LifeCycle 35%, SWOT 25% → Top-down score (1–5). This is mapped into a risk baseline and blended with cyclical/defensive baseline.

## Data sources

- Price & ETF data: `yfinance` (uses Yahoo Finance public APIs)

## How to run

1. Create a Python environment and install requirements:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r sector_analysis_app\requirements.txt
```

2. From the workspace root run:

```powershell
streamlit run sector_analysis_app\app.py
```

The app will open in your browser. Select a sector ETF, tweak Top-Down inputs or any factor override, and observe the Actual vs User-Modified scores.

## Example

Analyze `XLK` (Technology): the app fetches 2 years of price data, computes 1-year volatility, drawdown, Sharpe, correlations, and derives a numeric Sector Risk Score. Use the Top-Down controls to adjust Porter/LC/SWOT assumptions and immediately see the impact on the fundamentals and final score.

## Next steps / Improvements

- Expand ETF metadata (AUM, expense ratio) via a verified fund dataset API
- Build a small calibration dataset to derive normalization bounds from cross-sectional data rather than fixed bounds
- Add more advanced fundamentals (sector-level earnings growth, leverage, R&D aggregated from filings)

## Files of interest

- `sector_analysis_app/app.py` — main Streamlit UI
- `sector_analysis_app/src/data.py` — data fetching and helpers
- `sector_analysis_app/src/scoring.py` — normalization and scoring
- `sector_analysis_app/src/plots.py` — chart helpers
