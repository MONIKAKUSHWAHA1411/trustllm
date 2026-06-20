from .hallucination_detector import run_hallucination_detection
from .prompt_injection_test import run_prompt_injection_test
from .model_leaderboard import generate_leaderboard
from .llm_judge import judge_responses
from .merge_results import merge_results
from .bias_detector import run_bias_detection
from .golden_dataset import run_golden_validation
from .deepeval_runner import run_deepeval


def run_full_evaluation():

    print("Starting evaluation pipeline")

    run_prompt_injection_test()

    run_hallucination_detection()

    run_bias_detection()

    judge_responses()

    merge_results()

    generate_leaderboard()

    # Golden-dataset / acceptance-criteria gate (deterministic, offline).
    run_golden_validation()

    # DeepEval cross-check (skips gracefully if deepeval/key are absent).
    run_deepeval()

    print("Evaluation pipeline completed")


if __name__ == "__main__":
    run_full_evaluation()
