"""Qwen Code handler - main backend implementation.

Based on Roo-Code qwen-code.ts implementation:
https://github.com/RooCodeInc/Roo-Code/blob/main/src/api/providers/qwen-code.ts

This handler implements:
- OAuth authentication with token refresh
- Streaming chat completions
- Thinking/reasoning block parsing (<think>...</think>)
- Native tool calls support
- Token usage tracking
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import types
from typing import TYPE_CHECKING, Any, ClassVar

import httpx

from revibe.core.llm.backend.qwen.oauth import QwenOAuthManager
from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableTool,
    FunctionCall,
    LLMChunk,
    LLMMessage,
    LLMUsage,
    Role,
    StrToolChoice,
    ToolCall,
)

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfigUnion

# HTTP Status codes for error handling
HTTP_UNAUTHORIZED = 401


class ThinkingBlockParser:
    """Parser for Qwen's thinking/reasoning blocks.

    Handles <think>...</think> tags in the stream to separate
    reasoning content from regular text content.
    """

    def __init__(self) -> None:
        self._in_thinking_block = False
        self._buffer = ""

    def parse(self, text: str) -> tuple[str, str]:
        """Parse text and separate thinking content from regular content.

        Args:
            text: The text to parse.

        Returns:
            Tuple of (regular_content, reasoning_content).
        """
        regular_content = ""
        reasoning_content = ""

        # Add to buffer and process
        self._buffer += text

        while True:
            if self._in_thinking_block:
                # Look for closing tag
                end_idx = self._buffer.find("</think>")
                if end_idx != -1:
                    reasoning_content += self._buffer[:end_idx]
                    self._buffer = self._buffer[end_idx + 8 :]  # len("</think>") = 8
                    self._in_thinking_block = False
                else:
                    # Still in thinking block, emit all as reasoning
                    reasoning_content += self._buffer
                    self._buffer = ""
                    break
            else:
                # Look for opening tag
                start_idx = self._buffer.find("<think>")
                if start_idx != -1:
                    regular_content += self._buffer[:start_idx]
                    self._buffer = self._buffer[start_idx + 7 :]  # len("<think>") = 7
                    self._in_thinking_block = True
                else:
                    # No thinking block, emit all as regular content
                    regular_content += self._buffer
                    self._buffer = ""
                    break

        return regular_content, reasoning_content


class QwenBackend:
    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    """Backend for Qwen Code API.

    Features:
    - OpenAI-compatible chat completions API
    - Streaming with thinking/reasoning blocks
    - Native tool calls support
    - Token usage tracking
    """

    def __init__(
        self,
        provider: ProviderConfigUnion,
        *,
        timeout: float = 720.0,
        oauth_path: str | None = None,
    ) -> None:
        """Initialize the Qwen backend.

        Args:
            provider: Provider configuration.
            timeout: Request timeout in seconds.
            oauth_path: Optional custom path to OAuth credentials.
        """
        self._provider = provider
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._owns_client = True

        # OAuth manager for Qwen CLI authentication
        self._oauth_manager = QwenOAuthManager(oauth_path)

    async def __aenter__(self) -> QwenBackend:
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

    async def _get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """Get authentication headers.

        Args:
            force_refresh: If True, forces a token refresh for OAuth.

        Returns headers with OAuth token.
        """
        headers = {"Content-Type": "application/json"}

        access_token, _ = await self._oauth_manager.ensure_authenticated(
            force_refresh=force_refresh
        )
        headers["Authorization"] = f"Bearer {access_token}"

        return headers

    async def _get_base_url(self) -> str:
        """Get the API base URL.

        Returns URL from OAuth credentials or default.
        """
        _, base_url = await self._oauth_manager.ensure_authenticated()
        return base_url.rstrip("/")

    def _prepare_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert LLMMessages to OpenAI-compatible format."""
        return [msg.model_dump(exclude_none=True) for msg in messages]

    def _prepare_tools(
        self, tools: list[AvailableTool] | None
    ) -> list[dict[str, Any]] | None:
        """Convert tools to OpenAI-compatible format."""
        if not tools:
            return None
        return [tool.model_dump(exclude_none=True) for tool in tools]

    def _prepare_tool_choice(
        self, tool_choice: StrToolChoice | AvailableTool | None
    ) -> str | dict[str, Any] | None:
        """Convert tool choice to OpenAI-compatible format."""
        if tool_choice is None:
            return None
        if isinstance(tool_choice, str):
            return tool_choice
        return tool_choice.model_dump()

    def _parse_tool_calls(
        self, tool_calls: list[dict[str, Any]] | None
    ) -> list[ToolCall] | None:
        """Parse tool calls from response."""
        if not tool_calls:
            return None
        return [
            ToolCall(
                id=tc.get("id"),
                index=tc.get("index"),
                function=FunctionCall(
                    name=tc.get("function", {}).get("name"),
                    arguments=tc.get("function", {}).get("arguments"),
                ),
            )
            for tc in tool_calls
        ]

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
        """Complete a chat request (non-streaming).

        Args:
            model: Model configuration.
            messages: Chat messages.
            temperature: Sampling temperature.
            tools: Available tools.
            max_tokens: Maximum output tokens.
            tool_choice: Tool selection strategy.
            extra_headers: Additional HTTP headers.

        Returns:
            LLMChunk with the completion.
        """
        return await self._complete_with_retry(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )

    async def _complete_with_retry(  # noqa: PLR0914
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        _retry_count: int = 0,
    ) -> LLMChunk:
        """Internal complete method with retry logic for auth failures."""
        force_refresh = _retry_count > 0
        headers = await self._get_auth_headers(force_refresh=force_refresh)
        if extra_headers:
            headers.update(extra_headers)

        base_url = await self._get_base_url()
        url = f"{base_url}/chat/completions"

        payload: dict[str, Any] = {
            "model": model.name,
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = self._prepare_tools(tools)
        if tool_choice:
            payload["tool_choice"] = self._prepare_tool_choice(tool_choice)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            client = self._get_client()
            response = await client.post(
                url, headers=headers, content=json.dumps(payload).encode("utf-8")
            )
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                body_text = response.text[:200] if response.text else "(empty response)"
                raise ValueError(f"Invalid JSON response from API: {body_text}") from e

            # Parse response
            choices = data.get("choices", [])
            if not choices:
                raise ValueError(f"API response missing choices: {data}")
            choice = choices[0]
            message_data = choice.get("message", {})
            usage_data = data.get("usage", {})

            # Handle reasoning content (<think> blocks or native reasoning_content)
            content = message_data.get("content", "")
            reasoning_content = message_data.get("reasoning_content")

            # Parse thinking blocks from content if present
            if "<think>" in content or "</think>" in content:
                parser = ThinkingBlockParser()
                regular, thinking = parser.parse(content)
                content = regular
                if thinking and not reasoning_content:
                    reasoning_content = thinking

            return LLMChunk(
                message=LLMMessage(
                    role=Role.assistant,
                    content=content,
                    reasoning_content=reasoning_content,
                    tool_calls=self._parse_tool_calls(message_data.get("tool_calls")),
                ),
                usage=LLMUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                ),
            )

        except httpx.HTTPStatusError as e:
            # Retry once with fresh token on 401 Unauthorized
            if (
                e.response.status_code == HTTP_UNAUTHORIZED
                and self._oauth_manager
                and _retry_count == 0
            ):
                return await self._complete_with_retry(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    tools=tools,
                    max_tokens=max_tokens,
                    tool_choice=tool_choice,
                    extra_headers=extra_headers,
                    _retry_count=1,
                )
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=url,
                response=e.response,
                headers=e.response.headers,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
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
                has_tools=bool(tools),
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
        """Complete a chat request with streaming.

        Args:
            model: Model configuration.
            messages: Chat messages.
            temperature: Sampling temperature.
            tools: Available tools.
            max_tokens: Maximum output tokens.
            tool_choice: Tool selection strategy.
            extra_headers: Additional HTTP headers.

        Yields:
            LLMChunk objects as they arrive.
        """
        # Try streaming with retry on 401
        async for chunk in self._complete_streaming_with_retry(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
            _retry_count=0,
        ):
            yield chunk

    def _build_streaming_payload(
        self,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
    ) -> dict[str, Any]:
        """Build the payload for streaming requests."""
        payload: dict[str, Any] = {
            "model": model.name,
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if tools:
            payload["tools"] = self._prepare_tools(tools)
        if tool_choice:
            payload["tool_choice"] = self._prepare_tool_choice(tool_choice)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        return payload

    def _parse_sse_line(self, line: str) -> tuple[str, str] | None:
        """Parse an SSE line and return (key, value) if valid."""
        if not line.strip():
            return None

        if ":" not in line:
            return None

        delim_index = line.find(":")
        key = line[:delim_index].strip()
        # Value starts after colon, with optional leading space
        value = line[delim_index + 1 :].lstrip()

        return key, value

    def _handle_chunk_data(
        self,
        chunk_data: dict[str, Any],
        delta: dict[str, Any],
        usage: dict[str, Any] | None,
        thinking_parser: ThinkingBlockParser,
        full_content: str,
    ) -> tuple[str, str, list[ToolCall] | None]:
        """Handle chunk data and extract content, reasoning, and tool calls."""
        content = ""
        reasoning_content = ""
        tool_calls = None

        # Handle content with potential thinking blocks
        if delta.get("content"):
            new_text = delta["content"]

            # Handle cumulative content (some providers send full content)
            if new_text.startswith(full_content):
                new_text = new_text[len(full_content) :]

            if new_text:
                # Parse thinking blocks
                regular, thinking = thinking_parser.parse(new_text)
                content = regular
                reasoning_content = thinking

        # Handle native reasoning_content field
        if delta.get("reasoning_content"):
            reasoning_content = delta["reasoning_content"]

        # Parse tool calls
        if delta.get("tool_calls"):
            tool_calls = [
                ToolCall(
                    id=tc.get("id"),
                    index=tc.get("index"),
                    function=FunctionCall(
                        name=tc.get("function", {}).get("name"),
                        arguments=tc.get("function", {}).get("arguments"),
                    ),
                )
                for tc in delta["tool_calls"]
            ]

        return content, reasoning_content, tool_calls

    def _create_llm_chunk(
        self,
        content: str,
        reasoning_content: str,
        tool_calls: list[ToolCall] | None,
        usage: dict[str, Any] | None,
    ) -> LLMChunk:
        """Create an LLMChunk from the parsed data."""
        return LLMChunk(
            message=LLMMessage(
                role=Role.assistant,
                content=content if content else None,
                reasoning_content=reasoning_content if reasoning_content else None,
                tool_calls=tool_calls,
            ),
            usage=LLMUsage(
                prompt_tokens=usage.get("prompt_tokens", 0) if usage else 0,
                completion_tokens=usage.get("completion_tokens", 0) if usage else 0,
            ),
        )

    async def _complete_streaming_with_retry(  # noqa: PLR0914
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        _retry_count: int = 0,
    ) -> AsyncGenerator[LLMChunk, None]:
        """Internal streaming method with retry logic for auth failures."""
        force_refresh = _retry_count > 0
        headers = await self._get_auth_headers(force_refresh=force_refresh)
        if extra_headers:
            headers.update(extra_headers)

        base_url = await self._get_base_url()
        url = f"{base_url}/chat/completions"

        payload = self._build_streaming_payload(
            model, messages, temperature, tools, max_tokens, tool_choice
        )

        thinking_parser = ThinkingBlockParser()
        full_content = ""

        try:
            client = self._get_client()
            async with client.stream(
                method="POST",
                url=url,
                headers=headers,
                content=json.dumps(payload).encode("utf-8"),
            ) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    await self._handle_non_streaming_response(response)
                    return

                async for line in response.aiter_lines():
                    parsed = self._parse_sse_line(line)
                    if not parsed:
                        continue

                    key, value = parsed
                    if key != "data":
                        continue
                    if not value or value == "[DONE]":
                        continue

                    chunk_data = self._parse_chunk_data(value)
                    if chunk_data is None:
                        continue

                    if "error" in chunk_data:
                        self._handle_chunk_error(chunk_data)

                    choices = chunk_data.get("choices", [])
                    delta = choices[0].get("delta", {}) if choices else {}
                    usage = chunk_data.get("usage")

                    content, reasoning_content, tool_calls = self._handle_chunk_data(
                        chunk_data, delta, usage, thinking_parser, full_content
                    )

                    if delta.get("content"):
                        full_content = delta["content"]

                    yield self._create_llm_chunk(
                        content, reasoning_content, tool_calls, usage
                    )

        except httpx.HTTPStatusError as e:
            # Retry once with fresh token on 401 Unauthorized
            if (
                e.response.status_code == HTTP_UNAUTHORIZED
                and self._oauth_manager
                and _retry_count == 0
            ):
                async for chunk in self._complete_streaming_with_retry(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    tools=tools,
                    max_tokens=max_tokens,
                    tool_choice=tool_choice,
                    extra_headers=extra_headers,
                    _retry_count=1,
                ):
                    yield chunk
                return
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=url,
                response=e.response,
                headers=e.response.headers,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
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
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e

    async def _handle_non_streaming_response(self, response: httpx.Response) -> None:
        """Handle non-streaming response, raising appropriate errors."""
        body = await response.aread()
        body_text = body.decode("utf-8")
        if not body_text:
            return
        try:
            error_data = json.loads(body_text)
            error_msg = (
                error_data.get("error", {}).get("message")
                or error_data.get("message")
                or error_data.get("detail")
                or str(error_data)
            )
            raise ValueError(f"API returned error: {error_msg}")
        except json.JSONDecodeError:
            raise ValueError(f"Unexpected API response: {body_text[:200]}")

    def _parse_chunk_data(self, value: str) -> dict[str, Any] | None:
        """Parse chunk data from SSE value, returning None on JSON error."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def _handle_chunk_error(self, chunk_data: dict[str, Any]) -> None:
        """Handle error in chunk data."""
        error_info = chunk_data["error"]
        error_msg = (
            error_info.get("message")
            if isinstance(error_info, dict)
            else str(error_info)
        )
        raise ValueError(f"API error: {error_msg}")

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
        """Count tokens for a request.

        Uses a minimal completion to get token count from usage info.
        """
        probe_messages = list(messages)
        if not probe_messages or probe_messages[-1].role != Role.user:
            probe_messages.append(LLMMessage(role=Role.user, content=""))

        result = await self.complete(
            model=model,
            messages=probe_messages,
            temperature=temperature,
            tools=tools,
            max_tokens=1,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )

        if result.usage is None:
            raise ValueError("Missing usage in non streaming completion")

        return result.usage.prompt_tokens

    async def list_models(self) -> list[str]:
        """List available models from the Qwen API."""
        return []

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
