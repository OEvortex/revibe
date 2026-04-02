from __future__ import annotations

import os
from typing import TYPE_CHECKING

from revibe.core.llm.backend.known_providers import (
    KNOWN_PROVIDERS,
    get_example_model as get_registry_example_model,
    get_provider_description,
)
from revibe.core.model_sources import get_available_models

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfig


# Help links for providers requiring API keys
PROVIDER_HELP: dict[str, tuple[str, str]] = {
    "mistral": ("https://console.mistral.ai/api-keys", "Mistral AI Console"),
    "openai": ("https://platform.openai.com/api-keys", "OpenAI Platform"),
}

PROVIDER_DESCRIPTIONS: dict[str, str] = {
    name: get_provider_description(name) or "" for name in KNOWN_PROVIDERS
}


def mask_key(key: str) -> str:
    """Mask an API key for display, showing first 4 and last 4 characters."""
    if len(key) <= 8:  # noqa: PLR2004
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def check_key_status(provider: ProviderConfig) -> str:
    """Check if the provider's API key is configured."""
    env_var = getattr(provider, "api_key_env_var", "")
    if not env_var:
        return "Not required"
    if os.getenv(env_var):
        return "Configured"
    return "Not configured"


def get_example_model(provider_name: str) -> str | None:
    """Get the first available model alias for the provider."""
    if alias := get_registry_example_model(provider_name):
        return alias

    for model in get_available_models():
        if model.provider == provider_name:
            return model.alias
    return None


def build_provider_description(
    provider: ProviderConfig, show_details: bool = False
) -> str:
    """Build a multi-line description for the provider."""
    lines = []

    # Short summary
    desc = get_provider_description(provider.name) or provider.api_base
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

    return "\n".join(lines)
