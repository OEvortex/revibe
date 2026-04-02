from __future__ import annotations

from pathlib import Path
import tomllib

from revibe.core.model_config import DEFAULT_MODELS, ModelConfig
from revibe.core.paths.config_paths import MODEL_DIR


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


def get_available_models() -> list[ModelConfig]:
    models = list(DEFAULT_MODELS)

    try:
        model_dir = MODEL_DIR.path
    except RuntimeError:
        return _unique_models(models)

    if model_dir.is_dir():
        models.extend(_discover_model_files(model_dir))

    return _unique_models(models)
