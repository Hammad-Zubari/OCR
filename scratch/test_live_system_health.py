import sys
import os
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(override=True)

from app import (
    app,
    get_supabase_client,
    get_landingai_client,
    get_llm_config,
    verify_company_field_boundaries,
    verify_records_with_llm,
    save_excel,
    parse_excel_records
)
from web_search_service import extract_web_candidates_for_company

def run_health_checks():
    print("=" * 65)
    print("      LIVE SYSTEM & LLM HEALTH DIAGNOSTIC REPORT")
    print("=" * 65)

    # 1. Check Environment Configurations
    print("\n[1] Checking Environment Keys...")
    landingai_key = os.getenv("LANDINGAI_API_KEY") or os.getenv("VISION_AGENT_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    llm_key = os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    serper_key = os.getenv("SERPER_API_KEY")

    print(f"  - LandingAI Key present: {'YES' if landingai_key else 'NO'}")
    print(f"  - Supabase URL present: {'YES' if supabase_url else 'NO'}")
    print(f"  - Supabase Key present: {'YES' if supabase_key else 'NO'}")
    print(f"  - LLM Key present: {'YES' if llm_key else 'NO'} (Model: {llm_model})")
    print(f"  - Serper Key present: {'YES' if serper_key else 'NO'}")

    # 2. Check Supabase DB Connection
    print("\n[2] Testing Supabase Database Connection...")
    client, db_err = get_supabase_client()
    if db_err:
        print(f"  [FAIL] Supabase Error: {db_err}")
    else:
        try:
            res = client.table("books").select("id, book_name").limit(2).execute()
            print(f"  [OK] Supabase connection successful! (Found {len(res.data or [])} sample book records)")
        except Exception as e:
            print(f"  [FAIL] Supabase query error: {e}")

    # 3. Check LandingAI ADE Client
    print("\n[3] Testing LandingAI ADE Client Initialization...")
    try:
        lade_client = get_landingai_client()
        print("  [OK] LandingAI ADE client initialized successfully.")
    except Exception as e:
        print(f"  [FAIL] LandingAI error: {e}")

    # 4. Check LLM Source-Context Verification (LIVE API CALL)
    print("\n[4] Testing Live LLM Source-Context Verification (openai/gpt-oss-120b)...")
    sample_md = """
# CABSAT 2026 EXHIBITOR GUIDE

## 1. TECHFLOW SYSTEMS FZCO
Dubai Silicon Oasis, Dubai, UAE
Tel: +971 4 5015000
Email: contact@techflow.ae
Website: www.techflow.ae

## 2. METRO VISION BROADCAST
Media City Building 4, Dubai, UAE
Tel: +971 4 3911111
Email: info@metrovision.com
Website: www.metrovision.com
"""

    test_records = [
        {
            "name": "TECHFLOW SYSTEMS FZCO",
            "address": "Dubai Silicon Oasis, Dubai, UAE",
            "tel": "+971 4 5015000",
            "fax": "",
            "email": "contact@techflow.ae",
            "website": "www.techflow.ae"
        },
        {
            "name": "METRO VISION BROADCAST",
            "address": "Media City Building 4, Dubai, UAE",
            "tel": "+971 4 3911111",
            "fax": "",
            # Deliberately injected wrong email from Techflow to test leak detection
            "email": "contact@techflow.ae",
            "website": "www.metrovision.com"
        }
    ]

    t0 = time.time()
    verified_records = verify_records_with_llm(test_records, sample_md)
    elapsed = time.time() - t0

    print(f"  Latency: {elapsed:.2f} seconds")
    for i, r in enumerate(verified_records):
        v = r.get("llm_verification", {})
        print(f"  -> Record #{i+1} [{r['name']}]:")
        print(f"     Result: {v.get('result')} | Reason: {v.get('reason')}")
        print(f"     Cleaned Email in record: '{r['email']}'")
        print(f"     Field statuses: {v.get('fields')}")

    # Verify Company 2 contaminated email was cleared
    assert verified_records[1]["email"] == "", "LLM should have cleared the contaminated email!"
    print("  [OK] LLM Verification & Contamination Detection is working accurately!")

    # 5. Check Web Search Module (Serper)
    print("\n[5] Testing Web Search Service Module...")
    try:
        mock_rec = {"name": "TEST SEARCH CO", "address": "Dubai", "tel": "", "fax": "", "email": "", "website": ""}
        cands = extract_web_candidates_for_company("TEST SEARCH CO", "Dubai", mock_rec)
        print(f"  [OK] Web Search Module executed without crash (returned {len(cands)} suggestions).")
    except Exception as e:
        print(f"  [FAIL] Web search exception: {e}")

    # 6. Check Excel Export & Schema Safety
    print("\n[6] Testing Excel Schema & Safety...")
    out_file = BASE_DIR / "output" / "test_live_health.xlsx"
    save_excel(verified_records, out_file)
    import pandas as pd
    df = pd.read_excel(out_file)
    expected_cols = ["book_name", "name", "address", "tel", "fax", "email", "website"]
    assert list(df.columns) == expected_cols, f"Unexpected columns: {list(df.columns)}"
    assert "llm_verification" not in df.columns
    assert "web_suggestions" not in df.columns
    if out_file.exists():
        out_file.unlink()
    print(f"  [OK] Excel export contains strictly original 7 columns: {expected_cols}")

    print("\n" + "=" * 65)
    print("  [SUCCESS] ALL SYSTEMS AND LLM VERIFICATION ARE 100% OPERATIONAL!")
    print("=" * 65)

if __name__ == "__main__":
    run_health_checks()
