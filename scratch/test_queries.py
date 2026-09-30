import sys
sys.path.insert(0, '.')
from web_search_service import search_google_universal, extract_web_candidates_for_company

queries = [
    '"Shayan Granite"',
    '"Shayan Granite" Iran',
    '"Simin Sang" Iran',
    '"Ahrar Sepahan"',
    '"Sanat Gostarene Pouya Pars"'
]

for q in queries:
    data, err = search_google_universal(q)
    print(f"\nQuery: {q} -> Found: {len(data.get('organic_results', [])) if data else 0}")
    if data and data.get("organic_results"):
        for it in data.get("organic_results")[:3]:
            print("  ->", it.get("title")[:60], "=>", it.get("link"))
