"""Utility helpers for mapping internal model names to Artificial Analysis URLs."""

AA_BASE = "https://artificialanalysis.ai/models/"
AA_FALLBACK = "https://artificialanalysis.ai/leaderboards/models"

_SLUG_MAP = {
    # OpenAI
    "gpt": "gpt-4o",
    "gpt-4o": "gpt-4o",
    "gpt4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4-turbo": "gpt-4-turbo",
    "gpt4": "gpt-4o",
    # Anthropic
    "claude": "claude-3-5-sonnet",
    "claude-3": "claude-3-5-sonnet",
    "claude 3": "claude-3-5-sonnet",
    "claude-3-5-sonnet": "claude-3-5-sonnet",
    "claude 3.5 sonnet": "claude-3-5-sonnet",
    "claude-3-opus": "claude-3-opus",
    "claude 3 opus": "claude-3-opus",
    "claude-3-haiku": "claude-3-haiku",
    "claude 3 haiku": "claude-3-haiku",
    # Google
    "gemini-pro": "gemini-1-5-pro",
    "gemini": "gemini-1-5-pro",
    "gemini-1-5-pro": "gemini-1-5-pro",
    "gemini 1.5 pro": "gemini-1-5-pro",
    "gemini-1-5-flash": "gemini-1-5-flash",
    "gemini 1.5 flash": "gemini-1-5-flash",
    # Mistral
    "mistral": "mistral-large",
    "mistral:instruct": "mistral-large",
    "mistral-large": "mistral-large",
    "mistral large": "mistral-large",
    # Meta / Llama
    "llama": "llama-3-1-70b",
    "llama3": "llama-3-1-70b",
    "llama-3": "llama-3-1-70b",
    "llama 3": "llama-3-1-70b",
    "llama-3-1-70b": "llama-3-1-70b",
    "llama 3.1 70b": "llama-3-1-70b",
    "llama-3.1-70b": "llama-3-1-70b",
    "llama-v3p1-70b-instruct": "llama-3-1-70b",
    "meta-llama/llama-3.3-70b-instruct-turbo": "llama-3-3-70b",
    "meta-llama/llama-3.1-70b-instruct-turbo": "llama-3-1-70b",
    "llama-3.3-70b": "llama-3-3-70b",
    "llama 3.3 70b": "llama-3-3-70b",
    # Qwen
    "qwen": "qwen-2-5-72b-instruct",
    "qwen2.5-72b": "qwen-2-5-72b-instruct",
    "qwen 2.5 72b": "qwen-2-5-72b-instruct",
    "qwen/qwen2.5-72b-instruct-turbo": "qwen-2-5-72b-instruct",
    "accounts/fireworks/models/qwen2p5-72b-instruct": "qwen-2-5-72b-instruct",
    # DeepSeek
    "deepseek-r1": "deepseek-r1",
    "deepseek r1": "deepseek-r1",
    "deepseek-ai/deepseek-r1": "deepseek-r1",
    # Mixtral
    "mixtral": "mixtral-8x7b-instruct-v0-1",
    "mixtral-8x7b": "mixtral-8x7b-instruct-v0-1",
    "accounts/fireworks/models/mixtral-8x7b-instruct": "mixtral-8x7b-instruct-v0-1",
    # Mistral (additional)
    "mistral-7b": "mistral-7b-instruct-v0-3",
    "mistralai/mistral-7b-instruct-v0.3": "mistral-7b-instruct-v0-3",
}


def aa_model_url(model: str) -> str:
    """Return the Artificial Analysis model page URL, or the leaderboard fallback."""
    if not model:
        return AA_FALLBACK
    slug = _SLUG_MAP.get(model.lower().strip())
    return f"{AA_BASE}{slug}" if slug else AA_FALLBACK
