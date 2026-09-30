from web_search_service import extract_web_candidates_for_company, search_google_universal, build_targeted_search_query

records = [
    {'name': 'Shayan Granite', 'address': 'Shirin sou village, left hand of qazvin Rasht road, 60 km', 'tel': '+98 912-3470079, +98 242-5822786', 'fax': '', 'email': '', 'website': ''},
    {'name': 'Simin Sang Co', 'address': 'Factory, bolur-o-shisheh st, doulat abad road, Esfahan, Iran', 'tel': '+98 312-5836505, +98 312-5837238', 'fax': '', 'email': '', 'website': ''},
    {'name': 'Navid Ghotbi Ravandi', 'address': '', 'tel': '+98 21-44802858', 'fax': '', 'email': '', 'website': ''}
]

for r in records:
    name = r['name']
    query = build_targeted_search_query(name, r)
    print(f"\n======================================")
    print(f"Company: {name}")
    print(f"Query: {query}")
    cands = extract_web_candidates_for_company(name, r['address'], existing_record=r)
    print(f"Found Candidates: {cands}")
