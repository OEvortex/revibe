from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import os
import types
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

import httpx

from revibe.core.llm.backend.anthropic import (
    ANTHROPIC_ADAPTERS,
    AnthropicAdapterProtocol,
)
from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableTool,
    LLMChunk,
    LLMMessage,
    Role,
    StrToolChoice,
)
from revibe.core.utils import async_generator_retry, async_retry

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfigUnion


class AnthropicBackend:
    """Anthropic SDK-compatible backend for LLM interactions.

    This backend implements the Anthropic API format, supporting:
    - Streaming responses
    - Tool/function calling
    - Thinking content (for supported models)
    - Cache control markers
    - Image content
    """

    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    def __init__(
        self,
        provider: ProviderConfigUnion,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 720.0,
    ) -> None:
        """Initialize the Anthropic backend.

        Args:
            provider: Provider configuration with API base and credentials.
            client: Optional httpx client to use. If not provided, one will be created.
            timeout: Request timeout in seconds.
        """
        self._client = client
        self._owns_client = client is None
        self._provider = provider
        self._timeout = timeout

    def _provider_headers(self) -> dict[str, str]:
        custom_headers = getattr(self._provider, "custom_header", {}) or {}
        return dict(custom_headers)

    def _provider_extra_body(self) -> dict[str, Any]:
        extra_body = getattr(self._provider, "extra_body", {}) or {}
        return dict(extra_body)

    async def __aenter__(self) -> AnthropicBackend:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
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

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
            self._owns_client = True
        return self._client

    def _get_adapter(self) -> AnthropicAdapterProtocol:
        """Get the Anthropic adapter based on provider configuration."""
        api_style = getattr(self._provider, "api_style", "anthropic")
        return ANTHROPIC_ADAPTERS.get(api_style, ANTHROPIC_ADAPTERS["anthropic"])

    def _get_api_key(self) -> str | None:
        """Get API key from environment variable."""
        if self._provider.api_key_env_var:
            return os.getenv(self._provider.api_key_env_var)
        return None

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        base_url = self._provider.api_base.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}"

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
        """Complete a chat conversation using Anthropic API.

        Args:
            model: Model configuration.
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0 to 1.0).
            tools: Optional list of available tools.
            max_tokens: Maximum tokens to generate.
            tool_choice: How to choose tools (auto, none, or specific tool).
            extra_headers: Additional HTTP headers to include.

        Returns:
            LLMChunk containing the response message and usage information.

        Raises:
            BackendError: If the API request fails.
        """
        api_key = self._get_api_key()
        adapter = self._get_adapter()

        # Default max_tokens for non-streaming
        if max_tokens is None:
            max_tokens = 4096

        endpoint, headers, body = adapter.prepare_request(
            model_name=model.name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            enable_streaming=False,
            provider=self._provider,
            api_key=api_key,
        )

        headers.update(self._provider_headers())
        if extra_body := self._provider_extra_body():
            body = self._merge_request_body(body, extra_body)
        if extra_headers:
            headers.update(extra_headers)

        url = self._build_url(endpoint)

        try:
            res_data, _ = await self._make_request(url, body, headers)
            return adapter.parse_response(res_data)

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=url,
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
                endpoint=url,
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
        """Streaming version of complete method.

        Args:
            model: Model configuration.
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0 to 1.0).
            tools: Optional list of available tools.
            max_tokens: Maximum tokens to generate.
            tool_choice: How to choose tools (auto, none, or specific tool).
            extra_headers: Additional HTTP headers to include.

        Yields:
            LLMChunk containing response chunks and usage information.

        Raises:
            BackendError: If the API request fails.
        """
        api_key = self._get_api_key()
        adapter = self._get_adapter()

        # Default max_tokens for streaming (Anthropic requires this)
        if max_tokens is None:
            max_tokens = 4096

        endpoint, headers, body = adapter.prepare_request(
            model_name=model.name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            enable_streaming=True,
            provider=self._provider,
            api_key=api_key,
        )

        headers.update(self._provider_headers())
        if extra_body := self._provider_extra_body():
            body = self._merge_request_body(body, extra_body)
        if extra_headers:
            headers.update(extra_headers)

        url = self._build_url(endpoint)

        try:
            async for res_data in self._make_streaming_request(url, body, headers):
                chunk = adapter.parse_stream_chunk(res_data)
                if chunk is not None:
                    yield chunk

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=url,
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
                endpoint=url,
                error=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

    class HTTPResponse(NamedTuple):
        data: dict[str, Any]
        headers: dict[str, str]

    @async_retry(tries=3)
    async def _make_request(
        self, url: str, data: bytes, headers: dict[str, str]
    ) -> HTTPResponse:
        """Make a non-streaming HTTP request."""
        client = self._get_client()
        response = await client.post(url, content=data, headers=headers)
        response.raise_for_status()

        response_headers = dict(response.headers.items())
        response_json = response.json()
        return self.HTTPResponse(response_json, response_headers)

    @async_generator_retry(tries=3)
    async def _make_streaming_request(
        self, url: str, data: bytes, headers: dict[str, str]
    ) -> AsyncGenerator[dict[str, Any]]:
        """Make a streaming HTTP request and yield parsed chunks."""
        client = self._get_client()
        async with client.stream(
            method="POST", url=url, content=data, headers=headers
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip() == "":
                    continue

                DELIM_CHAR = ":"
                if f"{DELIM_CHAR} " not in line:
                    continue

                delim_index = line.find(DELIM_CHAR)
                key = line[0:delim_index]
                value = line[delim_index + 2 :]

                if key != "data":
                    continue
                if value == "[DONE]":
                    return

                yield json.loads(value.strip())

    @staticmethod
    def _merge_request_body(body: bytes, extra_body: dict[str, Any]) -> bytes:
        payload = json.loads(body.decode("utf-8"))
        AnthropicBackend._merge_dicts(payload, extra_body)
        return json.dumps(payload).encode("utf-8")

    @staticmethod
    def _merge_dicts(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                AnthropicBackend._merge_dicts(target[key], value)
            else:
                target[key] = value

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
        """Count tokens in the messages (approximation)."""
        probe_messages = list(messages)
        if not probe_messages or probe_messages[-1].role != Role.user:
            probe_messages.append(LLMMessage(role=Role.user, content=""))

        result = await self.complete(
            model=model,
            messages=probe_messages,
            temperature=temperature,
            tools=tools,
            max_tokens=16,  # Minimal amount
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )
        if result.usage is None:
            msg = "Missing usage in non streaming completion"
            raise ValueError(msg)

        return result.usage.prompt_tokens

    async def list_models(self) -> list[str]:
        """List available models from the provider."""
        api_key = self._get_api_key()
        headers: dict[str, str] = {"anthropic-version": "2023-06-01"}

        if api_key:
            headers["x-api-key"] = api_key
            headers["Authorization"] = f"Bearer {api_key}"

        base_url = self._provider.api_base.rstrip("/")
        url = f"{base_url}/models"

        try:
            client = self._get_client()
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return [m.get("id", "") for m in data if m.get("id")]
            if isinstance(data, dict) and "data" in data:
                return [m.get("id", "") for m in data["data"] if m.get("id")]
            return []

        except Exception:
            return []

    async def close(self) -> None:
        """Close the HTTP client if owned by this backend."""
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
