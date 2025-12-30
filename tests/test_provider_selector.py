from __future__ import annotations

from revibe.cli.textual_ui.widgets.provider_selector import ProviderSelector
from revibe.core.config import (
    LlamaCppProviderConfig,
    MistralProviderConfig,
    VibeConfig,
)


def test_provider_selector_merges_defaults() -> None:
    # Create a config with a minimal provider set
    cfg = VibeConfig.model_construct(
        providers=[
            MistralProviderConfig(name="mistral", api_base="https://api.mistral.ai/v1"),
            LlamaCppProviderConfig(name="llamacpp", api_base="http://127.0.0.1:8080/v1"),
        ]
    )

    selector = ProviderSelector(cfg)
    names = [p.name for p in selector.providers]

    # Ensure defaults are present even when the config only provided a subset
    assert "openai" in names
    assert "huggingface" in names
    assert "mistral" in names
    assert "llamacpp" in names
