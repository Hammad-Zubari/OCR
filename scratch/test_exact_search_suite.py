import sys
sys.path.insert(0, '.')
import json
from web_search_service import extract_web_candidates_for_company

test_cases = [
    {
        "name": "Sanat Gostarene Pouya Pars Co.",
        "address": "Unit 11,12, 3th floor, No. 1902 Opposite Mirzapour Ave., Shariati St. Tehran",
        "tel": "+98 21-22606606",
        "email": "sgpp.co@yahoo.com",
        "website": ""
    },
    {
        "name": "Milano Industrial Group",
        "address": "Tehran, Iran",
        "tel": "+98 21-1234567",
        "email": "",
        "website": ""
    },
    {
        "name": "Shayan Granite",
        "address": "Shirin sou village, left hand of qazvin Rasht road, 60 km",
        "tel": "+98 912-3470079, +98 242-5822786",
        "email": "",
        "website": ""
    },
    {
        "name": "Simin Sang Co",
        "address": "Factory, bolur-o-shisheh st, doulat abad road, Esfahan, Iran",
        "tel": "+98 312-5836505, +98 312-5837238",
        "email": "",
        "website": ""
    },
    {
        "name": "Parsa Chemical Industries Co",
        "address": "#8, No 343, north kargar st, Tehran, Iran",
        "tel": "+98 21-88337807-11",
        "email": "info@parsa-chem.com",
        "website": "www.parsa-chem.com"
    }
]

print("==================================================================")
print("RUNNING TWO-STAGE EXACT COMPANY VALIDATION TEST SUITE")
print("==================================================================")

for tc in test_cases:
    print(f"\nTarget Company: {tc['name']}")
    cands = extract_web_candidates_for_company(tc['name'], tc['address'], existing_record=tc)
    print(f"Final Web Candidates (NULL if empty): {json.dumps(cands, indent=2)}")

print("\n==================================================================")
print("TEST COMPLETED")
print("==================================================================")
