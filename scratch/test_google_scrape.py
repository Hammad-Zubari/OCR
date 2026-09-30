import requests
import urllib.parse
import re

def search_bing_html(query, num=5):
    try:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        res = requests.get(url, headers=headers, timeout=6)
        print("Bing Status:", res.status_code, "Len:", len(res.text))
        if res.status_code == 200:
            items = []
            # Extract <h2><a href="...">title</a></h2> and sibling snippets
            h2_blocks = re.findall(r'<h2><a[^>]+href="([^"]+)"[^>]*>(.*?)</a></h2>', res.text, re.IGNORECASE)
            for href, title in h2_blocks:
                title_clean = re.sub(r'<[^>]+>', ' ', title)
                title_clean = re.sub(r'\s+', ' ', title_clean).strip()
                if href.startswith("http") and not any(d in href for d in ["bing.com", "microsoft.com", "msn.com", "bingj.com"]):
                    items.append({"title": title_clean, "link": href, "snippet": title_clean})

            print(f"Bing found {len(items)} results for '{query}':")
            for it in items[:4]:
                print("  Title:", it["title"][:50])
                print("  Link :", it["link"])
                print("  Snip :", it["snippet"][:80])
            return items
    except Exception as e:
        print("Bing error:", e)
    return []

print("--- Testing Ahrar Sepahan on Bing ---")
search_bing_html("Ahrar Sepahan Company iran contact email website")

print("\n--- Testing Milano Industrial Group on Bing ---")
search_bing_html("Milano Industrial Group iran contact email website")

print("\n--- Testing Shayan Granite on Bing ---")
search_bing_html("Shayan Granite Rasht contact email website")
