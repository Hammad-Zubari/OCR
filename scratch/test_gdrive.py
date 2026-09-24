import re
import requests
from pathlib import Path

def extract_gdrive_file_id(url: str) -> str:
    if not url:
        return ""
    url = str(url).strip()
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{25,}$", url):
        return url
    return ""

test_urls = [
    "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view?usp=sharing",
    "https://drive.google.com/open?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
    "https://drive.google.com/uc?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs&export=download",
    "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
]

for u in test_urls:
    print(f"URL: {u} => Extracted ID: {extract_gdrive_file_id(u)}")
