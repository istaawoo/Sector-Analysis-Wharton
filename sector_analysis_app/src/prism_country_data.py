"""
PRISM Country Data Fetcher
Fetches top 40 economies by GDP with macro indicators (GDP, GDP per capita, growth rates).
Uses World Bank API with CSV fallback.
"""

import pandas as pd
import requests
import os
from typing import Dict, List, Optional
import json

# Hardcoded fallback: top 40 economies by nominal GDP (2023 World Bank estimates)
TOP_40_COUNTRIES = [
    {"code": "US", "name": "United States", "gdp_billions": 27360, "gdp_per_capita": 81695, "gdp_growth": 2.5},
    {"code": "CN", "name": "China", "gdp_billions": 17963, "gdp_per_capita": 12720, "gdp_growth": 5.2},
    {"code": "JP", "name": "Japan", "gdp_billions": 4231, "gdp_per_capita": 33950, "gdp_growth": 1.9},
    {"code": "DE", "name": "Germany", "gdp_billions": 4430, "gdp_per_capita": 52820, "gdp_growth": -0.3},
    {"code": "IN", "name": "India", "gdp_billions": 3730, "gdp_per_capita": 2612, "gdp_growth": 7.2},
    {"code": "GB", "name": "United Kingdom", "gdp_billions": 3332, "gdp_per_capita": 48910, "gdp_growth": 0.5},
    {"code": "FR", "name": "France", "gdp_billions": 3050, "gdp_per_capita": 45540, "gdp_growth": 0.9},
    {"code": "IT", "name": "Italy", "gdp_billions": 2255, "gdp_per_capita": 38140, "gdp_growth": 0.7},
    {"code": "BR", "name": "Brazil", "gdp_billions": 2173, "gdp_per_capita": 10130, "gdp_growth": 2.9},
    {"code": "CA", "name": "Canada", "gdp_billions": 2140, "gdp_per_capita": 54870, "gdp_growth": 1.1},
    {"code": "KR", "name": "South Korea", "gdp_billions": 1713, "gdp_per_capita": 33190, "gdp_growth": 1.4},
    {"code": "RU", "name": "Russia", "gdp_billions": 2062, "gdp_per_capita": 14391, "gdp_growth": 2.1},
    {"code": "ES", "name": "Spain", "gdp_billions": 1583, "gdp_per_capita": 33470, "gdp_growth": 2.5},
    {"code": "AU", "name": "Australia", "gdp_billions": 1688, "gdp_per_capita": 64950, "gdp_growth": 2.0},
    {"code": "MX", "name": "Mexico", "gdp_billions": 1811, "gdp_per_capita": 13810, "gdp_growth": 3.2},
    {"code": "ID", "name": "Indonesia", "gdp_billions": 1391, "gdp_per_capita": 5070, "gdp_growth": 5.0},
    {"code": "NL", "name": "Netherlands", "gdp_billions": 1119, "gdp_per_capita": 63750, "gdp_growth": 0.1},
    {"code": "SA", "name": "Saudi Arabia", "gdp_billions": 1069, "gdp_per_capita": 29850, "gdp_growth": -0.8},
    {"code": "TR", "name": "Turkey", "gdp_billions": 1154, "gdp_per_capita": 13430, "gdp_growth": 4.5},
    {"code": "CH", "name": "Switzerland", "gdp_billions": 905, "gdp_per_capita": 103880, "gdp_growth": 0.7},
    {"code": "PL", "name": "Poland", "gdp_billions": 842, "gdp_per_capita": 22310, "gdp_growth": 0.2},
    {"code": "TW", "name": "Taiwan", "gdp_billions": 790, "gdp_per_capita": 33140, "gdp_growth": 1.4},
    {"code": "BE", "name": "Belgium", "gdp_billions": 632, "gdp_per_capita": 54350, "gdp_growth": 1.4},
    {"code": "AR", "name": "Argentina", "gdp_billions": 640, "gdp_per_capita": 13710, "gdp_growth": -1.6},
    {"code": "SE", "name": "Sweden", "gdp_billions": 593, "gdp_per_capita": 56490, "gdp_growth": -0.2},
    {"code": "IE", "name": "Ireland", "gdp_billions": 545, "gdp_per_capita": 106060, "gdp_growth": 0.9},
    {"code": "AT", "name": "Austria", "gdp_billions": 516, "gdp_per_capita": 57300, "gdp_growth": -0.7},
    {"code": "TH", "name": "Thailand", "gdp_billions": 514, "gdp_per_capita": 7310, "gdp_growth": 2.5},
    {"code": "SG", "name": "Singapore", "gdp_billions": 515, "gdp_per_capita": 87890, "gdp_growth": 1.1},
    {"code": "IL", "name": "Israel", "gdp_billions": 525, "gdp_per_capita": 55540, "gdp_growth": 2.0},
    {"code": "NO", "name": "Norway", "gdp_billions": 485, "gdp_per_capita": 88750, "gdp_growth": 0.5},
    {"code": "AE", "name": "UAE", "gdp_billions": 507, "gdp_per_capita": 49450, "gdp_growth": 3.6},
    {"code": "PH", "name": "Philippines", "gdp_billions": 475, "gdp_per_capita": 4130, "gdp_growth": 5.5},
    {"code": "MY", "name": "Malaysia", "gdp_billions": 447, "gdp_per_capita": 13230, "gdp_growth": 3.7},
    {"code": "BD", "name": "Bangladesh", "gdp_billions": 455, "gdp_per_capita": 2670, "gdp_growth": 6.0},
    {"code": "VN", "name": "Vietnam", "gdp_billions": 433, "gdp_per_capita": 4350, "gdp_growth": 5.0},
    {"code": "DK", "name": "Denmark", "gdp_billions": 404, "gdp_per_capita": 68830, "gdp_growth": 1.8},
    {"code": "CL", "name": "Chile", "gdp_billions": 344, "gdp_per_capita": 17340, "gdp_growth": 0.2},
    {"code": "CO", "name": "Colombia", "gdp_billions": 363, "gdp_per_capita": 7050, "gdp_growth": 0.6},
    {"code": "ZA", "name": "South Africa", "gdp_billions": 373, "gdp_per_capita": 6100, "gdp_growth": 0.6},
]


