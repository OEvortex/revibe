"""Central provider registry and compatibility adaptation information.

Inspired by better-copilot-chat's knownProviders.ts. Each provider entry is
metadata-only (no hardcoded models). Models are auto-fetched from provider
APIs via model_fetcher.py and persisted to JSON config files under
revibe/core/llm/backend/providers/config/.

Priority when merging model configurations:
  Model Config > Provider Config > Known Provider Config
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal, TypedDict

SdkMode = Literal["anthropic", "openai", "oai-response"]


class SdkCompatConfig(TypedDict, total=False):
    base_url: str
    extra_body: dict[str, Any]
    custom_header: dict[str, str]


class ModelParserConfig(TypedDict, total=False):
    array_path: str
    cooldown_minutes: int
    filter_field: str
    filter_value: str
    id_field: str
    name_field: str
    description_field: str
    context_length_field: str
    tags_field: str


class KnownProviderConfig(TypedDict, total=False):
    # Display metadata
    display_name: str
    description: str
    family: str

    # SDK mode
    sdk_mode: SdkMode

    # SDK-specific base URLs
    openai: SdkCompatConfig
    anthropic: SdkCompatConfig
    responses: SdkCompatConfig

    # Authentication
    api_key_template: str
    supports_api_key: bool
    open_model_endpoint: bool

    # Dynamic model fetching
    fetch_models: bool
    models_endpoint: str
    model_parser: ModelParserConfig

    # Legacy field (kept for backward compat, should be empty)
    models: list[dict[str, Any]]


KNOWN_PROVIDERS: dict[str, KnownProviderConfig] = {
    "cerebras": {
        "display_name": "Cerebras",
        "description": "Cerebras - Fast inference",
        "family": "Cerebras",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.cerebras.ai/v1"},
        "api_key_template": "CEREBRAS_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 15,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "chutes": {
        "display_name": "Chutes AI",
        "description": "Chutes AI endpoint integration",
        "family": "Chutes AI",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://llm.chutes.ai/v1"},
        "supports_api_key": True,
        "api_key_template": "CHUTES_API_KEY",
        "open_model_endpoint": True,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "description": "DeepSeek model family",
        "family": "DeepSeek",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.deepseek.com/v1"},
        "anthropic": {"base_url": "https://api.deepseek.com/anthropic"},
        "api_key_template": "DEEPSEEK_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "groq": {
        "display_name": "Groq",
        "description": "Groq - High-speed inference",
        "family": "Groq",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.groq.com/openai/v1"},
        "api_key_template": "GROQ_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 15,
            "id_field": "id",
            "name_field": "id",
            "context_length_field": "context_window",
        },
    },
    "huggingface": {
        "display_name": "Hugging Face",
        "description": "Hugging Face Router endpoint integration",
        "family": "Hugging Face",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://router.huggingface.co/v1"},
        "supports_api_key": True,
        "api_key_template": "HUGGINGFACE_API_KEY",
        "open_model_endpoint": True,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 15,
            "id_field": "id",
            "name_field": "id",
            "context_length_field": "context_length",
        },
    },
    "kilocode": {
        "display_name": "Kilo Code",
        "description": "Kilo Code - Multi-model access via OpenRouter",
        "family": "Kilo Code",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.kilo.ai/api/openrouter"},
        "api_key_template": "KILOCODE_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "name",
            "context_length_field": "context_length",
        },
    },
    "knox": {
        "display_name": "Knox",
        "description": "Knox Chat - OpenAI SDK compatible endpoint",
        "family": "Knox",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.knox.chat/v1"},
        "api_key_template": "KNOX_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": True,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "minimax": {
        "display_name": "MiniMax",
        "description": "MiniMax family models with coding endpoint options",
        "family": "MiniMax",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.minimaxi.com/v1"},
        "anthropic": {"base_url": "https://api.minimaxi.com/anthropic"},
        "api_key_template": "MINIMAX_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "mistral": {
        "display_name": "Mistral AI",
        "description": "Mistral AI model endpoints",
        "family": "Mistral",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.mistral.ai/v1"},
        "api_key_template": "MISTRAL_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "name",
            "context_length_field": "context_length",
        },
    },
    "moonshot": {
        "display_name": "MoonshotAI",
        "description": "MoonshotAI Kimi model family",
        "family": "Moonshot AI",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.moonshot.cn/v1"},
        "anthropic": {"base_url": "https://api.kimi.com/coding"},
        "api_key_template": "MOONSHOT_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "nvidia": {
        "display_name": "NVIDIA NIM",
        "description": "NVIDIA NIM hosted model endpoints",
        "family": "NVIDIA",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://integrate.api.nvidia.com/v1"},
        "api_key_template": "NVIDIA_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": True,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "ollama": {
        "display_name": "Ollama",
        "description": "Ollama - Local and cloud model runner",
        "family": "Ollama",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://ollama.com/v1"},
        "anthropic": {"base_url": "https://ollama.com"},
        "api_key_template": "",
        "supports_api_key": False,
        "open_model_endpoint": True,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "models",
            "cooldown_minutes": 5,
            "id_field": "name",
            "name_field": "name",
        },
    },
    "openai": {
        "display_name": "OpenAI",
        "description": "OpenAI - GPT models",
        "family": "OpenAI",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://api.openai.com/v1"},
        "api_key_template": "OPENAI_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "opencode": {
        "display_name": "OpenCode",
        "description": "OpenCode endpoint integration",
        "family": "OpenCode",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://opencode.ai/zen/v1"},
        "anthropic": {"base_url": "https://opencode.ai/zen"},
        "supports_api_key": True,
        "api_key_template": "OPENCODE_API_KEY",
        "open_model_endpoint": True,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "description": "OpenRouter - Access to many third-party models",
        "family": "OpenRouter",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://openrouter.ai/api/v1"},
        "api_key_template": "OPENROUTER_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "name",
            "context_length_field": "context_length",
        },
    },
    "zhipu": {
        "display_name": "Zhipu AI",
        "description": "GLM family models and coding plan features",
        "family": "Zhipu AI",
        "sdk_mode": "openai",
        "openai": {"base_url": "https://open.bigmodel.cn/api/paas/v4"},
        "api_key_template": "ZHIPU_API_KEY",
        "supports_api_key": True,
        "open_model_endpoint": False,
        "fetch_models": True,
        "models_endpoint": "/models",
        "model_parser": {
            "array_path": "data",
            "cooldown_minutes": 10,
            "id_field": "id",
            "name_field": "id",
        },
    },
}


def get_known_provider(provider_name: str) -> KnownProviderConfig | None:
    return KNOWN_PROVIDERS.get(provider_name)


def get_provider_display_name(provider_name: str) -> str:
    provider = get_known_provider(provider_name)
    if provider is None:
        return provider_name
    name = provider.get("display_name")
    return name if isinstance(name, str) and name else provider_name


def get_provider_description(provider_name: str) -> str | None:
    provider = get_known_provider(provider_name)
    if provider is None:
        return None
    description = provider.get("description")
    return description if isinstance(description, str) and description else None


def get_provider_family(provider_name: str) -> str:
    provider = get_known_provider(provider_name)
    if provider is None:
        return provider_name
    family = provider.get("family")
    return family if isinstance(family, str) and family else provider_name


def get_provider_sdk_mode(provider_name: str) -> SdkMode:
    provider = get_known_provider(provider_name)
    if provider is None:
        return "openai"
    mode = provider.get("sdk_mode")
    return mode if mode in {"anthropic", "openai", "oai-response"} else "openai"


def get_provider_base_url(
    provider_name: str, sdk_mode: SdkMode | None = None
) -> str | None:
    """Get the base URL for a provider, optionally for a specific SDK mode."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return None

    mode = sdk_mode or get_provider_sdk_mode(provider_name)

    # Try SDK-specific URL first
    sdk_config = provider.get(mode)
    if isinstance(sdk_config, dict):
        url = sdk_config.get("base_url")
        if isinstance(url, str) and url:
            return url

    # Fallback to openai
    if mode != "openai":
        sdk_config = provider.get("openai")
        if isinstance(sdk_config, dict):
            url = sdk_config.get("base_url")
            if isinstance(url, str) and url:
                return url

    return None


