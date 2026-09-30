import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from web_search_service import (
    normalize_company_name,
    is_domain_relevant,
    extract_web_candidates_for_company,
    WEB_SEARCH_CACHE
)

def test_web_search_logic():
    print(">>> 1. Testing Domain Relevance & Normalization...")
    assert is_domain_relevant("https://www.abctextiles.com.pk/contact", "ABC Textiles Ltd")
    assert is_domain_relevant("https://bluesapphirechem.com", "Blue Sapphire Chemicals Private Limited")
    assert not is_domain_relevant("https://www.randomsite.com", "ABC Textiles Ltd")
    print("  [PASS] Domain relevance logic verified.")

    print("\n>>> 2. Testing Web Candidates Extraction with Mocked Serper Payload...")
    mock_company = "ABC TEXTILES LTD."
    mock_address = "Karachi Pakistan"
    existing_rec = {
        "name": "ABC TEXTILES LTD.",
        "address": "Karachi Pakistan",
        "tel": "",
        "fax": "",
        "email": "",
        "website": ""
    }

    # Populate cache with mock search response
    cache_key = mock_company.strip().lower()
    WEB_SEARCH_CACHE[cache_key] = {
        "knowledgeGraph": {
            "title": "ABC Textiles Ltd",
            "website": "https://www.abctextiles.com.pk",
            "phone": "+92 21 111 222 333"
        },
        "organic": [
            {
                "title": "Contact Us - ABC Textiles",
                "link": "https://www.abctextiles.com.pk/contact",
                "snippet": "For inquiries, email info@abctextiles.com.pk or call +92 21 3456789."
            }
        ]
    }

    candidates = extract_web_candidates_for_company(mock_company, mock_address, existing_rec)
    print("Extracted candidates:", candidates)

    assert "website" in candidates
    assert candidates["website"]["value"] == "https://www.abctextiles.com.pk"
    assert "email" in candidates
    assert candidates["email"]["value"] == "info@abctextiles.com.pk"
    assert "tel" in candidates
    assert candidates["tel"]["value"] == "+92 21 111 222 333"
    print("  [PASS] Missing fields successfully extracted from mock search data.")

    print("\n>>> 3. Testing Skip Web Search When Fields Are Already Full...")
    full_rec = {
        "name": "FULL CORP",
        "address": "123 Main St",
        "tel": "123456",
        "fax": "",
        "email": "full@corp.com",
        "website": "www.fullcorp.com"
    }
    cand_full = extract_web_candidates_for_company("FULL CORP", "123 Main St", full_rec)
    assert cand_full == {}, f"Expected empty candidates for fully populated record, got: {cand_full}"
    print("  [PASS] Completely populated companies skip web search.")

if __name__ == "__main__":
    test_web_search_logic()
    print("\nALL WEB SEARCH LOGIC TESTS PASSED SUCCESSFULLY!")
