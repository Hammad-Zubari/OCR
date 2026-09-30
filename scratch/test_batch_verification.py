import json
import requests

key = "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"
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

system_prompt = """You are an intelligent Exhibitor Source-Context Verification engine.
Verify whether extracted exhibitor data fields belong strictly to each TARGET company's section in the document Markdown or were accidentally taken from neighboring companies.

RULES:
1. Missing optional fields (fax, website, email, tel) are normal and NOT an error (status: "NOT_FOUND").
2. If an extracted field value is present in the CURRENT company context, status is "MATCH".
3. If an extracted field value appears under the PREVIOUS or NEXT company context and NOT the current company, status is "WRONG_CONTEXT" and record result MUST be "REVIEW".
4. If a field is not found anywhere in source, status is "NOT_FOUND".
5. If ambiguous, status is "UNCERTAIN".
6. Return STRICT JSON ONLY with an array of verification objects corresponding to each input record by record_index.

Output JSON Schema:
{
  "verifications": [
    {
      "record_index": 0,
      "result": "PASS" | "REVIEW",
      "reason": "Brief explanation",
      "fields": {
        "name": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
        "address": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
        "tel": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
        "fax": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
        "email": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" },
        "website": { "status": "MATCH" | "NOT_FOUND" | "WRONG_CONTEXT" | "UNCERTAIN" }
      }
    }
  ]
}
"""

user_prompt = """
Verify the following batch of extracted exhibitor records against their document context blocks:

[ITEM 0]
--- PREVIOUS CONTEXT ---
None
--- CURRENT CONTEXT ---
ABC TEXTILES LTD.
123 Main Street
Tel: +92 111 222
Email: abc@example.com
--- NEXT CONTEXT ---
XYZ GARMENTS LTD.
456 Market Road
Tel: +92 333 444
Email: xyz@example.com
--- EXTRACTED RECORD ---
{
  "name": "ABC TEXTILES LTD.",
  "address": "123 Main Street",
  "tel": "+92 111 222",
  "fax": "",
  "email": "xyz@example.com",
  "website": ""
}

[ITEM 1]
--- PREVIOUS CONTEXT ---
ABC TEXTILES LTD.
123 Main Street
Tel: +92 111 222
Email: abc@example.com
--- CURRENT CONTEXT ---
XYZ GARMENTS LTD.
456 Market Road
Tel: +92 333 444
Email: xyz@example.com
--- NEXT CONTEXT ---
None
--- EXTRACTED RECORD ---
{
  "name": "XYZ GARMENTS LTD.",
  "address": "456 Market Road",
  "tel": "+92 333 444",
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
    "max_tokens": 800
}

res = requests.post(url, headers=headers, json=body)
print("Status:", res.status_code)
try:
    data = res.json()
    content = data["choices"][0]["message"]["content"]
    print("\nParsed Batch Content:")
    print(json.dumps(json.loads(content), indent=2))
except Exception as e:
    print("Error parsing:", e)
