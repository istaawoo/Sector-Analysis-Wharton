import sys
sys.path.insert(0, 'sector_analysis_app/src')
from prism_country_data import get_country_metadata

countries = ['US', 'JP', 'DE', 'TW', 'FR', 'CN', 'BR', 'IN', 'AU', 'KR']
for cc in countries:
    meta = get_country_metadata(cc)
    print(f"{cc:3s}: GDP=${meta.get('gdp_billions', 0):.0f}B | Per capita=${meta.get('gdp_per_capita', 0):.0f} | Growth={meta.get('gdp_growth', 0):.1f}%")
