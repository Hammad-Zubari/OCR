import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv(override=True)

from web_search_service import DUAL_LLM_MANAGER, verify_candidate_with_llm

def test_dual_llm():
    providers = DUAL_LLM_MANAGER.get_providers()
    print(f"Configured Providers: {len(providers)}")
    for p in providers:
        print(f"  - {p['name']}: {p['model']} ({p['base_url']}) [Key: {p['key'][:8]}...]")
    
    assert len(providers) >= 1, "At least 1 provider should be active"
    
    # Test deterministic score >= 70 (LLM bypass)
    rec = {"name": "Test Steel Corp", "address": "Karachi", "tel": "021-123456"}
    res1, reason1 = verify_candidate_with_llm(rec, "http://teststeel.com", "Test Steel Corp", "Steel manufacturer", "", {}, deterministic_score=85)
    print("\nHigh similarity test (score 85):", res1, reason1)
    assert res1 == "MATCH", "Score >= 70 should match instantly without LLM"
    
    # Test deterministic score < 40 (LLM bypass)
    res2, reason2 = verify_candidate_with_llm(rec, "http://unrelated.com", "Random Shoe Store", "Shoes", "", {}, deterministic_score=20)
    print("Low similarity test (score 20):", res2, reason2)
    assert res2 == "NO_MATCH", "Score < 40 should reject instantly without LLM"
    
    print("\nAll Dual-LLM and bypass tests passed successfully!")

if __name__ == "__main__":
    test_dual_llm()
