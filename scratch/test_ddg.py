import urllib.parse
import urllib.request
import re
import requests

def test_ddg(query):
    try:
        url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        res = requests.post(url, data={'q': query}, headers=headers, timeout=8)
        print("DDG Post Status:", res.status_code)
        
        # Parse organic links and snippets with pure regex
        results = []
        raw_items = re.findall(r'<div class="result[^>]*>(.*?)</div>\s*<!--\s*end result', res.text, re.DOTALL | re.IGNORECASE)
        if not raw_items:
            raw_items = re.findall(r'<div[^>]*class="[^"]*result__body[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL | re.IGNORECASE)
            
        for block in re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.DOTALL | re.IGNORECASE):
            href, snip = block
            if "uddg=" in href:
                href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
            snip_clean = re.sub(r'<[^>]+>', '', snip).strip()
            results.append({"title": snip_clean[:50], "link": href, "snippet": snip_clean})
            
        if not results:
            # Fallback regex for all result__a links
            for block in re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.DOTALL | re.IGNORECASE):
                href, title = block
                if "uddg=" in href:
                    href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                results.append({"title": title_clean, "link": href, "snippet": ""})

        print(f"Found {len(results)} results for '{query}':")
        for r in results[:4]:
            print(f"  Title: {r['title']}")
            print(f"  Link : {r['link']}")
            print(f"  Snip : {r['snippet'][:80]}")
        return results
    except Exception as e:
        print("DDG search failed:", e)
        return []

test_ddg("Shayan Granite Rasht contact email website")
test_ddg("Simin Sang Co Esfahan contact email website")
