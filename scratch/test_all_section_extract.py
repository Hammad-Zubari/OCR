import re

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

        # Skip anchor tags, markdown headings, image tags
        if line_clean.startswith("<") or line_clean.startswith("#") or line_clean.startswith("!["):
            continue

        # Skip if line is just company name
        line_norm = re.sub(r"[^\w\s]", "", line_lower).strip()
        if comp_name_clean and (line_norm == comp_name_clean or comp_name_clean in line_norm and len(line_norm) - len(comp_name_clean) < 4):
            continue

        # Skip phone / fax / email / web lines
        if bool(re.search(r'\b(?:tel|telephone|phone|mobile|fax|telefax|email|e-mail|website|web|www|http|📞|☎️|📱|📠|✉️|🌐)\b', line_lower)):
            continue
        if "@" in line_clean:
            continue
        digits = re.sub(r"\D", "", line_clean)
        if len(digits) >= 6 and re.match(r'^[+\d\s\(\)\-\.,/]+$', line_clean):
            continue

        # Check if line is address line
        is_explicit_addr = bool(re.search(r'\b(?:address|addr|street|road|st\.|ave|avenue|blvd|building|bldg|floor|fl\.|p\.?o\.?\s*box|postal code|zip|industrial area|industrial zone|city|province|district|estate|📍)\b', line_lower))
        
        # Clean prefix
        cleaned = re.sub(r'^(?:(?:address|addr|office address|factory address|location|📍)\s*[:\-–]?\s*)+', '', line_clean, flags=re.IGNORECASE).strip()
        if is_explicit_addr and cleaned:
            addr_lines.append(cleaned)

    return ", ".join(addr_lines)


# Test with address sample
sample_2 = """
5- Parsian Industrial Group
📍 Address: No. 45, North Valiasr Ave, Tehran, Iran
Tel: +98 21 88776655
Fax: +98 21 88776656
✉️ Email: info@parsian-group.ir, sales@parsian-group.ir
🌐 Web: www.parsian-group.ir
"""

print("Address  :", extract_section_address(sample_2, "Parsian Industrial Group"))
print("Emails   :", extract_section_emails(sample_2))
print("Websites :", extract_section_websites(sample_2))
