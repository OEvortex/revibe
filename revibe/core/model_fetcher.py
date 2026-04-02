"""Dynamic model fetching from provider APIs.

Inspired by better-copilot-chat's DynamicModelProvider. Fetches model lists
from provider APIs, parses responses using configurable field mappings,
resolves token limits, and persists results to JSON config files.

Models are auto-fetched on first use and cached with a cooldown. The JSON
config files under revibe/core/llm/backend/providers/config/ serve as the
offline fallback and are updated whenever fresh data is fetched.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any

import httpx

from revibe.core.llm.backend.known_providers import (
    ModelParserConfig,
    get_model_parser,
    get_models_endpoint,
    get_provider_base_url,
    get_provider_custom_headers,
    is_open_model_endpoint,
    should_fetch_models,
    supports_api_key,
)
from revibe.core.llm.context_manager import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_MAX_OUTPUT_TOKENS,
    resolve_advertised_token_limits,
    resolve_global_capabilities,
)
from revibe.core.model_config import ModelConfig

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_MINUTES = 10
DEFAULT_TIMEOUT_SECONDS = 15.0


def _get_config_dir() -> Path:
    return Path(__file__).parent / "core" / "llm" / "backend" / "providers" / "config"


class _ModelFetchCache:
    """Thread-safe cache for fetched models with cooldown tracking."""

    def __init__(self) -> None:
        self._last_fetch: dict[str, float] = {}
        self._cached_models: dict[str, list[ModelConfig]] = {}

    def is_stale(self, provider_name: str, cooldown_minutes: int) -> bool:
        if provider_name not in self._last_fetch:
            return True
        elapsed_minutes = (time.monotonic() - self._last_fetch[provider_name]) / 60.0
        return elapsed_minutes >= cooldown_minutes

    def get(self, provider_name: str) -> list[ModelConfig] | None:
        return self._cached_models.get(provider_name)

    def set(self, provider_name: str, models: list[ModelConfig]) -> None:
        self._last_fetch[provider_name] = time.monotonic()
        self._cached_models[provider_name] = models

    def invalidate(self, provider_name: str | None = None) -> None:
        if provider_name is None:
            self._last_fetch.clear()
            self._cached_models.clear()
        else:
            self._last_fetch.pop(provider_name, None)
            self._cached_models.pop(provider_name, None)


_fetch_cache = _ModelFetchCache()


def _resolve_json_path(data: Any, path: str) -> Any:
    """Resolve a dot-separated JSON path like 'data.models'."""
    if not path:
        return data
    current = data
    for segment in path.split("."):
        if not segment:
            continue
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return None
    return current


def _parse_model_entry(
    entry: dict[str, Any], provider_name: str, parser: ModelParserConfig
) -> dict[str, Any] | None:
    """Parse a single model entry from the API response into a ModelConfig-compatible dict."""
    id_field = parser.get("id_field", "id")
    name_field = parser.get("name_field", "id")

    model_id = entry.get(id_field)
    if not isinstance(model_id, str) or not model_id:
        return None

    model_name = entry.get(name_field, model_id)
    if not isinstance(model_name, str):
        model_name = model_id

    context_length_field = parser.get("context_length_field")
    context_length: int | None = None
    if context_length_field and context_length_field in entry:
        raw_ctx = entry[context_length_field]
        if isinstance(raw_ctx, (int, float)) and raw_ctx > 0:
            context_length = int(raw_ctx)

    # Also check common alternative fields
    if context_length is None:
        for alt_field in ("context_window", "max_tokens", "context_length"):
            if alt_field in entry:
                raw = entry[alt_field]
                if isinstance(raw, (int, float)) and raw > 0:
                    context_length = int(raw)
                    break

    # Resolve token limits
    limits = resolve_advertised_token_limits(
        model_id,
        context_length,
        default_context_length=DEFAULT_CONTEXT_LENGTH,
        default_max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
    )

    # Resolve capabilities
    capabilities = resolve_global_capabilities(model_id)

    # Extract tags if available
    tags_field = parser.get("tags_field")
    _tags: list[str] = []
    if tags_field and tags_field in entry:
        raw_tags = entry[tags_field]
        if isinstance(raw_tags, list):
            _tags = [str(t) for t in raw_tags if t]

    # Clean ID for use as alias
    clean_id = model_id.replace("/", "-").replace("\\", "-").replace(" ", "-").lower()

    return {
        "name": model_id,
        "provider": provider_name,
        "alias": clean_id,
        "context": limits.total_context_tokens,
        "max_output": limits.max_output_tokens,
        "supported_formats": ["native", "xml"],
        "supports_thinking": False,
        "capabilities": capabilities,
    }


def _parse_models_response(
    data: Any, provider_name: str, parser: ModelParserConfig
) -> list[ModelConfig]:
    """Parse the full API response into a list of ModelConfig objects."""
    array_path = parser.get("array_path", "data")
    entries = _resolve_json_path(data, array_path)

    if not isinstance(entries, list):
        return []

    filter_field = parser.get("filter_field")
    filter_value = parser.get("filter_value")

    models: list[ModelConfig] = []
    seen_ids: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        if filter_field and filter_value:
            entry_value = entry.get(filter_field)
            if str(entry_value) != filter_value:
                continue

        if parsed := _parse_model_entry(entry, provider_name, parser):
            alias = parsed.get("alias", "")
            if alias in seen_ids:
                continue
            seen_ids.add(alias)

            try:
                models.append(ModelConfig.model_validate(parsed))
            except Exception:
                continue

    return models


def _save_models_to_json(provider_name: str, models: list[ModelConfig]) -> None:
    """Save fetched models to a per-provider JSON config file.

    Format matches better-copilot-chat's provider config structure:
    { "displayName": "...", "models": [...], ... }
    """
    from revibe.core.llm.backend.known_providers import get_provider_display_name

    config_dir = _get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / f"{provider_name}.json"

    # Load existing config or create new
    existing: dict[str, Any] = {}
    if config_path.is_file():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            existing = {}

    # Build model list
    model_dicts = [m.model_dump(mode="json", exclude_none=True) for m in models]

    # Update config
    config = {
        "displayName": get_provider_display_name(provider_name),
        "models": model_dicts,
    }

    # Preserve any extra fields from existing config
    for key, value in existing.items():
        if key not in {"displayName", "models"}:
            config[key] = value

    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info("Saved %d models to %s", len(models), config_path)
    except OSError as exc:
        logger.warning("Failed to save config for %s: %s", provider_name, exc)


def _load_models_from_json(provider_name: str) -> list[ModelConfig]:
    """Load cached models from a provider's JSON config file."""
    config_dir = _get_config_dir()
    config_path = config_dir / f"{provider_name}.json"

    if not config_path.is_file():
        return []

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, dict):
        return []

    models_data = data.get("models", [])
    if not isinstance(models_data, list):
        return []

    models: list[ModelConfig] = []
    for entry in models_data:
        if isinstance(entry, dict):
            try:
                models.append(ModelConfig.model_validate(entry))
            except Exception:
                continue
    return models


