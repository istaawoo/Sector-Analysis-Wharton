# PRISM Quick Reference Card

## Run PRISM (Full Analysis)

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run PRISM (15-30 minutes)
python run_prism.py --output_dir output/

# 3. View results
cd output
dir
```

---

## Output Files Cheat Sheet

| File | What It Is | When to Use |
|------|-----------|-------------|
| **`justification_report.md`** | Executive summary + allocation justifications | **Present to judges** |
| **`prism_country_sector_scores.csv`** | 440 country-sector PRISM scores | Find top opportunities, compare sectors |
| **`allocation_alignment.json`** | Your portfolio mapped to PRISM | Check alignment, identify weak holdings |
| **`methodology.md`** | Technical documentation | Answer "How did you calculate X?" |
| **`backsolve_changes.json`** | Suggested weight adjustments | Defend parameter choices |

---

## PRISM Score Interpretation

| PRISM Score | Tier | Meaning | Action |
|------------|------|---------|--------|
| **70-100** | Overweight | Strong opportunity | Recommend overweight position |
| **55-69** | Neutral | Moderate opportunity | Neutral weight, monitor |
| **0-54** | Underweight | Lower opportunity | Consider underweight or avoid |
| **N/A** | Not Scored | ETF / Diversified | Excluded from scoring |

---

## PRISM Components (How Score Is Built)

```
PRISM = 0.35 × Structural + 0.30 × Fundamentals + 0.20 × Behavior + 0.15 × TopDown
```

### 1. Structural (35%)
- **Porter's 5 Forces**: Barriers, substitutes, supplier/buyer power, rivalry
- **Industry Life Cycle**: Intro/Growth/Shakeout/Mature/Decline
- **What it measures**: Competitive dynamics, industry attractiveness

### 2. Fundamentals (30%)
- **Firm metrics**: ROE, profit margin, revenue growth, FCF, debt/equity, gross margin
- **Aggregation**: Market-cap weighted average of top 5-10 firms
- **What it measures**: Company quality, profitability, financial health

### 3. Market Behavior (20%)
- **Price metrics**: 12m/6m returns, volatility, max drawdown, beta vs SPY
- **Proxy**: Largest firm by market cap
- **What it measures**: Recent performance, risk, market stability

### 4. Top-Down (15%)
- **Country macro**: GDP growth, GDP per capita
- **SWOT**: Strengths, weaknesses, opportunities, threats (1-5 scale each)
- **What it measures**: Macro environment, strategic fit

---

## Common Questions & Quick Answers

### Q: "Why did we choose US over Qatar?"
**A:** "We analyzed top 40 economies. Qatar's PRISM scores ranged from X-Y across sectors, below our 55+ threshold. US Tech scored 53, US Financials scored Z, etc., providing better structural factors and firm fundamentals."

*(Check `prism_country_sector_scores.csv`, filter by `country == 'QA'` to find actual scores)*

### Q: "How do you justify MSFT at $20k?"
**A:** "MSFT (US - Information Technology) scored 53.14/100 in PRISM. While in Neutral tier, it benefits from strong fundamentals (score: 60.94) including high ROE and margins. Market behavior was depressed due to recent volatility, but structural factors remain solid."

*(Check `allocation_alignment.json`, find MSFT entry, cite justification text)*

### Q: "Why not increase weight on X sector?"
**A:** "PRISM ranks country-sector pairs. While [X sector] in [Y country] scored [Z], our diversification mandate limits single-sector exposure. We balanced PRISM recommendations with risk management and liquidity constraints."

### Q: "Did you backfit the model to your allocations?"
**A:** "No. PRISM uses fixed weights (Structural 35%, Fundamentals 30%, Behavior 20%, Top-Down 15%) derived from academic frameworks (Porter, Fama-French factors, SWOT). We then tested parameter sensitivity (see `backsolve_changes.json`) but retained default weights for transparency."

---

## Defensive Talking Points

### If judges challenge low PRISM scores:
1. **Diversification argument**: "While PRISM score is moderate, this holding provides geographic/sector diversification that improves portfolio-level Sharpe ratio."
2. **Contrarian argument**: "Market behavior score was depressed by recent volatility, but fundamentals remain strong. We see this as a buying opportunity."
3. **Strategic argument**: "Our mandate includes EM exposure for long-term growth. We accept lower PRISM scores in exchange for higher expected returns."

### If judges question methodology:
1. **Cite sources**: "PRISM uses Porter's 5 Forces (Harvard), Industry Life Cycle (Grantham), and Fama-French factors (academic finance literature)."
2. **Show transparency**: "All formulas are documented in `methodology.md` with exact normalization ranges."
3. **Demonstrate sensitivity**: "We tested alternative weights (see `backsolve_changes.json`) and found results robust."

---

## Fast Data Lookups

### Find top 10 opportunities
```python
import pandas as pd
df = pd.read_csv("output/prism_country_sector_scores.csv")
print(df.nlargest(10, "prism_score")[["country_name", "sector", "prism_score", "top_firms"]])
```

### Check your allocation tier distribution
```python
import json
with open("output/allocation_alignment.json") as f:
    data = json.load(f)

