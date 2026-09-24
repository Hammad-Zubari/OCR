import sys
sys.path.insert(0, '.')
import json
from web_search_service import extract_web_candidates_for_company

# Simulate the 6 extracted records from the user's PDF
records = [
    {
        "name": "Navid Ghotbi Ravandi",
        "address": "-",
        "tel": "+98 21-44802858, 912-3003374, +98 21-44804145",
        "fax": "+98 21-44804145",
        "email": "gh_modeller@yahoo.com",
        "website": ""
    },
    {
        "name": "Parsa Chemical Industries Co",
        "address": "#8, No 343, north kargar st, Tehran, Iran",
        "tel": "+98 21-88337807-11, +98 21-88636508",
        "fax": "+98 21-88636508",
        "email": "info@parsa-chem.com",
        "website": "www.parsa-chem.com"
    },
    {
        "name": "Sanat Gostarene Pouya Pars Co.",
        "address": "Unit 11,12, 3th floor, No. 1902 Opposite Mirzapour Ave., Shariati St. Tehran",
        "tel": "+98 21-22606606",
        "fax": "+98 21-22612069",
        "email": "sgpp.co@yahoo.com",
        "website": ""
    },
    {
        "name": "Shamim Azar Sahand LTD.",
        "address": "No. 2, Grand Floor, Abrisham Global Trading Center Emam Street, TABRIZ - IRAN",
        "tel": "+98 411-5256060",
        "fax": "+98 411-5263090",
        "email": "info@SHAMIMAS.com",
        "website": "www.SHAMIMAS.com, www.SHAMIM.co.com"
    },
    {
        "name": "Shayan Granite",
        "address": "Shirin sou village, left hand of qazvin Rasht road, 60 km",
        "tel": "+98 912-3470079, +98 242-5822786",
        "fax": "",
        "email": "",
        "website": ""
    },
    {
        "name": "Simin Sang Co",
        "address": "Factory, bolur-o-shisheh st, doulat abad road, Esfahan, Iran",
        "tel": "+98 312-5836505, +98 312-5837238",
        "fax": "",
        "email": "",
        "website": ""
    }
]

print("\n--- RUNNING WEB SEARCH ENRICHMENT ---")
for r in records:
    cands = extract_web_candidates_for_company(r["name"], r["address"], existing_record=r)
    r["web_suggestions"] = cands
    if cands and any(v.get("value") for v in cands.values()):
        r["verification_status"] = "needs_verification"
    else:
        r["verification_status"] = "verified"

    print(f"\nCompany: {r['name']}")
    print(f"Status: {r['verification_status']}")
    print(f"Web Suggestions: {json.dumps(r['web_suggestions'], indent=2)}")

needs_review = [r for r in records if r["verification_status"] == "needs_verification"]
print(f"\nTotal Records: {len(records)}")
print(f"Needs Verification (Tab 2 count): {len(needs_review)}")
print(f"Verified Records (Tab 3 count): {len(records) - len(needs_review)}")
