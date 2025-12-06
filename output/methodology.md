# PRISM Methodology

**Version:** 1.0  
**Last Updated:** 2025-12-06

---

## Overview

PRISM (Portfolio Risk & Investment Scoring Model) is a quantitative framework for evaluating country-sector investment opportunities on a 0-100 scale. It combines top-down strategic frameworks (Porter's 5 Forces, Industry Life Cycle, SWOT) with bottom-up fundamental and market behavior analysis.

## Data Sources

1. **Country Macro Data**: Top 40 economies by nominal GDP (World Bank / IMF 2023)
2. **Company Fundamentals**: Yahoo Finance API (yfinance)
3. **Price Data**: Yahoo Finance historical prices (2-year lookback)
4. **Sector Constituents**: Curated lists of top 5-10 companies per country-sector by market cap

## PRISM Score Components

### 1. Structural Score (35% weight)

Combines Porter's 5 Forces and Industry Life Cycle analysis:

**Porter's 5 Forces** (1-5 scale each, then normalized to 0-100):
- **Barriers to Entry**: Based on R&D intensity (% revenue) and regulation flag
- **Threat of Substitutes**: Sector-specific heuristic (e.g., Tech=4, Utilities=2)
- **Supplier Power**: HHI (Herfindahl-Hirschman Index) concentration proxy
- **Buyer Power**: Higher for consumer-facing sectors
- **Rivalry**: Inverse of HHI (lower concentration = higher rivalry)

**Industry Life Cycle** (1-5 mapping):
- Intro: 2.0, Growth: 4.0, Shakeout: 3.0, Mature: 3.5, Decline: 2.5

*Formula*: `Structural = 0.70 × Porter + 0.30 × Lifecycle`

### 2. Fundamental Quality Score (30% weight)

Market-cap weighted average of firm-level fundamental scores.

**Firm Score Components**:
- ROE (Return on Equity): 25% — normalized -10% to 40%, higher = better
- Profit Margin: 20% — normalized -10% to 50%, higher = better
- Revenue Growth (YoY): 15% — normalized -20% to 50%, higher = better
- FCF/Market Cap: 15% — normalized -5% to 15%, higher = better
- Debt/Equity: 15% — normalized 0 to 300, lower = better (inverted)
- Gross Margin: 10% — normalized 0% to 80%, higher = better

*Missing data defaults to 50 (neutral).*

### 3. Market Behavior Score (20% weight)

Uses price data from the largest firm (by market cap) in the sector as proxy.

**Components**:
- 12-month return: 20% — normalized -50% to 100%, higher = better
- 6-month return: 20% — normalized -50% to 100%, higher = better
- Annualized volatility: 25% — normalized 10% to 80%, lower = better (inverted)
- Max drawdown (1y): 20% — normalized 0% to 60%, lower = better (inverted)
- Beta vs SPY: 15% — normalized 0.5 to 2.0, lower = better (inverted)

### 4. Top-Down Mission-Fit Score (15% weight)

Combines country-level macro indicators and SWOT analysis.

**Components**:
- GDP Growth: 40% — normalized -2% to 8%, higher = better
- GDP Per Capita: 30% — normalized $1k to $100k, higher = better
- SWOT Net Score: 30% — (Strengths - Weaknesses) + (Opportunities - Threats), normalized -8 to 8

## Final PRISM Score

```
PRISM = 0.35 × Structural + 0.30 × Fundamentals + 0.20 × Behavior + 0.15 × TopDown
```

## Tier Definitions

- **Overweight**: PRISM ≥ 70
- **Neutral**: 55 ≤ PRISM < 70
- **Underweight**: PRISM < 55

## Limitations & Caveats

1. **Data Availability**: Some emerging market firms lack complete fundamental data; defaults to neutral scores (50).
2. **Exchange Closure**: Non-US exchanges may have delayed or limited API access.
3. **Proxy Assumptions**: Sector behavior proxied by largest firm; may not represent entire sector.
4. **Static Weights**: PRISM uses fixed component weights; customization may improve fit.
5. **HHI Proxies**: True HHI calculation requires detailed market share data; we use heuristics.

## Backsolving & Parameter Tuning

If allocations do not align with top PRISM picks, the model can suggest minimal weight adjustments (±10% per component) to improve alignment. This ensures transparency and avoids overfitting.

