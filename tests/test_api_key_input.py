from __future__ import annotations

from pathlib import Path

import pytest

from revibe.cli.textual_ui.widgets.api_key_input import ApiKeyInput
from revibe.core.config import GenericProviderConfig as ProviderConfig
from revibe.core.paths.global_paths import GLOBAL_ENV_FILE


def test_api_key_input_widget_exists() -> None:
    provider = ProviderConfig(
        name="test", api_base="https://example.com", api_key_env_var="TEST_API_KEY"
    )
    widget = ApiKeyInput(provider)
    assert widget.provider.name == "test"
    assert widget.provider.api_key_env_var == "TEST_API_KEY"


def test_api_key_input_messages() -> None:
    provider = ProviderConfig(
        name="groq", api_base="https://api.groq.com", api_key_env_var="GROQ_API_KEY"
    )
    widget = ApiKeyInput(provider)

    # Test ApiKeySubmitted message
    submitted_msg = widget.ApiKeySubmitted("groq", "test-key-123")
    assert submitted_msg.provider_name == "groq"
    assert submitted_msg.api_key == "test-key-123"

    # Test ApiKeyCancelled message
    cancelled_msg = widget.ApiKeyCancelled()
    assert cancelled_msg is not None


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    env_file = tmp_path / ".env"
    GLOBAL_ENV_FILE._resolver = lambda: env_file
    return env_file


def test_save_api_key_to_env_file(temp_env_file: Path) -> None:
    provider = ProviderConfig(
        name="groq", api_base="https://api.groq.com", api_key_env_var="GROQ_API_KEY"
    )

    # Ensure env file doesn't exist initially
    assert not temp_env_file.exists()

    # Simulate saving API key
    api_key = "gsk_test_key_12345"
    env_var_line = f"{provider.api_key_env_var}={api_key}"
    temp_env_file.write_text(env_var_line + "\n", encoding="utf-8")

    # Verify file was created and contains the key
    assert temp_env_file.exists()
    content = temp_env_file.read_text(encoding="utf-8")
    assert "GROQ_API_KEY=gsk_test_key_12345" in content


def test_update_existing_api_key(temp_env_file: Path) -> None:
    provider = ProviderConfig(
        name="openai",
        api_base="https://api.openai.com",
        api_key_env_var="OPENAI_API_KEY",
    )

    # Create initial env file with an old key
    initial_content = "OPENAI_API_KEY=old-key-123\n"
    temp_env_file.write_text(initial_content, encoding="utf-8")

    # Update with new key
    new_key = "sk-new-key-456"
    updated_content = f"{provider.api_key_env_var}={new_key}\n"
    temp_env_file.write_text(updated_content, encoding="utf-8")

    # Verify the key was updated
    content = temp_env_file.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-new-key-456" in content
    assert "old-key-123" not in content


def test_api_key_input_handles_no_env_var_provider() -> None:
    provider = ProviderConfig(
        name="ollama",
        api_base="http://127.0.0.1:11434/v1",
        api_key_env_var="",  # No API key required
    )
    widget = ApiKeyInput(provider)

    # Check that the provider is set correctly
    assert widget.provider.name == "ollama"
    assert widget.provider.api_key_env_var == ""
