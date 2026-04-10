import requests, cv2, base64

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

small = cv2.resize(frame, (320, 240))
_, buffer = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 75])
image_base64 = base64.b64encode(buffer).decode("utf-8")

response = requests.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "qwen2.5-vl-3b-instruct",
        "max_tokens": 100,
        "temperature": 0.0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    },
                    {
                        "type": "text",
                        "text": "Describe what you see in this image in detail."
                    }
                ]
            }
        ]
    },
    timeout=30
)

print(response.json())