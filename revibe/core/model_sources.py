"""Model discovery and loading from multiple sources.

Model sources (in priority order):
1. Per-provider JSON config files (auto-fetched models)
2. User-defined TOML files in ~/.revibe/models/

Dynamic model fetching from provider APIs is handled via model_fetcher.py.
"""

from __future__ import annotations

import logging
from pathlib import Path
import tomllib

from revibe.core.model_config import ModelConfig
from revibe.core.paths.config_paths import MODEL_DIR

logger = logging.getLogger(__name__)


def _load_model_file(path: Path) -> ModelConfig | None:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return None

    if isinstance(raw, dict) and isinstance(raw.get("model"), dict):
        raw = raw["model"]

    if not isinstance(raw, dict):
        return None

    try:
        return ModelConfig.model_validate(raw)
    except Exception:
        return None


def _discover_model_files(model_dir: Path) -> list[ModelConfig]:
    if not model_dir.is_dir():
        return []

    models: list[ModelConfig] = []
    for path in sorted(model_dir.glob("*.toml")):
        if (model := _load_model_file(path)) is not None:
            models.append(model)
    return models


def _unique_models(models: list[ModelConfig]) -> list[ModelConfig]:
    deduped: dict[tuple[str, str], ModelConfig] = {}
    for model in models:
        deduped[(model.provider, model.alias)] = model
    return list(deduped.values())


def _load_json_provider_models() -> list[ModelConfig]:
    """Load models from per-provider JSON config files."""
    try:
        from revibe.core.llm.backend.providers.config import load_all_provider_configs
    except ImportError:
        return []

    configs = load_all_provider_configs()
    models: list[ModelConfig] = []

    for _provider_name, config in configs.items():
        models_data = config.get("models", [])
        if not isinstance(models_data, list):
            continue
        for entry in models_data:
            if isinstance(entry, dict):
                try:
                    models.append(ModelConfig.model_validate(entry))
                except Exception:
                    continue

    return models


def get_available_models() -> list[ModelConfig]:
    """Get all available models from JSON configs and TOML files.

    This is the primary model loading path. Models come from:
    1. Per-provider JSON config files (auto-fetched from APIs)
    2. User-defined TOML files in ~/.revibe/models/
    """
    models: list[ModelConfig] = []

    # Load from JSON provider configs
    models.extend(_load_json_provider_models())

    # Load from user TOML files
    try:
        model_dir = MODEL_DIR.path
    except RuntimeError:
        return _unique_models(models)

    if model_dir.is_dir():
        models.extend(_discover_model_files(model_dir))

    return _unique_models(models)


async def get_models_with_dynamic_fetch_async(
    providers: list[tuple[str, str | None]] | None = None,
) -> list[ModelConfig]:
    """Get models with dynamic fetching from provider APIs.

    Fetches models from providers that support it, then combines with
    existing JSON config and TOML file models.

    Args:
        providers: Optional list of (provider_name, api_key) tuples.

    Returns:
        Deduplicated list of ModelConfig objects.
    """
    # Start with existing models from JSON configs and TOML files
    models = list(get_available_models())

    if not providers:
        return models

    from revibe.core.llm.backend.known_providers import should_fetch_models
    from revibe.core.model_fetcher import fetch_all_provider_models

    fetchable = [(name, key) for name, key in providers if should_fetch_models(name)]

    if not fetchable:
        return models

    results = await fetch_all_provider_models(fetchable)
    for provider_name, fetched_models in results.items():
        if fetched_models:
            models.extend(fetched_models)
            logger.info(
                "Added %d dynamically fetched models from %s",
                len(fetched_models),
                provider_name,
            )

    return _unique_models(models)


def sync_fetch_all_models(
    providers: list[tuple[str, str | None]] | None = None,
) -> list[ModelConfig]:
    """Synchronously fetch and load all models.

    For each provider that supports dynamic fetching, attempts to fetch
    models. Falls back to cached JSON configs on failure.

    Args:
        providers: Optional list of (provider_name, api_key) tuples.

    Returns:
        Deduplicated list of ModelConfig objects.
    """
    from revibe.core.llm.backend.known_providers import should_fetch_models
    from revibe.core.model_fetcher import fetch_models_sync

    # Load existing models
    models = list(get_available_models())

    if not providers:
        return models

    for provider_name, api_key in providers:
        if not should_fetch_models(provider_name):
            continue

        fetched = fetch_models_sync(provider_name, api_key)
        if fetched:
            models.extend(fetched)

    return _unique_models(models)
