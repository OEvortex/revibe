from __future__ import annotations

import os
from typing import TYPE_CHECKING

from revibe.core.config import DEFAULT_MODELS

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


# Centralized provider descriptions
PROVIDER_DESCRIPTIONS: dict[str, str] = {
    "mistral": "Mistral AI - Devstral models",
    "openai": "OpenAI - GPT-5, o1 models",
    "huggingface": "Hugging Face - Inference API and local models",
    "groq": "Groq - Fast inference",
    "ollama": "Ollama - Local models",
    "llamacpp": "llama.cpp - Local server",
    "cerebras": "Cerebras - Fast inference",
    "qwencode": "Qwen Code - QwenCli models via OAuth",
    "openrouter": "OpenRouter - Access to 100+ models from various providers",
    "geminicli": "Gemini CLI - Google Gemini models via CLI",
    "opencode": "OpenCode - Multi-provider access (Claude, GPT, Gemini, GLM, Kimi, Qwen, Grok)",
    "kilocode": "Kilo Code - Free coding models (Grok Code Fast, Devstral, KAT-Coder-Pro, MiniMax M2)",
    "antigravity": "Antigravity - Free Claude & Gemini models via Google OAuth",
}

# Help links for providers requiring API keys
PROVIDER_HELP: dict[str, tuple[str, str]] = {
    "mistral": ("https://console.mistral.ai/api-keys", "Mistral AI Console"),
    "openai": ("https://platform.openai.com/api-keys", "OpenAI Platform"),
    "groq": ("https://console.groq.com/keys", "Groq Console"),
    "huggingface": ("https://huggingface.co/settings/tokens", "Hugging Face Settings"),
    "cerebras": (
        "https://cloud.cerebras.ai/platform/api-keys",
        "Cerebras Cloud Platform",
    ),
    "openrouter": ("https://openrouter.ai/keys", "OpenRouter Dashboard"),
    "opencode": ("https://opencode.ai", "OpenCode Platform"),
    "kilocode": ("https://app.kilo.ai/profile", "Kilo Code Profile"),
}


def mask_key(key: str) -> str:
    """Mask an API key for display, showing first 4 and last 4 characters."""
    if len(key) <= 8:  # noqa: PLR2004
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def check_key_status(provider: ProviderConfigUnion) -> str:
    """Check if the provider's API key is configured."""
    env_var = getattr(provider, "api_key_env_var", "")
    if not env_var:
        return "Not required"
    if os.getenv(env_var):
        return "Configured"
    return "Not configured"


def get_example_model(provider_name: str) -> str | None:
    """Get the first available model alias for the provider."""
    for model in DEFAULT_MODELS:
        if model.provider == provider_name:
            return model.alias
    return None


def build_provider_description(
    provider: ProviderConfigUnion, show_details: bool = False
) -> str:
    """Build a multi-line description for the provider."""
    lines = []

    # Short summary
    desc = PROVIDER_DESCRIPTIONS.get(provider.name, provider.api_base)
    lines.append(f"[bold]{desc}[/]")

    # Auth status
    status = check_key_status(provider)
    env_var = getattr(provider, "api_key_env_var", "")
    if env_var:
        lines.append(f"Auth: API key ({env_var}) - {status}")
    else:
        lines.append("Auth: Not required")

    if show_details:
        # API base
        lines.append(f"API Base: {provider.api_base}")

        # Example model
        example_model = get_example_model(provider.name)
        if example_model:
            lines.append(f"Example Model: {example_model}")

        # Docs link
        if provider.name in PROVIDER_HELP:
            url, name = PROVIDER_HELP[provider.name]
            lines.append(f"Docs: {name} ({url})")
        elif provider.name == "qwencode":
            lines.append("Docs: Use /auth in `qwen` CLI for OAuth setup")
        elif provider.name == "geminicli":
            lines.append("Docs: Use /auth in `gemini` CLI for OAuth setup")
        elif provider.name == "antigravity":
            lines.append("Auth: Google OAuth (browser-based login)")

        # Data retention warning for KiloCode
        if provider.name == "kilocode":
            lines.append("")
            lines.append("[yellow]⚠ Data Retention Notice:[/]")
            lines.append("Kilo Code may retain and analyze prompts/completions")
            lines.append("from free models to improve their services.")

    return "\n".join(lines)
