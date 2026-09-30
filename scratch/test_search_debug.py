import os
import requests
import urllib.parse
import re
from dotenv import load_dotenv

load_dotenv(override=True)
query = "Ahrar Sepahan Company iran contact email website"

# 1. SearchApi
searchapi_key = os.getenv("SEARCHAPI_API_KEY", "").strip()
print("1. SearchApi Key:", searchapi_key)
if searchapi_key:
    try:
        url = "https://www.searchapi.io/api/v1/search"
        res = requests.get(url, params={"engine": "google", "q": query, "api_key": searchapi_key}, timeout=6)
        print("SearchApi Status:", res.status_code, res.text[:150])
    except Exception as e:
        print("SearchApi Error:", e)

# 2. Serper
serper_key = os.getenv("SERPER_API_KEY", "").strip()
print("\n2. Serper Key:", serper_key)
if serper_key:
    try:
        url = "https://google.serper.dev/search"
        res = requests.post(url, headers={"X-API-KEY": serper_key, "Content-Type": "application/json"}, json={"q": query}, timeout=6)
        print("Serper Status:", res.status_code, res.text[:150])
    except Exception as e:
        print("Serper Error:", e)

# 3. DuckDuckGo HTML
print("\n3. DuckDuckGo:")
try:
    url_ddg = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Origin": "https://html.duckduckgo.com",
        "Referer": "https://html.duckduckgo.com/"
    }
    res = requests.post(url_ddg, data={"q": query}, headers=headers, timeout=6)
    print("DDG POST Status:", res.status_code, "Length:", len(res.text))
    if "anomaly-detected" in res.text:
        print("DDG Anomaly/Bot block detected!")
except Exception as e:
    print("DDG Error:", e)
