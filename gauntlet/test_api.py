import os
import json
import requests

def test_api():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.")
        return
    print("OPENAI_API_KEY is present.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Test 1: chat/completions endpoint with gpt-5.6-luna
    payload = {
        "model": "gpt-5.6-luna",
        "messages": [
            {"role": "system", "content": "You are Luna, an adversarial art evaluator."},
            {"role": "user", "content": "Respond with a JSON object: {\"status\": \"ready\", \"role\": \"adversarial_evaluator\"}"}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        print("Endpoint /chat/completions status:", r.status_code)
        if r.status_code == 200:
            print("Response content:", r.json()["choices"][0]["message"]["content"])
        else:
            print("Response error:", r.text)
    except Exception as e:
        print("Chat completions error:", e)

    # Test 2: responses endpoint if supported
    responses_payload = {
        "model": "gpt-5.6-luna",
        "input": "Respond with JSON: {\"status\": \"ready\"}"
    }
    try:
        r2 = requests.post("https://api.openai.com/v1/responses", headers=headers, json=responses_payload, timeout=30)
        print("Endpoint /responses status:", r2.status_code)
        if r2.status_code == 200:
            print("Responses endpoint works!")
        else:
            print("Responses endpoint returned:", r2.status_code, r2.text[:200])
    except Exception as e:
        print("Responses error:", e)

if __name__ == "__main__":
    test_api()
