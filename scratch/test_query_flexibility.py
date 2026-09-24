import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from web_search_service import search_google_universal, get_search_api_key, build_targeted_search_query

key = get_search_api_key()
print("Search API Key loaded:", bool(key))

companies = [
    {
        "name": "Simin Sang Co",
        "address": "Factory, bolur-o-shisheh st, doulat abad road, Esfahan, Iran",
        "tel": "+98 312- 5836505, +98 312- 5837238"
    },
    {
        "name": "Shayan Granite",
        "address": "Shirin sou village, left hand of qazvin Rasht road, 60 km",
        "tel": "+98 912- 3470079, +98 242- 5822786"
    }
]

for comp in companies:
    print("\n" + "=" * 50)
    print("Testing Company:", comp["name"])
    
    # 1. Overly strict query
    strict_q = build_targeted_search_query(comp["name"], comp)
    print("Strict Query:", strict_q)
    res_strict, err1 = search_google_universal(strict_q)
    org_strict = (res_strict or {}).get("organic_results") or (res_strict or {}).get("organic") or []
    print(f"Strict Query Organic Results Count: {len(org_strict)}")
    
    # 2. Natural query without rigid quotes
    natural_q = f'{comp["name"]} Iran email contact'.strip()
    print("Natural Query:", natural_q)
    res_nat, err2 = search_google_universal(natural_q)
    org_nat = (res_nat or {}).get("organic_results") or (res_nat or {}).get("organic") or []
    print(f"Natural Query Organic Results Count: {len(org_nat)}")
    if org_nat:
        for item in org_nat[:3]:
            print("  -> Title:", item.get("title"))
            print("     Snippet:", item.get("snippet"))
            print("     Link:", item.get("link"))