def get_provider_custom_headers(
    provider_name: str, sdk_mode: SdkMode | None = None
) -> dict[str, str]:
    """Get custom headers for a provider's SDK mode."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return {}

    mode = sdk_mode or get_provider_sdk_mode(provider_name)
    sdk_config = provider.get(mode)
    if isinstance(sdk_config, dict):
        headers = sdk_config.get("custom_header")
        if isinstance(headers, dict):
            return dict(headers)

    return {}


def get_provider_extra_body(
    provider_name: str, sdk_mode: SdkMode | None = None
) -> dict[str, Any]:
    """Get extra body parameters for a provider's SDK mode."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return {}

    mode = sdk_mode or get_provider_sdk_mode(provider_name)
    sdk_config = provider.get(mode)
    if isinstance(sdk_config, dict):
        body = sdk_config.get("extra_body")
        if isinstance(body, dict):
            return dict(body)

    return {}


def should_fetch_models(provider_name: str) -> bool:
    """Check if a provider supports dynamic model fetching."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return False
    return bool(provider.get("fetch_models", False))


def get_models_endpoint(provider_name: str) -> str | None:
    """Get the models endpoint path for a provider."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return None
    endpoint = provider.get("models_endpoint")
    return endpoint if isinstance(endpoint, str) and endpoint else None


