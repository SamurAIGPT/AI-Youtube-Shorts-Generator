"""
LLM provider factory for AI YouTube Shorts Generator.

Supports multiple LLM providers for highlight selection:
- OpenAI (default): GPT-4o-mini
- MiniMax: MiniMax-M2.7 via OpenAI-compatible API

Provider selection via LLM_PROVIDER environment variable.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Provider constants
PROVIDER_OPENAI = "openai"
PROVIDER_MINIMAX = "minimax"
DEFAULT_PROVIDER = PROVIDER_OPENAI

# Provider configurations
PROVIDER_CONFIGS = {
    PROVIDER_OPENAI: {
        "env_key": "OPENAI_API",
        "default_model": "gpt-4o-mini",
        "base_url": None,  # Use default OpenAI endpoint
        "display_name": "OpenAI",
    },
    PROVIDER_MINIMAX: {
        "env_key": "MINIMAX_API_KEY",
        "default_model": "MiniMax-M2.7",
        "base_url": "https://api.minimax.io/v1",
        "display_name": "MiniMax",
    },
}


def get_provider():
    """Get the configured LLM provider name, with auto-detection fallback."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider and provider in PROVIDER_CONFIGS:
        return provider

    # Auto-detect based on available API keys
    if provider == "" or provider not in PROVIDER_CONFIGS:
        if os.getenv("MINIMAX_API_KEY"):
            return PROVIDER_MINIMAX
        if os.getenv("OPENAI_API"):
            return PROVIDER_OPENAI

    return DEFAULT_PROVIDER


def get_api_key(provider):
    """Get API key for the specified provider."""
    config = PROVIDER_CONFIGS[provider]
    api_key = os.getenv(config["env_key"])
    if not api_key:
        raise ValueError(
            f"{config['display_name']} API key not found. "
            f"Set {config['env_key']} in your .env file."
        )
    return api_key


def create_llm(provider=None, temperature=1.0):
    """
    Create a LangChain ChatOpenAI-compatible LLM instance.

    Args:
        provider: Provider name ('openai' or 'minimax'). Auto-detected if None.
        temperature: Sampling temperature. Clamped to (0.0, 1.0] for MiniMax.

    Returns:
        A LangChain ChatOpenAI instance configured for the selected provider.
    """
    if provider is None:
        provider = get_provider()

    config = PROVIDER_CONFIGS[provider]
    api_key = get_api_key(provider)
    model = os.getenv("LLM_MODEL", config["default_model"])

    # MiniMax requires temperature in (0.0, 1.0]
    if provider == PROVIDER_MINIMAX:
        temperature = max(0.01, min(temperature, 1.0))

    kwargs = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
    }
    if config["base_url"]:
        kwargs["base_url"] = config["base_url"]

    llm = ChatOpenAI(**kwargs)
    print(f"Using LLM provider: {config['display_name']} (model: {model})")
    return llm
