from .hallucination_detector import run_hallucination_detection
from .prompt_injection_test import run_prompt_injection_test
from .model_leaderboard import generate_leaderboard
from .llm_judge import judge_responses
from .merge_results import merge_results


def run_full_evaluation():

    print("Starting evaluation pipeline")

    run_prompt_injection_test()

    run_hallucination_detection()

    judge_responses()

    merge_results()

    generate_leaderboard()

    print("Evaluation pipeline completed")


if __name__ == "__main__":
    run_full_evaluation()