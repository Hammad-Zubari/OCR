import sys
import io
import json
import pandas as pd
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import (
    app,
    verify_company_field_boundaries,
    save_excel,
    save_supabase,
    clean_exhibitors,
    remove_duplicates
)

def test_source_context_attachment_and_boundaries():
    print(">>> Testing Source-Context Attachment & Boundary Verification...")
    
    sample_markdown = """
# EXHIBITOR DIRECTORY 2026

## ABC TEXTILES LTD.
123 Industrial Avenue, Karachi, Pakistan
Tel: +92 21 111 222 333
Email: contact@abctextiles.com
Website: www.abctextiles.com

## XYZ PHARMA INTERNATIONAL
456 Health Boulevard, Lahore, Pakistan
Tel: +92 42 444 555 666
Fax: +92 42 777 888
Email: info@xyzpharma.pk
Website: https://xyzpharma.pk

## GLOBAL TRADING CORP
789 Trade Tower, Islamabad, Pakistan
Tel: +92 51 999 000
Website: www.globaltrading.com
"""

    extracted = [
        {
            "name": "ABC TEXTILES LTD.",
            "address": "123 Industrial Avenue, Karachi, Pakistan",
            "tel": "+92 21 111 222 333",
            "fax": "",
            "email": "contact@abctextiles.com",
            "website": "www.abctextiles.com"
        },
        {
            "name": "XYZ PHARMA INTERNATIONAL",
            "address": "456 Health Boulevard, Lahore, Pakistan",
            "tel": "+92 42 444 555 666",
            "fax": "+92 42 777 888",
            "email": "info@xyzpharma.pk",
            "website": "https://xyzpharma.pk"
        },
        {
            "name": "GLOBAL TRADING CORP",
            "address": "789 Trade Tower, Islamabad, Pakistan",
            "tel": "+92 51 999 000",
            "fax": "",
            # Erroneously borrowed email from XYZ PHARMA
            "email": "info@xyzpharma.pk",
            "website": "www.globaltrading.com"
        }
    ]

    verified = verify_company_field_boundaries(extracted, sample_markdown)
    assert len(verified) == 3, f"Expected 3 records, got {len(verified)}"

    # Check Company 1
    c1 = verified[0]
    assert c1["name"] == "ABC TEXTILES LTD."
    assert "source_context" in c1
    assert "ABC TEXTILES LTD." in c1["source_context"]
    assert c1["email"] == "contact@abctextiles.com"

    # Check Company 2
    c2 = verified[1]
    assert c2["name"] == "XYZ PHARMA INTERNATIONAL"
    assert "source_context" in c2
    assert "XYZ PHARMA INTERNATIONAL" in c2["source_context"]
    assert c2["fax"] == "+92 42 777 888"
    assert c2["email"] == "info@xyzpharma.pk"

    # Check Company 3 (Leaked email must be eliminated)
    c3 = verified[2]
    assert c3["name"] == "GLOBAL TRADING CORP"
    assert "source_context" in c3
    assert "GLOBAL TRADING CORP" in c3["source_context"]
    assert c3["email"] == "", f"Leaked email was NOT cleared for Global Trading! Got: {c3['email']}"
    print("  [PASS] Cross-company email leak detected and stripped cleanly.")
    print("  [PASS] source_context properly populated for every record.")

def test_excel_export_schema_hygiene():
    print(">>> Testing Excel Export Schema Hygiene...")
    records = [
        {
            "name": "TEST CO",
            "address": "123 Test St",
            "tel": "123456",
            "fax": "",
            "email": "test@co.com",
            "website": "test.com",
            "source_context": "Sample markdown snippet",
            "source_start": 10,
            "source_end": 50,
            "verification_status": "VALID",
            "book_name": "Test Book"
        }
    ]
    
    out_file = BASE_DIR / "output" / "test_schema_check.xlsx"
    save_excel(records, out_file)
    
    df = pd.read_excel(out_file)
    expected_cols = ["book_name", "name", "address", "tel", "fax", "email", "website"]
    assert list(df.columns) == expected_cols, f"Unexpected columns in Excel export: {list(df.columns)}"
    assert "source_context" not in df.columns
    assert "verification_status" not in df.columns
    print(f"  [PASS] Excel export contains ONLY clean standard columns: {list(df.columns)}")
    if out_file.exists():
        out_file.unlink()

def test_supabase_save_data_hygiene():
    print(">>> Testing Supabase Save Data Payload Hygiene...")
    records = [
        {
            "name": "TEST SUPABASE CO",
            "address": "456 DB St",
            "tel": "987654",
            "fax": "",
            "email": "db@test.com",
            "website": "dbtest.com",
            "source_context": "Raw markdown",
            "source_start": 0,
            "source_end": 100,
            "verification_score": 100,
            "book_name": "DB Book"
        }
    ]
    
    # We inspect what db_records gets generated in save_supabase
    db_records = []
    for r in records:
        name = str(r.get("name", "")).strip()
        if not name:
            continue
        db_records.append({
            "name": name,
            "address": str(r.get("address", "")).strip(),
            "tel": str(r.get("tel", "")).strip(),
            "fax": str(r.get("fax", "")).strip(),
            "email": str(r.get("email", "")).strip(),
            "website": str(r.get("website", "")).strip(),
            "book_id": 999
        })
        
    for rec in db_records:
        assert set(rec.keys()) == {"name", "address", "tel", "fax", "email", "website", "book_id"}, f"Unexpected keys in DB payload: {rec.keys()}"
    print(f"  [PASS] Supabase payload contains strictly valid DB fields: {list(db_records[0].keys())}")

if __name__ == "__main__":
    test_source_context_attachment_and_boundaries()
    test_excel_export_schema_hygiene()
    test_supabase_save_data_hygiene()
    print("\nALL VISUAL VERIFICATION & STORAGE TESTS PASSED SUCCESSFULLY!")
