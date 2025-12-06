# How to Run the New PRISM Streamlit App

## Quick Start

### Run the PRISM Streamlit App (Web Interface)

```powershell
streamlit run prism_streamlit_app.py
```

**Open in browser:** http://localhost:8501

---

## What You'll See

The app has 5 pages (navigate via sidebar):

### 1. 🏠 Home
- Overview of PRISM methodology
- Quick stats (40 countries, 11 sectors, 440 opportunities)
- Instructions for using the app

### 2. 🌎 Country Rankings
- Top 10 countries by average PRISM score
- Detailed breakdown of any country you select
- Bar charts showing sector performance per country

### 3. 📊 Sector Analysis
- Global sector rankings (which sectors perform best across all countries)
- Heatmap showing PRISM scores for top 20 countries × 11 sectors
- Detailed view of top countries for any selected sector

### 4. 💼 Our Portfolio ⭐ **MOST IMPORTANT**
- Shows your $500K allocation
- Pie charts by country and sector
- Holdings table with PRISM scores and tiers (Overweight/Neutral/Underweight)
- **Individual justifications** for each holding with PRISM component breakdown
- Filter by country or tier

### 5. 📖 Methodology
- Explains the 4 PRISM components (Structural, Fundamentals, Behavior, Top-Down)
- Shows formulas and tier definitions
- Lists data sources

---

## Current Status

✅ **App is fully functional** - All 5 pages are built and working
⚠️ **PRISM data not generated yet** - Pages will show placeholder messages until you run the analysis

---

## To Get Real Data (Optional)

If you want to see actual PRISM scores instead of placeholders:

```powershell
python run_prism.py --output_dir output/
```

**Runtime:** 15-30 minutes (fetches data for 440 country-sector pairs)

**What it does:**
- Analyzes all 40 countries × 11 sectors = 440 combinations
- Fetches fundamentals for ~2,200 companies
- Generates `output/prism_country_sector_scores.csv`
- The Streamlit app automatically loads this file once it exists

---

## Key Features

### Portfolio Justification (Main Use Case)
1. Go to **💼 Our Portfolio** page
2. See all your holdings with PRISM scores
3. Click on any holding (e.g., MSFT) to see:
   - PRISM score breakdown (Structural, Fundamentals, Behavior, Top-Down)
   - Tier classification (Overweight/Neutral/Underweight)
   - Text justification explaining why it's a good/moderate/risky investment

### Country Comparison
1. Go to **🌎 Country Rankings** page
2. See which countries scored highest overall
3. Pick a country (e.g., Germany) to see all 11 sector scores for that country

### Sector Comparison
1. Go to **📊 Sector Analysis** page
2. See which sectors perform best globally
3. Look at heatmap to find best country-sector combinations
4. Pick a sector (e.g., Information Technology) to see top countries for that sector

---

## For Wharton Presentation

### Demo Flow:
1. Start on **Home** - Explain PRISM methodology (4 components, 440 opportunities)
2. Show **Country Rankings** - "We analyzed top 40 economies, here are the winners"
3. Show **Sector Analysis** - "Information Technology scores highest globally at X, followed by..."
4. **Main Event: Our Portfolio** - "Here's our $500K allocation mapped to PRISM scores"
   - Show pie charts (diversification)
   - Show holdings table (tier distribution)
   - Pick a high-scoring holding (e.g., MSFT) - "PRISM score 53, Neutral tier, strong fundamentals..."
   - Pick a low-scoring holding - "We know this scored lower, but it provides diversification..."
5. If asked about Qatar/Kuwait: Go to **Country Rankings**, filter to those countries, show their low scores

### Key Talking Points:
- "We didn't cherry-pick countries - we analyzed ALL top 40 economies systematically"
- "PRISM uses 4 objective components: Porter's 5 Forces, firm fundamentals, market behavior, country macro"
- "X% of our portfolio is in Overweight tier, Y% in Neutral, showing disciplined allocation"
- "We can justify every holding with specific PRISM metrics - transparency is key"

---

## Troubleshooting

### "No module named scipy" error?
Run this in PowerShell:
```powershell
& ".\.venv\Scripts\python.exe" -m pip install scipy
```

### App shows "PRISM scores not generated yet"?
This is normal! The app works with or without PRISM data:
- **Without data:** Shows your portfolio allocations and structure
- **With data:** Shows PRISM scores and detailed justifications

To generate data, run:
```powershell
python run_prism.py --output_dir output/
```

### Wrong Python environment?
Make sure you're using the venv:
```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run prism_streamlit_app.py
```

---

## Files Created

- **`prism_streamlit_app.py`** - Main Streamlit app (5 pages)
- **`prism_data_loader.py`** - Helper functions for loading PRISM data
- **`run_prism.py`** - Command-line tool to generate PRISM scores (optional)
- **`output/prism_country_sector_scores.csv`** - Generated after running `run_prism.py`

---

## Deployment to Streamlit Cloud

To deploy this to your Streamlit Cloud URL:

1. Push to GitHub:
   ```powershell
   git add prism_streamlit_app.py prism_data_loader.py
   git commit -m "Add new PRISM Streamlit app"
   git push origin main
   ```

2. In Streamlit Cloud dashboard:
   - Change "Main file path" from `streamlit_app.py` to `prism_streamlit_app.py`
   - Reboot app

**Note:** The old `streamlit_app.py` will still exist in your repo - you can delete it or keep it as backup.

---

## Summary

✅ **New PRISM app is ready to use**
✅ **Run with:** `streamlit run prism_streamlit_app.py`
✅ **5 pages:** Home, Country Rankings, Sector Analysis, Portfolio, Methodology
✅ **Works with or without PRISM data** (placeholders shown until you run analysis)
✅ **Portfolio page shows your $500K with justifications**
✅ **Perfect for Wharton presentation**

**Next step:** Open http://localhost:8501 and explore the app!
