import sys
import io
import json
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import (
    app,
    verify_company_field_boundaries,
    save_excel,
    clean_exhibitors,
    remove_duplicates
)

class TestCompleteSystem(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        self.client = app.test_client()

    def test_routes_security(self):
        # 1. Unauthenticated root redirect
        res = self.client.get("/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

        # 2. Authenticated root access
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test-user-id"
            sess["email"] = "user@example.com"
            sess["role"] = "user"
            sess["approved"] = True

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Visual Verification", res.data)
        self.assertIn(b"Document Source Viewer", res.data)

    def test_boundary_verification_engine(self):
        markdown = """
## ALPHA CORP
101 Tech St, Karachi
Tel: +92 21 11112222
Email: alpha@alphacorp.com
Website: www.alphacorp.com

## BETA CORP
202 Industrial Rd, Lahore
Tel: +92 42 33334444
Email: beta@betacorp.com
Website: www.betacorp.com
"""
        records = [
            {
                "name": "ALPHA CORP",
                "address": "101 Tech St, Karachi",
                "tel": "+92 21 11112222",
                "fax": "",
                "email": "alpha@alphacorp.com",
                "website": "www.alphacorp.com"
            },
            {
                "name": "BETA CORP",
                "address": "202 Industrial Rd, Lahore",
                "tel": "+92 42 33334444",
                "fax": "",
                "email": "beta@betacorp.com",
                "website": "www.betacorp.com"
            }
        ]

        verified = verify_company_field_boundaries(records, markdown)
        self.assertEqual(len(verified), 2)
        self.assertEqual(verified[0]["email"], "alpha@alphacorp.com")
        self.assertEqual(verified[1]["email"], "beta@betacorp.com")
        self.assertTrue(len(verified[0]["source_context"]) > 0)
        self.assertTrue(len(verified[1]["source_context"]) > 0)

    def test_export_excel_route(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test-user-id"
            sess["email"] = "user@example.com"
            sess["role"] = "user"
            sess["approved"] = True

        payload = {
            "book_name": "Test Book 2026",
            "records": [
                {
                    "name": "ACME CO",
                    "address": "Main Ave",
                    "tel": "12345",
                    "fax": "",
                    "email": "acme@co.com",
                    "website": "acme.com",
                    "source_context": "Sample Markdown Context"
                }
            ]
        }
        res = self.client.post("/export-excel", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("download_url", "").startswith("/download/"))

if __name__ == "__main__":
    unittest.main()
