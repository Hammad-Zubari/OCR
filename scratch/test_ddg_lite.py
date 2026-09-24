import requests
import re
from urllib.parse import unquote

def search_ddg_lite(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://lite.duckduckgo.com/",
        "Origin": "https://lite.duckduckgo.com",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        url = "https://lite.duckduckgo.com/lite/"
        res = requests.post(url, data={"q": query}, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            # In lite.duckduckgo.com, results have <a class="result-link" href="...">...</a>
            # and snippets in <td class="result-snippet">...</td>
            results = []
            links = re.findall(r'<a[^>]+class=[\'"]result-link[\'"][^>]+href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', html, re.DOTALL)
            snippets = re.findall(r'<td[^>]+class=[\'"]result-snippet[\'"][^>]*>(.*?)</td>', html, re.DOTALL)
            
            for i, (link, title) in enumerate(links[:5]):
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                clean_snippet = ""
                if i < len(snippets):
                    clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                
                # Unwrap redirect if needed
                if "uddg=" in link:
                    m = re.search(r'uddg=([^&]+)', link)
                    if m:
                        link = unquote(m.group(1))
                
                results.append({
                    "title": clean_title,
                    "link": link,
                    "snippet": clean_snippet
                })
            return {"organic": results}, None
        return None, f"Status: {res.status_code}"
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    for comp in ["Al Agili Furnishing LLC Dubai", "Ali Malik Group Co"]:
        print("Searching for:", comp)
        res, err = search_ddg_lite(f"{comp} official website contact email")
        print("Error:", err)
        organic = res.get("organic", []) if res else []
        print(f"Found {len(organic)} results:")
        for r in organic:
            print(" - Title:", r["title"])
            print("   Link:", r["link"])
            print("   Snippet:", r["snippet"][:100])
        print("-" * 50)
