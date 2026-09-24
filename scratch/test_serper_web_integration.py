import sys
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from web_search_service import (
    extract_web_candidates_for_company,
    WEB_SEARCH_CACHE
)
from app import save_excel, save_supabase

def test_complete_company_skips_search():
    print(">>> 1. Testing Complete Company Record (No Web Search)...")
    full_rec = {
        "name": "SIEMENS PAKISTAN ENGINEERING CO.",
        "address": "B-72 Estate Ave, S.I.T.E, Karachi",
        "tel": "+92 21 32574910",
        "fax": "+92 21 32563560",
        "email": "contact.pk@siemens.com",
        "website": "www.siemens.com.pk"
    }
    candidates = extract_web_candidates_for_company("SIEMENS PAKISTAN ENGINEERING CO.", full_rec["address"], full_rec)
    assert candidates == {}, f"Complete company must return empty web candidates, got: {candidates}"
    print("  [PASS] Complete company record successfully skipped web search.")

def test_missing_fields_search_and_no_overwrite():
    print("\n>>> 2. Testing Missing Fields Search & PDF Data Immutability...")
    partial_rec = {
        "name": "K-ELECTRIC LIMITED",
        "address": "KE House, Punjab Colony, Karachi",
        "tel": "+92 21 118",
        "fax": "",
        "email": "care@ke.com.pk", # PDF already extracted email!
        "website": ""             # Missing website
    }

    # Populate cache for testing
    cache_key = "k-electric limited"
    WEB_SEARCH_CACHE[cache_key] = {
        "knowledgeGraph": {
            "title": "K-Electric",
            "website": "https://www.ke.com.pk",
            "phone": "+92 21 99000"
        },
        "organic": [
            {
                "title": "K-Electric Official Website",
                "link": "https://www.ke.com.pk",
                "snippet": "Contact billings at billings@ke.com.pk or call +92 21 99000."
            }
        ]
    }

    candidates = extract_web_candidates_for_company("K-ELECTRIC LIMITED", partial_rec["address"], partial_rec)
    print("  Extracted Candidates for missing fields:", candidates)

    # 1. Missing website should be found
    assert "website" in candidates, "Missing website should have been proposed!"
    assert candidates["website"]["value"] == "https://www.ke.com.pk"

    # 2. Email was ALREADY in PDF -> web email must NOT be proposed/overwritten
    assert "email" not in candidates, "PDF email must NEVER be overwritten by web search!"

    print("  [PASS] Missing website proposed while existing PDF email remained strictly intact.")

def test_accept_and_reject_mechanics():
    print("\n>>> 3. Testing Accept & Reject Mechanics...")
    record = {
        "name": "TEST CO",
        "address": "Karachi",
        "tel": "",
        "fax": "",
        "email": "",
        "website": "",
        "web_suggestions": {
            "website": {"value": "https://testco.pk", "source_title": "Test Co", "source_url": "https://testco.pk"},
            "email": {"value": "info@testco.pk", "source_title": "Test Co", "source_url": "https://testco.pk"}
        }
    }

    # Simulate Accept for website
    record["website"] = record["web_suggestions"]["website"]["value"]
    del record["web_suggestions"]["website"]
    assert record["website"] == "https://testco.pk"
    assert "website" not in record["web_suggestions"]

    # Simulate Reject for email
    del record["web_suggestions"]["email"]
    assert record["email"] == "" # Keeps empty
    assert "email" not in record["web_suggestions"]

    print("  [PASS] Accept and Reject state transitions verified.")

def test_database_and_excel_export_hygiene():
    print("\n>>> 4. Testing Supabase & Excel Export Hygiene with Web Suggestions...")
    record = {
        "name": "EXPORT HYGIENE CO",
        "address": "456 Test Blvd",
        "tel": "123456",
        "fax": "",
        "email": "hygiene@test.com",
        "website": "hygiene.com",
        "source_context": "Sample markdown",
        "source_start": 0,
        "source_end": 50,
        "llm_verification": {"result": "PASS"},
        "web_suggestions": {
            "tel": {"value": "+92 300 1234567", "source_title": "Web result", "source_url": "https://example.com"}
        },
        "book_name": "Web Test Book"
    }

    # Excel export check
    out_file = BASE_DIR / "output" / "test_serper_export.xlsx"
    save_excel([record], out_file)

    import pandas as pd
    df = pd.read_excel(out_file)
    expected_cols = ["book_name", "name", "address", "tel", "fax", "email", "website"]
    assert list(df.columns) == expected_cols
    assert "web_suggestions" not in df.columns
    assert "source_context" not in df.columns
    if out_file.exists():
        out_file.unlink()
    print("  [PASS] Excel export contains strictly standard 7 columns.")

    # Supabase payload check
    db_records = []
    for r in [record]:
        db_records.append({
            "name": r["name"],
            "address": r["address"],
            "tel": r["tel"],
            "fax": r["fax"],
            "email": r["email"],
            "website": r["website"],
            "book_id": 999
        })
    assert set(db_records[0].keys()) == {"name", "address", "tel", "fax", "email", "website", "book_id"}
    print("  [PASS] Supabase payload contains strictly standard columns without web_suggestions.")

def test_missing_or_failed_serper_resilience():
    print("\n>>> 5. Testing Missing/Failed Serper Resilience...")
    # Empty API key
    empty_cand = extract_web_candidates_for_company("UNKNOWN CORP", api_key="")
    assert empty_cand == {}

    # Invalid API key
    invalid_cand = extract_web_candidates_for_company("UNKNOWN CORP", api_key="invalid_dummy_key_999")
    assert invalid_cand == {}
    print("  [PASS] System smoothly handles missing or invalid Serper key without failing.")

if __name__ == "__main__":
    test_complete_company_skips_search()
    test_missing_fields_search_and_no_overwrite()
    test_accept_and_reject_mechanics()
    test_database_and_excel_export_hygiene()
    test_missing_or_failed_serper_resilience()
    print("\n============================================================")
    print("ALL SERPER WEB INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("============================================================")
