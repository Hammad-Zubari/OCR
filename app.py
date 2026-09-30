import base64
import os
import re
import json
import time
import random
import sys
import uuid
import threading
from pathlib import Path
from difflib import SequenceMatcher
from functools import wraps

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
import dns.resolver
import pandas as pd
from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify,
    redirect,
    url_for,
    session,
    flash,
)
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from supabase import create_client
from landingai_ade import LandingAIADE
from web_search_service import (
    extract_web_candidates_for_company,
    reset_metrics_stats,
    get_metrics_stats
)

# =========================================================
# CONFIG & INITIALIZATION
# =========================================================

load_dotenv(override=True)

app = Flask(__name__, template_folder=str(PROJECT_ROOT / "Frontend"))
app.secret_key = os.getenv("SECRET_KEY", "exhibitor-system-secure-key-2026-xyz-987")

# Maximum upload size = 100 MB
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

BASE_DIR = PROJECT_ROOT
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PDF_EXTENSIONS = {".pdf"}
ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# Credit System & Baseline Historical Offset
LANDING_CREDIT_RATE_USD = 0.01
BASE_HISTORICAL_CREDITS = 3200.0
BASE_HISTORICAL_COST_USD = BASE_HISTORICAL_CREDITS * LANDING_CREDIT_RATE_USD

# In-memory Caches
EMAIL_VERIFICATION_CACHE = {}
MX_CACHE = {}

# =========================================================
# SUPABASE & LANDINGAI CLIENTS
# =========================================================

def get_supabase_client():
    load_dotenv(override=True)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None, "SUPABASE_URL ya SUPABASE_KEY .env mein configure nahi hai."
    try:
        client = create_client(url, key)
        return client, None
    except Exception as e:
        return None, f"Supabase client error: {str(e)}"


def get_landingai_client():
    load_dotenv(override=True)
    key = os.getenv("LANDINGAI_API_KEY") or os.getenv("VISION_AGENT_API_KEY")
    if not key:
        raise RuntimeError("LANDINGAI_API_KEY ya VISION_AGENT_API_KEY .env mein set nahi hai.")
    return LandingAIADE(apikey=key)


