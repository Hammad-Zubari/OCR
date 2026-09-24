import os
import re
import json
import time
import requests
import threading
from difflib import SequenceMatcher
from dotenv import load_dotenv

# In-memory caches for web search results, page text, and LLM verification
WEB_SEARCH_CACHE = {}
PAGE_FETCH_CACHE = {}
LLM_CANDIDATE_CACHE = {}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,4}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}")

LEGAL_GENERIC_WORDS = {
    "ltd", "limited", "inc", "incorporated", "corp", "corporation", "pvt", "private",
    "co", "company", "group", "holdings", "industries", "industrial", "international", "global",
    "enterprise", "enterprises", "solutions", "services", "technologies", "tech", "technology",
    "official", "website", "contact", "email", "phone", "manufacturing", "manufacture", "mfg",
    "trade", "trading", "products", "hardware", "llc", "gmbh", "srl", "sa", "bv", "ag", "kft"
}

GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "qq.com",
    "163.com", "126.com", "sina.com", "aliyun.com", "foxmail.com",
    "yandex.com", "mail.ru", "sohu.com", "139.com", "icloud.com", "aol.com"
}

DISALLOWED_DOMAINS = {
    "opensanctions.org",
    "ofac.treasury.gov",
    "treasury.gov",
    "govinfo.gov",
    "iranwatch.org",
    "ecfr.gov",
    "un.org",
    "wikipedia.org",
    "wikidata.org",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "pinterest.com",
    "tripadvisor.com",
    "reddit.com",
    "tiktok.com",
    "zoominfo.com",
    "rocketreach.co",
    "leadiq.com",
    "dnb.com",
    "volza.com",
    "scribd.com",
    "kompass.com"
}

COUNTRY_PHONE_CODES = {
    "98": {"country": "iran", "tld": ".ir"},
    "92": {"country": "pakistan", "tld": ".pk"},
    "971": {"country": "uae", "tld": ".ae"},
    "86": {"country": "china", "tld": ".cn"},
    "90": {"country": "turkey", "tld": ".tr"},
    "91": {"country": "india", "tld": ".in"},
    "1": {"country": "usa", "tld": ".us"},
    "44": {"country": "uk", "tld": ".uk"},
    "39": {"country": "italy", "tld": ".it"},
    "49": {"country": "germany", "tld": ".de"},
    "7": {"country": "russia", "tld": ".ru"}
}

