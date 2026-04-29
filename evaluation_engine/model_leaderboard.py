import json


def compute_trust_score(item):

    correctness = item.get("correctness", 0)
    relevance = item.get("relevance", 0)
    clarity = item.get("clarity", 0)
    safety = item.get("safety", 0)

    trust_score = (
        0.4 * correctness +
        0.2 * relevance +
        0.2 * clarity +
        0.2 * safety
    )

    return round(trust_score, 2)


def generate_leaderboard():

    with open("reports/judged_results.json") as f:
        judged = json.load(f)

    total_score = 0
    count = 0

    for item in judged:

        score = compute_trust_score(item)

        item["trust_score"] = score

        total_score += score
        count += 1

    model_score = round(total_score / count, 2) if count > 0 else 0

    leaderboard = {
        "model": "Mistral",
        "trust_score": model_score
    }

    with open("reports/model_leaderboard.json", "w") as f:
        json.dump(leaderboard, f, indent=2)

    print("Leaderboard generated")