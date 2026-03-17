import requests
import json

url = "http://localhost:11434/api/generate"

payload = {
    "model": "mistral",
    "prompt": "What is the capital of Australia?",
    "stream": False
}

response = requests.post(url, json=payload)

data = response.json()

print("Model Response:")
print(data["response"])