from __future__ import annotations

from pathlib import Path

import tomli_w

from revibe.core.config import SessionLoggingConfig, VibeConfig
from revibe.core.model_sources import get_available_models


def test_get_available_models_discovers_custom_model(config_dir: Path) -> None:
    model_dir = config_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "analysis.toml").write_text(
        tomli_w.dumps({
            "name": "analysis-model",
            "provider": "mistral",
            "alias": "analysis",
            "context": 123_456,
        }),
        encoding="utf-8",
    )

    models = get_available_models()

    assert any(model.alias == "analysis" for model in models)


def test_vibe_config_models_include_custom_model(config_dir: Path) -> None:
    model_dir = config_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "analysis.toml").write_text(
        tomli_w.dumps({
            "name": "analysis-model",
            "provider": "mistral",
            "alias": "analysis",
            "context": 123_456,
        }),
        encoding="utf-8",
    )

    config = VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
        include_prompt_detail=False,
    )

    assert any(model.alias == "analysis" for model in config.models)
