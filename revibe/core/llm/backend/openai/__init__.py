"""OpenAI Backend.

Implements streaming chat completion using OpenAI-compatible API.
Based on OEvortex/better-copilot-chat implementation.

Features:
- OpenAI-compatible chat completions API
- Streaming with SSE normalization
- Native tool calls support
- Token usage tracking
- Python-style completion chunk handling
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import os
import types
from typing import TYPE_CHECKING, Any, ClassVar

import httpx

from revibe.core.llm.backend.openai.handler import OpenAIHandler
from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableTool,
    LLMChunk,
    LLMMessage,
    Role,
    StrToolChoice,
)
from revibe.core.utils import (
    async_generator_retry as async_generator_retry,
    async_retry as async_retry,
)

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfigUnion


class OpenAIBackend:
    """Backend for OpenAI-compatible API.

    Features:
    - OpenAI-compatible chat completions API
    - Streaming with SSE normalization
    - Native tool calls support
    - Token usage tracking
    """

    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    def __init__(
        self,
        provider: ProviderConfigUnion,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 720.0,
    ) -> None:
        """Initialize the backend.

        Args:
            provider: Provider configuration.
            client: Optional httpx client to use. If not provided, one will be created.
            timeout: Request timeout in seconds.
        """
        self._client = client
        self._owns_client = client is None
        self._provider = provider
        self._timeout = timeout
        self._handler: OpenAIHandler | None = None

    def _provider_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        custom_headers = getattr(self._provider, "custom_header", {}) or {}
        headers.update(custom_headers)
        return headers

    def _provider_extra_body(self) -> dict[str, Any]:
        extra_body = getattr(self._provider, "extra_body", {}) or {}
        return dict(extra_body)

    async def __aenter__(self) -> OpenAIBackend:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        self._handler = OpenAIHandler(
            client=self._client,
            base_url=self._provider.api_base,
            headers=self._provider_headers(),
            extra_body=self._provider_extra_body(),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
        self._handler = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
            self._owns_client = True
        return self._client

    def _get_handler(self) -> OpenAIHandler:
        if self._handler is None:
            client = self._get_client()
            self._handler = OpenAIHandler(
                client=client,
                base_url=self._provider.api_base,
                headers=self._provider_headers(),
                extra_body=self._provider_extra_body(),
            )
        return self._handler

    def _get_api_key(self) -> str | None:
        """Get API key from environment."""
        if self._provider.api_key_env_var:
            return os.getenv(self._provider.api_key_env_var)
        return None

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
        """Make a non-streaming completion request.

        Args:
            model: Model configuration.
            messages: List of messages.
            temperature: Temperature for generation.
            tools: Available tools.
            max_tokens: Maximum tokens to generate.
            tool_choice: Tool choice strategy.
            extra_headers: Extra headers to include.

        Returns:
            LLMChunk with response.
        """
        api_key = self._get_api_key()
        handler = self._get_handler()

        try:
            return await handler.complete(
                model_name=model.name,
                messages=messages,
                temperature=temperature,
                tools=tools,
                max_tokens=max_tokens,
                tool_choice=tool_choice,
                api_key=api_key,
                extra_headers=extra_headers,
            )

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                response=e.response,
                headers=e.response.headers,
                model=model.name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                error=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

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
        """Make a streaming completion request.

        Args:
            model: Model configuration.
            messages: List of messages.
            temperature: Temperature for generation.
            tools: Available tools.
            max_tokens: Maximum tokens to generate.
            tool_choice: Tool choice strategy.
            extra_headers: Extra headers to include.

        Yields:
            LLMChunk for each chunk in the stream.
        """
        api_key = self._get_api_key()
        handler = self._get_handler()

        try:
            async for chunk in handler.complete_streaming(
                model_name=model.name,
                messages=messages,
                temperature=temperature,
                tools=tools,
                max_tokens=max_tokens,
                tool_choice=tool_choice,
                api_key=api_key,
                extra_headers=extra_headers,
            ):
                yield chunk

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                response=e.response,
                headers=e.response.headers,
                model=model.name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                error=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

    async def count_tokens(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        tools: list[AvailableTool] | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> int:
        """Count tokens by making a probe request.

        Args:
            model: Model configuration.
            messages: List of messages.
            temperature: Temperature for generation.
            tools: Available tools.
            tool_choice: Tool choice strategy.
            extra_headers: Extra headers to include.

        Returns:
            Token count.
        """
        probe_messages = list(messages)
        if not probe_messages or probe_messages[-1].role != Role.user:
            probe_messages.append(LLMMessage(role=Role.user, content=""))

        result = await self.complete(
            model=model,
            messages=probe_messages,
            temperature=temperature,
            tools=tools,
            max_tokens=16,  # Minimal amount for token counting
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )

        if result.usage is None:
            raise ValueError("Missing usage in non streaming completion")

        return result.usage.prompt_tokens

    async def list_models(self) -> list[str]:
        """List available models from the API.

        Returns:
            List of model IDs.
        """
        api_key = self._get_api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        url = f"{self._provider.api_base.rstrip('/')}/models"

        try:
            client = self._get_client()
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return [m["id"] for m in data if "id" in m]
            if isinstance(data, dict) and "data" in data:
                return [m["id"] for m in data["data"] if "id" in m]
            return []

        except Exception:
            return []

    async def close(self) -> None:
        """Close the backend and cleanup resources."""
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
        self._handler = None
