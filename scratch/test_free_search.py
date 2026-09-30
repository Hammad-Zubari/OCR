import urllib.request
import urllib.parse
import json
import re
import requests

def search_yahoo(query, num=5):
    try:
        url = "https://search.yahoo.com/search?p=" + urllib.parse.quote(query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            # Extract links and titles from Yahoo search
            items = []
            # match <a class="d-ib fz-20 lh-26 td-hu" or <a class="compTitle"
            raw = re.findall(r'<a[^>]+class="[^"]*(?:compTitle|fz-20|td-hu|thmb)[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.IGNORECASE)
            for href, title in raw:
                # unquote r.search.yahoo redirect if present
                if "/RU=" in href:
                    m = re.search(r'/RU=([^/]+)/', href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))
                title_clean = re.sub(r'<[^>]+>', ' ', title)
                title_clean = re.sub(r'\s+', ' ', title_clean).strip()
                if href.startswith("http") and not any(d in href for d in ["yahoo.com", "search.yahoo"]):
                    items.append({"title": title_clean, "link": href, "snippet": title_clean})
            print("Yahoo found:", len(items))
            for it in items[:4]:
                print("  ->", it["title"][:50], "=>", it["link"])
            return items
    except Exception as e:
        print("Yahoo error:", e)
    return []

search_yahoo("Ahrar Sepahan Company iran contact email website")
