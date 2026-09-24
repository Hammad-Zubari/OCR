import json
import requests

key = "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"
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

system_prompt = """You are an intelligent Exhibitor Source-Context Verification engine.
Your task is to verify whether extracted exhibitor data fields belong strictly to the TARGET company or were accidentally borrowed/taken from the PREVIOUS or NEXT company in the document Markdown.

RULES:
1. Missing optional fields (fax, website, email, tel) are normal and NOT an error.
2. If a field's value is present in the CURRENT company context, status is "MATCH".
3. If a field's value appears under the PREVIOUS or NEXT company context and NOT the current company, status is "WRONG_CONTEXT" and overall result MUST be "REVIEW".
4. If a field is not found anywhere in source, status is "NOT_FOUND".
5. If ambiguous, status is "UNCERTAIN".
6. Return STRICT JSON ONLY without markdown formatting or backticks.

JSON Schema:
{
  "result": "PASS" | "REVIEW",
  "reason": "Brief summary of verification",
  "fields": {
    "name": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
    "address": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
    "tel": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
    "fax": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
    "email": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
    "website": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" }
  }
}
"""

user_prompt = """
--- PREVIOUS COMPANY CONTEXT ---
None

--- CURRENT COMPANY CONTEXT ---
ABC TEXTILES LTD.
123 Main Street
Tel: +92 111 222
Email: abc@example.com

--- NEXT COMPANY CONTEXT ---
XYZ GARMENTS LTD.
456 Market Road
Tel: +92 333 444
Email: xyz@example.com

--- EXTRACTED RECORD TO VERIFY ---
{
  "name": "ABC TEXTILES LTD.",
  "address": "123 Main Street",
  "tel": "+92 111 222",
  "fax": "",
  "email": "xyz@example.com",
  "website": ""
}
"""

body = {
    "model": "openai/gpt-oss-120b",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.0,
    "max_tokens": 500
}

res = requests.post(url, headers=headers, json=body)
print("Status:", res.status_code)
print("Response text:", res.text)
try:
    data = res.json()
    content = data["choices"][0]["message"]["content"]
    print("\nParsed Content:")
    print(json.loads(content))
except Exception as e:
    print("Error parsing:", e)
