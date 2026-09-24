import requests
import urllib.parse
import re

query = "Ahrar Sepahan Company iran contact email website"

# 1. DDG POST (accept 200, 202)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print("\n--- Testing DDG Lite GET ---")
try:
    url = "https://lite.duckduckgo.com/lite/"
    res = requests.post(url, data={"q": query}, headers=headers, timeout=6)
    print("DDG Lite Status:", res.status_code, "Len:", len(res.text))
    links = re.findall(r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.IGNORECASE)
    print("DDG Lite Links found:", len(links))
    for href, title in links[:3]:
        print("  ->", title.strip(), "=>", href)
except Exception as e:
    print("DDG Lite error:", e)

print("\n--- Testing DDG HTML POST (200/202) ---")
try:
    url = "https://html.duckduckgo.com/html/"
    res = requests.post(url, data={"q": query}, headers=headers, timeout=6)
    print("DDG HTML Status:", res.status_code, "Len:", len(res.text))
    # Extract links
    raw_links = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.DOTALL | re.IGNORECASE)
    if not raw_links:
        raw_links = re.findall(r'<a[^>]+class="[^"]*result__url[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.DOTALL | re.IGNORECASE)
    if not raw_links:
        raw_links = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.DOTALL | re.IGNORECASE)
    print("DDG HTML raw links found:", len(raw_links))
    for href, txt in raw_links[:3]:
        print("  ->", href)
except Exception as e:
    print("DDG HTML error:", e)
