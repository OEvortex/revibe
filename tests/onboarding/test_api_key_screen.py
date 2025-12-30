from __future__ import annotations

from types import MethodType
from unittest.mock import Mock

import pytest

from revibe.core.config import GenericProviderConfig as ProviderConfig, VibeConfig
from revibe.core.model_config import ModelConfig
from revibe.setup.onboarding.screens.api_key import ApiKeyScreen


class TestApiKeyScreen:
    def test_on_show_skips_when_provider_has_no_api_key_env_var(self) -> None:
        """Test that ApiKeyScreen exits immediately when provider doesn't require API key."""
        # Create a mock config with a provider that has empty api_key_env_var
        provider = ProviderConfig(
            name="ollama",
            api_base="http://127.0.0.1:11434/v1",
            api_key_env_var="",  # No API key required
        )
        model = ModelConfig(name="llama3.2", provider="ollama", alias="llama3.2")
        config = VibeConfig(models=[model], providers=[provider])

        screen = ApiKeyScreen()
        screen._load_config = MethodType(lambda self: config, screen)  # Mock the config loading  # type: ignore[invalid-assignment]

        screen.app = Mock()
        screen.app.exit = Mock()

        # Call on_show
        screen.on_show()

        screen.app.exit.assert_called_with("completed")

    def test_on_show_does_not_skip_when_api_key_required(self) -> None:
        """Test that ApiKeyScreen does not exit when provider requires API key."""
        # Create a mock config with a provider that requires API key
        provider = ProviderConfig(
            name="openai",
            api_base="https://api.openai.com/v1",
            api_key_env_var="OPENAI_API_KEY",
        )
        model = ModelConfig(name="gpt-4", provider="openai", alias="gpt-4")
        config = VibeConfig(models=[model], providers=[provider])

        screen = ApiKeyScreen()
        screen._load_config = MethodType(lambda self: config, screen)  # Mock the config loading  # type: ignore[invalid-assignment]

        # Mock the app.exit method
        exit_called = False

        def mock_exit(value):
            nonlocal exit_called
            exit_called = True

        screen.app = type("MockApp", (), {"exit": mock_exit})()

        # Call on_show
        screen.on_show()

        # Should not have exited
        assert not exit_called
        # Provider should be set
        assert screen.provider is not None
        assert screen.provider.name == "openai"

    @pytest.mark.parametrize("provider_name", ["ollama", "llamacpp", "qwencode"])
    def test_skips_for_local_providers(self, provider_name: str) -> None:
        """Test that ApiKeyScreen skips for local providers without API key env vars."""
        # These providers have empty api_key_env_var in DEFAULT_PROVIDERS
        from revibe.core.config import DEFAULT_PROVIDERS

        provider = next(p for p in DEFAULT_PROVIDERS if p.name == provider_name)
        model = ModelConfig(
            name="test-model", provider=provider_name, alias="test-model"
        )
        config = VibeConfig(models=[model], providers=DEFAULT_PROVIDERS)

        screen = ApiKeyScreen()
        screen._load_config = MethodType(lambda self: config, screen)  # type: ignore[invalid-assignment]

        exit_called = False
        exit_value = None

        def mock_exit(value):
            nonlocal exit_called, exit_value
            exit_called = True
            exit_value = value

        screen.app = type("MockApp", (), {"exit": mock_exit})()

        screen.on_show()

        assert exit_called
        assert exit_value == "completed"
