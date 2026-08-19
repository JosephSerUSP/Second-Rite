import os
import requests
import json

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Test 1: standard chat/completions
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
            print("Response:", r.json()["choices"][0]["message"]["content"])
        else:
            print("Error:", r.status_code, r.text)
    except Exception as e:
        print("Exception:", e)

    # Test 2: check reasoning_effort options if any
    for effort in ["high", "xhigh"]:
        p_effort = dict(payload)
        p_effort["reasoning_effort"] = effort
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=p_effort, timeout=30)
            print(f"Effort {effort} status:", r.status_code)
            if r.status_code == 200:
                print(f"Effort {effort} worked!")
            else:
                print(f"Effort {effort} failed:", r.text[:200])
        except Exception as e:
            print(f"Effort {effort} ex:", e)

if __name__ == "__main__":
    main()
