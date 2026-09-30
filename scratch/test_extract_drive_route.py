import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app

print("Checking routes...")
routes = [str(p) for p in app.app.url_map.iter_rules()]
print("Has /extract-drive:", any("/extract-drive" in r for r in routes))
print("Has /extract:", any("/extract" in r and "drive" not in r for r in routes))
print("Has /upload-excel:", any("/upload-excel" in r for r in routes))

client = app.app.test_client()

with client.session_transaction() as sess:
    sess["user_id"] = "test-user-id"
    sess["email"] = "test@example.com"
    sess["role"] = "user"
    sess["approved"] = True

# Test empty drive URL
res = client.post("/extract-drive", json={"drive_url": "", "book_id": "B-101", "book_name": "Test Book"})
print("Empty drive URL test response code:", res.status_code, res.get_json())

# Test invalid drive URL
res2 = client.post("/extract-drive", json={"drive_url": "https://example.com/not-drive", "book_id": "B-101", "book_name": "Test Book"})
print("Invalid drive URL test response code:", res2.status_code, res2.get_json())
