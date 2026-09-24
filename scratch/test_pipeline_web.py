import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web_search_service import (
    search_google_universal,
    validate_company_identity,
    detect_country_from_record,
    extract_distinctive_name_tokens,
    fetch_webpage_text,
    EMAIL_REGEX,
    PHONE_REGEX
)

def extract_candidates_improved(company_name, existing_record):
    countries, cities = detect_country_from_record(existing_record)
    
    # 1. Natural query with location context
    loc_token = cities[0] if cities else (countries[0] if countries else "")
    query = f"{company_name} {loc_token} email website contact".strip()
    print("Executing Google Query:", query)
    
    raw_data, error = search_google_universal(query)
    if error or not raw_data:
        print("Search error or empty:", error)
        return {}
        
    organic = raw_data.get("organic_results") or raw_data.get("organic") or []
    print(f"Received {len(organic)} organic results from search.")
    
    candidates = {}
    pdf_tokens = extract_distinctive_name_tokens(company_name)
    
    for item in organic:
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        
        if not link or any(d in link.lower() for d in ["facebook.com", "linkedin.com", "twitter.com", "instagram.com", "youtube.com", "yelp.com", "x.com"]):
            continue
            
        page_title, page_text = fetch_webpage_text(link, timeout=3.5)
        effective_title = page_title or title
        
        decision, score, audit = validate_company_identity(
            pdf_record=existing_record,
            candidate_url=link,
            candidate_title=effective_title,
            candidate_snippet=snippet,
            page_text=page_text
        )
        
        if decision == "REJECT":
            continue
            
        full_text = f"{effective_title} {snippet} {page_text}"
        conf_label = "WEB - STRONG MATCH" if decision == "STRONG_MATCH" else "WEB - REVIEW REQUIRED"
        
        # Email candidate
        if "email" not in candidates:
            emails = EMAIL_REGEX.findall(full_text)
            for em in emails:
                em_clean = em.strip().rstrip(".,;:")
                em_dom = em_clean.split("@")[-1].lower()
                if not any(j in em_dom for j in ["example.com", "domain.com", "sentry.io", "wixpress.com", "google.com", "png", "jpg"]):
                    candidates["email"] = {
                        "value": em_clean,
                        "source_title": effective_title or "Web Search",
                        "source_url": link,
                        "confidence": conf_label,
                        "score": score
                    }
                    break
                    
        # Website candidate
        if "website" not in candidates:
            candidates["website"] = {
                "value": link,
                "source_title": effective_title or "Web Search",
                "source_url": link,
                "confidence": conf_label,
                "score": score
            }
            
    return candidates

comp = {
    "name": "Shayan Granite",
    "address": "Shirin sou village, left hand of qazvin Rasht road, 60 km",
    "tel": "+98 912- 3470079, +98 242- 5822786"
}

cands = extract_candidates_improved(comp["name"], comp)
print("\nFINAL EXTRACTED CANDIDATES:")
print(cands)
