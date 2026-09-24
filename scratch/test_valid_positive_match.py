import sys
sys.path.insert(0, '.')
import json
from web_search_service import extract_web_candidates_for_company

# Company that has a real verified official website
rec = {
    "name": "Goldasht Mosaic",
    "address": "Isfahan, Iran",
    "tel": "+98 31-1234567",
    "email": "",
    "website": ""
}

print("\n--- TESTING VALID COMPANY MATCH (Goldasht Mosaic) ---")
cands = extract_web_candidates_for_company(rec["name"], rec["address"], existing_record=rec)
print(f"Result for Goldasht Mosaic: {json.dumps(cands, indent=2)}")
