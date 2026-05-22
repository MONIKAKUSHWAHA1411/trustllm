"""
llm_runner/providers.py — TrustLLM Pro provider registry + unified client
==========================================================================
One place to define every cloud model provider TrustLLM Pro supports.
Each provider entry carries:
  - display_name      : human label used in the UI
  - api_key_url       : where the user gets their key
  - key_prefix_hint   : placeholder text for the input field
  - models            : list of (display_name, model_id) tuples

The ``generate_response`` function routes a (provider, model_id, prompt, key)
call to the right SDK. Each SDK is imported lazily so a missing dependency
fails with a clear message instead of crashing the app at startup.
"""

from typing import Dict, List, Tuple


PROVIDERS: Dict[str, dict] = {
    "claude": {
        "display_name": "Claude (Anthropic)",
        "api_key_url": "https://console.anthropic.com/settings/keys",
        "key_prefix_hint": "sk-ant-...",
        "models": [
            ("Claude 3.5 Sonnet", "claude-3-5-sonnet-latest"),
            ("Claude 3.5 Haiku", "claude-3-5-haiku-latest"),
        ],
    },
    "gpt": {
        "display_name": "GPT (OpenAI)",
        "api_key_url": "https://platform.openai.com/api-keys",
        "key_prefix_hint": "sk-proj-...  or  sk-...",
        "models": [
            ("GPT-4o", "gpt-4o"),
            ("GPT-4o mini", "gpt-4o-mini"),
        ],
    },
    "gemini": {
        "display_name": "Gemini (Google)",
        "api_key_url": "https://aistudio.google.com/app/apikey",
        "key_prefix_hint": "AIza...",
        "models": [
            ("Gemini 1.5 Pro", "gemini-1.5-pro"),
            ("Gemini 1.5 Flash", "gemini-1.5-flash"),
        ],
    },
    "mistral": {
        "display_name": "Mistral AI",
        "api_key_url": "https://console.mistral.ai/api-keys/",
        "key_prefix_hint": "32-char alphanumeric",
        "models": [
            ("Mistral Large", "mistral-large-latest"),
            ("Mistral Small", "mistral-small-latest"),
        ],
    },
    "phi": {
        "display_name": "Phi (Hugging Face)",
        "api_key_url": "https://huggingface.co/settings/tokens",
        "key_prefix_hint": "hf_...",
        "models": [
            ("Phi-3 mini", "microsoft/Phi-3-mini-4k-instruct"),
            ("Phi-3.5 mini", "microsoft/Phi-3.5-mini-instruct"),
        ],
    },
}


def list_all_models() -> List[Tuple[str, str, str]]:
    """Return [(provider_id, display_name, model_id), ...] for every Pro model."""
    out = []
    for pid, meta in PROVIDERS.items():
        for display, mid in meta["models"]:
            out.append((pid, display, mid))
    return out


def get_provider_for_model(model_id: str) -> str:
    """Find which provider owns this model_id. Raises ValueError if unknown."""
    for pid, meta in PROVIDERS.items():
        for _, mid in meta["models"]:
            if mid == model_id:
                return pid
    raise ValueError(f"Unknown model: {model_id}")


def get_display_for_model(model_id: str) -> str:
    """Human display name for a model_id, e.g. 'Claude 3.5 Sonnet'."""
    for meta in PROVIDERS.values():
        for display, mid in meta["models"]:
            if mid == model_id:
                return display
    return model_id


# -----------------------------------------------------------------------
# Unified generation entry point
# -----------------------------------------------------------------------

def generate_response(provider: str, model_id: str, prompt: str, api_key: str,
                      max_tokens: int = 512, temperature: float = 0.4) -> str:
    """Call the given provider/model with the user's API key.

    Raises RuntimeError with a friendly message on any failure (missing SDK,
    auth error, network error). The caller is expected to surface this to the
    user via st.error.
    """
    if not api_key:
        raise RuntimeError(f"No API key configured for provider '{provider}'.")

    try:
        if provider == "claude":
            return _generate_claude(model_id, prompt, api_key, max_tokens, temperature)
        if provider == "gpt":
            return _generate_gpt(model_id, prompt, api_key, max_tokens, temperature)
        if provider == "gemini":
            return _generate_gemini(model_id, prompt, api_key, max_tokens, temperature)
        if provider == "mistral":
            return _generate_mistral(model_id, prompt, api_key, max_tokens, temperature)
        if provider == "phi":
            return _generate_phi(model_id, prompt, api_key, max_tokens, temperature)
    except ImportError as e:
        raise RuntimeError(f"SDK for {provider} not installed: {e}")
    except Exception as e:
        raise RuntimeError(f"{provider} API call failed: {type(e).__name__}: {e}")

    raise ValueError(f"Unknown provider: {provider}")


# -----------------------------------------------------------------------
# Per-provider implementations
# -----------------------------------------------------------------------

def _generate_claude(model_id, prompt, api_key, max_tokens, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    # resp.content is a list of content blocks; first one is the text
    if resp.content and hasattr(resp.content[0], "text"):
        return resp.content[0].text.strip()
    return str(resp.content).strip()


def _generate_gpt(model_id, prompt, api_key, max_tokens, temperature):
    import openai
    client = openai.OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def _generate_gemini(model_id, prompt, api_key, max_tokens, temperature):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    resp = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
    )
    return (resp.text or "").strip()


def _generate_mistral(model_id, prompt, api_key, max_tokens, temperature):
    from mistralai import Mistral
    client = Mistral(api_key=api_key)
    resp = client.chat.complete(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def _generate_phi(model_id, prompt, api_key, max_tokens, temperature):
    from huggingface_hub import InferenceClient
    client = InferenceClient(model=model_id, token=api_key, timeout=60)
    return client.text_generation(
        prompt,
        max_new_tokens=max_tokens,
        temperature=temperature,
        return_full_text=False,
    ).strip()
