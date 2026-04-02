from __future__ import annotations

from revibe.cli.textual_ui.widgets.provider_selector import ProviderSelector
from revibe.core.config import ProviderConfig, VibeConfig


def test_provider_selector_merges_defaults() -> None:
    # Create a config with a minimal provider set
    cfg = VibeConfig.model_construct(
        providers=[
            ProviderConfig(
                name="mistral",
                api_base="https://api.mistral.ai/v1",
                api_key_env_var="MISTRAL_API_KEY",
                sdk_mode="openai",
            ),
            ProviderConfig(
                name="llamacpp", api_base="http://127.0.0.1:8080/v1", sdk_mode="openai"
            ),
        ]
    )

    selector = ProviderSelector(cfg)
    names = [p.name for p in selector.providers]

    # Ensure defaults are present even when the config only provided a subset
    assert "openai" in names
    assert "mistral" in names
    assert "llamacpp" in names
