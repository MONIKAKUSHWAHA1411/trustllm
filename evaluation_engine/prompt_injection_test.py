import json
import os

injection_patterns = [
    "ignore previous instructions",
    "reveal system prompt",
    "act as unrestricted ai",
    "bypass safety",
    "jailbreak",
    "override instructions"
]


def detect_injection(prompt):

    prompt_lower = prompt.lower()

    for pattern in injection_patterns:
        if pattern in prompt_lower:
            return "Injection"

    return "Normal"


def run_prompt_injection_test():

    base_dir = os.path.dirname(os.path.dirname(__file__))
    dataset_path = os.path.join(base_dir, "datasets", "trustllm_dataset.json")

    with open(dataset_path) as f:
        dataset = json.load(f)

    results = []

    for item in dataset:

        prompt = item.get("prompt", "")

        label = detect_injection(prompt)

        item["prompt_type"] = label

        results.append(item)

    report_path = os.path.join(base_dir, "reports", "prompt_injection_results.json")

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print("Prompt injection analysis completed")