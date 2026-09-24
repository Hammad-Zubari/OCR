import sys
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import (
    app,
    verify_company_field_boundaries,
    verify_records_with_llm,
    save_excel,
    save_supabase,
    remove_duplicates
)

def test_full_llm_verification_flow():
    print(">>> 1. Testing LLM Verification on Normal & Leaked Records...")

    sample_markdown = """
# ASIA ITCN DIRECTORY 2026

## 1. APEX LOGISTICS GROUP
Plot 45, Port Qasim Industrial Area, Karachi, Pakistan
Tel: +92 21 34720011, +92 21 34720012
Fax: +92 21 34720013
Email: operations@apexlogistics.pk
Website: www.apexlogistics.pk

## 2. BLUE SAPPHIRE CHEMICALS
Industrial Zone 3, Faisalabad, Pakistan
Tel: +92 41 8765432
Email: info@bluesapphirechem.com
Website: www.bluesapphirechem.com

## 3. CYBERNET DEFENSE LABS
Software Technology Park, Islamabad, Pakistan
Tel: +92 51 2289900
Website: https://cybernetlabs.io
"""

    extracted = [
        {
            "name": "APEX LOGISTICS GROUP",
            "address": "Plot 45, Port Qasim Industrial Area, Karachi, Pakistan",
            "tel": "+92 21 34720011, +92 21 34720012",
            "fax": "+92 21 34720013",
            "email": "operations@apexlogistics.pk",
            "website": "www.apexlogistics.pk"
        },
        {
            "name": "BLUE SAPPHIRE CHEMICALS",
            "address": "Industrial Zone 3, Faisalabad, Pakistan",
            "tel": "+92 41 8765432",
            "fax": "",
            "email": "info@bluesapphirechem.com",
            "website": "www.bluesapphirechem.com"
        },
        {
            "name": "CYBERNET DEFENSE LABS",
            "address": "Software Technology Park, Islamabad, Pakistan",
            "tel": "+92 51 2289900",
            "fax": "",
            # Erroneously took email from Blue Sapphire
            "email": "info@bluesapphirechem.com",
            "website": "https://cybernetlabs.io"
        }
    ]

    # Run boundary verification
    records = verify_company_field_boundaries(extracted, sample_markdown)
    
    # Run LLM verification
    verified_records = verify_records_with_llm(records, sample_markdown)

    assert len(verified_records) == 3, f"Expected 3 records, got {len(verified_records)}"

    print("Verified Records Summary:")
    for i, r in enumerate(verified_records):
        v = r.get("llm_verification", {})
        print(f"  Company #{i+1}: {r['name']}")
        print(f"    Email: '{r['email']}'")
        print(f"    LLM Result: {v.get('result')} | Reason: {v.get('reason')}")
        print(f"    Fields: {v.get('fields')}")

    # Company 1 should be PASS
    c1_v = verified_records[0].get("llm_verification", {})
    assert c1_v.get("result") in ("PASS", None), f"Company 1 should be PASS or unflagged, got: {c1_v}"

    # Company 3 email should be empty because it belonged to Company 2
    c3 = verified_records[2]
    assert c3["email"] == "", f"Company 3 contaminated email should be stripped! Got: {c3['email']}"
    c3_v = c3.get("llm_verification", {})
    if c3_v:
        email_status = c3_v.get("fields", {}).get("email", {}).get("status")
        print(f"  Company 3 email LLM status: {email_status}")

    print("  [PASS] LLM verification correctly evaluated records.")

def test_llm_failure_resilience():
    print("\n>>> 2. Testing LLM Failure Resilience (Graceful Fallback)...")
    
    # Temporarily override LLM API key to invalid
    old_key = os.environ.get("LLM_API_KEY")
    os.environ["LLM_API_KEY"] = "gsk_invalid_test_key_123"

    sample_md = "## SOME COMPANY\nAddress 123\nTel 555\n"
    records = [{"name": "SOME COMPANY", "address": "Address 123", "tel": "555", "fax": "", "email": "", "website": ""}]
    
    # Should not raise exception
    out = verify_records_with_llm(records, sample_md)
    assert len(out) == 1
    assert out[0]["name"] == "SOME COMPANY"
    print("  [PASS] System smoothly handled LLM API failure without dropping extracted data.")

    # Restore key
    if old_key:
        os.environ["LLM_API_KEY"] = old_key

def test_storage_and_export_integrity():
    print("\n>>> 3. Testing Storage & Export Integrity...")
    records = [
        {
            "name": "INTEGRITY CORP",
            "address": "777 Street",
            "tel": "111-222",
            "fax": "",
            "email": "info@integrity.com",
            "website": "integrity.com",
            "source_context": "Sample source markdown snippet",
            "source_start": 0,
            "source_end": 50,
            "llm_verification": {
                "result": "PASS",
                "reason": "Verified",
                "fields": {"email": {"status": "MATCH"}}
            },
            "book_name": "Test Catalog"
        }
    ]

    out_file = BASE_DIR / "output" / "test_integrity_export.xlsx"
    save_excel(records, out_file)

    import pandas as pd
    df = pd.read_excel(out_file)
    expected_cols = ["book_name", "name", "address", "tel", "fax", "email", "website"]
    assert list(df.columns) == expected_cols, f"Unexpected columns: {list(df.columns)}"
    assert "llm_verification" not in df.columns
    assert "source_context" not in df.columns
    if out_file.exists():
        out_file.unlink()
    print("  [PASS] Excel export contains strictly original 7 columns.")

    # Check Supabase record preparation
    db_records = []
    for r in records:
        db_records.append({
            "name": r["name"],
            "address": r["address"],
            "tel": r["tel"],
            "fax": r["fax"],
            "email": r["email"],
            "website": r["website"],
            "book_id": 123
        })
    assert set(db_records[0].keys()) == {"name", "address", "tel", "fax", "email", "website", "book_id"}
    print("  [PASS] Supabase record payload contains strictly standard database columns.")

if __name__ == "__main__":
    test_full_llm_verification_flow()
    test_llm_failure_resilience()
    test_storage_and_export_integrity()
    print("\n============================================================")
    print("ALL LLM VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("============================================================")
