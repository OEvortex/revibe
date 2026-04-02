"""OpenAI backend using the official openai SDK.

Handles streaming chat completion with tool calling and thinking/reasoning content.
Supports any OpenAI-compatible API endpoint.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import os
import types
from typing import TYPE_CHECKING, Any, ClassVar

import httpx
import openai

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
    from revibe.core.config import ModelConfig, ProviderConfig


class OpenAIBackend:
    """Backend using the official OpenAI Python SDK.

    Supports any OpenAI-compatible API. Handles:
    - Streaming and non-streaming completions
    - Tool/function calling
    - Reasoning/thinking content (for models that support it)
    - Multi-turn conversations
    """

    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    def __init__(self, provider: ProviderConfig, *, timeout: float = 720.0) -> None:
        self._provider = provider
        self._timeout = timeout
        self._client: openai.AsyncOpenAI | None = None

    def _get_api_key(self) -> str | None:
        if self._provider.api_key_env_var:
            return os.getenv(self._provider.api_key_env_var)
        return None

    def _get_client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            api_key = self._get_api_key()
            custom_headers = getattr(self._provider, "custom_header", {}) or {}

            self._client = openai.AsyncOpenAI(
                api_key=api_key or "",
                base_url=self._provider.api_base or None,
                default_headers=custom_headers,
                timeout=self._timeout,
                max_retries=2,
            )
        return self._client

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert LLMMessages to OpenAI chat completion format."""
        openai_messages: list[dict[str, Any]] = []

        for msg in messages:
            base: dict[str, Any] = {
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            }

            if msg.tool_call_id:
                base["tool_call_id"] = msg.tool_call_id

            if msg.tool_calls and msg.role == Role.assistant:
                base["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
                if msg.content:
                    base["content"] = msg.content
                elif msg.reasoning_content:
                    base["content"] = msg.reasoning_content
                else:
                    base["content"] = None
            elif msg.role == Role.tool and msg.tool_call_id:
                base["content"] = msg.content or ""
            elif isinstance(msg.content, str):
                base["content"] = msg.content
            elif isinstance(msg.content, list):
                base["content"] = msg.content
            else:
                base["content"] = msg.content

            openai_messages.append(base)

        return openai_messages

    @staticmethod
    def _convert_tools(tools: list[AvailableTool]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.function.name,
                    "description": t.function.description or "",
                    "parameters": t.function.parameters,
                },
            }
            for t in tools
        ]

    def _resolve_tool_choice(
        self, tool_choice: StrToolChoice | AvailableTool | None
    ) -> str | dict[str, Any] | None:
        if tool_choice is None:
            return None
        if isinstance(tool_choice, str):
            return tool_choice
        return {"type": "function", "function": {"name": tool_choice.function.name}}

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
        client = self._get_client()
        openai_messages = self._convert_messages(messages)
        model_id = model.name

        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": openai_messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = self._resolve_tool_choice(tool_choice)
        if extra_headers:
            kwargs["extra_headers"] = extra_headers

        try:
            response = await client.chat.completions.create(**kwargs)
        except openai.APIStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                response=e.response,
                headers=e.response.headers,
                model=model_id,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e
        except Exception as e:
            request_error = (
                e if isinstance(e, httpx.RequestError) else httpx.RequestError(str(e))
            )
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                error=request_error,
                model=model_id,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

        choice = response.choices[0] if response.choices else None
        if choice is None:
            return LLMChunk(
                message=LLMMessage(role=Role.assistant, content=""),
                usage=self._parse_usage(response.usage),
            )

        msg = choice.message
        tool_calls_list: list[ToolCall] | None = None
        if msg.tool_calls:
            tool_calls_list = [
                ToolCall(
                    id=tc.id,
                    type="function",
                    function=FunctionCall(
                        name=tc.function.name, arguments=tc.function.arguments
                    ),
                )
                for tc in msg.tool_calls
            ]

        message = LLMMessage(
            role=Role.assistant, content=msg.content, tool_calls=tool_calls_list
        )

        return LLMChunk(message=message, usage=self._parse_usage(response.usage))

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
        client = self._get_client()
        openai_messages = self._convert_messages(messages)
        model_id = model.name

        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": openai_messages,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = self._resolve_tool_choice(tool_choice)
        if extra_headers:
            kwargs["extra_headers"] = extra_headers

        try:
            stream = await client.chat.completions.create(**kwargs)

            async for chunk in stream:
                if not chunk.choices:
                    if chunk.usage:
                        yield LLMChunk(
                            message=LLMMessage(role=Role.assistant, content=""),
                            usage=self._parse_usage(chunk.usage),
                        )
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        yield LLMChunk(
                            message=LLMMessage(
                                role=Role.assistant,
                                tool_calls=[
                                    ToolCall(
                                        id=tc.id or "",
                                        type="function",
                                        function=FunctionCall(
                                            name=tc.function.name
                                            if tc.function and tc.function.name
                                            else "",
                                            arguments=tc.function.arguments
                                            if tc.function and tc.function.arguments
                                            else "",
                                        ),
                                    )
                                ],
                            ),
                            usage=None,
                        )

                # Text content
                if delta.content:
                    yield LLMChunk(
                        message=LLMMessage(role=Role.assistant, content=delta.content),
                        usage=None,
                    )

                # Reasoning content (extended_thinking models)
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    yield LLMChunk(
                        message=LLMMessage(
                            role=Role.assistant,
                            reasoning_content=delta.reasoning_content,
                        ),
                        usage=None,
                    )

                # Final chunk with finish_reason
                if choice.finish_reason and chunk.usage:
                    yield LLMChunk(
                        message=LLMMessage(role=Role.assistant, content=""),
                        usage=self._parse_usage(chunk.usage),
                    )

        except openai.APIStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                response=e.response,
                headers=e.response.headers,
                model=model_id,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e
        except Exception as e:
            request_error = (
                e if isinstance(e, httpx.RequestError) else httpx.RequestError(str(e))
            )
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/chat/completions",
                error=request_error,
                model=model_id,
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
        probe_messages = list(messages)
        if not probe_messages or probe_messages[-1].role != Role.user:
            probe_messages.append(LLMMessage(role=Role.user, content=""))

        result = await self.complete(
            model=model,
            messages=probe_messages,
            temperature=temperature,
            tools=tools,
            max_tokens=16,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )
        if result.usage is None:
            msg = "Missing usage in non-streaming completion"
            raise ValueError(msg)
        return result.usage.prompt_tokens

    async def list_models(self) -> list[str]:
        client = self._get_client()
        try:
            response = await client.models.list()
            return [m.id for m in response.data]
        except Exception:
            return []

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> OpenAIBackend:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.close()

    @staticmethod
    def _parse_usage(usage: Any) -> LLMUsage | None:
        if usage is None:
            return None
        return LLMUsage(
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
