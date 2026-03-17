import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL = "mistral"

# Load dataset
with open("../datasets/prompts.json", "r") as file:
    prompts = json.load(file)

results = []

for item in prompts:
    
    prompt_text = item["prompt"]
    
    payload = {
        "model": MODEL,
        "prompt": prompt_text,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    data = response.json()

    model_response = data["response"]

    result = {
    "id": item["id"],
    "category": item["category"],
    "prompt": prompt_text,
    "expected_answer": item.get("expected_answer"),
    "model_response": model_response
    }

    results.append(result)

    print("\n-----------------------------------")
    print("Prompt:", prompt_text)
    print("Response:", model_response)


# Save results
with open("../reports/results.json", "w") as f:
    json.dump(results, f, indent=4)

print("\nResults saved to reports/results.json")