from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from revibe.core.llm.backend.openai import OpenAIBackend

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class OpenRouterBackend(OpenAIBackend):
    """OpenRouter backend that supports both native and XML tool calling formats.

    OpenRouter provides an OpenAI-compatible API at https://openrouter.ai/api/v1
    and supports various models with both native tool calling and XML-based approaches.
    """

    def __init__(
        self,
        provider: ProviderConfigUnion,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 720.0,
    ) -> None:
        super().__init__(provider=provider, client=client, timeout=timeout)
