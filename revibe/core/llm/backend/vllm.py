from __future__ import annotations

from typing import TYPE_CHECKING, Any

from revibe.core.config import ProviderConfig
from revibe.core.llm.backend.openai import OpenAIBackend
from revibe.core.types import LLMChunk, LLMMessage, StrToolChoice

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig


class VLLMBackend(OpenAIBackend):
    """vLLM backend for self-hosted model serving.

    Compatible with vLLM's OpenAI-compatible API server.
    """

    supported_formats: list[str] = ["openai"]

    def __init__(self, provider: ProviderConfig, timeout: float = 720.0) -> None:
        super().__init__(provider=provider, timeout=timeout)

    async def complete(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[Any] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | Any | None,
        extra_headers: dict[str, str] | None,
    ) -> LLMChunk:
        """Complete using vLLM endpoint."""
        return await super().complete(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )

    async def complete_streaming(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[Any] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | Any | None,
        extra_headers: dict[str, str] | None,
    ) -> Any:
        """Stream using vLLM endpoint."""
        async for chunk in super().complete_streaming(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        ):
            yield chunk

    async def list_models(self) -> list[str]:
        """List available models from vLLM server."""
        import os

        api_base = self.provider.api_base or "http://localhost:8000/v1"
        api_key = os.environ.get(self.provider.api_key_env_var, "")

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with self._client as client:
                response = await client.get(f"{api_base}/models", headers=headers)
                response.raise_for_status()
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []
