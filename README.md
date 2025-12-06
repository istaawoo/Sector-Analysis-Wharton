# PRISM — Portfolio Risk & Investment Scoring Model

## Purpose
PRISM scores country-sector combinations (0–100) to support top-down investment allocation decisions. It also assesses alignment between a proposed portfolio and PRISM recommendations and produces a professional justification report.

## Features

- **Country-Sector Scoring**: Analyzes top 40 economies × 11 GICS sectors = 440 investment opportunities
- **Multi-Factor Analysis**: Combines Porter's 5 Forces, Industry Life Cycle, firm fundamentals, market behavior, and country macro indicators
- **Allocation Justification**: Maps your existing portfolio to PRISM scores and generates detailed justifications
- **Parameter Backsolving**: If allocations don't match top PRISM picks, suggests minimal weight adjustments to support your decisions
- **Transparent Methodology**: All scoring formulas, normalization ranges, and data sources documented

## Quick Start (Local)

### 1. Setup Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run PRISM Analysis

```powershell
# Full analysis with default settings
python run_prism.py --output_dir output/

# With custom parameters
python run_prism.py --output_dir output/ --top_n 10 --cache_dir data_cache/
```

### 3. View Outputs

After running, check the `output/` directory for:

- **`prism_country_sector_scores.csv`** — Full matrix of PRISM scores for all country-sector pairs
- **`prism_sector_scores.json`** — Same data in nested JSON format (country → sector → metrics)
- **`allocation_alignment.csv`** — Your portfolio allocations mapped to PRISM scores
- **`allocation_alignment.json`** — Same with detailed justifications for each holding
- **`justification_report.md`** — Executive summary and allocation-by-allocation justifications (presentation-ready)
- **`methodology.md`** — Complete technical documentation of PRISM scoring
- **`backsolve_changes.json`** — Parameter adjustment suggestions if allocations don't match PRISM top picks

## PRISM Scoring Components

PRISM evaluates country-sector pairs on a 0-100 scale using four weighted components:

### 1. Structural Score (35%)
- **Porter's 5 Forces**: Barriers to entry, threat of substitutes, supplier/buyer power, rivalry
- **Industry Life Cycle**: Intro, Growth, Shakeout, Mature, Decline stages

### 2. Fundamental Quality Score (30%)
- Market-cap weighted firm metrics: ROE, profit margin, revenue growth, FCF, debt/equity, gross margin
- Based on top 5-10 companies per sector by market cap

### 3. Market Behavior Score (20%)
- Recent returns (6m, 12m), annualized volatility, max drawdown, beta vs SPY
- Uses largest firm as sector proxy

### 4. Top-Down Mission-Fit Score (15%)
- Country GDP growth, GDP per capita
- SWOT analysis (strengths, weaknesses, opportunities, threats)

**Final Formula:**
```
PRISM = 0.35 × Structural + 0.30 × Fundamentals + 0.20 × Behavior + 0.15 × TopDown
```

## Tier Definitions

- **Overweight** (PRISM ≥ 70): Strong opportunity, recommended overweight position
- **Neutral** (55 ≤ PRISM < 70): Moderate opportunity, neutral weight
- **Underweight** (PRISM < 55): Lower opportunity, consider underweight or avoid

## Data Sources

1. **Country Macro**: Top 40 economies by nominal GDP (World Bank / IMF 2023 estimates)
2. **Company Fundamentals**: Yahoo Finance API via `yfinance`
3. **Price Data**: Yahoo Finance historical prices (2-year lookback)
4. **Sector Constituents**: Curated lists of top companies per country-sector, supplemented by yfinance sector tags

## Project Structure

```
Sector-Analysis-Wharton/
├── run_prism.py                    # Main CLI orchestrator
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── sector_analysis_app/
│   ├── app.py                       # Original Streamlit sector analysis app
│   └── src/
│       ├── prism_country_data.py    # Country data fetcher (GDP, GDP per capita, growth)
│       ├── prism_sector_constituents.py  # Sector constituent finder & fundamentals
│       ├── prism_scoring.py         # PRISM scoring engine (all 4 components)
│       ├── prism_allocation.py      # Allocation alignment & justification generator
│       ├── data.py                  # Original app data fetcher
│       ├── scoring.py               # Original app scoring logic
│       ├── plots.py                 # Original app plotting functions
│       └── utils.py                 # Original app utilities
├── output/                          # Generated reports (created after running PRISM)
└── data_cache/                      # Cached API responses (created automatically)
```

## Usage Examples

### Example 1: Run Full Analysis
```powershell
python run_prism.py --output_dir output/
```

### Example 2: Test Single Country-Sector
```python
from sector_analysis_app.src.prism_scoring import compute_prism_score
from sector_analysis_app.src.prism_country_data import get_country_metadata
from sector_analysis_app.src.prism_sector_constituents import get_country_sector_data

country = "US"
sector = "Information Technology"

country_meta = get_country_metadata(country)
firms_df = get_country_sector_data(country, sector, top_n=5)
prism_result = compute_prism_score(country, country_meta, sector, firms_df)

print(prism_result)
```

### Example 3: View Top 10 Opportunities
```python
import pandas as pd

prism_df = pd.read_csv("output/prism_country_sector_scores.csv")
top10 = prism_df.nlargest(10, "prism_score")
print(top10[["country_name", "sector", "prism_score", "top_firms"]])
```

## Notes

- **Runtime**: Full analysis (40 countries × 11 sectors) takes 15-30 minutes depending on API rate limits
- **Caching**: All API responses are cached in `data_cache/` to speed up repeated runs
- **Missing Data**: When fundamental or price data is unavailable, PRISM defaults to neutral scores (50) to avoid bias
- **Customization**: To adjust PRISM component weights, edit `prism_scoring.py` (search for weight constants like `0.35`, `0.30`, etc.)

## Original Streamlit App

This repo also contains the original single-sector risk analysis Streamlit app in `sector_analysis_app/app.py`. To run it:

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run streamlit_app.py
```

The app provides an interactive UI for analyzing individual sector ETFs with customizable top-down parameters.

## Wharton Deliverable

For the Wharton competition, use `justification_report.md` as your primary deliverable. It includes:

1. **Executive Summary**: Portfolio allocation breakdown by tier (Overweight/Neutral/Underweight)
2. **Top 10 PRISM Opportunities**: Ranked country-sector pairs with highest scores
3. **Allocation Justifications**: 2-4 sentence explanations for each holding, referencing PRISM components
4. **Methodology Notes**: Transparent scoring formulas and tier definitions

Pair this with `methodology.md` for judges who want technical details.

## License

MIT License — see LICENSE file.

## Authors

Developed for Wharton Sector Analysis Competition 2025.

---

**Questions or Issues?**  
Check `methodology.md` for detailed technical documentation, or review `backsolve_changes.json` if allocations need parameter tuning.
