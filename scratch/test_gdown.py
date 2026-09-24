import gdown
import re
from pathlib import Path

def download_gdrive_file(drive_url: str, output_path: Path):
    file_id_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", drive_url)
    file_id = file_id_match.group(1) if file_id_match else None
    if not file_id:
        id_match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", drive_url)
        file_id = id_match.group(1) if id_match else drive_url.strip()
    
    url = f"https://drive.google.com/uc?id={file_id}"
    print(f"Downloading from: {url}")
    out = gdown.download(url, str(output_path), quiet=False, fuzzy=True)
    return out

print("gdown loaded successfully!")
