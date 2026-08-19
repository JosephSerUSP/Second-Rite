import os
import base64
import requests
from io import BytesIO
from PIL import Image, ImageDraw

def test_vision():
    api_key = os.environ.get("OPENAI_API_KEY")
    img = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 40, 140, 180], fill=(200, 80, 80, 255))
    draw.ellipse([70, 20, 120, 70], fill=(240, 200, 150, 255))

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-5.6-luna",
        "messages": [
            {
                "role": "system",
                "content": "You are Luna, an adversarial art evaluator. Respond strictly in JSON: {\"critique\": string, \"detected_shape\": string}"
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this test sprite and tell me what you see."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        }
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"}
    }

    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
    print("Vision test status:", r.status_code)
    if r.status_code == 200:
        print("Vision test response:", r.json()["choices"][0]["message"]["content"])
    else:
        print("Vision test error:", r.text)

if __name__ == "__main__":
    test_vision()
