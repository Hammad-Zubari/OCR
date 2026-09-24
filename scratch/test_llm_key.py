import requests
import os

key = "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"

# Test Groq
groq_url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {key}"}
try:
    res = requests.get(groq_url, headers=headers)
    print("Groq response status:", res.status_code)
    if res.status_code == 200:
        models = [m["id"] for m in res.json().get("data", [])]
        print("Groq available models:", models[:10])
except Exception as e:
    print("Groq error:", e)

# Test chat completion with Groq
chat_url = "https://api.groq.com/openai/v1/chat/completions"
body = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 10
}
try:
    res = requests.post(chat_url, headers=headers, json=body)
    print("Chat completion test with llama-3.3-70b-versatile:", res.status_code, res.text[:200])
except Exception as e:
    print("Chat error:", e)

# Also test model passed by user: openai/gpt-oss-120b
body["model"] = "openai/gpt-oss-120b"
try:
    res = requests.post(chat_url, headers=headers, json=body)
    print("Chat completion test with openai/gpt-oss-120b on Groq:", res.status_code, res.text[:200])
except Exception as e:
    print("Chat error:", e)