# =========================================================
# AUTHENTICATION HELPERS & DECORATORS
# =========================================================

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_current_user_profile():
    """Fetches the latest profile (role, approved) for the logged-in user from Supabase."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    if not is_valid_uuid(user_id):
        return {
            "id": user_id,
            "email": session.get("email", ""),
            "role": session.get("role", "user"),
            "approved": session.get("approved", False),
        }

    client, error = get_supabase_client()
    if not client or error:
        return {
            "id": user_id,
            "email": session.get("email", ""),
            "role": session.get("role", "user"),
            "approved": session.get("approved", False),
        }

    try:
        res = client.table("users").select("id, email, role, approved, created_at").eq("id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            profile = res.data[0]
            session["role"] = profile.get("role", "user")
            session["approved"] = bool(profile.get("approved", False))
            session["email"] = profile.get("email", session.get("email", ""))
            return profile
    except Exception as e:
        print(f"Error fetching current user profile: {e}")

    return {
        "id": user_id,
        "email": session.get("email", ""),
        "role": session.get("role", "user"),
        "approved": session.get("approved", False),
    }


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json:
                return jsonify({"success": False, "error": "Authentication required. Please login."}), 401
            return redirect(url_for("login_route"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login_route"))
        profile = get_current_user_profile()
        if not profile or profile.get("role") != "admin":
            if request.is_json:
                return jsonify({"success": False, "error": "Admin access required."}), 403
            flash("Admin access required.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


def approved_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"success": False, "error": "Authentication required."}), 401
        profile = get_current_user_profile()
        if not profile or not profile.get("approved"):
            return jsonify({
                "success": False,
                "error": "Database saving is not available until an administrator approves your account."
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# =========================================================
# CHINESE TEXT FILTERING
# =========================================================

CHINESE_CHAR_REGEX = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]"
)


def contains_chinese(text):
    if not text:
        return False
    return bool(CHINESE_CHAR_REGEX.search(str(text)))


def clean_chinese_text(text):
    if not text:
        return ""
    raw = str(text).strip()
    if raw.lower() in {"none", "null", "nan"}:
        return ""

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    cleaned_lines = []

    for line in lines:
        if contains_chinese(line):
            line_no_cjk = CHINESE_CHAR_REGEX.sub("", line)
            line_no_cjk = re.sub(r"\(\s*\)", "", line_no_cjk)
            line_no_cjk = re.sub(r"\[\s*\]", "", line_no_cjk)
            line_no_cjk = re.sub(r"（\s*）", "", line_no_cjk)
            line_no_cjk = re.sub(r"\s+", " ", line_no_cjk).strip()
            line_no_cjk = re.sub(r"^[\s,;:\-\/]+|[\s,;:\-\/]+$", "", line_no_cjk).strip()
            if re.search(r"[a-zA-Z]", line_no_cjk):
                cleaned_lines.append(line_no_cjk)
        else:
            cleaned_lines.append(line)

    result = ", ".join(cleaned_lines) if len(cleaned_lines) > 1 else (cleaned_lines[0] if cleaned_lines else "")
    result = CHINESE_CHAR_REGEX.sub("", result)
    result = re.sub(r"\(\s*\)", "", result)
    result = re.sub(r"\[\s*\]", "", result)
    result = re.sub(r"（\s*）", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r"^[\s,;:\-\/]+|[\s,;:\-\/]+$", "", result).strip()
    return result


def clean_category_name(raw_category):
    if not raw_category:
        return None
    val = clean_chinese_text(raw_category).strip()
    if not val or val.lower() in {"none", "null", "nan", "-"}:
        return None
    val = re.sub(r"^(?:[A-Z]\s+)?Area\s+[A-Z0-9]+[ \t\-:]*", "", val, flags=re.IGNORECASE).strip()
    if re.match(r"^Area\s+[A-Z0-9]+$", val, flags=re.IGNORECASE):
        return None
    val = re.sub(r"\s+", " ", val).strip(" -:,")
    return val if val else None


# =========================================================
# EXTRACTION SCHEMA
# =========================================================

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "exhibitors": {
            "type": "array",
            "description": (
                "List of exhibitors/companies found in the document. "
                "CRITICAL BOUNDARY RULE: Each company's details (Address, Tel, Fax, Email, Website) MUST "
                "strictly come ONLY from that specific company's individual section/block. "
                "DO NOT take or borrow contact info from a preceding or succeeding company if a field is missing. "
                "For documents with Chinese text, IGNORE and OMIT all Chinese characters, Chinese company names, "
                "and Chinese addresses. Extract ONLY the English / Latin company name and English postal address. "
                "CRITICAL CATEGORY EXTRACTION RULE: Look specifically at the vertical sidebar or margin banner running along "
                "the right edge, left edge, or header of the page (for example: vertical text such as 'Large Machinery & Equipment', "
                "'Electronics & Household Electrical Appliances', 'Building Materials', 'Hardware & Tools', etc.). "
                "Assign this exact English category heading to the 'category' field for ALL exhibitors on that page or section. "
                "When this vertical margin heading changes in the document, all subsequent exhibitors must receive the new category."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Company or exhibitor name in English / Latin script only. Do NOT include Chinese characters."
                    },
                    "address": {
                        "type": "string",
                        "description": "Company postal address in English / Latin script only. If none, return empty."
                    },
                    "tel": {
                        "type": "string",
                        "description": "Telephone, phone numbers, Center Office, Office, Factory, Mobile, or numbers following phone/call icons (e.g. +98 311- 3318702). If multiple exist, separate by comma. If none, return empty."
                    },
                    "fax": {
                        "type": "string",
                        "description": "Fax number(s). If multiple exist, separate by comma. If none, return empty."
                    },
                    "email": {
                        "type": "string",
                        "description": "Company email address(es). If multiple exist, separate by comma. If none, return empty."
                    },
                    "website": {
                        "type": "string",
                        "description": "Company website URL(s). If none, return empty."
                    },
                    "category": {
                        "type": ["string", "null"],
                        "description": (
                            "The industry or product category/section for this exhibitor in English. "
                            "Look at the vertical sidebar, margin banner, or section header printed on the page "
                            "(e.g. on the right-hand vertical edge such as 'Large Machinery & Equipment', "
                            "'Area A Large Machinery & Equipment', 'Electronic & Electrical Products', etc.). "
                            "Extract the clean English category name (e.g. 'Large Machinery & Equipment'). "
                            "Do NOT include Chinese characters (omit '大型机械及设备' or 'A 区'). "
                            "All exhibitors on the page under this vertical margin heading share this category. "
                            "When the vertical heading changes on a subsequent page or section, start the new category. "
                            "If absolutely no section or vertical heading exists, return null."
                        )
                    }
                },
                "required": ["name"]
            }
        }
    },
    "required": ["exhibitors"]
}


def sanitize_record(item):
    name = clean_chinese_text(item.get("name", "")).strip()
    if not name:
        return None

    raw_addr = clean_chinese_text(item.get("address", "")).strip()
    raw_tel = clean_chinese_text(item.get("tel", "")).strip()
    raw_fax = clean_chinese_text(item.get("fax", "")).strip()
    raw_email = clean_chinese_text(item.get("email", "")).strip()
    raw_website = clean_chinese_text(item.get("website", "")).strip()
    raw_category = item.get("category")
    category = clean_category_name(clean_chinese_text(raw_category)) if raw_category else None

    # Address sanitization: prevent merging 10 different addresses
    addr = raw_addr
    if addr.count(",") > 4 or "\n" in addr:
        parts = [p.strip() for p in re.split(r"[\n|]", addr) if p.strip()]
        if len(parts) > 1:
            addr = parts[0]
        else:
            addr_parts = [p.strip() for p in addr.split(",") if p.strip()]
            addr = ", ".join(addr_parts[:3])

    # Tel sanitization: at most 2 distinct phone numbers
    tel = raw_tel
    if tel:
        parts = [p.strip() for p in re.split(r"[,;\n|]", tel) if p.strip()]
        valid_tels = []
        for p in parts:
            d = re.sub(r"\D", "", p)
            if 6 <= len(d) <= 22 and p not in valid_tels:
                valid_tels.append(p)
        tel = ", ".join(valid_tels[:2])

    # Fax sanitization: at most 2 distinct fax numbers
    fax = raw_fax
    if fax:
        parts = [p.strip() for p in re.split(r"[,;\n|]", fax) if p.strip()]
        valid_faxes = []
        for p in parts:
            d = re.sub(r"\D", "", p)
            if 6 <= len(d) <= 22 and p not in valid_faxes:
                valid_faxes.append(p)
        fax = ", ".join(valid_faxes[:2])

    # Email sanitization: at most 2 distinct emails
    email = raw_email
    if email:
        parts = [p.strip() for p in re.split(r"[,;\s\n|]", email) if "@" in p and "." in p]
        valid_emails = []
        for p in parts:
            p_clean = p.strip(".,;:<>(){}[]\"'")
            if "@" in p_clean and "." in p_clean.split("@")[-1] and p_clean not in valid_emails:
                valid_emails.append(p_clean)
        email = ", ".join(valid_emails[:2])

    # Website sanitization: at most 2 distinct websites
    website = raw_website
    if website:
        parts = [p.strip() for p in re.split(r"[,;\s\n|]", website) if p.strip() and "@" not in p]
        valid_webs = []
        for p in parts:
            p_clean = p.strip(".,;:<>(){}[]\"'")
            if ("." in p_clean or "http" in p_clean) and p_clean not in valid_webs:
                valid_webs.append(p_clean)
        website = ", ".join(valid_webs[:2])

    page_no = item.get("page_number") or item.get("page") or item.get("page_no")
    try:
        p_num = int(page_no) if page_no is not None else 1
    except (ValueError, TypeError):
        p_num = 1

    return {
        "name": name,
        "page_number": p_num,
        "address": addr,
        "tel": tel,
        "fax": fax,
        "email": email,
        "website": website,
        "category": category or None
    }


def clean_exhibitors(raw_data):
    if not raw_data:
        return []
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            return []

    if isinstance(raw_data, dict):
        exhibitors = raw_data.get("exhibitors", [])
    elif isinstance(raw_data, list):
        exhibitors = raw_data
    else:
        exhibitors = []

    cleaned = []
    for item in exhibitors:
        if not isinstance(item, dict):
            continue
        rec = sanitize_record(item)
        if rec and rec["name"]:
            cleaned.append(rec)
    return cleaned


def remove_duplicates(records):
    unique = {}
    for record in records:
        name = str(record.get("name", "")).strip()
        if not name:
            continue
        key = name.casefold()
        page_no = record.get("page_number") or record.get("page") or 1
        try:
            page_no = int(page_no)
        except (ValueError, TypeError):
            page_no = 1

        if key not in unique:
            unique[key] = {
                "name": name,
                "page_number": page_no,
                "address": record.get("address", ""),
                "tel": record.get("tel", ""),
                "fax": record.get("fax", ""),
                "email": record.get("email", ""),
                "website": record.get("website", ""),
                "category": clean_category_name(record.get("category")),
                "country": record.get("country", ""),
                "source_context": record.get("source_context", ""),
                "source_start": record.get("source_start", 0),
                "source_end": record.get("source_end", 0),
                "llm_verification": record.get("llm_verification", None),
                "web_suggestions": record.get("web_suggestions", {})
            }
        else:
            existing = unique[key]
            for field in [
                "address", "tel", "fax", "email", "website", "category", "country",
                "source_context", "source_start", "source_end", "llm_verification", "web_suggestions"
            ]:
                if not existing.get(field) and record.get(field):
                    existing[field] = record[field]
            if not existing.get("page_number") and record.get("page_number"):
                existing["page_number"] = record["page_number"]
    return list(unique.values())


# =========================================================
# SOURCE CONTEXT & SECTION BOUNDARY VERIFICATION
# =========================================================

def normalize_for_search(text):
    if not text:
        return ""
    text_clean = CHINESE_CHAR_REGEX.sub("", str(text))
    return re.sub(r"\s+", " ", text_clean.lower()).strip()


def normalize_digits(text):
    if not text:
        return ""
    return re.sub(r"\D", "", str(text))


def normalize_domain(url_or_email):
    if not url_or_email:
        return ""
    s = str(url_or_email).strip().lower()
    if "@" in s:
        s = s.split("@")[-1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0].split(":")[0]
    return s


def split_emails(email_str):
    if not email_str:
        return []
    parts = re.split(r"[,/;\n|]|\bor\b|\band\b", str(email_str), flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def split_phones(phone_str):
    if not phone_str:
        return []
    parts = re.split(r"[,/;\n|]|\bor\b|\band\b", str(phone_str), flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def find_best_position(sub, text, start_from=0):
    """Finds the best matching character position of a company name in the text starting from start_from."""
    sub_clean = str(sub or "").strip()
    if not sub_clean or not text:
        return -1

    # 1. Exact search
    idx = text.lower().find(sub_clean.lower(), start_from)
    if idx != -1:
        return idx

    # 2. Match without punctuation / extra spaces
    sub_norm = re.sub(r"[^\w\s]", " ", sub_clean.lower())
    sub_words = [w for w in sub_norm.split() if len(w) > 2]
    if sub_words:
        first_word = sub_words[0]
        search_idx = start_from
        while True:
            idx = text.lower().find(first_word, search_idx)
            if idx == -1:
                break
            snippet = text[idx:idx + len(sub_clean) + 50]
            ratio = SequenceMatcher(None, sub_clean.lower(), snippet[:len(sub_clean)].lower()).ratio()
            if ratio >= 0.70:
                return idx
            search_idx = idx + len(first_word)
            if search_idx >= len(text):
                break

    return -1


def locate_companies_in_source(records, source_markdown):
    """Locates the sequential start positions of each company in document source text."""
    positions = []
    curr_pos = 0

    for r in records:
        name = r.get("name", "").strip()
        pos = find_best_position(name, source_markdown, start_from=curr_pos)
        if pos != -1:
            positions.append(pos)
            curr_pos = pos + max(1, len(name))
        else:
            # Fallback search from start
            pos_any = find_best_position(name, source_markdown, start_from=0)
            if pos_any != -1:
                positions.append(pos_any)
            else:
                positions.append(curr_pos)
    return positions


def extract_margin_category_from_markdown(md_text):
    """
    Detects vertical sidebar or page margin categories from OCR markdown.
    Handles Canton Fair and trade catalog formats, e.g.:
    'Area A \n Large Machinery & Equipment'
    'Area A - Large Machinery & Equipment'
    '大型机械及设备 \n Large Machinery & Equipment'
    '## Large Machinery & Equipment'
    """
    if not md_text:
        return None

    # 1. Area X followed by English category text on next line or same line (e.g. Area A \n Large Machinery & Equipment)
    m = re.search(r"Area\s+[A-Z0-9]+[ \t\-:]*\n+[ \t]*([A-Za-z][A-Za-z0-9 \t&,/\-]{3,70})[ \t]*(?:\n|$)", md_text, re.IGNORECASE)
    if m:
        c = clean_category_name(m.group(1))
        if c and not re.search(r"co\.|ltd|inc|corp|road|street|floor|bldg|tel|fax|email|www", c, re.IGNORECASE):
            return c

    m = re.search(r"Area\s+[A-Z0-9]+[ \t\-:]+([A-Za-z][A-Za-z0-9 \t&,/\-]{3,70})[ \t]*(?:\n|$)", md_text, re.IGNORECASE)
    if m:
        c = clean_category_name(m.group(1))
        if c and not re.search(r"co\.|ltd|inc|corp|road|street|floor|bldg|tel|fax|email|www", c, re.IGNORECASE):
            return c

    # 2. Chinese section line followed immediately by English category line (common in Chinese catalogs)
    lines = [line.strip() for line in md_text.splitlines() if line.strip()]
    for i in range(len(lines) - 1):
        line = lines[i]
        next_line = lines[i + 1]
        if re.search(r"[\u4e00-\u9fff]", line) and not re.search(r"[\u4e00-\u9fff]", next_line):
            c = clean_category_name(next_line)
            if c and 4 <= len(c) <= 65 and not re.search(r"co\.|ltd|inc|corp|road|street|floor|bldg|tel|fax|email|www|http|room|no\.|session|phase", c, re.IGNORECASE):
                if any(w in c.lower() for w in [
                    "machinery", "equipment", "appliance", "electronic", "hardware", "tool",
                    "textile", "garment", "building", "material", "chemical", "vehicle",
                    "parts", "consumer", "goods", "products", "lighting", "energy", "food",
                    "medicine", "supplies"
                ]):
                    return c

    # 3. Explicit markdown headings # or ##
    for m in re.finditer(r"(?m)^\s{0,3}#{1,6}\s+([^\r\n]+)", md_text):
        c = clean_category_name(m.group(1))
        if c and len(c) > 3 and not re.search(r"co\.|ltd|inc|corp|road|street|floor|bldg|tel|fax|email|www", c, re.IGNORECASE):
            return c

    return None


def assign_categories_from_source(records, source_markdown):
    """
    Propagate categories across exhibitor records based on:
    1) Existing categories extracted by LandingAI ADE / Mistral OCR.
    2) Margin / section headings detected in source markdown per page.
    3) Sequential forward-fill carry-forward: whenever a new heading/category is encountered,
       start that category and assign it to all subsequent exhibitors until the next heading.
    """
    if not records:
        return records

    page_categories = {}
    if source_markdown:
        page_blocks = re.split(r"(<!-- Page \d+ -->)", source_markdown)
        current_pno = 1
        for block in page_blocks:
            p_match = re.search(r"<!-- Page (\d+) -->", block)
            if p_match:
                current_pno = int(p_match.group(1))
            else:
                cat = extract_margin_category_from_markdown(block)
                if cat:
                    page_categories[current_pno] = cat

    current_category = None
    for record in records:
        rec_cat = clean_category_name(record.get("category"))
        pno = record.get("page_number", 1)

        if rec_cat:
            current_category = rec_cat
            record["category"] = rec_cat
        elif pno in page_categories and page_categories[pno]:
            current_category = page_categories[pno]
            record["category"] = current_category
        elif current_category:
            record["category"] = current_category
        else:
            record["category"] = None

    return records


def value_in_text(value, text, field_type):
    """Checks whether a field value exists inside a given text region."""
    if not value or not text:
        return False

    val_str = str(value).strip().lower()
    text_lower = text.lower()

    if field_type == "email":
        parts = split_emails(val_str)
        if not parts:
            return False
        for p in parts:
            p_clean = p.strip().strip("<>()[]")
            if "@" in p_clean and p_clean in text_lower:
                return True
        return False

    elif field_type in ("tel", "fax"):
        val_digits = normalize_digits(val_str)
        if len(val_digits) < 5:
            return False
        text_digits = normalize_digits(text)
        return val_digits in text_digits

    elif field_type == "website":
        dom = normalize_domain(val_str)
        if len(dom) >= 4 and dom in text_lower:
            return True
        return False

    elif field_type == "address":
        val_clean = re.sub(r"[^a-z0-9\s]", " ", val_str)
        words = [w for w in val_clean.split() if len(w) > 3]
        if not words:
            return False
        matches = sum(1 for w in words if w in text_lower)
        return (matches / len(words)) >= 0.55

    return False


def extract_section_phones_and_fax(section_text):
    if not section_text:
        return "", ""

    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    phones = []
    faxes = []

    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()

        # Skip HTML tags, markdown headings, image tags
        if line_clean.startswith("<") or line_clean.startswith("#") or line_clean.startswith("!["):
            continue

        is_fax = bool(re.search(r'\b(?:fax|telefax|📠)\b', line_lower))
        is_phone_line = bool(re.search(
            r'\b(?:tel|telephone|phone|mobile|cell|call|center office|head office|office|factory|branch|sales|hotline|📞|☎️|📱)\b',
            line_lower
        ))

        # Strip prefixes like "Center Office:", "Factory:", "Tel:", "Phone:", "📞", etc.
        cleaned_line = re.sub(
            r'^(?:(?:center office|head office|office|factory|branch|sales|hotline|tel|telephone|phone|mobile|cell|fax|telefax|📞|☎️|📱|📠)\s*[:\-–]?\s*)+',
            '',
            line_clean,
            flags=re.IGNORECASE
        ).strip()

        digits = re.sub(r"\D", "", cleaned_line)
        if len(digits) >= 6:
            if is_phone_line or is_fax or re.match(r'^[+\d\s\(\)\-\.,/]+$', cleaned_line):
                if re.match(r'^[+\d\s\(\)\-\.,/]+$', cleaned_line):
                    val = cleaned_line.strip(" ,;:")
                    if is_fax:
                        if val not in faxes:
                            faxes.append(val)
                    else:
                        if val not in phones:
                            phones.append(val)
                else:
                    num_match = re.search(r'(\+?\d[\d\s\(\)\-\.,/]{5,30}\d)', cleaned_line)
                    if num_match:
                        val = num_match.group(1).strip(" ,;:")
                        d = re.sub(r"\D", "", val)
                        if 6 <= len(d) <= 22:
                            if is_fax:
                                if val not in faxes:
                                    faxes.append(val)
                            else:
                                if val not in phones:
                                    phones.append(val)

    return ", ".join(phones), ", ".join(faxes)


def extract_section_emails(section_text):
    if not section_text:
        return ""
    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    raw_emails = EMAIL_REGEX.findall(section_text)
    valid_emails = []
    for em in raw_emails:
        em_clean = em.strip().rstrip(".,;:)")
        em_dom = em_clean.split("@")[-1].lower()
        if not any(junk in em_dom for junk in ["example.com", "domain.com", "png", "jpg", "jpeg", "gif"]):
            if em_clean not in valid_emails:
                valid_emails.append(em_clean)
    return ", ".join(valid_emails)


def extract_section_websites(section_text):
    if not section_text:
        return ""
    WEB_REGEX = re.compile(r'(?:https?://[^\s<>"]+|www\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+(?:/[^\s<>"]*)?)', re.IGNORECASE)
    raw_webs = WEB_REGEX.findall(section_text)
    valid_webs = []
    for web in raw_webs:
        web_clean = web.strip().rstrip(".,;:)")
        if web_clean not in valid_webs and "@" not in web_clean:
            valid_webs.append(web_clean)
    return ", ".join(valid_webs)


def extract_section_address(section_text, company_name=""):
    if not section_text:
        return ""
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    addr_lines = []
    comp_name_clean = re.sub(r"[^\w\s]", "", company_name.lower()).strip() if company_name else ""

    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()

        if line_clean.startswith("<") or line_clean.startswith("#") or line_clean.startswith("!["):
            continue

        line_norm = re.sub(r"[^\w\s]", "", line_lower).strip()
        if comp_name_clean and (line_norm == comp_name_clean or (comp_name_clean in line_norm and len(line_norm) - len(comp_name_clean) < 4)):
            continue

        if bool(re.search(r'\b(?:tel|telephone|phone|mobile|fax|telefax|email|e-mail|website|web|www|http|📞|☎️|📱|📠|✉️|🌐)\b', line_lower)):
            continue
        if "@" in line_clean:
            continue
        digits = re.sub(r"\D", "", line_clean)
        if len(digits) >= 6 and re.match(r'^[+\d\s\(\)\-\.,/]+$', line_clean):
            continue

        is_explicit_addr = bool(re.search(r'\b(?:address|addr|street|road|st\.|ave|avenue|blvd|building|bldg|floor|fl\.|p\.?o\.?\s*box|postal code|zip|industrial area|industrial zone|city|province|district|estate|📍)\b', line_lower))
        cleaned = re.sub(r'^(?:(?:address|addr|office address|factory address|location|📍)\s*[:\-–]?\s*)+', '', line_clean, flags=re.IGNORECASE).strip()
        if is_explicit_addr and cleaned:
            addr_lines.append(cleaned)

    return ", ".join(addr_lines)


def recover_missing_fields_from_section(rec, current_section):
    """
    Recovers phone, fax, email, website, and address from the company's verified section text
    if LandingAI extraction left them empty or missed them.
    """
    if not current_section:
        return rec

    sec_phones, sec_faxes = extract_section_phones_and_fax(current_section)
    sec_emails = extract_section_emails(current_section)
    sec_webs = extract_section_websites(current_section)
    sec_address = extract_section_address(current_section, rec.get("name", ""))

    # Recover Tel
    if not rec.get("tel") and sec_phones:
        rec["tel"] = sec_phones
    elif rec.get("tel") and sec_phones:
        current_digits = normalize_digits(rec["tel"])
        sec_digits = normalize_digits(sec_phones)
        if len(sec_digits) > len(current_digits) and current_digits in sec_digits:
            rec["tel"] = sec_phones

    # Recover Fax
    if not rec.get("fax") and sec_faxes:
        rec["fax"] = sec_faxes

    # Recover Email
    if not rec.get("email") and sec_emails:
        rec["email"] = sec_emails

    # Recover Website
    if not rec.get("website") and sec_webs:
        rec["website"] = sec_webs

    # Recover Address
    if not rec.get("address") and sec_address:
        rec["address"] = sec_address

    return rec


def verify_company_field_boundaries(records, source_markdown):
    """
    Validates that each extracted field belongs strictly to THAT company's section,
    was not erroneously borrowed from a previous or next company, and recovers
    any missing fields directly present in that company's source section.
    """
    if not records or not source_markdown or not source_markdown.strip():
        return records

    positions = locate_companies_in_source(records, source_markdown)
    n = len(records)
    cleaned_records = []

    for i, r in enumerate(records):
        start_pos = positions[i]
        end_pos = positions[i + 1] if i + 1 < n and positions[i + 1] > start_pos else len(source_markdown)
        current_section = source_markdown[start_pos:end_pos]

        rec = {
            "name": str(r.get("name", "")).strip(),
            "address": str(r.get("address", "")).strip(),
            "tel": str(r.get("tel", "")).strip(),
            "fax": str(r.get("fax", "")).strip(),
            "email": str(r.get("email", "")).strip(),
            "website": str(r.get("website", "")).strip(),
            "category": r.get("category") or None,
            "page_number": r.get("page_number", 1),
            "source_context": current_section.strip(),
            "source_start": start_pos,
            "source_end": end_pos
        }
        if r.get("book_name"):
            rec["book_name"] = r["book_name"]

        prev_section = ""
        if i > 0 and positions[i - 1] < start_pos:
            prev_section = source_markdown[positions[i - 1]:start_pos]

        next_section = ""
        if i + 1 < n and positions[i + 1] > start_pos:
            next_end = positions[i + 2] if i + 2 < n and positions[i + 2] > positions[i + 1] else len(source_markdown)
            next_section = source_markdown[positions[i + 1]:next_end]

        other_sections = source_markdown[:start_pos] + "\n" + source_markdown[end_pos:]

        fields_to_check = ["email", "tel", "fax", "website", "address"]

        for field in fields_to_check:
            val = rec.get(field, "")
            if not val:
                continue

            in_current = value_in_text(val, current_section, field)

            if not in_current:
                # Check if this field belongs to a previous or next company section
                in_prev = value_in_text(val, prev_section, field)
                in_next = value_in_text(val, next_section, field)
                in_other = value_in_text(val, other_sections, field)

                if in_prev or in_next or in_other:
                    # Cross-company leak confirmed! Clear the contaminated field.
                    rec[field] = ""
                else:
                    # If field is completely missing from document (hallucination)
                    if field in ("email", "tel", "fax", "website"):
                        rec[field] = ""

        # Additional domain-to-company name cross-correlation for emails/websites
        curr_name_clean = re.sub(r"[^a-z0-9]", "", rec["name"].lower())
        for neighbor_idx in [i - 1, i + 1]:
            if 0 <= neighbor_idx < n:
                neighbor = records[neighbor_idx]
                neighbor_name_clean = re.sub(r"[^a-z0-9]", "", str(neighbor.get("name", "")).lower())

                # Check email domain
                if rec.get("email"):
                    email_dom = normalize_domain(rec["email"]).split(".")[0]
                    if len(email_dom) >= 4 and len(neighbor_name_clean) >= 4:
                        if email_dom in neighbor_name_clean and email_dom not in curr_name_clean:
                            # Email belongs to neighboring company!
                            rec["email"] = ""

                # Check website domain
                if rec.get("website"):
                    web_dom = normalize_domain(rec["website"]).split(".")[0]
                    if len(web_dom) >= 4 and len(neighbor_name_clean) >= 4:
                        if web_dom in neighbor_name_clean and web_dom not in curr_name_clean:
                            # Website belongs to neighboring company!
                            rec["website"] = ""

        # Recover any missing fields present in the section markdown
        rec = recover_missing_fields_from_section(rec, current_section)

        cleaned_records.append(rec)

    return cleaned_records


# In-memory Caches
EMAIL_VERIFICATION_CACHE = {}
MX_CACHE = {}
LLM_VERIFICATION_CACHE = {}





# =========================================================
# EXCEL GENERATION & PARSING
# =========================================================

def save_excel(records, output_file):
    columns = [
        "page_number",
        "book_id",
        "country",
        "category",
        "name",
        "address",
        "tel",
        "fax",
        "email",
        "website"
    ]
    df = pd.DataFrame(records)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    df = df[columns]
    df.to_excel(output_file, index=False)


def parse_excel_records(file_stream_or_path, filename):
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        df = pd.read_excel(file_stream_or_path)
    elif suffix == ".xls":
        df = pd.read_excel(file_stream_or_path, engine="xlrd")
    elif suffix == ".csv":
        df = pd.read_csv(file_stream_or_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    if df.empty:
        return []

    col_map = {}
    for col in df.columns:
        c = str(col).strip().lower().replace("_", " ").replace("-", " ")
        if any(k in c for k in ["company name", "company", "exhibitor", "name", "title"]) and "name" not in col_map:
            col_map["name"] = col
        elif any(k in c for k in ["address", "location", "street"]) and "address" not in col_map:
            col_map["address"] = col
        elif any(k in c for k in ["phone", "telephone", "tel", "mobile", "contact no"]) and "tel" not in col_map:
            col_map["tel"] = col
        elif any(k in c for k in ["fax", "telefax"]) and "fax" not in col_map:
            col_map["fax"] = col
        elif any(k in c for k in ["email", "e mail", "mail"]) and "email" not in col_map:
            col_map["email"] = col
        elif any(k in c for k in ["website", "web", "url", "site", "domain"]) and "website" not in col_map:
            col_map["website"] = col
        elif any(k in c for k in ["category", "section", "sector"]) and "category" not in col_map:
            col_map["category"] = col
        elif any(k in c for k in ["page", "page no", "page number", "pg"]) and "page_number" not in col_map:
            col_map["page_number"] = col

    if "name" not in col_map and len(df.columns) > 0:
        col_map["name"] = df.columns[0]

    def get_cell(row, field):
        column = col_map.get(field)
        if column is None:
            return ""
        val = row.get(column, "")
        return "" if pd.isna(val) else str(val).strip()

    records = []
    for _, row in df.iterrows():
        name = clean_chinese_text(get_cell(row, "name"))
        if not name:
            continue
        pg_raw = get_cell(row, "page_number")
        try:
            pg_val = int(pg_raw) if pg_raw else 1
        except Exception:
            pg_val = 1
        records.append({
            "name": name,
            "page_number": pg_val,
            "address": clean_chinese_text(get_cell(row, "address")),
            "tel": clean_chinese_text(get_cell(row, "tel")),
            "fax": clean_chinese_text(get_cell(row, "fax")),
            "email": clean_chinese_text(get_cell(row, "email")),
            "website": clean_chinese_text(get_cell(row, "website")),
            "category": clean_chinese_text(get_cell(row, "category")) or None
        })

    return remove_duplicates(records)


# =========================================================
# SUPABASE DATABASE & BOOK METADATA OPERATIONS
# =========================================================

BOOK_METADATA_FILE = OUTPUT_DIR / "book_metadata.json"
_BOOK_METADATA_LOCK = threading.Lock()

def get_all_book_metadata():
    with _BOOK_METADATA_LOCK:
        if not BOOK_METADATA_FILE.exists():
            return {}
        try:
            with open(BOOK_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def get_book_country(book_id, default="General"):
    if not book_id:
        return default
    meta = get_all_book_metadata()
    b_info = meta.get(str(book_id).strip(), {})
    if isinstance(b_info, dict):
        return b_info.get("country", "").strip() or default
    elif isinstance(b_info, str):
        return b_info.strip() or default
    return default

def set_book_metadata(book_id, country=None, book_name=None, year=None, old_book_id=None):
    if not book_id:
        return
    book_id = str(book_id).strip()
    with _BOOK_METADATA_LOCK:
        meta = {}
        if BOOK_METADATA_FILE.exists():
            try:
                with open(BOOK_METADATA_FILE, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

        if old_book_id and str(old_book_id).strip() != book_id and str(old_book_id).strip() in meta:
            old_data = meta.pop(str(old_book_id).strip(), {})
            if isinstance(old_data, dict):
                if country is None:
                    country = old_data.get("country")
                if book_name is None:
                    book_name = old_data.get("book_name")
                if year is None:
                    year = old_data.get("year")

        current = meta.get(book_id, {})
        if not isinstance(current, dict):
            current = {"country": str(current)}

        if country is not None:
            current["country"] = str(country).strip() or "General"
        if book_name is not None:
            current["book_name"] = str(book_name).strip()
        if year is not None:
            current["year"] = str(year).strip() or None

        meta[book_id] = current
        try:
            with open(BOOK_METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Save Book Metadata Error]: {e}")


def normalize_catalog_name(name):
    if not name:
        return ""
    # Strip file extensions
    s = re.sub(r'\.(pdf|xlsx|xls|csv)$', '', str(name).strip(), flags=re.IGNORECASE)
    # Remove surrounding quotes or punctuation
    s = s.strip("\"' ")
    # Replace punctuation like dashes/underscores with space
    s = re.sub(r'[-_/\\]', ' ', s)
    # Normalize brackets
    s = re.sub(r'[\(\[\{]+', ' ', s)
    s = re.sub(r'[\)\]\}]+', ' ', s)
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()


def alphanumeric_slug(name):
    if not name:
        return ""
    s = re.sub(r'\.(pdf|xlsx|xls|csv)$', '', str(name).strip(), flags=re.IGNORECASE)
    return re.sub(r'[^a-z0-9]', '', s.lower())


def find_existing_catalog(book_id=None, book_name=None):
    """
    Finds an existing catalog in Supabase 'books' table:
    1. By exact ID
    2. By case-insensitive ID
    3. By exact book_name
    4. By normalized book_name (ignoring extensions, brackets, extra whitespace)
    5. By alphanumeric slug
    6. By fuzzy similarity (ratio >= 0.88)
    Returns: dict of existing book from DB or None
    """
    client, error = get_supabase_client()
    if error or not client:
        return None

    book_id_clean = str(book_id or "").strip()
    book_name_clean = str(book_name or "").strip()

    try:
        # 1. Exact ID check
        if book_id_clean:
            res_id = client.table("books").select("id, book_name, country, year").eq("id", book_id_clean).limit(1).execute()
            if res_id.data and len(res_id.data) > 0:
                return res_id.data[0]

        # Fetch all books for robust matching
        all_books_res = client.table("books").select("id, book_name, country, year").execute()
        all_books = all_books_res.data or []

        # 2. Case-insensitive ID check
        if book_id_clean:
            for b in all_books:
                if str(b.get("id", "")).strip().lower() == book_id_clean.lower():
                    return b

        if not book_name_clean:
            return None

        # 3. Exact case-insensitive name match
        for b in all_books:
            b_name = str(b.get("book_name", "")).strip()
            if b_name.lower() == book_name_clean.lower():
                return b

        # 4. Normalized name match
        input_norm = normalize_catalog_name(book_name_clean)
        if input_norm:
            for b in all_books:
                db_norm = normalize_catalog_name(b.get("book_name", ""))
                if db_norm and db_norm == input_norm:
                    return b

        # 5. Alphanumeric match
        input_alpha = alphanumeric_slug(book_name_clean)
        if input_alpha and len(input_alpha) >= 4:
            for b in all_books:
                db_alpha = alphanumeric_slug(b.get("book_name", ""))
                if db_alpha and db_alpha == input_alpha:
                    return b

        # 6. Fuzzy match (similarity >= 0.88)
        if input_norm and len(input_norm) >= 10:
            best_match = None
            best_ratio = 0.0
            for b in all_books:
                db_norm = normalize_catalog_name(b.get("book_name", ""))
                if db_norm and len(db_norm) >= 10:
                    ratio = SequenceMatcher(None, input_norm, db_norm).ratio()
                    if ratio > best_ratio and ratio >= 0.88:
                        best_ratio = ratio
                        best_match = b
            if best_match:
                return best_match

    except Exception as e:
        print(f"[find_existing_catalog Error]: {e}")

    return None


def create_book(book_id, book_name, country=None, year=None):
    """
    Creates or reuses a book record in Supabase:
    1. If catalog already exists in database (by book_id or matching book_name):
       - Reuses the existing catalog in DB.
       - NEVER creates a new catalog row or duplicate name.
       - Keeps DB's existing ID and book_name.
       - Updates country/year if missing in DB.
       - Returns existing_id and existing_name.
    2. If neither book_id nor book_name exists in DB:
       - Creates a new book record in the database.
    """
    client, error = get_supabase_client()
    if error:
        return False, None, None, error

    book_id = str(book_id or "").strip()
    book_name = str(book_name or "").strip() or "General Catalog"
    country = str(country or "").strip() or "General"
    year = str(year or "").strip() or None

    if not book_id:
        return False, None, None, "Book ID is required. Please enter a manual Book ID."

    try:
        # Check if catalog already exists in DB (by ID or catalog Name)
        existing_book = find_existing_catalog(book_id=book_id, book_name=book_name)
        if existing_book:
            final_id = str(existing_book.get("id", book_id)).strip()
            final_name = str(existing_book.get("book_name", "")).strip() or book_name
            final_country = str(existing_book.get("country", "")).strip() or country
            final_year = existing_book.get("year") or year

            set_book_metadata(final_id, country=final_country, book_name=final_name, year=final_year)
            try:
                update_data = {}
                if country and country != "General" and (not existing_book.get("country") or existing_book.get("country") == "General"):
                    update_data["country"] = country
                if year is not None and not existing_book.get("year"):
                    update_data["year"] = year
                if update_data:
                    client.table("books").update(update_data).eq("id", final_id).execute()
            except Exception:
                pass

            return True, final_id, final_name, f"Catalog [{final_id}] '{final_name}' pehle se DB mein mojood hai. Naya catalog nahi banaya gaya, existing catalog reuse kiya gaya."

        # Neither book_id nor book_name exists -> create new book record
        insert_data = {
            "id": book_id,
            "book_name": book_name,
            "year": year
        }
        try:
            response = client.table("books").insert(dict(insert_data, country=country)).execute()
        except Exception:
            try:
                response = client.table("books").insert(dict(insert_data, country=country)).execute()
            except Exception:
                response = client.table("books").insert({"id": book_id, "book_name": book_name}).execute()

        set_book_metadata(book_id, country=country, book_name=book_name, year=year)

        if response.data and len(response.data) > 0:
            created_id = str(response.data[0].get("id", book_id))
            created_name = str(response.data[0].get("book_name", book_name))
            return True, created_id, created_name, f"New catalog '{created_name}' [ID: {created_id}] created successfully."
        return True, book_id, book_name, f"New catalog '{book_name}' [ID: {book_id}] record created."

    except Exception as e:
        print(f"[Supabase create_book error]: {e}")
        return False, None, None, f"Database error while creating/verifying book: {str(e)}"
    except Exception as e:
        return False, None, None, str(e)


def update_book_details(old_book_id, new_book_id, new_book_name, country=None, year=None):
    """
    Updates an existing Book's ID, Name, Country, and optional Year.
    When Book ID is changed:
    1. Validates that new_book_id is not already assigned to another book.
    2. Updates or cascades the ID and Country to all related exhibitors in the database.
    3. Updates local activity audit logs and book metadata to keep history synchronized.
    """
    client, error = get_supabase_client()
    if error:
        return False, error

    old_book_id = str(old_book_id or "").strip()
    new_book_id = str(new_book_id or "").strip()
    new_book_name = str(new_book_name or "").strip() or "General Catalog"
    country = str(country or "").strip() or "General"
    year = str(year or "").strip() or None

    if not old_book_id:
        return False, "Old Book ID is required."
    if not new_book_id:
        return False, "New Book ID cannot be empty."

    try:
        # Find existing book
        old_res = client.table("books").select("id, book_name, year").eq("id", old_book_id).limit(1).execute()
        if not old_res.data or len(old_res.data) == 0:
            return False, f"Book with ID '{old_book_id}' not found in database."

        target_tables = ["exhibitor", "exhibitors"]

        if new_book_id != old_book_id:
            # Check if new_book_id is already assigned to a different book
            chk_res = client.table("books").select("id, book_name, year").eq("id", new_book_id).limit(1).execute()
            if chk_res.data and len(chk_res.data) > 0:
                conflict_name = chk_res.data[0].get("book_name", "")
                return False, f"Cannot change ID: Book ID '{new_book_id}' is already assigned to book '{conflict_name}'."

            # Insert new book record first to satisfy any foreign keys
            insert_data = {"id": new_book_id, "book_name": new_book_name, "country": country}
            if year is not None:
                insert_data["year"] = year
            try:
                client.table("books").insert(insert_data).execute()
            except Exception:
                client.table("books").insert({"id": new_book_id, "book_name": new_book_name}).execute()

            # Update all exhibitors referencing old_book_id to new_book_id and country
            for tbl in target_tables:
                try:
                    client.table(tbl).update({"book_id": new_book_id, "country": country}).eq("book_id", old_book_id).execute()
                except Exception as ex_err:
                    print(f"[Update exhibitors error on {tbl}]: {ex_err}")

            # Delete old book entry from books table
            try:
                client.table("books").delete().eq("id", old_book_id).execute()
            except Exception as del_err:
                print(f"[Delete old book error]: {del_err}")

        else:
            # Only book name / country changed
            update_data = {"book_name": new_book_name, "country": country}
            if year is not None:
                update_data["year"] = year
            try:
                client.table("books").update(update_data).eq("id", old_book_id).execute()
            except Exception:
                client.table("books").update({"book_name": new_book_name}).eq("id", old_book_id).execute()

            # Update country for all exhibitors belonging to this book
            for tbl in target_tables:
                try:
                    client.table(tbl).update({"country": country}).eq("book_id", old_book_id).execute()
                except Exception as ex_cntry_err:
                    print(f"[Update exhibitors country error on {tbl}]: {ex_cntry_err}")

        # Update metadata store
        set_book_metadata(new_book_id, country=country, book_name=new_book_name, year=year, old_book_id=old_book_id)

        # Update local activity logs
        logs = get_user_save_activities()
        modified_logs = False
        for entry in logs:
            if str(entry.get("book_id", "")).strip() == old_book_id:
                entry["book_id"] = new_book_id
                entry["book_name"] = new_book_name
                modified_logs = True

        if modified_logs:
            try:
                with open(SAVE_ACTIVITY_FILE, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False)
            except Exception as log_save_err:
                print(f"[Save Activity Update Error]: {log_save_err}")

        return True, f"Book '{new_book_id}' ({new_book_name}) and country '{country}' updated successfully."
    except Exception as e:
        return False, str(e)


def save_supabase(records, book_id, country=None):
    if not records:
        return True, 0, "No records to save."

    client, error = get_supabase_client()
    if error:
        return False, 0, error

    book_id = str(book_id or "").strip()
    country = str(country or get_book_country(book_id, default="General")).strip()
    target_tables = ["exhibitor", "exhibitors"]

    db_records = []
    for r in records:
        name = str(r.get("name", "")).strip()
        if not name:
            continue
        rec_country = str(r.get("country", "")).strip() or country
        db_records.append({
            "name": name,
            "address": str(r.get("address", "")).strip(),
            "tel": str(r.get("tel", "")).strip(),
            "fax": str(r.get("fax", "")).strip(),
            "email": str(r.get("email", "")).strip(),
            "website": str(r.get("website", "")).strip(),
            "category": str(r.get("category", "")).strip() or None,
            "country": rec_country,
            "book_id": book_id
        })

    if not db_records:
        return False, 0, "No valid records to save."

    for table_name in target_tables:
        try:
            res = client.table(table_name).insert(db_records).execute()
            saved_count = len(res.data) if res.data else len(db_records)
            return True, saved_count, f"{saved_count} exhibitors saved to '{table_name}'."
        except Exception as table_err:
            err_str = str(table_err)
            if "PGRST205" in err_str or "not find the table" in err_str:
                continue
            # If country column not found, fallback to insert without country
            if "country" in err_str:
                try:
                    fallback_records = [{k: v for k, v in rec.items() if k not in {"country"}} for rec in db_records]
                    res = client.table(table_name).insert(fallback_records).execute()
                    saved_count = len(res.data) if res.data else len(fallback_records)
                    return True, saved_count, f"{saved_count} exhibitors saved to '{table_name}'."
                except Exception as fb_err:
                    print(f"[Supabase Fallback Save Error on {table_name}] {fb_err}")
            if "category" in err_str:
                try:
                    fallback_records = [{k: v for k, v in rec.items() if k != "category"} for rec in db_records]
                    res = client.table(table_name).insert(fallback_records).execute()
                    saved_count = len(res.data) if res.data else len(fallback_records)
                    return True, saved_count, f"{saved_count} exhibitors saved to '{table_name}'."
                except Exception as category_err:
                    print(f"[Supabase Category Fallback Save Error on {table_name}] {category_err}")
            print(f"[Supabase Save Error on {table_name}] {table_err}")

    return False, 0, "Could not save to Supabase table."


SAVE_ACTIVITY_FILE = OUTPUT_DIR / "user_save_activity.json"
EXTRACTION_LEDGER_FILE = OUTPUT_DIR / "extraction_credit_ledger.json"


def filter_by_timeframe(items, timeframe="all", date_field="created_at"):
    """
    Filters a list of dictionary items by timeframe ('all', 'daily', 'weekly', 'monthly')
    using ISO timestamps in `date_field`.
    """
    if not items or not timeframe or str(timeframe).lower() == "all":
        return list(items or [])

    from datetime import datetime, timedelta
    now_dt = datetime.now()
    timeframe_lower = str(timeframe).lower()
    filtered = []

    for item in items:
        dt_str = item.get(date_field)
        if not dt_str:
            filtered.append(item)
            continue
        try:
            clean_dt_str = str(dt_str).replace("Z", "")
            if "+" in clean_dt_str:
                clean_dt_str = clean_dt_str.split("+")[0]
            entry_dt = datetime.fromisoformat(clean_dt_str)

            if timeframe_lower in {"daily", "today"}:
                if entry_dt.date() == now_dt.date():
                    filtered.append(item)
            elif timeframe_lower in {"weekly", "7days", "week"}:
                if (now_dt - entry_dt) <= timedelta(days=7):
                    filtered.append(item)
            elif timeframe_lower in {"monthly", "30days", "month"}:
                if (now_dt - entry_dt) <= timedelta(days=30):
                    filtered.append(item)
            else:
                filtered.append(item)
        except Exception:
            filtered.append(item)

    return filtered


def log_extraction_credit_activity(
    user_id,
    user_email,
    book_id,
    book_name,
    filename,
    pages_processed,
    parse_credits,
    extract_credits,
    total_credits,
    records_extracted,
    duration_ms=0,
    parse_job_id="",
    extract_job_ids=None,
    engine="LandingAI ADE",
    model="dpt-2-latest / extract-latest"
):
    """
    Logs LandingAI ADE credit consumption, pages processed, extracted count, and cost estimate
    to the persistent extraction credit ledger for admin reporting and audit trail.
    """
    try:
        from datetime import datetime
        now_dt = datetime.now()
        timestamp_iso = now_dt.isoformat()
        time_formatted = now_dt.strftime("%d %b %Y, %I:%M:%S %p")
        time_short = now_dt.strftime("%I:%M %p")

        # Cost rate: 100 credits = $1.00.
        cost_est = round(float(total_credits or 0.0) * LANDING_CREDIT_RATE_USD, 4)

        entry = {
            "id": uuid.uuid4().hex,
            "user_id": str(user_id or "unknown"),
            "user_email": str(user_email or "Unknown User"),
            "engine": str(engine or "LandingAI ADE"),
            "model": str(model or "dpt-2-latest / extract-latest"),
            "book_id": str(book_id or ""),
            "book_name": str(book_name or "General Catalog"),
            "filename": str(filename or "document.pdf"),
            "pages_processed": int(pages_processed or 0),
            "parse_credits": round(float(parse_credits or 0.0), 2),
            "extract_credits": round(float(extract_credits or 0.0), 2),
            "total_credits": round(float(total_credits or 0.0), 2),
            "records_extracted": int(records_extracted or 0),
            "cost_estimate_usd": cost_est,
            "duration_ms": int(duration_ms or 0),
            "parse_job_id": str(parse_job_id or ""),
            "extract_job_ids": extract_job_ids or [],
            "created_at": timestamp_iso,
            "created_at_formatted": time_formatted,
            "time_short": time_short
        }

        logs = []
        if EXTRACTION_LEDGER_FILE.exists():
            try:
                with open(EXTRACTION_LEDGER_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.insert(0, entry)
        logs = logs[:2500]
        with open(EXTRACTION_LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        print(f"[Credit Ledger Log] User '{user_email}' used {total_credits:.2f} ADE credits ({pages_processed} pages, {records_extracted} records, est. ${cost_est:.4f}) for '{filename}' at {time_formatted}")
        return True
    except Exception as e:
        print(f"[Credit Ledger Log Error] {e}")
        return False


def get_extraction_credit_ledger(timeframe="all", search=""):
    """Retrieves logged extraction credit ledger entries filtered by timeframe and search string."""
    logs = []
    if EXTRACTION_LEDGER_FILE.exists():
        try:
            with open(EXTRACTION_LEDGER_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            print(f"[Error reading credit ledger logs] {e}")
            logs = []

    # 1. Apply timeframe filtering
    filtered = filter_by_timeframe(logs, timeframe=timeframe, date_field="created_at")

    # 2. Apply search filter if provided
    if search and str(search).strip():
        q = str(search).strip().lower()
        filtered = [
            e for e in filtered
            if q in str(e.get("user_email", "")).lower()
            or q in str(e.get("filename", "")).lower()
            or q in str(e.get("book_name", "")).lower()
            or q in str(e.get("book_id", "")).lower()
            or q in str(e.get("parse_job_id", "")).lower()
            or q in str(e.get("created_at_formatted", "")).lower()
        ]

    # Recalculate persisted rows with the current rate so historical entries
    # and new entries use the same pricing in cards, tables, and exports.
    normalized = []
    for entry in filtered:
        item = dict(entry)
        credits = float(item.get("total_credits") or item.get("credits_used") or 0.0)
        item["cost_estimate_usd"] = round(credits * LANDING_CREDIT_RATE_USD, 4)
        normalized.append(item)
    return normalized


def delete_extraction_credit_entry(entry_id):
    """Deletes a specific extraction credit ledger entry by ID."""
    logs = []
    if EXTRACTION_LEDGER_FILE.exists():
        try:
            with open(EXTRACTION_LEDGER_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    new_logs = [e for e in logs if str(e.get("id")) != str(entry_id)]
    if len(new_logs) == len(logs):
        return False

    try:
        with open(EXTRACTION_LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(new_logs, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Delete Credit Ledger Log Error] {e}")
        return False


def clear_all_extraction_credit_entries():
    """Clears all extraction credit ledger entries."""
    try:
        with open(EXTRACTION_LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Clear Credit Ledger Logs Error] {e}")
        return False


def log_user_save_activity(user_id, user_email, book_id, book_name, saved_count):
    """Logs user database saving activity with exact timestamp, book name, and record count."""
    try:
        from datetime import datetime
        now_dt = datetime.now()
        timestamp_iso = now_dt.isoformat()
        time_formatted = now_dt.strftime("%d %b %Y, %I:%M:%S %p")
        time_short = now_dt.strftime("%I:%M %p")

        log_entry = {
            "id": uuid.uuid4().hex,
            "user_id": str(user_id or "unknown"),
            "user_email": str(user_email or "Unknown User"),
            "book_id": str(book_id or ""),
            "book_name": str(book_name or "General Catalog"),
            "saved_count": int(saved_count or 0),
            "created_at": timestamp_iso,
            "created_at_formatted": time_formatted,
            "time_short": time_short
        }

        # 1. Save to persistent local JSON audit log
        logs = []
        if SAVE_ACTIVITY_FILE.exists():
            try:
                with open(SAVE_ACTIVITY_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.insert(0, log_entry)
        logs = logs[:1500]
        with open(SAVE_ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        # 2. Also attempt to save to Supabase if table exists
        client, error = get_supabase_client()
        if client and not error:
            for tbl in ["save_activity_logs", "user_activity_logs", "activity_logs"]:
                try:
                    client.table(tbl).insert({
                        "user_id": str(user_id),
                        "user_email": str(user_email),
                        "book_id": int(book_id) if (isinstance(book_id, int) or (isinstance(book_id, str) and book_id.isdigit())) else None,
                        "book_name": str(book_name),
                        "saved_count": int(saved_count),
                        "created_at": timestamp_iso
                    }).execute()
                    break
                except Exception:
                    continue

        print(f"[Activity Log] User '{user_email}' saved {saved_count} records for book '{book_name}' at {time_formatted}")
        return True
    except Exception as e:
        print(f"[Activity Log Error] {e}")
        return False


def get_user_save_activities(timeframe="all", search=""):
    """Retrieves all logged user save activities sorted chronologically descending, with optional timeframe/search."""
    logs = []
    if SAVE_ACTIVITY_FILE.exists():
        try:
            with open(SAVE_ACTIVITY_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            print(f"[Error reading activity logs] {e}")
            logs = []

    filtered = filter_by_timeframe(logs, timeframe=timeframe, date_field="created_at")

    if search and str(search).strip():
        q = str(search).strip().lower()
        filtered = [
            e for e in filtered
            if q in str(e.get("user_email", "")).lower()
            or q in str(e.get("book_name", "")).lower()
            or q in str(e.get("book_id", "")).lower()
            or q in str(e.get("created_at_formatted", "")).lower()
        ]

    return filtered


def delete_user_save_activity(activity_id):
    """Deletes a specific user save activity log entry by ID."""
    logs = []
    if SAVE_ACTIVITY_FILE.exists():
        try:
            with open(SAVE_ACTIVITY_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    new_logs = [entry for entry in logs if str(entry.get("id")) != str(activity_id)]
    if len(new_logs) == len(logs):
        return False
    try:
        with open(SAVE_ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_logs, f, indent=2, ensure_ascii=False)
        
        # Also attempt to delete from Supabase if table exists
        client, error = get_supabase_client()
        if client and not error:
            for tbl in ["save_activity_logs", "user_activity_logs", "activity_logs"]:
                try:
                    client.table(tbl).delete().eq("id", activity_id).execute()
                    break
                except Exception:
                    continue
        return True
    except Exception as e:
        print(f"[Delete Activity Log Error] {e}")
        return False


def clear_all_user_save_activities():
    """Clears all user save activity logs."""
    try:
        with open(SAVE_ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        
        # Also attempt to clear Supabase table if exists
        client, error = get_supabase_client()
        if client and not error:
            for tbl in ["save_activity_logs", "user_activity_logs", "activity_logs"]:
                try:
                    client.table(tbl).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                    break
                except Exception:
                    continue
        return True
    except Exception as e:
        print(f"[Clear Activities Error] {e}")
        return False





# =========================================================
# USER CREDITS & CREDIT REQUEST MANAGEMENT SYSTEM
# =========================================================

USER_CREDITS_FILE = OUTPUT_DIR / "user_credits.json"
CREDIT_REQUESTS_FILE = OUTPUT_DIR / "credit_requests.json"
DEFAULT_INITIAL_USER_CREDITS = 100.0  # Default initial credit for non-admin users


def get_user_credits_data(user_id=None, email=None, role="user"):
    """
    Retrieves credit balance and statistics for a specific user.
    Admins are recognized as unlimited.
    """
    user_id_str = str(user_id or "").strip()
    email_str = str(email or "").strip().lower()
    
    data = {}
    if USER_CREDITS_FILE.exists():
        try:
            with open(USER_CREDITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    key = user_id_str if user_id_str else email_str
    if not key:
        return {
            "user_id": "",
            "email": "",
            "credits": 0.0,
            "total_allocated": 0.0,
            "total_used": 0.0,
            "role": role,
            "is_admin": (role == "admin")
        }

    record = data.get(key)
    if not record and email_str:
        for k, v in data.items():
            if str(v.get("email", "")).lower() == email_str:
                record = v
                key = k
                break

    is_admin = (role == "admin")
    if not record:
        init_credits = 999999.0 if is_admin else DEFAULT_INITIAL_USER_CREDITS
        record = {
            "user_id": user_id_str,
            "email": email_str,
            "credits": init_credits,
            "total_allocated": init_credits,
            "total_used": 0.0,
            "role": role,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        data[key] = record
        try:
            with open(USER_CREDITS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[User Credit Save Warning] {e}")

    record["is_admin"] = is_admin
    return record


def deduct_user_credits(user_id, amount, email=None, role="user"):
    """
    Deducts credits upon extraction.
    Admin users bypass credit limits and are not deducted.
    """
    if role == "admin":
        return True, 999999.0

    user_id_str = str(user_id or "").strip()
    email_str = str(email or "").strip().lower()
    key = user_id_str if user_id_str else email_str
    if not key:
        return False, 0.0

    data = {}
    if USER_CREDITS_FILE.exists():
        try:
            with open(USER_CREDITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    record = data.get(key)
    if not record and email_str:
        for k, v in data.items():
            if str(v.get("email", "")).lower() == email_str:
                record = v
                key = k
                break

    if not record:
        record = {
            "user_id": user_id_str,
            "email": email_str,
            "credits": DEFAULT_INITIAL_USER_CREDITS,
            "total_allocated": DEFAULT_INITIAL_USER_CREDITS,
            "total_used": 0.0,
            "role": role,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    amt = float(amount or 0.0)
    current_cr = float(record.get("credits", 0.0))
    new_cr = max(0.0, round(current_cr - amt, 2))
    record["credits"] = new_cr
    record["total_used"] = round(float(record.get("total_used", 0.0)) + amt, 2)
    record["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if email_str:
        record["email"] = email_str

    data[key] = record
    try:
        with open(USER_CREDITS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Deduct Credits Error] {e}")

    return True, new_cr


def add_user_credits(user_id, amount, email=None):
    """
    Admin adds / allocates credits to a user balance.
    """
    user_id_str = str(user_id or "").strip()
    email_str = str(email or "").strip().lower()
    key = user_id_str if user_id_str else email_str
    if not key:
        return False, 0.0, "User identifier missing."

    data = {}
    if USER_CREDITS_FILE.exists():
        try:
            with open(USER_CREDITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    record = data.get(key)
    if not record and email_str:
        for k, v in data.items():
            if str(v.get("email", "")).lower() == email_str:
                record = v
                key = k
                break

    amt = float(amount or 0.0)
    if not record:
        record = {
            "user_id": user_id_str,
            "email": email_str,
            "credits": amt,
            "total_allocated": amt,
            "total_used": 0.0,
            "role": "user",
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        record["credits"] = round(float(record.get("credits", 0.0)) + amt, 2)
        record["total_allocated"] = round(float(record.get("total_allocated", 0.0)) + amt, 2)
        record["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if email_str:
            record["email"] = email_str

    data[key] = record
    try:
        with open(USER_CREDITS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return False, 0.0, str(e)

    return True, record["credits"], "Credits added successfully."


def create_credit_request(user_id, user_email, requested_amount, reason=""):
    """
    Creates a new user credit request sent to Admin for approval.
    """
    try:
        reqs = []
        if CREDIT_REQUESTS_FILE.exists():
            try:
                with open(CREDIT_REQUESTS_FILE, "r", encoding="utf-8") as f:
                    reqs = json.load(f)
            except Exception:
                reqs = []

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        req_id = uuid.uuid4().hex[:12]
        
        user_data = get_user_credits_data(user_id=user_id, email=user_email)
        curr_credits = user_data.get("credits", 0.0)

        new_req = {
            "id": req_id,
            "user_id": str(user_id or ""),
            "user_email": str(user_email or ""),
            "requested_amount": float(requested_amount or 50.0),
            "current_balance": float(curr_credits),
            "reason": str(reason or "").strip(),
            "status": "pending",
            "created_at": now_str,
            "approved_amount": 0.0,
            "resolved_at": None
        }

        reqs.insert(0, new_req)
        with open(CREDIT_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reqs, f, indent=2, ensure_ascii=False)

        return True, new_req, "Credit request submitted successfully."
    except Exception as e:
        return False, None, str(e)


def get_all_credit_requests(status_filter="all"):
    """
    Retrieves all credit requests with optional status filter.
    """
    reqs = []
    if CREDIT_REQUESTS_FILE.exists():
        try:
            with open(CREDIT_REQUESTS_FILE, "r", encoding="utf-8") as f:
                reqs = json.load(f)
        except Exception:
            reqs = []

    if status_filter and status_filter != "all":
        reqs = [r for r in reqs if str(r.get("status", "")).lower() == status_filter.lower()]

    return reqs


def approve_credit_request(req_id, approved_amount=None):
    """
    Admin approves a credit request, crediting the user balance immediately.
    """
    reqs = []
    if CREDIT_REQUESTS_FILE.exists():
        try:
            with open(CREDIT_REQUESTS_FILE, "r", encoding="utf-8") as f:
                reqs = json.load(f)
        except Exception:
            reqs = []

    target_req = None
    for r in reqs:
        if str(r.get("id")) == str(req_id):
            target_req = r
            break

    if not target_req:
        return False, "Credit request not found."

    if target_req.get("status") == "approved":
        return False, "This request has already been approved."

    amt = float(approved_amount if approved_amount is not None else target_req.get("requested_amount", 50.0))
    u_id = target_req.get("user_id")
    u_email = target_req.get("user_email")

    succ, new_bal, msg = add_user_credits(user_id=u_id, amount=amt, email=u_email)
    if not succ:
        return False, f"Failed to add credits: {msg}"

    target_req["status"] = "approved"
    target_req["approved_amount"] = amt
    target_req["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(CREDIT_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reqs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Approve Request Save Error] {e}")

    return True, f"Successfully approved {amt:.2f} credits for {u_email}. New balance: {new_bal:.2f} cr."


def reject_credit_request(req_id, reason=""):
    """
    Admin rejects a credit request.
    """
    reqs = []
    if CREDIT_REQUESTS_FILE.exists():
        try:
            with open(CREDIT_REQUESTS_FILE, "r", encoding="utf-8") as f:
                reqs = json.load(f)
        except Exception:
            reqs = []

    target_req = None
    for r in reqs:
        if str(r.get("id")) == str(req_id):
            target_req = r
            break

    if not target_req:
        return False, "Credit request not found."

    target_req["status"] = "rejected"
    target_req["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    target_req["reject_reason"] = reason

    try:
        with open(CREDIT_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reqs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return False, str(e)

    return True, "Credit request rejected."


def delete_credit_request(req_id):
    """
    Admin deletes a credit request record.
    """
    reqs = []
    if CREDIT_REQUESTS_FILE.exists():
        try:
            with open(CREDIT_REQUESTS_FILE, "r", encoding="utf-8") as f:
                reqs = json.load(f)
        except Exception:
            reqs = []

    new_reqs = [r for r in reqs if str(r.get("id")) != str(req_id)]
    if len(new_reqs) == len(reqs):
        return False

    try:
        with open(CREDIT_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(new_reqs, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        return False


# =========================================================
# USER CREDITS & ADMIN CREDIT REQUEST ROUTES
# =========================================================

@app.route("/api/user-credits", methods=["GET"])
@login_required
def api_get_user_credits():
    """
    Returns current user's credit balance and usage stats.
    """
    try:
        user_id = session.get("user_id")
        user_email = session.get("email")
        user_role = session.get("role", "user")
        cdata = get_user_credits_data(user_id=user_id, email=user_email, role=user_role)
        return jsonify({"success": True, **cdata})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/request-credits", methods=["POST"])
@login_required
def api_request_credits():
    """
    Allows a standard user to submit a credit request to Admin.
    """
    try:
        user_id = session.get("user_id")
        user_email = session.get("email")
        payload = request.get_json(silent=True) or {}
        requested_amount = float(payload.get("requested_credits", payload.get("amount", 100)))
        reason = str(payload.get("reason", "")).strip()

        if requested_amount <= 0:
            return jsonify({"success": False, "error": "Requested credit amount must be greater than 0."}), 400

        succ, req_obj, msg = create_credit_request(
            user_id=user_id,
            user_email=user_email,
            requested_amount=requested_amount,
            reason=reason
        )
        if not succ:
            return jsonify({"success": False, "error": msg}), 400

        return jsonify({
            "success": True,
            "message": "Aapki credit request admin ko bhej di gayi hai. Approval ke baad credits add ho jayenge.",
            "request": req_obj
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-requests", methods=["GET"])
@admin_required
def admin_get_credit_requests():
    """
    Lists credit requests with filter (all, pending, approved, rejected).
    """
    try:
        status_filter = str(request.args.get("status", "all")).strip().lower()
        reqs = get_all_credit_requests(status_filter=status_filter)
        
        # Count pending
        all_reqs = get_all_credit_requests("all")
        pending_count = sum(1 for r in all_reqs if str(r.get("status", "")).lower() == "pending")

        # Attach live user balance to each request
        for r in reqs:
            uid = r.get("user_id")
            uemail = r.get("user_email")
            cdata = get_user_credits_data(user_id=uid, email=uemail)
            r["current_credits"] = cdata.get("credits", 0.0)

        return jsonify({
            "success": True,
            "requests": reqs,
            "pending_count": pending_count,
            "filter": status_filter
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-requests/<req_id>/approve", methods=["POST"])
@admin_required
def admin_approve_credit_req(req_id):
    """
    Approves a user credit request and allocates credits.
    """
    try:
        payload = request.get_json(silent=True) or {}
        approved_amount = payload.get("approved_credits", payload.get("amount"))
        if approved_amount is not None:
            approved_amount = float(approved_amount)
            if approved_amount <= 0:
                return jsonify({"success": False, "error": "Approved amount must be greater than 0."}), 400

        succ, msg = approve_credit_request(req_id, approved_amount=approved_amount)
        if not succ:
            return jsonify({"success": False, "error": msg}), 400

        # Fetch updated request for response
        reqs = get_all_credit_requests("all")
        matched = next((r for r in reqs if str(r.get("id")) == str(req_id)), None)
        new_bal = 0.0
        if matched:
            cdata = get_user_credits_data(user_id=matched.get("user_id"), email=matched.get("user_email"))
            new_bal = cdata.get("credits", 0.0)

        return jsonify({
            "success": True,
            "message": msg,
            "new_balance": new_bal
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-requests/<req_id>/reject", methods=["POST"])
@admin_required
def admin_reject_credit_req(req_id):
    """
    Rejects a user credit request.
    """
    try:
        payload = request.get_json(silent=True) or {}
        reason = str(payload.get("reason", "")).strip()
        succ, msg = reject_credit_request(req_id, reason=reason)
        if not succ:
            return jsonify({"success": False, "error": msg}), 400

        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-requests/<req_id>/delete", methods=["POST"])
@admin_required
def admin_delete_credit_req(req_id):
    """
    Deletes a credit request record.
    """
    try:
        succ = delete_credit_request(req_id)
        if not succ:
            return jsonify({"success": False, "error": "Credit request record not found or could not be deleted."}), 404

        return jsonify({"success": True, "message": "Credit request record deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/users/<user_id>/add-credits", methods=["POST"])
@admin_required
def admin_add_user_credits_route(user_id):
    """
    Direct credit allocation from Admin to a specific user.
    """
    try:
        payload = request.get_json(silent=True) or {}
        credits_to_add = float(payload.get("credits_to_add", payload.get("amount", 0)))
        if credits_to_add <= 0:
            return jsonify({"success": False, "error": "Credit amount must be greater than 0."}), 400

        # Look up email from Supabase if possible
        email = None
        client, err = get_supabase_client()
        if not err and client:
            try:
                ures = client.table("users").select("email").eq("id", user_id).limit(1).execute()
                if ures.data and len(ures.data) > 0:
                    email = ures.data[0].get("email")
            except Exception:
                pass

        succ, new_bal, msg = add_user_credits(user_id=user_id, amount=credits_to_add, email=email)
        if not succ:
            return jsonify({"success": False, "error": msg}), 400

        return jsonify({
            "success": True,
            "message": f"Successfully added {credits_to_add:.2f} credits.",
            "new_balance": new_bal
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("ecom_dashboard") if session.get("role") == "admin" else url_for("index"))
        return render_template("login.html")

    email = str(request.form.get("email", "")).strip().lower()
    password = str(request.form.get("password", "")).strip()

    if not email or not password:
        return render_template("login.html", error="Email aur password enter karein.")

    client, err = get_supabase_client()
    if err:
        return render_template("login.html", error=f"Database connection error: {err}")

    try:
        auth_response = client.auth.sign_in_with_password({"email": email, "password": password})
        if not auth_response.user:
            return render_template("login.html", error="Invalid login credentials.")

        user_id = auth_response.user.id

        # Sync profile with public.users
        user_res = client.table("users").select("id, email, role, approved").eq("id", user_id).limit(1).execute()
        if user_res.data and len(user_res.data) > 0:
            profile = user_res.data[0]
            role = profile.get("role", "user")
            approved = bool(profile.get("approved", False))
        else:
            # Check if this is the first user in system
            all_users = client.table("users").select("id", count="exact").execute()
            count = all_users.count or len(all_users.data or [])
            role = "admin" if count == 0 else "user"
            approved = True if role == "admin" else False

            client.table("users").insert({
                "id": user_id,
                "email": email,
                "role": role,
                "approved": approved
            }).execute()

        session["user_id"] = user_id
        session["email"] = email
        session["role"] = role
        session["approved"] = approved

        flash(f"Welcome back, {email}!", "success")
        return redirect(url_for("ecom_dashboard") if role == "admin" else url_for("index"))

    except Exception as e:
        err_msg = str(e)
        if "Invalid login credentials" in err_msg:
            err_msg = "Invalid email or password."
        return render_template("login.html", error=err_msg)


@app.route("/signup", methods=["GET", "POST"])
def signup_route():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("index"))
        return render_template("signup.html")

    email = str(request.form.get("email", "")).strip().lower()
    password = str(request.form.get("password", "")).strip()

    if not email or not password:
        return render_template("signup.html", error="Email aur password enter karein.")

    if len(password) < 6:
        return render_template("signup.html", error="Password kam az kam 6 characters ka hona chahiye.")

    client, err = get_supabase_client()
    if err:
        return render_template("signup.html", error=f"Database connection error: {err}")

    try:
        auth_response = client.auth.sign_up({"email": email, "password": password})
        if not auth_response.user:
            return render_template("signup.html", error="Registration fail ho gayi.")

        user_id = auth_response.user.id

        # Determine role and approval
        all_users = client.table("users").select("id", count="exact").execute()
        count = all_users.count or len(all_users.data or [])
        role = "admin" if count == 0 else "user"
        approved = True if role == "admin" else False

        client.table("users").insert({
            "id": user_id,
            "email": email,
            "role": role,
            "approved": approved
        }).execute()

        session["user_id"] = user_id
        session["email"] = email
        session["role"] = role
        session["approved"] = approved

        if not approved:
            flash("Account successfully create ho gaya! Admin approval ke baad aap database mein save kar sakein ge.", "info")
            return redirect(url_for("index"))

        flash("Admin account create ho gaya!", "success")
        return redirect(url_for("ecom_dashboard"))

    except Exception as e:
        return render_template("signup.html", error=f"Signup error: {str(e)}")


@app.route("/logout")
def logout_route():
    session.clear()
    flash("Aap successfully logout ho gaye hain.", "info")
    return redirect(url_for("login_route"))


# =========================================================
# APPLICATION CORE ROUTES
# =========================================================

@app.route("/")
@login_required
def index():
    profile = get_current_user_profile()
    return render_template(
        "index.html",
        current_user_email=session.get("email", ""),
        current_user_role=profile.get("role", "user") if profile else "user",
        current_user_approved=profile.get("approved", False) if profile else False
    )


def extract_landingai_billing_info(response_obj):
    """Extracts job_id, credit_usage / total_credits, duration_ms, and page_count from LandingAI ADE response."""
    if not response_obj:
        return {}
    meta = getattr(response_obj, "metadata", None)
    if not meta:
        return {}
    
    # 1. Direct attribute access (Pydantic models / objects)
    credit_usage = getattr(meta, "credit_usage", None)
    if credit_usage is None:
        billing = getattr(meta, "billing", None)
        if billing:
            if isinstance(billing, dict):
                credit_usage = billing.get("total_credits") or billing.get("credits")
            else:
                credit_usage = getattr(billing, "total_credits", getattr(billing, "credits", None))
    
    job_id = getattr(meta, "job_id", "")
    duration_ms = getattr(meta, "duration_ms", 0)
    page_count = getattr(meta, "page_count", 0)
    failed_pages = getattr(meta, "failed_pages", [])

    # 2. Dictionary / model_dump fallback if meta is dict
    if isinstance(meta, dict):
        if credit_usage is None:
            credit_usage = meta.get("credit_usage")
        if credit_usage is None and "billing" in meta:
            b = meta["billing"]
            if isinstance(b, dict):
                credit_usage = b.get("total_credits") or b.get("credits")
        job_id = job_id or meta.get("job_id", "")
        duration_ms = duration_ms or meta.get("duration_ms", 0)
        page_count = page_count or meta.get("page_count", 0)
        failed_pages = failed_pages or meta.get("failed_pages", [])

    try:
        credit_val = float(credit_usage) if credit_usage is not None else 0.0
    except (ValueError, TypeError):
        credit_val = 0.0

    return {
        "job_id": str(job_id or ""),
        "credit_usage": credit_val,
        "duration_ms": int(duration_ms or 0),
        "page_count": int(page_count or 0),
        "failed_pages": failed_pages or []
    }


def download_pdf_from_gdrive(drive_url: str, output_path: Path) -> tuple[bool, str, str]:
    """
    Downloads a PDF document from a shared or public Google Drive link.
    Supports gdown and direct requests fallbacks.
    Returns (success: bool, display_name: str, error_message: str).
    """
    if not drive_url or not str(drive_url).strip():
        return False, "", "Google Drive link provide karein."

    drive_url = str(drive_url).strip()

    # Extract file ID from different Google Drive URL formats
    file_id = None
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", drive_url)
    if m:
        file_id = m.group(1)
    if not file_id:
        m2 = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", drive_url)
        if m2:
            file_id = m2.group(1)
    if not file_id and re.match(r"^[a-zA-Z0-9_-]{20,}$", drive_url):
        file_id = drive_url

    if not file_id:
        return False, "", "Invalid Google Drive link. Please provide a valid file share URL (e.g. https://drive.google.com/file/d/.../view)."

    display_name = f"Google_Drive_{file_id[:8]}.pdf"

    # 1. Attempt download using gdown
    try:
        import gdown
        download_url = f"https://drive.google.com/uc?id={file_id}"
        out = gdown.download(download_url, str(output_path), quiet=True, fuzzy=True)
        if out and output_path.exists() and output_path.stat().st_size > 0:
            with open(output_path, "rb") as f:
                header = f.read(5)
                if header.startswith(b"%PDF"):
                    return True, display_name, ""
    except Exception as g_err:
        print(f"[gdown warning]: {g_err}")

    # 2. Fallback: direct requests stream
    try:
        session = requests.Session()
        direct_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t"
        resp = session.get(direct_url, stream=True, timeout=60, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
            if output_path.exists() and output_path.stat().st_size > 0:
                with open(output_path, "rb") as f:
                    header = f.read(5)
                    if header.startswith(b"%PDF"):
                        return True, display_name, ""
    except Exception as req_err:
        print(f"[requests direct warning]: {req_err}")

    # 3. Fallback: uc export with confirmation cookie
    try:
        session = requests.Session()
        uc_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = session.get(uc_url, stream=True, timeout=60)
        token = None
        for k, v in resp.cookies.items():
            if k.startswith("download_warning"):
                token = v
                break
        if token:
            resp = session.get(f"{uc_url}&confirm={token}", stream=True, timeout=60)

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)

        if output_path.exists() and output_path.stat().st_size > 0:
            with open(output_path, "rb") as f:
                header = f.read(5)
                if header.startswith(b"%PDF"):
                    return True, display_name, ""
    except Exception as req_err2:
        print(f"[requests uc warning]: {req_err2}")

    return False, "", "Could not download file from Google Drive. Please ensure the Google Drive file permission is set to 'Anyone with the link can view' and is a valid PDF document."


def split_pdf_if_needed(pdf_path: Path, max_bytes=25 * 1024 * 1024) -> list[Path]:
    """
    Checks if PDF file size exceeds LandingAI ADE 50 MiB single-file limit or contains stream errors.
    Uses PyMuPDF (fitz) to repair, sanitize, deflate streams, and split large PDFs safely into clean <=25MB chunks.
    """
    try:
        import pymupdf

        file_size = pdf_path.stat().st_size
        src_doc = pymupdf.open(str(pdf_path))
        total_pages = len(src_doc)

        if total_pages <= 1:
            src_doc.close()
            return [pdf_path]

        # If file is already small enough, no splitting needed
        if file_size <= max_bytes:
            src_doc.close()
            return [pdf_path]

        num_chunks = max(2, int((file_size / max_bytes) + 1.5))
        pages_per_chunk = max(1, total_pages // num_chunks)

        chunk_paths = []
        chunk_start = 0
        part_num = 1

        while chunk_start < total_pages:
            chunk_end = min(total_pages, chunk_start + pages_per_chunk)

            chunk_doc = pymupdf.open()
            chunk_doc.insert_pdf(src_doc, from_page=chunk_start, to_page=chunk_end - 1)

            chunk_file = pdf_path.parent / f"{pdf_path.stem}_part{part_num}.pdf"
            # deflate=True, garbage=4, clean=True sanitizes xrefs and removes any truncated stream issues
            chunk_doc.save(str(chunk_file), deflate=True, garbage=4, clean=True)
            chunk_doc.close()

            generated_size = chunk_file.stat().st_size
            if generated_size > 35 * 1024 * 1024 and (chunk_end - chunk_start) > 1:
                # If still large, halve pages for this partition
                pages_per_chunk = max(1, (chunk_end - chunk_start) // 2)
                try:
                    chunk_file.unlink()
                except Exception:
                    pass
                continue

            chunk_paths.append(chunk_file)
            part_num += 1
            chunk_start = chunk_end

        src_doc.close()
        print(f"\n[Auto PDF Splitter] PDF '{pdf_path.name}' ({file_size / (1024*1024):.1f} MB) repaired & partitioned into {len(chunk_paths)} sub-files ({pages_per_chunk} pages avg).\n")
        return chunk_paths

    except Exception as e:
        print(f"[PyMuPDF Splitter Warning] PyMuPDF failed: {e}. Trying pypdf fallback...")
        try:
            from pypdf import PdfReader, PdfWriter
            reader = PdfReader(str(pdf_path), strict=False)
            total_pages = len(reader.pages)
            if total_pages <= 1:
                return [pdf_path]

            num_chunks = max(2, int((pdf_path.stat().st_size / max_bytes) + 1.5))
            pages_per_chunk = max(1, total_pages // num_chunks)

            chunk_paths = []
            for chunk_start in range(0, total_pages, pages_per_chunk):
                writer = PdfWriter()
                chunk_end = min(total_pages, chunk_start + pages_per_chunk)
                for page_num in range(chunk_start, chunk_end):
                    writer.add_page(reader.pages[page_num])

                chunk_file = pdf_path.parent / f"{pdf_path.stem}_part{len(chunk_paths)+1}.pdf"
                with open(chunk_file, "wb") as f_out:
                    writer.write(f_out)
                chunk_paths.append(chunk_file)
            return chunk_paths
        except Exception as pypdf_err:
            print(f"[PDF Splitter Warning] Fallback also failed: {pypdf_err}")
            return [pdf_path]


def process_pdf_with_mistral(pdf_path: Path, book_id: str, book_name: str, display_filename: str, country: str = "General"):
    """
    Parses and extracts structured exhibitor records from PDF using Mistral OCR (mistral-ocr-latest)
    and structures with Ministral LLM & normalization cleaners.
    """
    api_key = os.getenv("MISTRAL_API_KEY", "jbUWvBlLucUQxVO8uydfPdJxEjUgXzvD")
    model = os.getenv("MISTRAL_MODEL", "mistral-ocr-latest")
    country = str(country or "").strip() or "General"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "document": {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64_pdf}"
        }
    }

    t0 = time.time()
    resp = requests.post("https://api.mistral.ai/v1/ocr", headers=headers, json=payload, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f"Mistral OCR API Error ({resp.status_code}): {resp.text}")

    ocr_data = resp.json()
    pages = ocr_data.get("pages", [])
    pages_processed = len(pages)

    all_raw_records = []
    all_source_markdown = []

    for p_idx, page in enumerate(pages):
        page_md = page.get("markdown", "").strip()
        if not page_md:
            continue
        all_source_markdown.append(f"<!-- Page {p_idx+1} -->\n{page_md}")

        system_prompt = """You are an expert document OCR schema extractor.
