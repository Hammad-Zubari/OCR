import requests
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}
res = requests.get('https://www.bing.com/search?q=Ahrar+Sepahan+Company+iran', headers=headers, timeout=6)
print("Status:", res.status_code)

# Parse links with regex
all_links = re.findall(r'href="(https?://[^"]+)"', res.text)
ignored = ["bing.com", "microsoft.com", "live.com", "w3.org", "schema.org", "r.bing.com", "javascript", "msn.com", "aspnetcdn.com", "cloudflare.com"]
clean = []
for l in all_links:
    if not any(ig in l.lower() for ig in ignored):
        if l not in clean:
            clean.append(l)

print("Found external URLs on Bing:", len(clean))
for l in clean[:6]:
    print(" ->", l)
