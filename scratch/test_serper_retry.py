import requests
import json
import time

serper_key = "GRugBqby6x9JbePA55Rjktuh"
url = "https://google.serper.dev/search"

headers = {
    "X-API-KEY": serper_key,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

payload = {
    "q": "Systems Limited Lahore Pakistan official website email phone",
    "num": 5
}

session = requests.Session()

for attempt in range(3):
    try:
        print(f"Attempt {attempt+1}...")
        res = session.post(url, headers=headers, json=payload, timeout=15)
        print("Serper response status:", res.status_code)
        if res.status_code == 200:
            data = res.json()
            print("Organic results:", len(data.get("organic", [])))
            for item in data.get("organic", [])[:2]:
                print("Title:", item.get("title"))
                print("Link:", item.get("link"))
                print("Snippet:", item.get("snippet"))
            break
        else:
            print("Error text:", res.text)
    except Exception as e:
        print(f"Error on attempt {attempt+1}: {e}")
        time.sleep(2)
