from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from revibe.core.llm.backend.openai import OpenAIBackend
from revibe.core.types import AvailableTool, LLMChunk, LLMMessage, StrToolChoice

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfigUnion


class KiloCodeBackend(OpenAIBackend):
    def __init__(self, provider: ProviderConfigUnion, timeout: float = 720.0) -> None:
        super().__init__(provider=provider, timeout=timeout)

    async def complete(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> LLMChunk:
        # Add Kilo Code specific headers
        kilo_headers = {
            "X-KiloCode-Version": "4.140.2",
            "HTTP-Referer": "https://kilocode.ai",
            "X-Title": "Kilo Code",
            "User-Agent": "Kilo-Code/4.140.2"
        }

        if extra_headers:
            kilo_headers.update(extra_headers)

        return await super().complete(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=kilo_headers,
        )

    async def complete_streaming(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> AsyncGenerator[LLMChunk, None]:
        # Add Kilo Code specific headers
        kilo_headers = {
            "X-KiloCode-Version": "4.140.2",
            "HTTP-Referer": "https://kilocode.ai",
            "X-Title": "Kilo Code",
            "User-Agent": "Kilo-Code/4.140.2"
        }

        if extra_headers:
            kilo_headers.update(extra_headers)

        async for chunk in super().complete_streaming(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=kilo_headers,
        ):
            yield chunk
