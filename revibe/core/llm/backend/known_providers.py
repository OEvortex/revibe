from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal, TypedDict

SdkMode = Literal["anthropic", "openai", "oai-response"]


class KnownProviderConfig(TypedDict, total=False):
    description: str
    sdk_mode: SdkMode
    models: list[dict[str, Any]]


KNOWN_PROVIDERS: dict[str, KnownProviderConfig] = {
    "mistral": {
        "description": "Mistral AI - Devstral models",
        "sdk_mode": "openai",
        "models": [
            {
                "name": "mistral-vibe-cli-latest",
                "provider": "mistral",
                "alias": "devstral-2",
                "temperature": 0.2,
                "input_price": 0.4,
                "output_price": 2.0,
                "context": 200_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "devstral-small-latest",
                "provider": "mistral",
                "alias": "devstral-small",
                "temperature": 0.2,
                "input_price": 0.1,
                "output_price": 0.3,
                "context": 200_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
        ],
    },
    "openai": {
        "description": "OpenAI - GPT models",
        "sdk_mode": "openai",
        "models": [
            {
                "name": "gpt-5.2",
                "provider": "openai",
                "alias": "gpt-5.2",
                "temperature": 0.2,
                "input_price": 1.75,
                "output_price": 14.0,
                "context": 400_000,
                "max_output": 128_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-5.1",
                "provider": "openai",
                "alias": "gpt-5.1",
                "temperature": 0.2,
                "input_price": 1.25,
                "output_price": 10.0,
                "context": 400_000,
                "max_output": 128_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-5",
                "provider": "openai",
                "alias": "gpt-5",
                "temperature": 0.2,
                "input_price": 1.25,
                "output_price": 10.0,
                "context": 400_000,
                "max_output": 128_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-5-mini",
                "provider": "openai",
                "alias": "gpt-5-mini",
                "temperature": 0.2,
                "input_price": 0.25,
                "output_price": 2.0,
                "context": 400_000,
                "max_output": 128_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-5.2-pro",
                "provider": "openai",
                "alias": "gpt-5.2-pro",
                "temperature": 0.2,
                "input_price": 21.0,
                "output_price": 168.0,
                "context": 400_000,
                "max_output": 128_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-5-pro",
                "provider": "openai",
                "alias": "gpt-5-pro",
                "temperature": 0.2,
                "input_price": 15.0,
                "output_price": 120.0,
                "context": 400_000,
                "max_output": 128_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-4.1",
                "provider": "openai",
                "alias": "gpt-4.1",
                "temperature": 0.2,
                "input_price": 2.0,
                "output_price": 8.0,
                "context": 1_000_000,
                "max_output": 32_768,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
        ],
    },
    "opencode": {
        "description": "OpenCode - Multi-provider access",
        "sdk_mode": "oai-response",
        "models": [
            {
                "name": "claude-sonnet-4-5",
                "provider": "opencode",
                "alias": "claude-sonnet-4-5",
                "temperature": 0.2,
                "input_price": 3.0,
                "output_price": 15.0,
                "context": 200_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "claude-opus-4-5",
                "provider": "opencode",
                "alias": "claude-opus-4-5",
                "temperature": 0.2,
                "input_price": 5.0,
                "output_price": 15.0,
                "context": 200_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gpt-5.2",
                "provider": "opencode",
                "alias": "gpt-5.2",
                "temperature": 0.2,
                "input_price": 2.5,
                "output_price": 10.0,
                "context": 128_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "gemini-3-pro",
                "provider": "opencode",
                "alias": "gemini-3-pro",
                "temperature": 0.2,
                "input_price": 2.0,
                "output_price": 12.0,
                "context": 1_000_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "qwen3-coder",
                "provider": "opencode",
                "alias": "qwen3-coder",
                "temperature": 0.2,
                "input_price": 1.0,
                "output_price": 5.0,
                "context": 128_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
        ],
    },
    "openrouter": {
        "description": "OpenRouter - Access to many third-party models",
        "sdk_mode": "openai",
        "models": [
            {
                "name": "anthropic/claude-sonnet-4.5",
                "provider": "openrouter",
                "alias": "claude-sonnet-4.5",
                "temperature": 0.2,
                "input_price": 3.0,
                "output_price": 15.0,
                "context": 1_000_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "anthropic/claude-opus-4.5",
                "provider": "openrouter",
                "alias": "claude-opus-4.5",
                "temperature": 0.2,
                "input_price": 5.0,
                "output_price": 25.0,
                "context": 200_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "google/gemini-3-pro-preview",
                "provider": "openrouter",
                "alias": "gemini-3-pro-preview",
                "temperature": 0.2,
                "input_price": 2.0,
                "output_price": 12.0,
                "context": 1_000_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "moonshotai/kimi-k2-thinking",
                "provider": "openrouter",
                "alias": "kimi-k2-thinking-openrouter",
                "temperature": 0.2,
                "input_price": 0.4,
                "output_price": 1.75,
                "context": 262_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
            {
                "name": "nvidia/nemotron-3-nano-30b-a3b",
                "provider": "openrouter",
                "alias": "nemotron-3-nano-30b-a3b",
                "temperature": 0.2,
                "input_price": 0.06,
                "output_price": 0.24,
                "context": 262_000,
                "max_output": 32_000,
                "supported_formats": ["native", "xml"],
                "supports_thinking": False,
            },
        ],
    },
}


def get_known_provider(provider_name: str) -> KnownProviderConfig | None:
    return KNOWN_PROVIDERS.get(provider_name)


def get_provider_description(provider_name: str) -> str | None:
    provider = get_known_provider(provider_name)
    if provider is None:
        return None
    description = provider.get("description")
    return description if isinstance(description, str) and description else None


def get_known_provider_models(provider_name: str) -> list[dict[str, Any]]:
    provider = get_known_provider(provider_name)
    if provider is None:
        return []
    models = provider.get("models", [])
    if not isinstance(models, list):
        return []
    return [model for model in models if isinstance(model, dict)]


def get_example_model(provider_name: str) -> str | None:
    for model in get_known_provider_models(provider_name):
        alias = model.get("alias")
        if isinstance(alias, str) and alias:
            return alias

    return None


def iter_known_models() -> Iterator[dict[str, Any]]:
    for provider in KNOWN_PROVIDERS.values():
        yield from provider.get("models", [])
