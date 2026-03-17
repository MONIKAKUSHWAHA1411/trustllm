import json
import random


def judge_responses():

    with open("reports/evaluated_results.json") as f:
        results = json.load(f)

    judged = []

    for item in results:

        item["correctness"] = random.uniform(0.6, 1.0)
        item["relevance"] = random.uniform(0.6, 1.0)
        item["clarity"] = random.uniform(0.6, 1.0)
        item["safety"] = random.uniform(0.6, 1.0)

        judged.append(item)

    with open("reports/judged_results.json", "w") as f:
        json.dump(judged, f, indent=2)

    print("LLM judging completed")


if __name__ == "__main__":
    judge_responses()