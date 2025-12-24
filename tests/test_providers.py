from __future__ import annotations

from revibe.core.config import DEFAULT_PROVIDERS, VibeConfig


def test_default_providers_include_huggingface() -> None:
    assert any(p.name == "huggingface" for p in DEFAULT_PROVIDERS)


def test_vibeconfig_providers_include_huggingface() -> None:
    # Use model_construct to avoid validators that require API keys
    config = VibeConfig.model_construct()
    assert any(p.name == "huggingface" for p in config.providers)
