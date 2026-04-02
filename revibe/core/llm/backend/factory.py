"""Backend factory — maps sdk_mode to the correct backend class.

All providers are OpenAI-compatible, Anthropic-compatible, or use the
OpenAI Responses API. The sdk_mode field on the provider config determines
which backend class handles requests.
"""

from __future__ import annotations

from typing import Any

from revibe.core.llm.backend.anthropic import AnthropicBackend
from revibe.core.llm.backend.oai import OAIBackend
from revibe.core.llm.backend.openai import OpenAIBackend

SDK_MODE_BACKEND: dict[str, type] = {
    "openai": OpenAIBackend,
    "anthropic": AnthropicBackend,
    "oai-response": OAIBackend,
}


def get_backend_for_provider(provider: Any) -> type:
    """Get the backend class for a provider based on its sdk_mode.

    Args:
        provider: Provider config object with an sdk_mode field.

    Returns:
        The backend class to instantiate.
    """
    sdk_mode = getattr(provider, "sdk_mode", "openai")
    return SDK_MODE_BACKEND.get(sdk_mode, OpenAIBackend)
