import sys
sys.path.insert(0, '.')
import json
from web_search_service import extract_web_candidates_for_company

# Test with a company where website is missing and a real company site exists
rec = {
    "name": "Parsa Chemical Industries Co",
    "address": "#8, No 343, north kargar st, Tehran, Iran",
    "tel": "+98 21-88337807",
    "email": "",
    "website": ""
}

print("\n--- TESTING CONFIRMED EXACT COMPANY (Parsa Chemical) ---")
cands = extract_web_candidates_for_company(rec["name"], rec["address"], existing_record=rec)
print(f"Result for Parsa Chemical: {json.dumps(cands, indent=2)}")
