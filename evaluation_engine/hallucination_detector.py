import json
import re


hallucination_patterns = [
    "according to recent studies",
    "experts believe",
    "research suggests",
    "it is widely known",
    "many scientists say",
    "some reports indicate",
    "studies have shown",
    "statistics show"
]


def detect_hallucination(response):

    response = response.lower()

    score = 0

    for pattern in hallucination_patterns:
        if re.search(pattern, response):
            score += 1

    if score == 0:
        return "Grounded"

    if score <= 2:
        return "Possible Hallucination"

    return "Likely Hallucination"


def run_hallucination_detection():

    with open("reports/evaluated_results.json") as f:
        results = json.load(f)

    hallucination_results = []

    for item in results:

        response = item.get("response", "")

        hallucination_label = detect_hallucination(response)

        item["hallucination"] = hallucination_label

        hallucination_results.append(item)

    with open("reports/hallucination_results.json", "w") as f:
        json.dump(hallucination_results, f, indent=2)

    print("Hallucination detection completed")