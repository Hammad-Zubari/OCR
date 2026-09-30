import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import verify_company_field_boundaries, recover_missing_fields_from_section
from web_search_service import extract_web_candidates_for_company

def test_goldasht_mosaic_recovery():
    source_markdown = """
#10: Goldasht Mosaic

4- Goldasht Mosaic
📞 Center Office: +98 311- 3318702
+98 311- 3323517
Factory: +98 311- 2233808- 2232794
🛠️ Producer of Granite Mosaic With the Automatic Machines
🏗️ Shah Mohammadi

<a id='9b09647f-6299-4ea9-8755-b81071191d45'>
"""
    # Simulate LandingAI extraction returning name but empty tel / address
    raw_records = [
        {
            "name": "Goldasht Mosaic",
            "address": "",
            "tel": "",
            "fax": "",
            "email": "",
            "website": ""
        }
    ]

    verified = verify_company_field_boundaries(raw_records, source_markdown)
    rec = verified[0]

    print("Test Goldasht Mosaic Recovery Results:")
    print("  Name    :", rec["name"])
    print("  Tel     :", rec["tel"])
    print("  Fax     :", rec["fax"])
    print("  Email   :", rec["email"])
    print("  Website :", rec["website"])
    print("  Address :", rec["address"])

    assert rec["name"] == "Goldasht Mosaic", "Name mismatch"
    assert "+98 311- 3318702" in rec["tel"], "Missing Center Office number in tel"
    assert "+98 311- 3323517" in rec["tel"], "Missing second office number in tel"
    assert "+98 311- 2233808- 2232794" in rec["tel"], "Missing factory number in tel"
    print("[PASS] Goldasht Mosaic recovery test PASSED!\n")


def test_web_search_scope():
    # Test that web candidate search does not include address
    rec = {
        "name": "Test Company",
        "address": "",
        "tel": "",
        "fax": "",
        "email": "",
        "website": ""
    }
    candidates = extract_web_candidates_for_company("Test Company", address="", existing_record=rec)
    print("Web Search Candidates keys:", list(candidates.keys()))
    assert "address" not in candidates, "Address should NOT be in web candidates"
    print("[PASS] Web Search Scope test PASSED!\n")


if __name__ == "__main__":
    test_goldasht_mosaic_recovery()
    test_web_search_scope()
    print("[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")
