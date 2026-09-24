import requests
import re
from urllib.parse import unquote

def search_ddg_fallback(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": query}, headers=headers, timeout=10)
        if resp.status_code == 200:
            html = resp.text
            # Extract organic snippets and links
            results = []
            # Results are in class="result__body"
            chunks = re.findall(r'<div class="result__body">(.*?)</div>\s*</div>', html, re.DOTALL)
            for c in chunks[:5]:
                title_match = re.search(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', c, re.DOTALL)
                link_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', c, re.DOTALL)
                raw_href = ""
                snippet = ""
                if title_match:
                    raw_href = title_match.group(1)
                if link_match:
                    snippet = re.sub(r'<[^>]+>', '', link_match.group(1)).strip()
                
                # Unwrap duckduckgo redirect url if needed
                if "uddg=" in raw_href:
                    m = re.search(r'uddg=([^&]+)', raw_href)
                    if m:
                        raw_href = unquote(m.group(1))
                elif raw_href.startswith("//duckduckgo.com/l/?uddg="):
                    m = re.search(r'uddg=([^&]+)', raw_href)
                    if m:
                        raw_href = unquote(m.group(1))
                
                if raw_href:
                    results.append({
                        "title": re.sub(r'<[^>]+>', '', title_match.group(2) if title_match else "").strip(),
                        "link": raw_href,
                        "snippet": snippet
                    })
            return {"organic": results}, None
        return None, f"Status {resp.status_code}"
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    res, err = search_ddg_fallback("Al Agili Furnishing LLC Dubai official website contact")
    print("Error:", err)
    print("Found items:", len(res.get("organic", []) if res else []))
    if res and res.get("organic"):
        for it in res["organic"]:
            print(" - Link:", it["link"])
            print("   Snippet:", it["snippet"][:100])
