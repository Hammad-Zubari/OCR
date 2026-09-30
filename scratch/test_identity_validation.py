import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv(override=True)

from web_search_service import validate_company_identity, DUAL_LLM_MANAGER, extract_distinctive_name_tokens

def test_token_extraction():
    print("\n--- Test 1: Distinctive Name Token Extraction ---")
    name1 = "SHENZHEN PROFIT CONCEPT INTERNATIONAL COMPANY LTD"
    tokens1 = extract_distinctive_name_tokens(name1)
    print(f"'{name1}' -> Distinctive Tokens: {tokens1}")
    assert "profit" in tokens1 and "concept" in tokens1
    assert "international" not in tokens1 and "company" not in tokens1 and "ltd" not in tokens1

    name2 = "JIANGYIN SILI PRODUCTS CORPORATION"
    tokens2 = extract_distinctive_name_tokens(name2)
    print(f"'{name2}' -> Distinctive Tokens: {tokens2}")
    assert "sili" in tokens2
    assert "products" not in tokens2 and "corporation" not in tokens2

def test_rejection_cases():
    print("\n--- Test 2: Weak Candidate Rejection ---")
    
    # 1. Shenzhen Profit Concept vs Exhibitor Detail
    rec1 = {"name": "SHENZHEN PROFIT CONCEPT INTERNATIONAL COMPANY LTD", "address": "Shenzhen, China"}
    dec1, score1, audit1 = validate_company_identity(rec1, "https://example.com/exhibitor-detail", "Exhibitor Detail - Fair", "Exhibitor information in Shenzhen China", "")
    print(f"Case 1 Decision: {dec1} (Score: {score1})")
    assert dec1 == "REJECT", f"Expected REJECT, got {dec1}"

    # 2. Yiwu Yongsheng vs Generic City Directory
    rec2 = {"name": "YIWU YONGSHENG COUNTY ADHESIVE TAPE CO., LTD", "address": "Yiwu, Zhejiang, China"}
    dec2, score2, audit2 = validate_company_identity(rec2, "https://chinaverifiedsupplier.com/city/jinhua", "Verified Jinhua Manufacturer China", "Suppliers in Jinhua China", "")
    print(f"Case 2 Decision: {dec2} (Score: {score2})")
    assert dec2 == "REJECT", f"Expected REJECT, got {dec2}"

    # 3. China Company vs Russian Domain
    rec3 = {"name": "SHANGHAI QIYANG ADHESIVE PRODUCTS CO., LTD", "address": "Shanghai, China"}
    dec3, score3, audit3 = validate_company_identity(rec3, "https://tlogistik.ru/zapchasti/Shanghai-Qiyang-Adhesive-Products-Co-Ltd/", "Russian Spare Parts", "Catalog in Moscow", "")
    print(f"Case 3 Decision: {dec3} (Score: {score3})")
    assert dec3 == "REJECT", f"Expected REJECT, got {dec3}"

def test_phone_conflict():
    print("\n--- Test 3: Phone Number Conflict Detection ---")
    rec = {"name": "TEST TRADING CORP", "address": "Shanghai, China", "tel": "+86 21 88889999"}
    dec, score, audit = validate_company_identity(
        rec, 
        "https://example.com/test", 
        "Test Trading Corp Official", 
        "Contact phone: +86 21 11112222", 
        "Call our office at +86 21 11112222"
    )
    print(f"Phone Conflict Decision: {dec} (Score: {score})")
    assert dec == "REJECT" or audit["phone_score"] < 0, "Conflicting phone must receive heavy negative penalty"

def test_circuit_breaker():
    print("\n--- Test 4: LLM Circuit Breaker ---")
    providers_before = [p["name"] for p in DUAL_LLM_MANAGER.get_providers()]
    print(f"Providers before: {providers_before}")
    
    # Disable LLM-2 due to 401
    DUAL_LLM_MANAGER.disable_provider("LLM-2", "401 Invalid API Key test")
    providers_after = [p["name"] for p in DUAL_LLM_MANAGER.get_providers()]
    print(f"Providers after: {providers_after}")
    assert "LLM-2" not in providers_after, "LLM-2 should be disabled from active pool"

if __name__ == "__main__":
    test_token_extraction()
    test_rejection_cases()
    test_phone_conflict()
    test_circuit_breaker()
    print("\nAll Web Identity Validation & Circuit Breaker tests passed successfully!")