def get_model_parser(provider_name: str) -> ModelParserConfig | None:
    """Get the model parser configuration for a provider."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return None
    parser = provider.get("model_parser")
    return parser if isinstance(parser, dict) else None


def get_api_key_template(provider_name: str) -> str:
    """Get the API key template for a provider."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return "sk-xxxxxxxx"
    template = provider.get("api_key_template")
    return template if isinstance(template, str) and template else "sk-xxxxxxxx"


def supports_api_key(provider_name: str) -> bool:
    """Check if a provider supports API key authentication."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return True
    return bool(provider.get("supports_api_key", True))


def is_open_model_endpoint(provider_name: str) -> bool:
    """Check if a provider has an open/unauthenticated model endpoint."""
    provider = get_known_provider(provider_name)
    if provider is None:
        return False
    return bool(provider.get("open_model_endpoint", False))


def get_example_model(provider_name: str) -> str | None:
    """Get an example model name for a provider.

    Since models are dynamically fetched, this returns the provider's
    display_name as a representative identifier, or None.
    """
    provider = get_known_provider(provider_name)
    if provider is None:
        return None
    try:
        from revibe.core.llm.backend.providers.config import get_models_from_config

        models = get_models_from_config(provider_name)
        if models:
            alias = models[0].get("alias")
            if isinstance(alias, str) and alias:
                return alias
    except Exception:
        pass
    return None


def iter_known_models() -> Iterator[dict[str, Any]]:
    """Iterate over all hardcoded models (legacy, should be empty)."""
    for provider in KNOWN_PROVIDERS.values():
        yield from provider.get("models", [])


def get_provider_configs_from_registry() -> list[dict[str, Any]]:
    """Build ProviderConfig-compatible dicts from the KNOWN_PROVIDERS registry.

    This replaces hardcoded DEFAULT_PROVIDERS with a dynamic derivation from
    the registry, so adding a provider to KNOWN_PROVIDERS automatically
    makes it available in the UI.
    """
    configs: list[dict[str, Any]] = []
    for name, provider in KNOWN_PROVIDERS.items():
        base_url = get_provider_base_url(name)
        if not base_url:
            continue
        configs.append({
            "name": name,
            "display_name": provider.get("display_name", name),
            "api_base": base_url,
            "api_key_env_var": provider.get("api_key_template", ""),
            "api_style": "openai",
            "sdk_mode": provider.get("sdk_mode", "openai"),
            "family": provider.get("family", ""),
            "fetch_models": provider.get("fetch_models", False),
            "models_endpoint": provider.get("models_endpoint", ""),
        })
    return configs
