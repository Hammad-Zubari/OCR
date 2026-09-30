import requests
import json

def test_endpoints():
    key = "4bda8b947059534ccffa801ca554a3ef"
    model = "gpt-6-astra"
    
    # Check openrouter
    print("Testing openrouter with gpt-6-astra...")
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Return json: {\"reply\": \"test\"}"}],
                "temperature": 0.0
            },
            timeout=10
        )
        print("OpenRouter Status:", res.status_code)
        print("OpenRouter Body:", res.text[:300])
    except Exception as e:
        print("OpenRouter error:", e)

    # Check groq with primary key from .env
    from dotenv import load_dotenv
    import os
    load_dotenv()
    groq_key = os.getenv("LLM_API_KEY")
    groq_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    print("\nTesting Groq with primary key...")
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": groq_model,
                "messages": [{"role": "user", "content": "Return json: {\"reply\": \"test\"}"}],
                "temperature": 0.0
            },
            timeout=10
        )
        print("Groq Status:", res.status_code)
        print("Groq Body:", res.text[:300])
    except Exception as e:
        print("Groq error:", e)

if __name__ == "__main__":
    test_endpoints()
