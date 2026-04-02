"""Per-provider JSON model config files.

Fetched models are stored here as {provider_name}.json files.
Each file contains a ProviderConfig-compatible dict with a 'models' list.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent


def get_provider_config_path(provider_name: str) -> Path:
    """Get the JSON config file path for a provider."""
    return CONFIG_DIR / f"{provider_name}.json"


def load_provider_config(provider_name: str) -> dict[str, Any] | None:
    """Load a provider's JSON config file."""
    path = get_provider_config_path(provider_name)
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load provider config %s: %s", provider_name, exc)
        return None


def save_provider_config(provider_name: str, config: dict[str, Any]) -> None:
    """Save a provider's config to its JSON file."""
    path = get_provider_config_path(provider_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info(
            "Saved provider config %s with %d models",
            provider_name,
            len(config.get("models", [])),
        )
    except OSError as exc:
        logger.warning("Failed to save provider config %s: %s", provider_name, exc)


def load_all_provider_configs() -> dict[str, dict[str, Any]]:
    """Load all provider JSON config files from the config directory."""
    configs: dict[str, dict[str, Any]] = {}
    if not CONFIG_DIR.is_dir():
        return configs

    for path in sorted(CONFIG_DIR.glob("*.json")):
        provider_name = path.stem
        if config := load_provider_config(provider_name):
            configs[provider_name] = config

    return configs


def get_models_from_config(provider_name: str) -> list[dict[str, Any]]:
    """Get the models list from a provider's JSON config file."""
    config = load_provider_config(provider_name)
    if config is None:
        return []
    models = config.get("models", [])
    return models if isinstance(models, list) else []
