from __future__ import annotations

import os
from unittest.mock import patch

from revibe.core.config import MistralProviderConfig
from revibe.setup.onboarding.provider_info import (
    build_provider_description,
    check_key_status,
    get_example_model,
    mask_key,
)


def test_mask_key() -> None:
    assert mask_key("1234567890") == "1234...7890"
    assert mask_key("short") == "*****"


def test_check_key_status() -> None:
    provider_no_key = MistralProviderConfig(
        name="test", api_base="https://test.com", api_key_env_var=""
    )
    assert check_key_status(provider_no_key) == "Not required"

    provider_with_key = MistralProviderConfig(
        name="test", api_base="https://test.com", api_key_env_var="TEST_KEY"
    )

    with patch.dict(os.environ, {"TEST_KEY": "value"}):
        assert check_key_status(provider_with_key) == "Configured"

    with patch.dict(os.environ, {}, clear=True):
        assert check_key_status(provider_with_key) == "Not configured"


def test_get_example_model() -> None:
    # Assuming DEFAULT_MODELS has mistral models
    assert get_example_model("mistral") == "devstral-2"
    assert get_example_model("nonexistent") is None


def test_build_provider_description_basic() -> None:
    provider = MistralProviderConfig(
        name="mistral",
        api_base="https://api.mistral.ai/v1",
        api_key_env_var="MISTRAL_API_KEY",
    )

    with patch.dict(os.environ, {}, clear=True):
        desc = build_provider_description(provider, show_details=False)
    lines = desc.split("\n")
    assert "[bold]Mistral AI - Devstral models[/]" in lines[0]
    assert "Auth: API key (MISTRAL_API_KEY) - Not configured" in lines[1]


def test_build_provider_description_with_details() -> None:
    provider = MistralProviderConfig(
        name="mistral",
        api_base="https://api.mistral.ai/v1",
        api_key_env_var="MISTRAL_API_KEY",
    )

    desc = build_provider_description(provider, show_details=True)
    lines = desc.split("\n")
    assert "API Base: https://api.mistral.ai/v1" in lines[2]
    assert "Example Model: devstral-2" in lines[3]