async def fetch_models_from_provider(  # noqa: PLR0911
    provider_name: str,
    api_key: str | None = None,
    *,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[ModelConfig]:
    """Fetch available models from a provider's /models endpoint.

    Args:
        provider_name: Name of the provider (e.g., 'openai', 'mistral').
        api_key: Optional API key for authentication.
        force: If True, bypass the cooldown cache.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of ModelConfig objects from the API, or empty list on failure.
    """
    # Check if provider supports fetching
    if not should_fetch_models(provider_name):
        cached = _load_models_from_json(provider_name)
        _fetch_cache.set(provider_name, cached)
        return cached

    parser = get_model_parser(provider_name)
    if parser is None:
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)

    cooldown = parser.get("cooldown_minutes", DEFAULT_COOLDOWN_MINUTES)

    # Check cooldown
    if not force and not _fetch_cache.is_stale(provider_name, cooldown):
        if cached := _fetch_cache.get(provider_name):
            return cached

    # Check if we need an API key
    if (
        not api_key
        and supports_api_key(provider_name)
        and not is_open_model_endpoint(provider_name)
    ):
        # Load from JSON cache instead
        json_models = _load_models_from_json(provider_name)
        if json_models:
            _fetch_cache.set(provider_name, json_models)
        return json_models

    # Get endpoint URL
    endpoint = get_models_endpoint(provider_name)
    if not endpoint:
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)

    api_base = get_provider_base_url(provider_name)
    if not api_base:
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)

    # Build URL (endpoint can be full URL or path)
    url = (
        endpoint if endpoint.startswith("http") else f"{api_base.rstrip('/')}{endpoint}"
    )

    # Build headers
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    headers.update(get_provider_custom_headers(provider_name))
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=2, max_connections=5),
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        models = _parse_models_response(data, provider_name, parser)
        if models:
            _fetch_cache.set(provider_name, models)
            _save_models_to_json(provider_name, models)
            logger.info("Fetched %d models from %s", len(models), provider_name)
        else:
            # Fall back to JSON cache
            json_models = _load_models_from_json(provider_name)
            if json_models:
                _fetch_cache.set(provider_name, json_models)
                return json_models
        return models

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP error fetching models from %s: %s %s",
            provider_name,
            exc.response.status_code,
            exc.response.reason_phrase,
        )
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)
    except httpx.RequestError as exc:
        logger.warning("Request error fetching models from %s: %s", provider_name, exc)
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)
    except Exception:
        logger.exception("Unexpected error fetching models from %s", provider_name)
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)


