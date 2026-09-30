import sys
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import extract_landingai_billing_info

def test_billing_extraction():
    print("Testing LandingAI Billing Extraction...")

    # Mock ParseResponse with metadata
    mock_parse = MagicMock()
    mock_parse.metadata.credit_usage = 4.0
    mock_parse.metadata.duration_ms = 1850
    mock_parse.metadata.job_id = "job_parse_123"
    mock_parse.metadata.page_count = 4
    mock_parse.metadata.failed_pages = []

    res_parse = extract_landingai_billing_info(mock_parse)
    assert res_parse["credit_usage"] == 4.0
    assert res_parse["page_count"] == 4
    assert res_parse["job_id"] == "job_parse_123"
    print(" - Parse Billing Extraction: OK (4.0 credits, 4 pages)")

    # Mock ExtractResponse with metadata
    mock_extract = MagicMock()
    mock_extract.metadata.credit_usage = 1.5
    mock_extract.metadata.duration_ms = 920
    mock_extract.metadata.job_id = "job_extract_456"

    res_extract = extract_landingai_billing_info(mock_extract)
    assert res_extract["credit_usage"] == 1.5
    assert res_extract["job_id"] == "job_extract_456"
    print(" - Extract Billing Extraction: OK (1.5 credits)")

    # Mock billing.total_credits alternate structure
    mock_alt = MagicMock()
    del mock_alt.metadata.credit_usage
    mock_alt.metadata.billing = {"total_credits": 2.5}
    mock_alt.metadata.duration_ms = 500
    mock_alt.metadata.job_id = "job_alt_789"
    mock_alt.metadata.page_count = 2

    res_alt = extract_landingai_billing_info(mock_alt)
    assert res_alt["credit_usage"] == 2.5
    print(" - Alternate Billing Schema Extraction: OK (2.5 credits)")

    print("\nALL BILLING TRACKING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_billing_extraction()