def get_top40_countries() -> pd.DataFrame:
    """
    Returns a DataFrame with top 40 economies including:
    - code (ISO 2-letter)
    - name
    - gdp_billions
    - gdp_per_capita
    - gdp_growth (%)
    """
    return pd.DataFrame(TOP_40_COUNTRIES)


def get_country_metadata(country_code: str) -> Optional[Dict]:
    """Get metadata for a single country by code."""
    df = get_top40_countries()
    row = df[df["code"] == country_code]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def fetch_worldbank_gdp(country_codes: List[str], cache_dir: str = "data_cache") -> pd.DataFrame:
    """
    Attempt to fetch GDP data from World Bank API for given countries.
    Falls back to hardcoded TOP_40_COUNTRIES if API fails.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "worldbank_gdp.csv")
    
    if os.path.exists(cache_file):
        print(f"Loading cached World Bank GDP data from {cache_file}")
        return pd.read_csv(cache_file)
    
    # Try World Bank API
    try:
        print("Fetching GDP data from World Bank API...")
        # World Bank API endpoint for GDP (current US$)
        url = "https://api.worldbank.org/v2/country/{}/indicator/NY.GDP.MKTP.CD?format=json&per_page=1000&date=2022:2023"
        
        all_data = []
        for code in country_codes:
            try:
                resp = requests.get(url.format(code.lower()), timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1 and data[1]:
                        # Extract most recent value
                        for item in data[1]:
                            if item.get("value"):
                                all_data.append({
                                    "code": code,
                                    "year": item["date"],
                                    "gdp": item["value"]
                                })
                                break
            except Exception as e:
                print(f"Failed to fetch {code}: {e}")
        
        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(cache_file, index=False)
            print(f"Cached World Bank data to {cache_file}")
            return df
        else:
            raise Exception("No data returned from World Bank API")
            
    except Exception as e:
        print(f"World Bank API failed: {e}. Using fallback hardcoded data.")
        df = get_top40_countries()
        df.to_csv(cache_file, index=False)
        return df


if __name__ == "__main__":
    # Test
    countries = get_top40_countries()
    print(countries.head(10))
    print(f"\nTotal countries: {len(countries)}")
    
    # Test single country lookup
    us_meta = get_country_metadata("US")
    print(f"\nUS metadata: {us_meta}")