Extract all company exhibitors from the document markdown into valid JSON following this format:
{
  "exhibitors": [
    {
      "name": "Company Name",
      "address": "Full physical or mailing address",
      "tel": "Telephone or mobile number",
      "email": "Official email address",
      "website": "Website URL",
      "fax": "Fax number if present",
      "category": "Actual English section/category heading from the page margin, vertical sidebar, or header (e.g. 'Large Machinery & Equipment'). Do NOT include Chinese characters. All exhibitors on the page share this vertical category heading."
    }
  ]
}
Look specifically for the vertical margin banner or sidebar on the right/left edge of the page that indicates the industry category (e.g. 'Large Machinery & Equipment'). Assign this category to every exhibitor under that section until a new vertical heading begins.
Return ONLY valid JSON."""

        chat_payload = {
            "model": "ministral-8b-latest",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Document Markdown Page {p_idx+1}:\n{page_md}"}
            ],
            "temperature": 0.0
        }

        page_cat = extract_margin_category_from_markdown(page_md)
        try:
            c_resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=chat_payload, timeout=60)
            if c_resp.status_code == 200:
                c_json = c_resp.json()
                content = c_json["choices"][0]["message"]["content"]
                extracted_data = json.loads(content)
                cleaned = clean_exhibitors(extracted_data)
                for c_rec in cleaned:
                    c_rec["page_number"] = p_idx + 1
                    c_rec["country"] = country
                    if not c_rec.get("category") and page_cat:
                        c_rec["category"] = page_cat
                all_raw_records.extend(cleaned)
        except Exception as e:
            print(f"[Mistral Page {p_idx+1}] Extraction warning: {e}")

    records = remove_duplicates(all_raw_records)
    if not records:
        return jsonify({"success": False, "error": "Koi exhibitor data extract nahi hua Mistral OCR se."}), 422

    source_text = "\n\n".join(all_source_markdown)
    records = assign_categories_from_source(records, source_text)

    reset_metrics_stats()
    complete_count = 0
    incomplete_count = 0
    needs_review_count = 0
    rate_limited_count = 0

    for r in records:
        name = str(r.get("name", "")).strip()
        address = str(r.get("address", "")).strip()
        tel = str(r.get("tel", "")).strip()
        email = str(r.get("email", "")).strip()
        website = str(r.get("website", "")).strip()

        has_email = bool(email)
        has_tel = bool(tel)

        if has_email and has_tel:
            complete_count += 1
            r["web_suggestions"] = {}
            r["verification_status"] = "verified"
        else:
            incomplete_count += 1
            web_cands = extract_web_candidates_for_company(name, address, existing_record=r)
            r["web_suggestions"] = web_cands if web_cands else {}

            has_rate_limit = any(v.get("rate_limited") for v in (r["web_suggestions"] or {}).values())
            has_suggestions = any(v.get("value") for v in (r["web_suggestions"] or {}).values())

            if has_rate_limit:
                r["verification_status"] = "rate_limited"
                rate_limited_count += 1
            elif has_suggestions:
                r["verification_status"] = "needs_verification"
                needs_review_count += 1
            else:
                r["verification_status"] = "verified"

        r["book_id"] = book_id
        r["book_name"] = book_name
        r["country"] = country

    metrics = get_metrics_stats()
    metrics["total_extracted"] = len(records)
    metrics["complete_from_pdf"] = complete_count
    metrics["needing_enrichment"] = incomplete_count
    metrics["needs_review"] = needs_review_count
    metrics["rate_limited_records"] = rate_limited_count
    metrics["llm_batches_before_optimization"] = 0
    metrics["llm_calls_after_optimization"] = 0

    excel_name = f"exhibitors_{uuid.uuid4().hex}.xlsx"
    excel_path = OUTPUT_DIR / excel_name
    save_excel(records, excel_path)

    user_id = session.get("user_id", "anonymous") if session else "anonymous"
    user_email = session.get("email", "anonymous@user.com") if session else "anonymous@user.com"
    user_role = session.get("role", "user") if session else "user"
    tot_duration = int((time.time() - t0) * 1000)

    # Deduct user credits (1 credit per processed page for Mistral OCR)
    mistral_credits_used = max(1.0, float(pages_processed))
    deduct_user_credits(user_id, mistral_credits_used, email=user_email, role=user_role)
    user_credit_info = get_user_credits_data(user_id=user_id, email=user_email, role=user_role)

    log_extraction_credit_activity(
        user_id=user_id,
        user_email=user_email,
        book_id=book_id,
        book_name=book_name,
        filename=display_filename,
        pages_processed=pages_processed,
        parse_credits=0.0,
        extract_credits=0.0,
        total_credits=0.0,
        records_extracted=len(records),
        duration_ms=tot_duration,
        parse_job_id="mistral-ocr-latest",
        extract_job_ids=["ministral-8b-latest"],
        engine="Mistral OCR",
        model="mistral-ocr-latest"
    )

    return jsonify({
        "success": True,
        "message": "Mistral OCR extraction complete. Preview ready.",
        "engine": "mistral",
        "engine_label": "Mistral OCR (mistral-ocr-latest)",
        "book_id": book_id,
        "book_name": book_name,
        "country": country,
        "total": len(records),
        "download_url": f"/download/{excel_name}",
        "source_markdown": source_text,
        "landingai_billing": {
            "total_credits": 0.0,
            "parse_credits": 0.0,
            "extract_credits": 0.0,
            "page_count": pages_processed,
            "parse_job_id": "mistral-ocr-latest",
            "extract_jobs": []
        },
        "user_credits": {
            "remaining": user_credit_info.get("credits", 0.0) if user_role != "admin" else "Unlimited",
            "deducted": mistral_credits_used if user_role != "admin" else 0.0,
            "is_admin": (user_role == "admin")
        },
        "metrics": metrics,
        "data": records
    })


def process_pdf_document(pdf_path: Path, book_id: str, book_name: str, display_filename: str, engine: str = "landingai", country: str = "General"):
    """
    Core engine for parsing, extracting, cross-verifying, and web-enriching exhibitor data from a PDF file.
    Supports both LandingAI ADE and Mistral OCR engines.
    """
    country = str(country or "").strip() or "General"
    if str(engine).lower() == "mistral":
        return process_pdf_with_mistral(pdf_path, book_id, book_name, display_filename, country=country)
    landingai_client = get_landingai_client()

    pdf_chunks = split_pdf_if_needed(pdf_path)

    parse_billings = []
    extract_billings = []
    all_raw_records = []
    all_source_markdown = []
    page_counter = 0

    for c_idx, chunk_file in enumerate(pdf_chunks):
        if len(pdf_chunks) > 1:
            print(f"[LandingAI Processing] Processing Part {c_idx+1}/{len(pdf_chunks)} ({chunk_file.name})...")

        # Step 1: Parse chunk
        parse_response = landingai_client.parse(document=chunk_file, model="dpt-2-latest")
        p_bill = extract_landingai_billing_info(parse_response)
        if p_bill:
            parse_billings.append(p_bill)

        # Step 2: Extract from chunk
        splits = getattr(parse_response, "splits", None)
        if splits and len(splits) > 0:
            for split in splits:
                page_counter += 1
                markdown = getattr(split, "markdown", "")
                if not markdown or not markdown.strip():
                    continue
                all_source_markdown.append(f"<!-- Page {page_counter} -->\n{markdown}")
                try:
                    extract_response = landingai_client.extract(
                        schema=json.dumps(EXTRACTION_SCHEMA),
                        markdown=markdown,
                        model="extract-latest"
                    )
                    ext_bill = extract_landingai_billing_info(extract_response)
                    if ext_bill:
                        extract_billings.append(ext_bill)
                    extraction = getattr(extract_response, "extraction", None)
                    split_records = clean_exhibitors(extraction)
                    page_cat = extract_margin_category_from_markdown(markdown)
                    for s_rec in split_records:
                        s_rec["page_number"] = page_counter
                        s_rec["country"] = country
                        if not s_rec.get("category") and page_cat:
                            s_rec["category"] = page_cat
                    all_raw_records.extend(split_records)
                except Exception as e:
                    print(f"Extraction section warning: {e}")
        else:
            page_counter += 1
            markdown = getattr(parse_response, "markdown", "")
            if markdown:
                all_source_markdown.append(f"<!-- Page {page_counter} -->\n{markdown}")
            extract_response = landingai_client.extract(
                schema=json.dumps(EXTRACTION_SCHEMA),
                markdown=markdown,
                model="extract-latest"
            )
            ext_bill = extract_landingai_billing_info(extract_response)
            if ext_bill:
                extract_billings.append(ext_bill)
            extraction = getattr(extract_response, "extraction", None)
            raw_cleaned = clean_exhibitors(extraction)
            page_cat = extract_margin_category_from_markdown(markdown)
            for r_rec in raw_cleaned:
                r_rec["page_number"] = page_counter
                r_rec["country"] = country
                if not r_rec.get("category") and page_cat:
                    r_rec["category"] = page_cat
            all_raw_records.extend(raw_cleaned)

        # Clean temporary chunk file if it was created
        if chunk_file != pdf_path:
            try:
                if chunk_file.exists():
                    chunk_file.unlink()
            except Exception:
                pass

    total_parse_credits = sum(b.get("credit_usage", 0.0) for b in parse_billings)
    total_extract_credits = sum(b.get("credit_usage", 0.0) for b in extract_billings)
    total_credits = total_parse_credits + total_extract_credits
    pages_processed = sum(b.get("page_count", 0) for b in parse_billings)

    print("\n" + "=" * 65)
    print("      LANDINGAI ADE BILLING & ACTUAL CREDIT USAGE REPORT")
    print("=" * 65)
    print(f"  File Name         : {display_filename}")
    print(f"  Pages Processed   : {pages_processed}")
    for idx, pb in enumerate(parse_billings):
        print(f"  Parse #{idx+1} Job ID  : {pb.get('job_id')} | Credits: {pb.get('credit_usage', 0.0):.2f} ({pb.get('duration_ms', 0)} ms)")
    for idx, eb in enumerate(extract_billings):
        print(f"  Extract #{idx+1} Job ID : {eb.get('job_id')} | Credits: {eb.get('credit_usage', 0.0):.2f} ({eb.get('duration_ms', 0)} ms)")
    print("  " + "-" * 61)
    print(f"  TOTAL LANDINGAI CREDITS CONSUMED : {total_credits:.2f} credits")
    print("=" * 65 + "\n")

    # Step 3: Clean & Deduplicate
    records = remove_duplicates(all_raw_records)
    if not records:
        return jsonify({"success": False, "error": "Koi exhibitor data extract nahi hua."}), 422

    source_text = "\n\n".join(all_source_markdown)
    records = assign_categories_from_source(records, source_text)

    # Step 4: Selective Web Enrichment with Deterministic Prioritization
    reset_metrics_stats()
    complete_count = 0
    incomplete_count = 0
    needs_review_count = 0
    rate_limited_count = 0

    for r in records:
        name = str(r.get("name", "")).strip()
        address = str(r.get("address", "")).strip()
        tel = str(r.get("tel", "")).strip()
        email = str(r.get("email", "")).strip()
        website = str(r.get("website", "")).strip()

        has_email = bool(email)
        has_tel = bool(tel)

        # If both Email AND Tel are present from PDF, skip web search entirely!
        if has_email and has_tel:
            complete_count += 1
            r["web_suggestions"] = {}
            r["verification_status"] = "verified"
        else:
            incomplete_count += 1
            # Search web ONLY for records missing Email or Tel
            web_cands = extract_web_candidates_for_company(name, address, existing_record=r)
            r["web_suggestions"] = web_cands if web_cands else {}

            has_rate_limit = any(v.get("rate_limited") for v in (r["web_suggestions"] or {}).values())
            has_suggestions = any(v.get("value") for v in (r["web_suggestions"] or {}).values())

            if has_rate_limit:
                r["verification_status"] = "rate_limited"
                rate_limited_count += 1
            elif has_suggestions:
                r["verification_status"] = "needs_verification"
                needs_review_count += 1
            else:
                r["verification_status"] = "verified"

        r["book_id"] = book_id
        r["book_name"] = book_name
        r["country"] = country

    metrics = get_metrics_stats()
    metrics["total_extracted"] = len(records)
    metrics["complete_from_pdf"] = complete_count
    metrics["needing_enrichment"] = incomplete_count
    metrics["needs_review"] = needs_review_count
    metrics["rate_limited_records"] = rate_limited_count
    metrics["llm_batches_before_optimization"] = 0
    metrics["llm_calls_after_optimization"] = 0

    print("\n" + "=" * 65)
    print("       EXHIBITOR PROCESSING & PERFORMANCE METRICS")
    print("=" * 65)
    print(f"  Companies Extracted       : {len(records)}")
    print(f"  Complete from PDF         : {complete_count} (0 web searches / 0 LLM calls)")
    print(f"  Needing Web Enrichment    : {incomplete_count}")
    print(f"  Web Searches Conducted    : {metrics.get('web_searches_run', 0)}")
    print(f"  Candidates Evaluated      : {metrics.get('candidates_evaluated', 0)}")
    print(f"  Deterministic Matches     : {metrics.get('deterministic_matches', 0)} (0 LLM calls)")
    print(f"  Deterministic Rejections  : {metrics.get('deterministic_rejects', 0)} (0 LLM calls)")
    print(f"  Ambiguous LLM Calls       : {metrics.get('llm_calls_made', 0)} (Saved {max(0, metrics['llm_batches_before_optimization'] - metrics.get('llm_calls_made', 0))} LLM calls!)")
    print(f"  LLM 429 Rate Limits Hit   : {metrics.get('llm_429_hits', 0)}")
    print(f"  Rate Limited Records      : {rate_limited_count}")
    print("=" * 65 + "\n")

    # Step 5: Excel Preview Export
    excel_name = f"exhibitors_{uuid.uuid4().hex}.xlsx"
    excel_path = OUTPUT_DIR / excel_name
    save_excel(records, excel_path)

    # Log Extraction Credit Usage in Admin Audit Ledger
    user_id = session.get("user_id", "anonymous") if session else "anonymous"
    user_email = session.get("email", "anonymous@user.com") if session else "anonymous@user.com"
    user_role = session.get("role", "user") if session else "user"
    tot_duration = sum(b.get("duration_ms", 0) for b in parse_billings + extract_billings)
    first_parse_job_id = parse_billings[0].get("job_id", "") if parse_billings else ""
    ext_job_ids = [eb.get("job_id", "") for eb in extract_billings if eb.get("job_id")]

    # Deduct LandingAI credits
    landingai_credits_to_deduct = float(total_credits) if total_credits > 0 else float(pages_processed)
    deduct_user_credits(user_id, landingai_credits_to_deduct, email=user_email, role=user_role)
    user_credit_info = get_user_credits_data(user_id=user_id, email=user_email, role=user_role)

    log_extraction_credit_activity(
        user_id=user_id,
        user_email=user_email,
        book_id=book_id,
        book_name=book_name,
        filename=display_filename,
        pages_processed=pages_processed,
        parse_credits=total_parse_credits,
        extract_credits=total_extract_credits,
        total_credits=total_credits,
        records_extracted=len(records),
        duration_ms=tot_duration,
        parse_job_id=first_parse_job_id,
        extract_job_ids=ext_job_ids
    )

    # DO NOT save to Supabase automatically. Return preview only.
    return jsonify({
        "success": True,
        "message": "PDF extraction complete. Preview ready.",
        "book_id": book_id,
        "book_name": book_name,
        "country": country,
        "total": len(records),
        "download_url": f"/download/{excel_name}",
        "source_markdown": source_text,
        "landingai_billing": {
            "total_credits": round(total_credits, 2),
            "parse_credits": round(total_parse_credits, 2),
            "extract_credits": round(total_extract_credits, 2),
            "page_count": pages_processed,
            "parse_job_id": parse_billings[0].get("job_id", "") if parse_billings else "",
            "extract_jobs": extract_billings
        },
        "user_credits": {
            "remaining": user_credit_info.get("credits", 0.0) if user_role != "admin" else "Unlimited",
            "deducted": landingai_credits_to_deduct if user_role != "admin" else 0.0,
            "is_admin": (user_role == "admin")
        },
        "metrics": metrics,
        "data": records
    })



@app.route("/extract", methods=["POST"])
@login_required
def extract():
    pdf_path = None
    try:
        profile = get_current_user_profile()
        user_id = session.get("user_id", "anonymous")
        user_email = session.get("email", "")
        role = profile.get("role", "user") if profile else "user"

        if role != "admin":
            user_cr_data = get_user_credits_data(user_id=user_id, email=user_email, role=role)
            if float(user_cr_data.get("credits", 0.0)) <= 0.0:
                return jsonify({
                    "success": False,
                    "credit_exhausted": True,
                    "current_credits": 0.0,
                    "error": "Aapke paas credits khatam ho chuke hain (Balance: 0.00 cr). Kripya 'Request Credits' button daba kar Admin se mazeed credit mangwayen."
                }), 403

        if "pdf" not in request.files:
            return jsonify({"success": False, "error": "PDF file select karein."}), 400

        file = request.files["pdf"]
        if not file.filename:
            return jsonify({"success": False, "error": "PDF file select karein."}), 400

        if Path(file.filename).suffix.lower() not in ALLOWED_PDF_EXTENSIONS:
            return jsonify({"success": False, "error": "Sirf PDF files allowed hain."}), 400

        book_id = str(request.form.get("book_id", "")).strip()
        book_name = str(request.form.get("book_name", "")).strip() or Path(file.filename).stem.title()
        country = str(request.form.get("country", "")).strip() or "General"
        engine = str(request.form.get("engine", "landingai")).strip().lower()

        original_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{original_name}"
        pdf_path = UPLOAD_DIR / unique_name
        file.save(pdf_path)

        return process_pdf_document(pdf_path, book_id, book_name, file.filename, engine=engine, country=country)

    except Exception as e:
        print(f"Extract error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        try:
            if pdf_path and pdf_path.exists():
                pdf_path.unlink()
        except Exception:
            pass


@app.route("/extract-drive", methods=["POST"])
@login_required
def extract_drive():
    pdf_path = None
    try:
        profile = get_current_user_profile()
        user_id = session.get("user_id", "anonymous")
        user_email = session.get("email", "")
        role = profile.get("role", "user") if profile else "user"

        if role != "admin":
            user_cr_data = get_user_credits_data(user_id=user_id, email=user_email, role=role)
            if float(user_cr_data.get("credits", 0.0)) <= 0.0:
                return jsonify({
                    "success": False,
                    "credit_exhausted": True,
                    "current_credits": 0.0,
                    "error": "Aapke paas credits khatam ho chuke hain (Balance: 0.00 cr). Kripya 'Request Credits' button daba kar Admin se mazeed credit mangwayen."
                }), 403

        payload = request.get_json(silent=True) or request.form or {}
        drive_url = str(payload.get("drive_url", "")).strip()
        book_id = str(payload.get("book_id", "")).strip()
        book_name = str(payload.get("book_name", "")).strip()
        country = str(payload.get("country", "")).strip() or "General"
        engine = str(payload.get("engine", "landingai")).strip().lower()

        if not drive_url:
            return jsonify({"success": False, "error": "Google Drive link enter karein."}), 400
        if not book_id:
            return jsonify({"success": False, "error": "Book ID enter karein."}), 400
        if not book_name:
            book_name = "Google Drive Catalog"

        unique_name = f"gdrive_{uuid.uuid4().hex}.pdf"
        pdf_path = UPLOAD_DIR / unique_name

        success, display_name, err_msg = download_pdf_from_gdrive(drive_url, pdf_path)
        if not success:
            return jsonify({"success": False, "error": err_msg or "Google Drive se PDF download nahi ho saki."}), 400

        return process_pdf_document(pdf_path, book_id, book_name, display_name, engine=engine, country=country)

    except Exception as e:
        print(f"Google Drive Extract error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        try:
            if pdf_path and pdf_path.exists():
                pdf_path.unlink()
        except Exception:
            pass



@app.route("/upload-excel", methods=["POST"])
@login_required
def upload_excel():
    try:
        if "excel" not in request.files:
            return jsonify({"success": False, "error": "Excel/CSV file select karein."}), 400

        file = request.files["excel"]
        if not file.filename:
            return jsonify({"success": False, "error": "Excel/CSV file select karein."}), 400

        suffix = Path(file.filename).suffix.lower()
        if suffix not in ALLOWED_EXCEL_EXTENSIONS:
            return jsonify({"success": False, "error": "Sirf .xlsx, .xls ya .csv files allowed hain."}), 400

        book_id = str(request.form.get("book_id", "")).strip()
        book_name = str(request.form.get("book_name", "")).strip() or Path(file.filename).stem.title()
        country = str(request.form.get("country", "")).strip() or "General"

        records = parse_excel_records(file, file.filename)
        if not records:
            return jsonify({"success": False, "error": "File mein koi valid company records nahi mile."}), 422

        for r in records:
            r["book_id"] = book_id
            r["book_name"] = book_name
            r["country"] = country
            r["web_suggestions"] = {}
            r["verification_status"] = "verified"

        excel_name = f"exhibitors_{uuid.uuid4().hex}.xlsx"
        excel_path = OUTPUT_DIR / excel_name
        save_excel(records, excel_path)

        return jsonify({
            "success": True,
            "message": f"{len(records)} records loaded from file.",
            "book_id": book_id,
            "book_name": book_name,
            "country": country,
            "total": len(records),
            "download_url": f"/download/{excel_name}",
            "data": records
        })

    except Exception as e:
        print(f"Excel upload error: {e}")
        return jsonify({"success": False, "error": f"Excel read error: {str(e)}"}), 500


@app.route("/save-supabase", methods=["POST"])
@login_required
@approved_required
def save_supabase_route():
    try:
        payload = request.get_json(silent=True) or {}
        book_id = str(payload.get("book_id", "")).strip()
        book_name = str(payload.get("book_name", "")).strip() or "General Catalog"
        country = str(payload.get("country", "")).strip() or "General"
        year = str(payload.get("year", "")).strip() or None
        records = payload.get("records", [])

        if not book_id:
            return jsonify({"success": False, "error": "Book ID enter karein. Manual Book ID lazmi hai."}), 400

        if not records:
            return jsonify({"success": False, "error": "Save karne ke liye koi records nahi hain."}), 400

        book_success, final_book_id, final_book_name, book_msg = create_book(book_id, book_name, country=country, year=year)
        if not book_success:
            return jsonify({"success": False, "error": book_msg}), 400

        success, saved_count, message = save_supabase(records, final_book_id, country=country)
        if not success:
            return jsonify({"success": False, "error": message}), 400

        # Log User Save Activity for Admin Dashboard Audit Trail
        user_id = session.get("user_id", "unknown")
        user_email = session.get("email", "unknown@user.com")
        log_user_save_activity(user_id, user_email, final_book_id, final_book_name, saved_count)

        return jsonify({
            "success": True,
            "message": f"Catalog '{final_book_name}' [ID: {final_book_id}, Country: {country}] ke {saved_count} exhibitors database mein save ho gaye.",
            "book_id": final_book_id,
            "book_name": final_book_name,
            "country": country,
            "year": year,
            "saved_count": saved_count
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/books", methods=["GET"])
@login_required
def api_get_books():
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500
    try:
        res = client.table("books").select("id, book_name, country, year").order("uploaded_at", desc=True).execute()
        return jsonify({"success": True, "books": res.data or []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/export-excel", methods=["POST"])
@login_required
def export_excel():
    try:
        payload = request.get_json(silent=True) or {}
        records = payload.get("records", [])
        book_id = payload.get("book_id", "")
        book_name = payload.get("book_name", "")

        if not records:
            return jsonify({"success": False, "error": "Export karne ke liye koi records nahi hain."}), 400

        for r in records:
            if not r.get("book_id") and book_id:
                r["book_id"] = book_id
            if not r.get("book_name") and book_name:
                r["book_name"] = book_name

        excel_name = f"exhibitors_{uuid.uuid4().hex}.xlsx"
        excel_path = OUTPUT_DIR / excel_name
        save_excel(records, excel_path)

        return jsonify({"success": True, "download_url": f"/download/{excel_name}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/download/<filename>")
def download_excel(filename):
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        return "File not found", 404
    return send_file(file_path, as_attachment=True, download_name="exhibitors.xlsx")


# =========================================================
# ADMIN COMMAND CENTER ROUTES (/ecom & /admin/*)
# =========================================================

@app.route("/admin")
@app.route("/ecom")
@admin_required
def ecom_dashboard():
    profile = get_current_user_profile()
    return render_template(
        "admin.html",
        current_user_email=session.get("email", ""),
        current_user_role=profile.get("role", "admin") if profile else "admin"
    )


@app.route("/admin/overview-metrics")
@admin_required
def admin_overview_metrics():
    client, error = get_supabase_client()
    timeframe = request.args.get("timeframe", "all").strip().lower()

    try:
        # Users from Supabase
        users_list = []
        total_users = 0
        pending_users = 0
        if client and not error:
            try:
                u_res = client.table("users").select("id, email, role, approved, created_at").execute()
                users_list = u_res.data or []
                total_users = len(users_list)
                pending_users = len([u for u in users_list if not u.get("approved")])
            except Exception as u_err:
                print(f"[Overview users error]: {u_err}")

        # Books from Supabase
        total_books = 0
        if client and not error:
            try:
                b_res = client.table("books").select("id", count="exact").execute()
                total_books = b_res.count or len(b_res.data or [])
            except Exception as b_err:
                print(f"[Overview books error]: {b_err}")

        # Exhibitors from Supabase
        total_exhibitors = 0
        if client and not error:
            for tbl in ["exhibitor", "exhibitors"]:
                try:
                    ex_res = client.table(tbl).select("id", count="exact").execute()
                    total_exhibitors = ex_res.count or len(ex_res.data or [])
                    break
                except Exception:
                    continue

        # Credit Ledger Data (Timeframe filtered)
        credit_entries = get_extraction_credit_ledger(timeframe=timeframe)
        total_extractions = len(credit_entries)
        live_credits_used = sum(float(e.get("total_credits", 0.0)) for e in credit_entries)
        total_parse_credits = sum(float(e.get("parse_credits", 0.0)) for e in credit_entries)
        total_extract_credits = sum(float(e.get("extract_credits", 0.0)) for e in credit_entries)
        total_pages_processed = sum(int(e.get("pages_processed", 0)) for e in credit_entries)
        total_records_extracted = sum(int(e.get("records_extracted", 0)) for e in credit_entries)
        live_cost_usd = sum(float(e.get("cost_estimate_usd", 0.0)) for e in credit_entries)

        # Baseline offset: 3,200.00 credits and $32.00 USD
        base_credits = BASE_HISTORICAL_CREDITS if timeframe in ["all", "cumulative"] else 0.0
        base_cost_usd = BASE_HISTORICAL_COST_USD if timeframe in ["all", "cumulative"] else 0.0
        total_credits_used = base_credits + live_credits_used
        total_cost_usd = base_cost_usd + live_cost_usd

        # User Save Activities (Timeframe filtered)
        save_activities = get_user_save_activities(timeframe=timeframe)
        total_saves = len(save_activities)
        total_records_saved_by_users = sum(int(a.get("saved_count", 0)) for a in save_activities)

        # Build User Productivity Matrix (Cross-referencing users, extractions, and saves)
        user_productivity_map = {}
        for u in users_list:
            u_email = str(u.get("email", "")).lower()
            if u_email:
                user_productivity_map[u_email] = {
                    "id": u.get("id"),
                    "email": u.get("email"),
                    "role": u.get("role", "user"),
                    "approved": u.get("approved", False),
                    "extractions_count": 0,
                    "credits_used": 0.0,
                    "pages_processed": 0,
                    "records_extracted": 0,
                    "records_saved": 0,
                    "saves_count": 0,
                    "estimated_cost_usd": 0.0,
                    "last_activity": None
                }

        # Aggregate from extraction ledger
        for e in credit_entries:
            e_email = str(e.get("user_email", "anonymous")).lower()
            if e_email not in user_productivity_map:
                user_productivity_map[e_email] = {
                    "id": e.get("user_id", "unknown"),
                    "email": e.get("user_email", "anonymous"),
                    "role": "user",
                    "approved": True,
                    "extractions_count": 0,
                    "credits_used": 0.0,
                    "pages_processed": 0,
                    "records_extracted": 0,
                    "records_saved": 0,
                    "saves_count": 0,
                    "estimated_cost_usd": 0.0,
                    "last_activity": None
                }
            entry_stat = user_productivity_map[e_email]
            entry_stat["extractions_count"] += 1
            entry_stat["credits_used"] += float(e.get("total_credits", 0.0))
            entry_stat["pages_processed"] += int(e.get("pages_processed", 0))
            entry_stat["records_extracted"] += int(e.get("records_extracted", 0))
            entry_stat["estimated_cost_usd"] += float(e.get("cost_estimate_usd", 0.0))
            if not entry_stat["last_activity"] or str(e.get("created_at", "")) > str(entry_stat["last_activity"]):
                entry_stat["last_activity"] = e.get("created_at_formatted") or e.get("created_at")

        # Aggregate from save activities
        for a in save_activities:
            a_email = str(a.get("user_email", "anonymous")).lower()
            if a_email not in user_productivity_map:
                user_productivity_map[a_email] = {
                    "id": a.get("user_id", "unknown"),
                    "email": a.get("user_email", "anonymous"),
                    "role": "user",
                    "approved": True,
                    "extractions_count": 0,
                    "credits_used": 0.0,
                    "pages_processed": 0,
                    "records_extracted": 0,
                    "records_saved": 0,
                    "saves_count": 0,
                    "estimated_cost_usd": 0.0,
                    "last_activity": None
                }
            entry_stat = user_productivity_map[a_email]
            entry_stat["saves_count"] += 1
            entry_stat["records_saved"] += int(a.get("saved_count", 0))
            if not entry_stat["last_activity"] or str(a.get("created_at", "")) > str(entry_stat["last_activity"]):
                entry_stat["last_activity"] = a.get("created_at_formatted") or a.get("created_at")

        user_productivity = list(user_productivity_map.values())
        user_productivity.sort(key=lambda x: (x["records_saved"], x["credits_used"], x["extractions_count"]), reverse=True)

        for u in user_productivity:
            u["credits_used"] = round(u["credits_used"], 2)
            u["estimated_cost_usd"] = round(u["estimated_cost_usd"], 3)

        # Database Storage Analytics Estimate
        est_storage_mb = round((total_exhibitors * 0.75 + total_books * 2.0) / 1024, 2)
        est_storage_kb = round(total_exhibitors * 0.75 + total_books * 2.0, 1)

        # Timeline Trend Data for Interactive Visual Analytics
        from datetime import datetime
        timeline_buckets = {}
        for e in credit_entries:
            raw_ts = e.get("created_at")
            if not raw_ts:
                continue
            try:
                dt_obj = datetime.fromisoformat(str(raw_ts))
                date_key = dt_obj.strftime("%Y-%m-%d")
                date_label = dt_obj.strftime("%d %b")
            except Exception:
                date_key = str(raw_ts)[:10]
                date_label = date_key

            if date_key not in timeline_buckets:
                timeline_buckets[date_key] = {
                    "label": date_label,
                    "credits": 0.0,
                    "pages": 0,
                    "extractions": 0,
                    "records_extracted": 0,
                    "records_saved": 0,
                    "cost_usd": 0.0
                }
            timeline_buckets[date_key]["credits"] += float(e.get("total_credits", 0.0))
            timeline_buckets[date_key]["pages"] += int(e.get("pages_processed", 0))
            timeline_buckets[date_key]["extractions"] += 1
            timeline_buckets[date_key]["records_extracted"] += int(e.get("records_extracted", 0))
            timeline_buckets[date_key]["cost_usd"] += float(e.get("cost_estimate_usd", 0.0))

        for a in save_activities:
            raw_ts = a.get("created_at")
            if not raw_ts:
                continue
            try:
                dt_obj = datetime.fromisoformat(str(raw_ts))
                date_key = dt_obj.strftime("%Y-%m-%d")
                date_label = dt_obj.strftime("%d %b")
            except Exception:
                date_key = str(raw_ts)[:10]
                date_label = date_key

            if date_key not in timeline_buckets:
                timeline_buckets[date_key] = {
                    "label": date_label,
                    "credits": 0.0,
                    "pages": 0,
                    "extractions": 0,
                    "records_extracted": 0,
                    "records_saved": 0,
                    "cost_usd": 0.0
                }
            timeline_buckets[date_key]["records_saved"] += int(a.get("saved_count", 0))

        sorted_date_keys = sorted(timeline_buckets.keys())
        chart_timeline = {
            "labels": [timeline_buckets[k]["label"] for k in sorted_date_keys],
            "credits": [round(timeline_buckets[k]["credits"], 2) for k in sorted_date_keys],
            "pages": [timeline_buckets[k]["pages"] for k in sorted_date_keys],
            "records_extracted": [timeline_buckets[k]["records_extracted"] for k in sorted_date_keys],
            "records_saved": [timeline_buckets[k]["records_saved"] for k in sorted_date_keys],
            "cost_usd": [round(timeline_buckets[k]["cost_usd"], 3) for k in sorted_date_keys]
        }

        # Top Users Chart Data (Limit to top 6 active users)
        top_active_users = [u for u in user_productivity if (u.get("credits_used", 0) > 0 or u.get("records_saved", 0) > 0 or u.get("extractions_count", 0) > 0)][:6]
        chart_users = {
            "labels": [u["email"].split("@")[0] if "@" in u["email"] else u["email"] for u in top_active_users],
            "emails": [u["email"] for u in top_active_users],
            "credits": [u["credits_used"] for u in top_active_users],
            "records_saved": [u["records_saved"] for u in top_active_users],
            "extractions": [u["extractions_count"] for u in top_active_users]
        }

        chart_distribution = {
            "parse_credits": round(total_parse_credits, 2),
            "extract_credits": round(total_extract_credits, 2)
        }

        return jsonify({
            "success": True,
            "timeframe": timeframe,
            "metrics": {
                "total_users": total_users,
                "pending_users": pending_users,
                "approved_users": total_users - pending_users,
                "total_books": total_books,
                "total_exhibitors": total_exhibitors,
                "total_saves": total_saves,
                "total_records_saved_by_users": total_records_saved_by_users,
                "total_extractions": total_extractions,
                "base_credits": BASE_HISTORICAL_CREDITS,
                "base_cost_usd": BASE_HISTORICAL_COST_USD,
                "live_credits_used": round(live_credits_used, 2),
                "live_cost_usd": round(live_cost_usd, 3),
                "total_credits_used": round(total_credits_used, 2),
                "total_parse_credits": round(total_parse_credits, 2),
                "total_extract_credits": round(total_extract_credits, 2),
                "total_pages_processed": total_pages_processed,
                "total_records_extracted": total_records_extracted,
                "total_cost_usd": round(total_cost_usd, 3),
                "est_storage_mb": est_storage_mb,
                "est_storage_kb": est_storage_kb,
                "user_productivity": user_productivity,
                "chart_timeline": chart_timeline,
                "chart_users": chart_users,
                "chart_distribution": chart_distribution,
                "recent_extractions": credit_entries[:8],
                "recent_activities": save_activities[:8]
            }
        })
    except Exception as e:
        print(f"[Admin overview metrics error] {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-ledger/export")
@admin_required
def admin_export_credit_ledger():
    try:
        timeframe = request.args.get("timeframe", "all").strip().lower()
        search = request.args.get("search", "").strip()
        entries = get_extraction_credit_ledger(timeframe=timeframe, search=search)

        export_rows = []
        for e in entries:
            export_rows.append({
                "Date & Time": e.get("created_at_formatted") or e.get("created_at", ""),
                "User Email": e.get("user_email", ""),
                "Document Name": e.get("filename", ""),
                "Book ID": e.get("book_id", ""),
                "Book Name": e.get("book_name", ""),
                "Pages Processed": e.get("pages_processed", 0),
                "Parse Credits": e.get("parse_credits", 0.0),
                "Extract Credits": e.get("extract_credits", 0.0),
                "Total ADE Credits": e.get("total_credits", 0.0),
                "Records Extracted": e.get("records_extracted", 0),
                "Est. Cost (USD)": e.get("cost_estimate_usd", 0.0),
                "Parse Job ID": e.get("parse_job_id", ""),
                "Duration (ms)": e.get("duration_ms", 0)
            })

        df = pd.DataFrame(export_rows)
        excel_name = f"credit_ledger_{timeframe}_{uuid.uuid4().hex[:8]}.xlsx"
        excel_path = OUTPUT_DIR / excel_name
        df.to_excel(excel_path, index=False)

        return send_file(excel_path, as_attachment=True, download_name=f"landingai_credit_ledger_{timeframe}.xlsx")
    except Exception as e:
        return f"Export error: {str(e)}", 500


@app.route("/admin/credit-ledger")
@admin_required
def admin_get_credit_ledger():
    try:
        timeframe = request.args.get("timeframe", "all").strip().lower()
        search = request.args.get("search", "").strip()
        entries = get_extraction_credit_ledger(timeframe=timeframe, search=search)

        total_credits = sum(float(e.get("total_credits", 0.0)) for e in entries)
        total_parse = sum(float(e.get("parse_credits", 0.0)) for e in entries)
        total_extract = sum(float(e.get("extract_credits", 0.0)) for e in entries)
        total_pages = sum(int(e.get("pages_processed", 0)) for e in entries)
        total_records = sum(int(e.get("records_extracted", 0)) for e in entries)
        total_cost = sum(float(e.get("cost_estimate_usd", 0.0)) for e in entries)

        return jsonify({
            "success": True,
            "timeframe": timeframe,
            "search": search,
            "entries": entries,
            "total_entries": len(entries),
            "total_credits": round(total_credits, 2),
            "total_parse_credits": round(total_parse, 2),
            "total_extract_credits": round(total_extract, 2),
            "total_pages_processed": total_pages,
            "total_records_extracted": total_records,
            "total_cost_usd": round(total_cost, 3)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-ledger/<entry_id>/delete", methods=["POST"])
@admin_required
def admin_delete_credit_ledger_entry(entry_id):
    try:
        success = delete_extraction_credit_entry(entry_id)
        if success:
            return jsonify({"success": True, "message": "Credit ledger record successfully deleted."})
        return jsonify({"success": False, "error": "Credit ledger record not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/credit-ledger/clear", methods=["POST"])
@admin_required
def admin_clear_credit_ledger():
    try:
        clear_all_extraction_credit_entries()
        return jsonify({"success": True, "message": "All credit ledger records cleared successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/save-activities")
@admin_required
def admin_get_save_activities():
    try:
        timeframe = request.args.get("timeframe", "all").strip().lower()
        search = request.args.get("search", "").strip()
        activities = get_user_save_activities(timeframe=timeframe, search=search)
        total_records_saved = sum(int(a.get("saved_count", 0)) for a in activities)

        return jsonify({
            "success": True,
            "timeframe": timeframe,
            "search": search,
            "activities": activities,
            "total": len(activities),
            "total_records_saved": total_records_saved
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/save-activities/export")
@admin_required
def admin_export_save_activities():
    try:
        timeframe = request.args.get("timeframe", "all").strip().lower()
        search = request.args.get("search", "").strip()
        activities = get_user_save_activities(timeframe=timeframe, search=search)

        export_rows = []
        for a in activities:
            export_rows.append({
                "Date & Time": a.get("created_at_formatted") or a.get("created_at", ""),
                "User Email": a.get("user_email", ""),
                "Book ID": a.get("book_id", ""),
                "Book Name": a.get("book_name", ""),
                "Records Saved": a.get("saved_count", 0),
                "Database Status": "Saved to Supabase Database"
            })

        df = pd.DataFrame(export_rows)
        excel_name = f"user_activities_{timeframe}_{uuid.uuid4().hex[:8]}.xlsx"
        excel_path = OUTPUT_DIR / excel_name
        df.to_excel(excel_path, index=False)

        return send_file(excel_path, as_attachment=True, download_name=f"user_ingestion_activities_{timeframe}.xlsx")
    except Exception as e:
        return f"Export error: {str(e)}", 500


@app.route("/admin/save-activities/<activity_id>/delete", methods=["POST"])
@admin_required
def admin_delete_save_activity(activity_id):
    try:
        success = delete_user_save_activity(activity_id)
        if success:
            return jsonify({"success": True, "message": "Activity log successfully delete ho gaya."})
        return jsonify({"success": False, "error": "Activity record nahi mila."}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/save-activities/clear", methods=["POST"])
@admin_required
def admin_clear_save_activities():
    try:
        clear_all_user_save_activities()
        return jsonify({"success": True, "message": "All activity logs successfully cleared."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/ledger-report-data")
@admin_required
def admin_ledger_report_data():
    """Provides consolidated financial and operational audit data formatted for printable reports."""
    from datetime import datetime
    timeframe = request.args.get("timeframe", "all").strip().lower()
    now_dt = datetime.now()

    timeframe_labels = {
        "daily": "Daily Report (Today)",
        "today": "Daily Report (Today)",
        "weekly": "Weekly Report (Last 7 Days)",
        "week": "Weekly Report (Last 7 Days)",
        "monthly": "Monthly Report (This Month / Last 30 Days)",
        "month": "Monthly Report (This Month / Last 30 Days)",
        "all": "All-Time Cumulative Master Ledger"
    }

    try:
        credit_entries = get_extraction_credit_ledger(timeframe=timeframe)
        save_activities = get_user_save_activities(timeframe=timeframe)

        live_credits = sum(float(e.get("total_credits", 0.0)) for e in credit_entries)
        total_parse = sum(float(e.get("parse_credits", 0.0)) for e in credit_entries)
        total_extract = sum(float(e.get("extract_credits", 0.0)) for e in credit_entries)
        total_pages = sum(int(e.get("pages_processed", 0)) for e in credit_entries)
        total_records_extracted = sum(int(e.get("records_extracted", 0)) for e in credit_entries)
        live_cost_usd = sum(float(e.get("cost_estimate_usd", 0.0)) for e in credit_entries)

        base_credits = BASE_HISTORICAL_CREDITS if timeframe in ["all", "cumulative"] else 0.0
        base_cost = BASE_HISTORICAL_COST_USD if timeframe in ["all", "cumulative"] else 0.0
        total_credits = base_credits + live_credits
        total_cost_usd = base_cost + live_cost_usd
        total_records_saved = sum(int(a.get("saved_count", 0)) for a in save_activities)

        # Get DB live counts
        total_books = 0
        total_exhibitors = 0
        client, error = get_supabase_client()
        if client and not error:
            try:
                b_res = client.table("books").select("id", count="exact").execute()
                total_books = b_res.count or len(b_res.data or [])
                for tbl in ["exhibitor", "exhibitors"]:
                    try:
                        ex_res = client.table(tbl).select("id", count="exact").execute()
                        total_exhibitors = ex_res.count or len(ex_res.data or [])
                        break
                    except Exception:
                        continue
            except Exception:
                pass

        # User breakdown
        user_productivity = {}
        for e in credit_entries:
            ue = str(e.get("user_email", "unknown"))
            if ue not in user_productivity:
                user_productivity[ue] = {"email": ue, "extractions": 0, "credits": 0.0, "pages": 0, "extracted": 0, "saved": 0, "cost": 0.0}
            user_productivity[ue]["extractions"] += 1
            user_productivity[ue]["credits"] += float(e.get("total_credits", 0.0))
            user_productivity[ue]["pages"] += int(e.get("pages_processed", 0))
            user_productivity[ue]["extracted"] += int(e.get("records_extracted", 0))
            user_productivity[ue]["cost"] += float(e.get("cost_estimate_usd", 0.0))

        for a in save_activities:
            ue = str(a.get("user_email", "unknown"))
            if ue not in user_productivity:
                user_productivity[ue] = {"email": ue, "extractions": 0, "credits": 0.0, "pages": 0, "extracted": 0, "saved": 0, "cost": 0.0}
            user_productivity[ue]["saved"] += int(a.get("saved_count", 0))

        user_summary_list = list(user_productivity.values())
        user_summary_list.sort(key=lambda x: x["saved"], reverse=True)

        return jsonify({
            "success": True,
            "report_meta": {
                "generated_at": now_dt.strftime("%d %B %Y, %I:%M:%S %p"),
                "generated_by": session.get("email", "Admin"),
                "timeframe": timeframe,
                "timeframe_label": timeframe_labels.get(timeframe, "Custom Ledger Period"),
                "organization": "Exhibitor Data Management System"
            },
            "summary": {
                "total_extractions": len(credit_entries),
                "total_credits_used": round(total_credits, 2),
                "total_parse_credits": round(total_parse, 2),
                "total_extract_credits": round(total_extract, 2),
                "total_pages_processed": total_pages,
                "total_records_extracted": total_records_extracted,
                "total_cost_usd": round(total_cost_usd, 3),
                "total_saves": len(save_activities),
                "total_records_saved": total_records_saved,
                "total_books_in_db": total_books,
                "total_exhibitors_in_db": total_exhibitors
            },
            "user_productivity": user_summary_list,
            "credit_entries": credit_entries,
            "save_activities": save_activities
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500




@app.route("/admin/create-user", methods=["POST"])
@admin_required
def admin_create_user():
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500
    try:
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", "")).strip()
        role = str(payload.get("role", "user")).lower()
        if role not in {"admin", "user"}:
            role = "user"
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required."}), 400
        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400

        auth_response = client.auth.sign_up({"email": email, "password": password})
        if not auth_response.user:
            return jsonify({"success": False, "error": "Could not create user auth account."}), 500

        user_id = auth_response.user.id
        client.table("users").insert({
            "id": user_id,
            "email": email,
            "role": role,
            "approved": True
        }).execute()

        # Set initial credits
        get_user_credits_data(user_id=user_id, email=email, role=role)

        return jsonify({"success": True, "message": "User created successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/users")
@admin_required
def admin_get_users():
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        res = client.table("users").select("id, email, role, approved, created_at").order("created_at", desc=True).execute()
        users_list = res.data or []
        for u in users_list:
            u_cr = get_user_credits_data(user_id=u.get("id"), email=u.get("email"), role=u.get("role", "user"))
            u["credits"] = u_cr.get("credits", 0.0)
            u["total_allocated"] = u_cr.get("total_allocated", 0.0)
            u["total_used"] = u_cr.get("total_used", 0.0)
            u["is_admin"] = (u.get("role") == "admin")
        return jsonify({"success": True, "users": users_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/users/<user_id>/approve", methods=["POST"])
@admin_required
def admin_approve_user(user_id):
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        client.table("users").update({"approved": True}).eq("id", user_id).execute()
        return jsonify({"success": True, "message": "User access approved successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/users/<user_id>/toggle-status", methods=["POST"])
@admin_required
def admin_toggle_user_status(user_id):
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        payload = request.get_json(silent=True) or {}
        approved = bool(payload.get("approved", True))
        client.table("users").update({"approved": approved}).eq("id", user_id).execute()
        return jsonify({"success": True, "message": f"User status set to {'Approved' if approved else 'Pending'}."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/users/<user_id>/role", methods=["POST"])
@admin_required
def admin_change_user_role(user_id):
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        payload = request.get_json(silent=True) or {}
        role = str(payload.get("role", "user")).lower()
        if role not in {"admin", "user"}:
            role = "user"
        update_data = {"role": role}
        if role == "admin":
            update_data["approved"] = True
        client.table("users").update(update_data).eq("id", user_id).execute()
        return jsonify({"success": True, "message": f"User role updated to '{role}'."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/users/<user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        current_user_id = session.get("user_id")
        if str(user_id) == str(current_user_id):
            return jsonify({"success": False, "error": "Aap apna khud ka account delete nahi kar sakte."}), 400

        # Delete from public.users table
        client.table("users").delete().eq("id", user_id).execute()

        # Try to delete from Supabase Auth admin API if available
        try:
            if hasattr(client, "auth") and hasattr(client.auth, "admin"):
                client.auth.admin.delete_user(user_id)
        except Exception as auth_del_err:
            print(f"Auth delete note: {auth_del_err}")

        return jsonify({"success": True, "message": "User successfully delete ho gaya."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/books")
@admin_required
def admin_get_books():
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        books_res = client.table("books").select("id, book_name, year, uploaded_at").order("uploaded_at", desc=True).execute()
        books = books_res.data or []
        meta_map = get_all_book_metadata()

        # Find target exhibitor table
        target_table = "exhibitor"
        for tbl in ["exhibitor", "exhibitors"]:
            try:
                client.table(tbl).select("id").limit(1).execute()
                target_table = tbl
                break
            except Exception:
                continue

        # Count exact records per book and attach country
        for b in books:
            b_id_str = str(b.get("id", ""))
            b["country"] = meta_map.get(b_id_str, {}).get("country", "") or b.get("country", "General")
            b["year"] = meta_map.get(b_id_str, {}).get("year") or b.get("year")
            try:
                c_res = client.table(target_table).select("id", count="exact").eq("book_id", b_id_str).limit(1).execute()
                b["exhibitor_count"] = c_res.count if c_res.count is not None else len(c_res.data or [])
            except Exception as cnt_err:
                print(f"[Admin Books Count Error for #{b.get('id')}]: {cnt_err}")
                b["exhibitor_count"] = 0

        return jsonify({"success": True, "books": books})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/books/<book_id>/update", methods=["POST"])
@admin_required
def admin_update_book(book_id):
    try:
        payload = request.get_json(silent=True) or {}
        new_book_id = str(payload.get("new_book_id", "")).strip()
        new_book_name = str(payload.get("new_book_name", "")).strip()
        new_country = str(payload.get("country", "")).strip()
        new_year = str(payload.get("year", "")).strip() or None

        if not new_book_id:
            return jsonify({"success": False, "error": "New Book ID cannot be empty."}), 400
        if not new_book_name:
            return jsonify({"success": False, "error": "New Book Name cannot be empty."}), 400

        success, msg = update_book_details(book_id, new_book_id, new_book_name, country=new_country, year=new_year)
        if not success:
            return jsonify({"success": False, "error": msg}), 400

        return jsonify({
            "success": True,
            "message": msg,
            "old_book_id": book_id,
            "new_book_id": new_book_id,
            "new_book_name": new_book_name,
            "country": new_country,
            "year": new_year
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/exhibitors")
@admin_required
def admin_get_exhibitors():
    client, error = get_supabase_client()
    if error:
        return jsonify({"success": False, "error": error}), 500

    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = max(1, min(100, int(request.args.get("per_page", 50))))
        book_id = str(request.args.get("book_id", "")).strip()
        search = str(request.args.get("search", "")).strip()
        country = str(request.args.get("country", "")).strip()

        # Get books map and metadata
        meta_map = get_all_book_metadata()
        books_res = client.table("books").select("id, book_name").execute()
        all_books = books_res.data or []
        books_map = {str(b["id"]): b["book_name"] for b in all_books}

        target_table = "exhibitor"
        for tbl in ["exhibitor", "exhibitors"]:
            try:
                client.table(tbl).select("id").limit(1).execute()
                target_table = tbl
                break
            except Exception:
                continue

        query = client.table(target_table).select("*", count="exact")

        if book_id:
            query = query.eq("book_id", book_id)
        elif country:
            country_matched_book_ids = [
                str(b["id"]) for b in all_books
                if country.lower() in str(meta_map.get(str(b["id"]), {}).get("country", "")).lower()
            ]
            if country_matched_book_ids:
                if len(country_matched_book_ids) == 1:
                    query = query.eq("book_id", country_matched_book_ids[0])
                else:
                    query = query.in_("book_id", country_matched_book_ids)
            else:
                query = query.eq("book_id", "__no_match__")

        if search:
            # Check if search is an exact Book ID
            exact_book_id_matches = [b["id"] for b in all_books if str(b["id"]).lower() == search.lower()]
            if exact_book_id_matches:
                query = query.eq("book_id", exact_book_id_matches[0])
            else:
                # Search matches Book Name(s) or Country
                matching_name_book_ids = [str(b["id"]) for b in all_books if search.lower() in str(b.get("book_name", "")).lower()]
                matching_country_book_ids = [
                    str(b["id"]) for b in all_books
                    if search.lower() in str(meta_map.get(str(b["id"]), {}).get("country", "")).lower()
                ]
                all_matching_book_ids = list(set(matching_name_book_ids + matching_country_book_ids))

                filters = [
                    f"name.ilike.%{search}%",
                    f"category.ilike.%{search}%",
                    f"address.ilike.%{search}%",
                    f"email.ilike.%{search}%",
                    f"website.ilike.%{search}%",
                    f"tel.ilike.%{search}%",
                    f"fax.ilike.%{search}%"
                ]
                for mb_id in all_matching_book_ids:
                    filters.append(f"book_id.eq.{mb_id}")

                query = query.or_(",".join(filters))

        offset = (page - 1) * per_page
        query = query.order("id", desc=True).range(offset, offset + per_page - 1)
        res = query.execute()

        exhibitors = res.data or []
        total = res.count or len(exhibitors)

        for ex in exhibitors:
            b_key = str(ex.get("book_id", ""))
            ex["book_name"] = books_map.get(b_key, f"Book #{b_key}")
            ex["country"] = meta_map.get(b_key, {}).get("country", "") or "General"

        total_pages = max(1, (total + per_page - 1) // per_page)

        return jsonify({
            "success": True,
            "exhibitors": exhibitors,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/export-exhibitors")
@admin_required
def admin_export_exhibitors():
    client, error = get_supabase_client()
    if error:
        return f"Database error: {error}", 500

    try:
        book_id = str(request.args.get("book_id", "")).strip()
        search = str(request.args.get("search", "")).strip()
        country = str(request.args.get("country", "")).strip()

        meta_map = get_all_book_metadata()
        books_res = client.table("books").select("id, book_name").execute()
        all_books = books_res.data or []
        books_map = {str(b["id"]): b["book_name"] for b in all_books}

        target_table = "exhibitor"
        for tbl in ["exhibitor", "exhibitors"]:
            try:
                client.table(tbl).select("id").limit(1).execute()
                target_table = tbl
                break
            except Exception:
                continue

        query = client.table(target_table).select("*")

        if book_id:
            query = query.eq("book_id", book_id)
        elif country:
            country_matched_book_ids = [
                str(b["id"]) for b in all_books
                if country.lower() in str(meta_map.get(str(b["id"]), {}).get("country", "")).lower()
            ]
            if country_matched_book_ids:
                if len(country_matched_book_ids) == 1:
                    query = query.eq("book_id", country_matched_book_ids[0])
                else:
                    query = query.in_("book_id", country_matched_book_ids)
            else:
                query = query.eq("book_id", "__no_match__")
        elif search:
            exact_book_id_matches = [b["id"] for b in all_books if str(b["id"]).lower() == search.lower()]
            if exact_book_id_matches:
                query = query.eq("book_id", exact_book_id_matches[0])
            else:
                matching_name_book_ids = [str(b["id"]) for b in all_books if search.lower() in str(b.get("book_name", "")).lower()]
                matching_country_book_ids = [
                    str(b["id"]) for b in all_books
                    if search.lower() in str(meta_map.get(str(b["id"]), {}).get("country", "")).lower()
                ]
                all_matching_book_ids = list(set(matching_name_book_ids + matching_country_book_ids))

                filters = [
                    f"name.ilike.%{search}%",
                    f"category.ilike.%{search}%",
                    f"address.ilike.%{search}%",
                    f"email.ilike.%{search}%",
                    f"website.ilike.%{search}%",
                    f"tel.ilike.%{search}%",
                    f"fax.ilike.%{search}%"
                ]
                for mb_id in all_matching_book_ids:
                    filters.append(f"book_id.eq.{mb_id}")
                query = query.or_(",".join(filters))

        res = query.execute()
        exhibitors = res.data or []

        for ex in exhibitors:
            b_key = str(ex.get("book_id", ""))
            ex["book_name"] = books_map.get(b_key, f"Book #{b_key}")
            ex["country"] = meta_map.get(b_key, {}).get("country", "") or "General"

        if book_id:
            raw_book_name = books_map.get(book_id, f"Book_{book_id}")
            clean_book_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', str(raw_book_name)).strip().replace(' ', '_')
            if not clean_book_name:
                clean_book_name = f"Book_{book_id}"
            download_filename = f"{clean_book_name}_{book_id}_exhibitors.xlsx"
        elif country:
            clean_country = re.sub(r'[^a-zA-Z0-9_\-\s]', '', country).strip().replace(' ', '_')
            download_filename = f"{clean_country}_exhibitors.xlsx"
        else:
            download_filename = "all_books_exhibitors.xlsx"

        excel_name = f"exhibitors_export_{uuid.uuid4().hex}.xlsx"
        excel_path = OUTPUT_DIR / excel_name
        save_excel(exhibitors, excel_path)

        return send_file(excel_path, as_attachment=True, download_name=download_filename)

    except Exception as e:
        return f"Export error: {str(e)}", 500


# =========================================================
# FAVICON & MAIN
# =========================================================

@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    print("=" * 60)
    print("EXHIBITOR DATA MANAGEMENT SYSTEM")
    print("=" * 60)
    print("App running at: http://127.0.0.1:5000")
    print("Admin dashboard at: http://127.0.0.1:5000/ecom")
    app.run(host="127.0.0.1", port=5000, debug=True)