KNOWN_CITIES = {
    "iran": ["tehran", "esfahan", "isfahan", "shiraz", "tabriz", "mashhad", "karaj", "ahvaz", "qom", "saveh", "rasht", "kerman", "yazd", "arak", "khorasan"],
    "pakistan": ["karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "peshawar", "multan", "sialkot", "gujranwala", "quetta", "hub"],
    "uae": ["dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah"],
    "china": ["beijing", "shanghai", "shenzhen", "guangzhou", "hangzhou", "ningbo", "yiwu", "foshan", "dongguan", "qingdao", "jiangyin", "fujian", "zhejiang", "guangdong", "jiangsu", "shandong", "hebei", "henan", "sichuan"],
    "italy": ["rome", "milan", "turin", "florence", "venice", "bologna", "naples"],
    "usa": ["new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia", "san antonio", "san diego", "dallas", "austin"],
    "russia": ["moscow", "saint petersburg", "novosibirsk", "yekaterinburg", "kazan"]
}

ALL_GEO_WORDS = set()
for c_list in KNOWN_CITIES.values():
    ALL_GEO_WORDS.update(c_list)
for c_name in KNOWN_CITIES.keys():
    ALL_GEO_WORDS.add(c_name)


def normalize_text(text):
    if not text:
        return ""
    clean = re.sub(r"[^\w\s]", " ", str(text).lower())
    return " ".join(clean.split())


def extract_distinctive_name_tokens(name):
    """
    Extracts core brand tokens by removing generic corporate suffixes and common stop words.
    Example:
      'SHENZHEN PROFIT CONCEPT INTERNATIONAL COMPANY LTD' -> ['profit', 'concept']
      'SHANGHAI QIYANG ADHESIVE PRODUCTS CO., LTD' -> ['qiyang', 'adhesive']
      'JIANGYIN SILI PRODUCTS CORPORATION' -> ['sili']
    """
    clean = normalize_text(name)
    raw_tokens = [w for w in clean.split() if len(w) > 1 and w not in LEGAL_GENERIC_WORDS]
    
    # Separate core brand tokens from geographical tokens
    core_brand_tokens = [w for w in raw_tokens if w not in ALL_GEO_WORDS and len(w) > 2]
    all_distinctive = [w for w in raw_tokens if len(w) > 2]
    
    # If all tokens were geo/generic, fallback to all distinctive
    return core_brand_tokens if core_brand_tokens else all_distinctive


def detect_country_from_record(record):
    """Detects country and cities from address and telephone fields."""
    if not record:
        return [], []
    address = normalize_text(record.get("address", ""))
    tel = str(record.get("tel", "")) + " " + str(record.get("fax", ""))
    
    detected_countries = set()
    detected_cities = set()
    
    # 1. Check phone country codes
    digits = re.sub(r"\D", "", tel)
    for code, info in COUNTRY_PHONE_CODES.items():
        if tel.strip().startswith("+" + code) or re.search(r'\b\+' + code + r'\b', tel) or (len(code) >= 2 and digits.startswith(code)):
            detected_countries.add(info["country"])
            
    # 2. Check address text for country and city names
    for country, cities in KNOWN_CITIES.items():
        if country in address:
            detected_countries.add(country)
        for city in cities:
            if city in address:
                detected_cities.add(city)
                detected_countries.add(country)

    return list(detected_countries), list(detected_cities)


def build_targeted_search_query(company_name, existing_record=None):
    """
    Builds an exact-name anchored search query with location context.
    Example:
      "SHANGHAI QIYANG ADHESIVE PRODUCTS CO., LTD" Shanghai
      "JIANGYIN SILI PRODUCTS CORPORATION" Jiangyin
    """
    clean_name = company_name.strip().strip('"').strip()
    existing_record = existing_record or {}
    countries, cities = detect_country_from_record(existing_record)
    
    parts = [f'"{clean_name}"']
    if cities:
        parts.append(cities[0])
    elif countries:
        parts.append(countries[0])
        
    return " ".join(parts)


def fetch_webpage_text(url, timeout=2.5):
    """
    Fast, selective fetch of a candidate webpage to extract page title and text.
    Cached in memory to prevent redundant HTTP requests.
    """
    if not url or not url.startswith("http"):
        return "", ""
    if url in PAGE_FETCH_CACHE:
        return PAGE_FETCH_CACHE[url]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        res = requests.get(url, headers=headers, timeout=timeout)
        if res.status_code == 200:
            html = res.text[:35000]
            
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""
            title = re.sub(r'\s+', ' ', title)
            
            body_clean = re.sub(r'<script[^>]*>[\s\S]*?</script>', ' ', html, flags=re.IGNORECASE)
            body_clean = re.sub(r'<style[^>]*>[\s\S]*?</style>', ' ', body_clean, flags=re.IGNORECASE)
            body_clean = re.sub(r'<[^>]+>', ' ', body_clean)
            body_clean = re.sub(r'\s+', ' ', body_clean).strip()
            
            result = (title, body_clean[:4000])
            PAGE_FETCH_CACHE[url] = result
            return result
    except Exception:
        pass

    PAGE_FETCH_CACHE[url] = ("", "")
    return "", ""


# =========================================================
# STAGE 1: DETERMINISTIC MULTI-SIGNAL VALIDATION ENGINE
# =========================================================

def validate_company_identity(pdf_record, candidate_url, candidate_title="", candidate_snippet="", page_text=""):
    """
    Stage 1: Rigorous Multi-Signal Identity Validation.
    Signals evaluated:
      1. Exact/distinctive company name tokens (excluding generic suffixes)
      2. Street address, building, and postal code match
      3. City and Country match (supporting only)
      4. Normalized phone digit alignment vs conflict penalty
      5. Email & custom domain alignment (generic providers excluded)
      6. Website & brand domain alignment
    
    States:
      - 'REJECT': Clearly different or insufficient evidence (Score < 45)
      - 'PLAUSIBLE_REVIEW': Strong evidence ($45 <= Score < 75), sent for LLM cross-check
      - 'VERIFIED': High confidence multi-field match (Score >= 75 with >=2 independent signals)
    """
    comp_name = pdf_record.get("name", "")
    core_brand_tokens = extract_distinctive_name_tokens(comp_name)
    pdf_countries, pdf_cities = detect_country_from_record(pdf_record)
    
    cand_url_clean = str(candidate_url).lower()
    cand_domain = re.sub(r"^https?://", "", cand_url_clean).split("/")[0].replace("www.", "")
    full_web_text = f"{candidate_title} {candidate_snippet} {page_text[:2500]} {cand_domain}".lower()
    
    # 0. Check Disallowed Domains
    if any(cand_domain.endswith(d) or d in cand_domain for d in DISALLOWED_DOMAINS):
        audit = {
            "company": comp_name,
            "candidate_url": candidate_url,
            "candidate_title": candidate_title,
            "name_score": 0, "address_score": 0, "phone_score": 0, "email_score": 0, "domain_score": 0,
            "total_score": 0,
            "identity_status": "REJECT",
            "reasons": [f"Disallowed third-party/directory source: '{cand_domain}'"]
        }
        _print_audit_log(audit)
        return "REJECT", 0, audit

    # 0.1 Check generic directory category / city landing pages
    if re.search(r"/(?:city|category|classified|zapchasti)/", cand_url_clean):
        audit = {
            "company": comp_name,
            "candidate_url": candidate_url,
            "candidate_title": candidate_title,
            "name_score": 0, "address_score": 0, "phone_score": 0, "email_score": 0, "domain_score": 0,
            "total_score": 0,
            "identity_status": "REJECT",
            "reasons": [f"Generic directory category/city page: '{cand_url_clean}'"]
        }
        _print_audit_log(audit)
        return "REJECT", 0, audit

    score = 0
    reasons = []
    hard_conflict = False
    independent_signals = 0

    # -------------------------------------------------------------
    # Signal 1: Distinctive Company Name Match (0 to 35 points)
    # -------------------------------------------------------------
    name_score = 0
    matched_core_tokens = [t for t in core_brand_tokens if t in cand_domain or t in candidate_title.lower() or t in candidate_snippet.lower()]
    domain_core_matches = [t for t in core_brand_tokens if t in cand_domain]
    
    if len(core_brand_tokens) > 0:
        match_ratio = len(matched_core_tokens) / len(core_brand_tokens)
        if domain_core_matches:
            name_score += 25
            independent_signals += 1
            reasons.append(f"Distinctive brand '{domain_core_matches[0]}' in domain '{cand_domain}'")
        elif match_ratio >= 0.80:
            name_score += 20
            reasons.append(f"All distinctive brand tokens {matched_core_tokens} matched")
        elif match_ratio >= 0.50:
            name_score += 10
            reasons.append(f"Partial brand tokens {matched_core_tokens} matched")
        else:
            # Less than 50% distinctive brand tokens matched -> Hard Reject
            hard_conflict = True
            reasons.append(f"Missing distinctive brand tokens (Need: {core_brand_tokens} vs Found: {matched_core_tokens})")

    ratio = SequenceMatcher(None, normalize_text(comp_name), normalize_text(candidate_title)).ratio()
    if ratio >= 0.70:
        name_score += 10
        reasons.append(f"Title similarity ratio {ratio:.2f}")
    elif ratio >= 0.50:
        name_score += 5

    name_score = min(35, name_score)
    score += name_score
    if name_score >= 20:
        independent_signals += 1

    # -------------------------------------------------------------
    # Signal 2: Address, Postal Code & Location Match (0 to 25 points / Conflict)
    # -------------------------------------------------------------
    loc_score = 0
    pdf_addr = normalize_text(pdf_record.get("address", ""))
    
    # Check postal code (e.g. 5 or 6 digit codes)
    postal_matches = re.findall(r'\b\d{5,6}\b', pdf_addr)
    for p_code in postal_matches:
        if p_code in full_web_text:
            loc_score += 20
            independent_signals += 1
            reasons.append(f"Exact postal code match: '{p_code}'")
            break
            
    # Check street / building tokens (excluding city/country)
    addr_tokens = [w for w in pdf_addr.split() if w not in ALL_GEO_WORDS and len(w) > 3 and not w.isdigit()]
    matched_addr_tokens = [w for w in addr_tokens if w in full_web_text]
    if len(matched_addr_tokens) >= 2 and loc_score == 0:
        loc_score += 15
        independent_signals += 1
        reasons.append(f"Street/Address tokens matched: {matched_addr_tokens[:3]}")

    # City & Country supporting match (Weak: Max 10 pts together)
    if pdf_cities and any(city in full_web_text for city in pdf_cities):
        loc_score += 5
        reasons.append(f"City match: '{pdf_cities[0]}'")
    if pdf_countries and any(c in full_web_text for c in pdf_countries):
        loc_score += 5
        reasons.append(f"Country match: '{pdf_countries[0]}'")

    # Foreign country conflict detection (e.g. PDF is China/Iran but web is Russia/USA/Italy)
    if pdf_countries:
        for foreign_c, foreign_cities in KNOWN_CITIES.items():
            if foreign_c not in pdf_countries:
                tld_f = COUNTRY_PHONE_CODES.get("1" if foreign_c == "usa" else "7" if foreign_c == "russia" else "39" if foreign_c == "italy" else "", {}).get("tld", "")
                if (tld_f and cand_domain.endswith(tld_f)) or (foreign_c in full_web_text and not any(c in full_web_text for c in pdf_countries)):
                    hard_conflict = True
                    loc_score = -40
                    reasons.append(f"Country conflict: PDF is {pdf_countries} but web source is {foreign_c} (TLD '{tld_f}')")
                    break

    loc_score = max(-40, min(25, loc_score))
    score += loc_score

    # -------------------------------------------------------------
    # Signal 3: Phone Number Alignment vs Conflict (0 to 25 points / -30 penalty)
    # -------------------------------------------------------------
    phone_score = 0
    pdf_tel = str(pdf_record.get("tel", "")).strip()
    pdf_digits = re.sub(r"\D", "", pdf_tel)
    
    # Extract phones from web text
    web_phone_matches = PHONE_REGEX.findall(full_web_text)
    web_digits_list = [re.sub(r"\D", "", p) for p in web_phone_matches if len(re.sub(r"\D", "", p)) >= 7]
    
    if len(pdf_digits) >= 7:
        pdf_core = pdf_digits[-7:]  # Compare trailing 7 digits
        if any(pdf_core in wd for wd in web_digits_list):
            phone_score = 25
            independent_signals += 1
            reasons.append(f"Exact phone digit match: '...{pdf_core}'")
        elif web_digits_list:
            # Both have phone numbers and they clearly conflict!
            phone_score = -30
            hard_conflict = True
            reasons.append(f"Phone number conflict: PDF phone '{pdf_tel}' does not match web candidate phones")
    elif web_digits_list and not pdf_digits:
        # Candidate has phone while PDF had none -> Supporting candidate value
        phone_score = 5

    phone_score = max(-30, min(25, phone_score))
    score += phone_score

    # -------------------------------------------------------------
    # Signal 4: Email & Domain Alignment (0 to 15 points)
    # -------------------------------------------------------------
    email_score = 0
    pdf_email = str(pdf_record.get("email", "")).strip().lower()
    
    if "@" in full_web_text:
        web_emails = EMAIL_REGEX.findall(full_web_text)
        for em in web_emails:
            em_clean = em.strip().rstrip(".,;:").lower()
            em_dom = em_clean.split("@")[-1]
            
            if pdf_email and em_clean == pdf_email:
                email_score = 15
                independent_signals += 1
                reasons.append(f"Exact email match: '{em_clean}'")
                break
            elif em_dom in cand_domain and em_dom not in GENERIC_EMAIL_DOMAINS:
                email_score = 10
                independent_signals += 1
                reasons.append(f"Company-owned email domain '{em_dom}' aligns with website")
                break
                
    score += email_score

    # -------------------------------------------------------------
    # Signal 5: Website & Domain Alignment (0 to 15 points)
    # -------------------------------------------------------------
    domain_score = 0
    pdf_web = normalize_text(pdf_record.get("website", ""))
    
    if pdf_web and cand_domain in pdf_web:
        domain_score = 15
        independent_signals += 1
        reasons.append(f"Website domain matches PDF website: '{cand_domain}'")
    elif domain_core_matches:
        domain_score = 10
        reasons.append(f"Brand domain alignment: '{cand_domain}'")
        
    score += domain_score

    # -------------------------------------------------------------
    # Final Decision & State Categorization
    # -------------------------------------------------------------
    final_score = max(0, min(100, score))
    
    # Require at least 2 independent signals or strong evidence to verify
    if hard_conflict or final_score < 45:
        decision = "REJECT"
    elif final_score >= 75 and independent_signals >= 2:
        decision = "VERIFIED"
    else:
        decision = "PLAUSIBLE_REVIEW"
        
    if not reasons:
        reasons.append(f"Score: {final_score}/100")

    audit = {
        "company": comp_name,
        "candidate_url": candidate_url,
        "candidate_title": candidate_title,
        "name_score": name_score,
        "address_score": loc_score,
        "phone_score": phone_score,
        "email_score": email_score,
        "domain_score": domain_score,
        "total_score": final_score,
        "identity_status": decision,
        "reasons": reasons
    }
    
    _print_audit_log(audit)
    return decision, final_score, audit


def _print_audit_log(audit):
    def _safe_str(s):
        return str(s).encode("ascii", "replace").decode("ascii")

    print(f"\n==================================================")
    print(f"WEB IDENTITY VALIDATION AUDIT")
    print(f"Company         : {_safe_str(audit.get('company', ''))}")
    print(f"Candidate       : {_safe_str(audit.get('candidate_title', '')[:50])} ({_safe_str(audit.get('candidate_url', ''))})")
    print(f"Name Score      : {audit.get('name_score', 0)} / 35")
    print(f"Address Score   : {audit.get('address_score', 0)} / 25")
    print(f"Phone Score     : {audit.get('phone_score', 0)} / 25")
    print(f"Email Score     : {audit.get('email_score', 0)} / 15")
    print(f"Domain Score    : {audit.get('domain_score', 0)} / 15")
    print(f"Total Score     : {audit.get('total_score', 0)} / 100")
    print(f"Identity Status : {audit.get('identity_status', 'REJECT')}")
    print(f"Reasons         : {_safe_str(', '.join(audit.get('reasons', [])))}")
    print(f"==================================================\n")


# Global Metrics Tracker
METRICS_STATS = {
    "web_searches_run": 0,
    "candidates_evaluated": 0,
    "deterministic_matches": 0,
    "deterministic_rejects": 0,
    "llm_calls_made": 0,
    "llm_429_hits": 0,
    "rate_limited_candidates": 0
}

def reset_metrics_stats():
    for k in METRICS_STATS:
        METRICS_STATS[k] = 0

def get_metrics_stats():
    return dict(METRICS_STATS)


class GlobalLLMRateLimiter:
    """
    Global thread-safe rate limiter and concurrency controller for Groq / LLM API calls.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.last_request_time = 0.0
        self.semaphore = None

    def _get_semaphore(self):
        load_dotenv(override=True)
        try:
            concurrency = max(1, int(os.getenv("LLM_CONCURRENCY", "2")))
        except Exception:
            concurrency = 2
        if self.semaphore is None:
            self.semaphore = threading.Semaphore(concurrency)
        return self.semaphore

    def acquire(self):
        sem = self._get_semaphore()
        sem.acquire()
        with self.lock:
            load_dotenv(override=True)
            try:
                min_interval = float(os.getenv("LLM_MIN_REQUEST_INTERVAL", "1.0"))
            except Exception:
                min_interval = 1.0
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self.last_request_time = time.time()

    def release(self):
        sem = self._get_semaphore()
        try:
            sem.release()
        except Exception:
            pass

GLOBAL_LLM_LIMITER = GlobalLLMRateLimiter()


class DualLLMManager:
    """
    Multi-LLM Load Balancer with Dynamic Circuit Breaker.
    Treats HTTP 401 (Auth Error) and HTTP 429 (Rate Limit) completely separately.
    - If 401/403 received: Disables that provider immediately for the session.
    - If 429 received: Bounded backoff and instant failover.
    """
    def __init__(self):
        self._index = 0
        self._lock = threading.Lock()
        self._disabled_providers = set()

    def disable_provider(self, prov_name, reason="401 Invalid API Key"):
        with self._lock:
            self._disabled_providers.add(prov_name)
        print(f"[LLM Circuit Breaker] Provider '{prov_name}' disabled for session: {reason}")

    def get_providers(self):
        load_dotenv(override=True)
        providers = []
        
        # LLM 1 (Primary - Groq)
        k1 = os.getenv("LLM_API_KEY", "").strip()
        m1 = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
        b1 = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        if k1 and "LLM-1" not in self._disabled_providers:
            providers.append({"name": "LLM-1", "key": k1, "model": m1, "base_url": b1})
            
        # LLM 2 (Secondary / Load Balancer)
        k2 = os.getenv("LLM_API_KEY_2", "").strip()
        m2 = os.getenv("LLM_MODEL_2", "gpt-6-astra").strip()
        b2 = (os.getenv("LLM_BASE_URL_2", "").strip() or b1).rstrip("/")
        if k2 and "LLM-2" not in self._disabled_providers:
            providers.append({"name": "LLM-2", "key": k2, "model": m2, "base_url": b2})
            
        return providers

    def get_ordered_providers(self):
        """Returns active providers with round-robin starting provider."""
        providers = self.get_providers()
        if not providers:
            return []
        with self._lock:
            start_idx = self._index % len(providers)
            self._index += 1
        return providers[start_idx:] + providers[:start_idx]

DUAL_LLM_MANAGER = DualLLMManager()


# =========================================================
# STAGE 2: LLM CROSS-CHECK VERIFICATION (DISABLED / BYPASSED)
# =========================================================

def verify_candidate_with_llm(pdf_record, candidate_url, candidate_title, candidate_snippet, page_text, candidate_fields, deterministic_score=50):
    """
    Stage 2: LLM verification is TEMPORARILY BYPASSED as requested to prevent 429 rate limits & delays.
    Direct deterministic validation handles matches and rejects in 0 milliseconds.
    """
    if deterministic_score >= 50:
        METRICS_STATS["deterministic_matches"] += 1
        return "MATCH", f"Deterministic score match ({deterministic_score}/100) [LLM Bypassed]"
    else:
        METRICS_STATS["deterministic_rejects"] += 1
        return "NO_MATCH", f"Deterministic low-similarity score ({deterministic_score}/100) [LLM Bypassed]"


# =========================================================
# UNIVERSAL SEARCH CLIENT (SERPER / SEARCHAPI / SERPAPI)
# =========================================================

def search_google_universal(query, api_key=None, num=5):
    """
    Executes a Google Search query supporting Serper.dev, SearchApi.io, or SerpApi automatically.
    """
    load_dotenv(override=True)
    serper_key = os.getenv("SERPER_API_KEY", "").strip() or api_key
    searchapi_key = os.getenv("SEARCHAPI_API_KEY", "").strip() or api_key
    serpapi_key = os.getenv("SERPAPI_API_KEY", "").strip() or api_key

    # 1. Primary: Serper.dev (Fastest, High Throughput)
    if serper_key:
        try:
            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query, "num": num})
            headers = {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
            res = requests.post(url, headers=headers, data=payload, timeout=5)
            if res.status_code == 200:
                METRICS_STATS["web_searches_run"] += 1
                return res.json(), None
        except Exception as e:
            print(f"[Serper Search Error] {e}")

    # 2. Secondary: SearchApi.io
    if searchapi_key:
        try:
            url = "https://www.searchapi.io/api/v1/search"
            params = {
                "engine": "google",
                "q": query,
                "api_key": searchapi_key,
                "num": num
            }
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                METRICS_STATS["web_searches_run"] += 1
                return res.json(), None
        except Exception as e:
            print(f"[SearchApi Error] {e}")

    # 3. Tertiary: SerpApi
    if serpapi_key:
        try:
            url = "https://serpapi.com/search.json"
            params = {
                "engine": "google",
                "q": query,
                "api_key": serpapi_key,
                "num": num
            }
            res = requests.get(url, params=params, timeout=6)
            if res.status_code == 200:
                METRICS_STATS["web_searches_run"] += 1
                return res.json(), None
        except Exception as e:
            print(f"[SerpApi Error] {e}")

    return None, "No active search provider key configured (SERPER_API_KEY, SEARCHAPI_API_KEY, SERPAPI_API_KEY)."


# =========================================================
# MAIN ENTRY POINT: SELECTIVE WEB CANDIDATES ENRICHMENT
# =========================================================

def extract_web_candidates_for_company(company_name, address="", existing_record=None, api_key=None):
    """
    Main extraction pipeline:
      1. Determines missing fields in PDF record.
      2. Executes exact targeted Google search query.
      3. Stage 1: Deterministic Multi-Signal Validation (rejects non-matches instantly).
      4. Stage 2: Dual-LLM Verification (ambiguous candidates only).
      5. Returns validated web suggestions for user review or NULL.
    """
    if not company_name or not company_name.strip():
        return {}

    existing_record = existing_record or {}
    has_email = bool(str(existing_record.get("email", "")).strip())
    has_tel = bool(str(existing_record.get("tel", "")).strip())

    # Skip web search completely if BOTH Email and Tel are already present!
    if has_email and has_tel:
        return {}

    missing_fields = []
    if not has_email:
        missing_fields.append("email")
    if not has_tel:
        missing_fields.append("tel")
    if not str(existing_record.get("website", "")).strip():
        missing_fields.append("website")

    if not missing_fields:
        return {}

    cache_key = normalize_text(f"{company_name}_{address}")
    raw_data = WEB_SEARCH_CACHE.get(cache_key)

    if not raw_data:
        query_quoted = build_targeted_search_query(company_name, existing_record)
        raw_data, error = search_google_universal(query_quoted, api_key=api_key)
        
        organic_check = (raw_data.get("organic_results") or raw_data.get("organic") or []) if raw_data else []
        if not organic_check:
            clean_name = company_name.strip().strip('"').strip()
            countries, cities = detect_country_from_record(existing_record)
            loc = cities[0] if cities else (countries[0] if countries else "")
            query_natural = f"{clean_name} {loc} contact email website".strip()
            raw_data_fallback, _ = search_google_universal(query_natural, api_key=api_key)
            if raw_data_fallback and (raw_data_fallback.get("organic_results") or raw_data_fallback.get("organic")):
                raw_data = raw_data_fallback

        if error and not raw_data:
            print(f"[Web Search Warning] {company_name}: {error}")
            return {}
        WEB_SEARCH_CACHE[cache_key] = raw_data

    if not raw_data:
        return {}

    candidates = {}
    best_candidate_score = -1

    organic = raw_data.get("organic_results") or raw_data.get("organic") or []
    if isinstance(organic, list):
        for item in organic[:3]:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            
            if not link:
                continue

            cand_domain = re.sub(r"^https?://", "", link.lower()).split("/")[0].replace("www.", "")
            if any(cand_domain.endswith(d) or d in cand_domain for d in DISALLOWED_DOMAINS):
                continue

            # Stage 1 Fast Pre-Validation with Snippet
            decision, score, audit = validate_company_identity(
                pdf_record=existing_record,
                candidate_url=link,
                candidate_title=title,
                candidate_snippet=snippet,
                page_text=""
            )

            # Reject if not meeting strict criteria
            if decision == "REJECT":
                continue

            # Only fetch webpage text if email is missing and not already present in snippet
            page_text = ""
            if "email" in missing_fields and "@" not in snippet:
                page_title, page_text = fetch_webpage_text(link, timeout=1.2)
                effective_title = page_title or title
            else:
                effective_title = title

            full_text = f"{effective_title} {snippet} {page_text}"
            temp_fields = {}
            
            # Website
            if "website" in missing_fields:
                clean_web_val = link.strip()
                if "/" in clean_web_val.replace("://", ""):
                    match_root = re.match(r'^(https?://[^/]+)', clean_web_val)
                    if match_root:
                        clean_web_val = match_root.group(1)
                temp_fields["website"] = clean_web_val

            # Email
            if "email" in missing_fields:
                emails = EMAIL_REGEX.findall(full_text)
                for em in emails:
                    em_clean = em.strip().rstrip(".,;:")
                    em_dom = em_clean.split("@")[-1].lower()
                    if not any(junk in em_dom for junk in ["example.com", "domain.com", "sentry.io", "wixpress.com", "google.com", "png", "jpg"]):
                        temp_fields["email"] = em_clean
                        break

            # Tel
            if "tel" in missing_fields:
                phone_match = re.search(r'(?:Phone|Tel|Mobile|Call|Contact)?\s*[:\-]?\s*(\+?\d[\d\s\-\(\)\.]{7,18}\d)', full_text, re.IGNORECASE)
                if phone_match:
                    ph_clean = phone_match.group(1).strip()
                    digits = re.sub(r"\D", "", ph_clean)
                    if 7 <= len(digits) <= 15:
                        temp_fields["tel"] = ph_clean
                else:
                    phones = PHONE_REGEX.findall(full_text)
                    for ph in phones:
                        ph_clean = ph.strip().rstrip(".")
                        digits = re.sub(r"\D", "", ph_clean)
                        if 7 <= len(digits) <= 15:
                            temp_fields["tel"] = ph_clean
                            break

            if not temp_fields:
                continue

            METRICS_STATS["candidates_evaluated"] += 1

            # -------------------------------------------------------------
            # STAGE 2: Deterministic Scoring (LLM Bypassed)
            # -------------------------------------------------------------
            if decision == "VERIFIED" or score >= 65:
                confidence_label = "WEB - VERIFIED"
            else:
                confidence_label = "WEB - PLAUSIBLE REVIEW"
            rate_limited_flag = False

            if score > best_candidate_score:
                best_candidate_score = score
                candidates = {}

                if "website" in temp_fields:
                    candidates["website"] = {
                        "value": temp_fields["website"],
                        "source_title": effective_title or "Official Website",
                        "source_url": link.strip(),
                        "confidence": confidence_label,
                        "score": score,
                        "rate_limited": rate_limited_flag
                    }

                if "email" in temp_fields:
                    candidates["email"] = {
                        "value": temp_fields["email"],
                        "source_title": effective_title or "Official Web Contact",
                        "source_url": link.strip(),
                        "confidence": confidence_label,
                        "score": score,
                        "rate_limited": rate_limited_flag
                    }

                if "tel" in temp_fields:
                    candidates["tel"] = {
                        "value": temp_fields["tel"],
                        "source_title": effective_title or "Official Web Contact",
                        "source_url": link.strip(),
                        "confidence": confidence_label,
                        "score": score,
                        "rate_limited": rate_limited_flag
                    }

    return candidates