async def fetch_all_provider_models(
    providers: list[tuple[str, str | None]],
    *,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[ModelConfig]]:
    """Fetch models from multiple providers concurrently.

    Args:
        providers: List of (provider_name, api_key) tuples.
        force: If True, bypass cooldown caches.
        timeout: HTTP request timeout per provider.

    Returns:
        Dict mapping provider names to their fetched ModelConfig lists.
    """
    tasks = [
        fetch_models_from_provider(name, key, force=force, timeout=timeout)
        for name, key in providers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output: dict[str, list[ModelConfig]] = {}
    for (name, _), result in zip(providers, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("Failed to fetch models for %s: %s", name, result)
            output[name] = []
        else:
            output[name] = result
    return output


def fetch_models_sync(
    provider_name: str,
    api_key: str | None = None,
    *,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[ModelConfig]:
    """Synchronous wrapper for fetch_models_from_provider."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.debug(
            "Running event loop detected; returning cached models for %s", provider_name
        )
        return _fetch_cache.get(provider_name) or _load_models_from_json(provider_name)

    return asyncio.run(
        fetch_models_from_provider(provider_name, api_key, force=force, timeout=timeout)
    )


def invalidate_cache(provider_name: str | None = None) -> None:
    """Invalidate the model fetch cache for a provider or all providers."""
    _fetch_cache.invalidate(provider_name)


def load_all_cached_models() -> dict[str, list[ModelConfig]]:
    """Load all cached models from JSON config files."""
    from revibe.core.llm.backend.providers.config import load_all_provider_configs

    configs = load_all_provider_configs()
    result: dict[str, list[ModelConfig]] = {}

    for provider_name, config in configs.items():
        models_data = config.get("models", [])
        if not isinstance(models_data, list):
            continue
        models: list[ModelConfig] = []
        for entry in models_data:
            if isinstance(entry, dict):
                try:
                    models.append(ModelConfig.model_validate(entry))
                except Exception:
                    continue
        if models:
            result[provider_name] = models

    return result
