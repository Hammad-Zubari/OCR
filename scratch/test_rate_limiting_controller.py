import sys
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import (
    verify_records_with_llm,
    get_llm_config,
    LLM_VERIFICATION_CACHE
)

def test_rate_limit_controller():
    print("=" * 60)
    print("TESTING LLM RATE LIMIT CONTROLLER & PACING ENGINE")
    print("=" * 60)

    # 1. Config Test
    key, model, base_url, concurrency, delay_sec, max_retries = get_llm_config()
    print(f"[Config] Model: {model} | Concurrency: {concurrency} | Delay: {delay_sec}s | Max Retries: {max_retries}")
    assert concurrency == 1, "Concurrency should be 1"
    assert max_retries == 4, "Max retries should be 4"

    sample_md = """
    # EXHIBITOR DIRECTORY
    ## ALPHA CORP
    Dubai, UAE
    Email: info@alpha.com
    Website: www.alpha.com

    ## BETA ENTERPRISES
    Sharjah, UAE
    Email: contact@beta.com
    Website: www.beta.com
    """

    records = [
        {"name": "ALPHA CORP", "address": "Dubai, UAE", "tel": "", "fax": "", "email": "info@alpha.com", "website": "www.alpha.com"},
        {"name": "BETA ENTERPRISES", "address": "Sharjah, UAE", "tel": "", "fax": "", "email": "contact@beta.com", "website": "www.beta.com"}
    ]

    # 2. Test 429 Retry-After & Exhaustion Fallback
    print("\n>>> 1. Testing 429 Rate-Limit Recovery & RATE_LIMITED Marking...")
    mock_429_resp = MagicMock()
    mock_429_resp.status_code = 429
    mock_429_resp.headers = {"Retry-After": "0.1"}
    mock_429_resp.text = '{"error": {"message": "Rate limit reached. Please try again in 0.1s"}}'

    with patch("requests.post", return_value=mock_429_resp) as mock_post:
        out = verify_records_with_llm(records.copy(), sample_md)
        assert len(out) == 2, "Records must never be lost!"
        assert mock_post.call_count == 4, f"Expected 4 retries, got {mock_post.call_count}"
        for r in out:
            v = r.get("llm_verification", {})
            assert v.get("result") == "RATE_LIMITED", f"Expected RATE_LIMITED, got {v.get('result')}"
            assert r["name"] in ["ALPHA CORP", "BETA ENTERPRISES"], "Extracted record content must be preserved!"
        print(" [PASS] Exhausted 429 requests correctly marked as RATE_LIMITED without losing records.")

    # 3. Test Successful Verification with Caching
    print("\n>>> 2. Testing Successful Verification & In-Memory Caching...")
    LLM_VERIFICATION_CACHE.clear()
    
    mock_200_resp = MagicMock()
    mock_200_resp.status_code = 200
    mock_200_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"verifications": [{"record_index": 0, "result": "PASS", "reason": "Matched context", "fields": {"email": {"status": "MATCH"}}}, {"record_index": 1, "result": "PASS", "reason": "Matched context", "fields": {"email": {"status": "MATCH"}}}]}'
            }
        }]
    }

    with patch("requests.post", return_value=mock_200_resp) as mock_post:
        # First call: hits API once
        out1 = verify_records_with_llm(records.copy(), sample_md)
        assert mock_post.call_count == 1, "Expected 1 API call for first batch"
        assert out1[0]["llm_verification"]["result"] == "PASS"

        # Second call with same records: should be fulfilled from CACHE with 0 additional API calls
        mock_post.reset_mock()
        out2 = verify_records_with_llm(records.copy(), sample_md)
        assert mock_post.call_count == 0, "Expected 0 API calls (fulfilled from cache)!"
        assert out2[0]["llm_verification"]["result"] == "PASS"
        print(" [PASS] Cache completely prevented redundant API calls on subsequent runs.")

    print("\n" + "=" * 60)
    print("ALL RATE LIMIT CONTROLLER TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_rate_limit_controller()
