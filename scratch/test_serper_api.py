import requests
import json

serper_key = "GRugBqby6x9JbePA55Rjktuh"
url = "https://google.serper.dev/search"

headers = {
    "X-API-KEY": serper_key,
    "Content-Type": "application/json"
}

query = "ABC Textile Ltd Karachi Pakistan official website contact email phone"
payload = {
    "q": query,
    "num": 5
}

try:
    res = requests.post(url, headers=headers, json=payload, timeout=10)
    print("Serper status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print("Knowledge Graph:", data.get("knowledgeGraph"))
        print("Organic results count:", len(data.get("organic", [])))
        for r in data.get("organic", [])[:3]:
            print(f"- Title: {r.get('title')}")
            print(f"  Link: {r.get('link')}")
            print(f"  Snippet: {r.get('snippet')}\n")
    else:
        print("Error response:", res.text)
except Exception as e:
    print("Request exception:", e)
