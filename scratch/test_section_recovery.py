import re

def extract_section_phones_and_fax(section_text):
    if not section_text:
        return "", ""

    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    phones = []
    faxes = []

    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()

        # Skip HTML tags, markdown headings, images
        if line_clean.startswith("<") or line_clean.startswith("#") or line_clean.startswith("!["):
            continue

        is_fax = bool(re.search(r'\b(?:fax|telefax|📠)\b', line_lower))
        is_phone_line = bool(re.search(
            r'\b(?:tel|telephone|phone|mobile|cell|call|center office|head office|office|factory|branch|sales|hotline|📞|☎️|📱)\b',
            line_lower
        ))

        # Strip prefixes
        cleaned_line = re.sub(
            r'^(?:(?:center office|head office|office|factory|branch|sales|hotline|tel|telephone|phone|mobile|cell|fax|telefax|📞|☎️|📱|📠)\s*[:\-–]?\s*)+',
            '',
            line_clean,
            flags=re.IGNORECASE
        ).strip()

        # Check if line contains digits
        digits = re.sub(r"\D", "", cleaned_line)
        if len(digits) >= 6:
            # If line has multiple numbers separated by slash, comma, or multi-spaces
            # e.g., "+98 311- 2233808- 2232794" or "+98 311- 3318702, +98 311- 3323517"
            # Extract distinct phone candidates
            if is_phone_line or is_fax or re.match(r'^[+\d\s\(\)\-\.,/]+$', cleaned_line):
                # If cleaned_line itself is pure phone numbers
                if re.match(r'^[+\d\s\(\)\-\.,/]+$', cleaned_line):
                    # Clean redundant commas or trailing chars
                    val = cleaned_line.strip(" ,;:")
                    if is_fax:
                        if val not in faxes:
                            faxes.append(val)
                    else:
                        if val not in phones:
                            phones.append(val)
                else:
                    # Line might have text and numbers (e.g. "Tel: +98 21 12345678 (10 lines)")
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

# Test on user's exact sample
sample_text = """
4- Goldasht Mosaic
📞 Center Office: +98 311- 3318702
+98 311- 3323517
Factory: +98 311- 2233808- 2232794
🛠️ Producer of Granite Mosaic With the Automatic Machines
🏗️ Shah Mohammadi

<a id='9b09647f-6299-4ea9-8755-b81071191d45'>
"""

phones, faxes = extract_section_phones_and_fax(sample_text)
print("Recovered Phones:", phones)
print("Recovered Faxes :", faxes)