tiers = {}
for item in data:
    tier = item["tier"]
    tiers[tier] = tiers.get(tier, 0) + item["amount"]

for tier, amount in sorted(tiers.items()):
    print(f"{tier}: ${amount:,.2f}")
```

### Find why a country scored low
```python
df = pd.read_csv("output/prism_country_sector_scores.csv")
qatar = df[df["country"] == "QA"]
print(qatar[["sector", "prism_score", "structural_score", "fundamentals_score"]].sort_values("prism_score"))
```

---

## Customization Shortcuts

### Change PRISM weights
Edit `sector_analysis_app/src/prism_scoring.py`, line ~195:
```python
prism_score = (
    0.35 * structural_score +   # Change this
    0.30 * fundamentals_score +  # or this
    0.20 * behavior_score +      # or this
    0.15 * topdown_score         # or this
)
```

### Add more countries
Edit `sector_analysis_app/src/prism_country_data.py`, add to `TOP_40_COUNTRIES` list:
```python
{"code": "QA", "name": "Qatar", "gdp_billions": 180, "gdp_per_capita": 62000, "gdp_growth": 2.0},
```

### Add more firms for a sector
Edit `sector_analysis_app/src/prism_sector_constituents.py`, update `CURATED_CONSTITUENTS`:
```python
"IN": {
    "Information Technology": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS"],
}
```

---

## Presentation Slide Templates

### Slide 1: PRISM Overview
- Title: "PRISM: Portfolio Risk & Investment Scoring Model"
- Bullet: "Analyzed 440 country-sector pairs across top 40 economies"
- Bullet: "Four-factor model: Structural (35%), Fundamentals (30%), Behavior (20%), Top-Down (15%)"
- Bullet: "Objective, transparent, auditable methodology"

### Slide 2: Portfolio Summary
- Table: Allocation by tier (Overweight X%, Neutral Y%, Underweight Z%)
- Chart: Pie chart showing allocation by region (US, Developed, EM)
- Stat: "Average PRISM score: XX.X/100 (top XX percentile)"

### Slide 3: Top Opportunities
- Table: Top 10 country-sector pairs by PRISM score
- Highlight: Which ones you invested in (green), which you passed on (gray)
- Explain: "We weighted diversification and liquidity alongside PRISM scores"

### Slide 4: Allocation Justifications (Sample)
- Pick 3-5 holdings (mix of tiers)
- For each: Ticker, $ amount, PRISM score, 2-sentence justification
- Example: "MSFT ($20k, PRISM 53.14): Strong fundamentals (ROE 40%+), market leader in cloud/AI"

### Slide 5: Why We Didn't Choose X
- Show PRISM scores for countries you didn't select (Qatar, Kuwait, etc.)
- Explain: "Scores below 55 threshold due to [structural constraints / limited liquidity / concentration risk]"

---

## Checklist Before Presentation

- [ ] Run `python run_prism.py --output_dir output/`
- [ ] Review `justification_report.md` (check for surprises)
- [ ] Check `backsolve_changes.json` (note if adjustments needed)
- [ ] Extract top 10 opportunities table for slide
- [ ] Prepare 2-3 "Why not X?" defenses (Qatar, Kuwait, etc.)
- [ ] Test answer to "How did you calculate PRISM?" (cite `methodology.md`)
- [ ] Have `allocation_alignment.json` open during Q&A for quick lookups

---

## Emergency Fixes

### If run_prism.py crashes partway:
```powershell
# Delete cache and restart
Remove-Item -Recurse data_cache
python run_prism.py --output_dir output/
```

### If a specific country/sector fails:
- Check `data_issues.log` (if exists)
- Manually add tickers to `CURATED_CONSTITUENTS` in `prism_sector_constituents.py`
- Re-run

### If output looks wrong:
- Verify allocations in `prism_allocation.py` (ALLOCATIONS dict, line ~15)
- Check component weights in `prism_scoring.py` (line ~195)

---

**Remember:** PRISM is a tool to *support* your decisions, not replace judgment. Use it to build a narrative, then defend with strategic reasoning. Good luck! 🚀
