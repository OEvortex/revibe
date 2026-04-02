"""Anthropic backend using the official anthropic SDK.

Handles streaming chat completion with tool calling and thinking content.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import os
import types
from typing import TYPE_CHECKING, Any, ClassVar, cast

import anthropic
import httpx

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


class AnthropicBackend:
    """Backend using the official Anthropic Python SDK.

    Supports:
    - Streaming and non-streaming completions
    - Tool/function calling
    - Thinking/reasoning content
    - Multi-turn conversations
    """

    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    def __init__(self, provider: ProviderConfig, *, timeout: float = 720.0) -> None:
        self._provider = provider
        self._timeout = timeout
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_api_key(self) -> str | None:
        if self._provider.api_key_env_var:
            return os.getenv(self._provider.api_key_env_var)
        return None

    def _get_base_url(self) -> str | None:
        return self._provider.api_base if self._provider.api_base else None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            api_key = self._get_api_key()
            base_url = self._get_base_url()
            custom_headers = getattr(self._provider, "custom_header", {}) or {}

            kwargs: dict[str, Any] = {
                "api_key": api_key or "",
                "default_headers": custom_headers,
                "timeout": self._timeout,
            }
            if base_url:
                kwargs["base_url"] = base_url

            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    def _convert_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[list[dict[str, Any]], str]:
        """Convert LLMMessages to Anthropic format, extracting system prompt."""
        anthropic_messages: list[dict[str, Any]] = []
        system_parts: list[str] = []

        for msg in messages:
            if msg.role == Role.system:
                if text := self._extract_text(msg):
                    system_parts.append(text)
                continue

            role = "user" if msg.role in {Role.user, Role.tool} else "assistant"
            content = self._convert_content(msg)

            if msg.tool_calls and msg.role == Role.assistant:
                blocks: list[dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in msg.tool_calls:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments)
                        if tc.function.arguments
                        else {},
                    })
                anthropic_messages.append({"role": role, "content": blocks})
            elif msg.role == Role.tool and msg.tool_call_id:
                tool_content = content or ""
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": tool_content,
                        }
                    ],
                })
            else:
                anthropic_messages.append({"role": role, "content": content or ""})

        return anthropic_messages, "".join(system_parts)

    @staticmethod
    def _extract_text(msg: LLMMessage) -> str | None:
        if isinstance(msg.content, str):
            return msg.content or None
        if isinstance(msg.content, list):
            parts = [
                p.get("text", "")
                for p in msg.content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            return "".join(parts) or None
        return None

    @staticmethod
    def _convert_content(msg: LLMMessage) -> str | None:
        if isinstance(msg.content, str):
            return msg.content or None
        if isinstance(msg.content, list):
            texts = [
                p.get("text", "")
                for p in msg.content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            return "".join(texts) or None
        return None

    @staticmethod
    def _convert_tools(tools: list[AvailableTool]) -> list[dict[str, Any]]:
        return [
            {
                "name": t.function.name,
                "description": t.function.description or "",
                "input_schema": {
                    "type": "object",
                    "properties": t.function.parameters.get("properties", {}),
                    "required": t.function.parameters.get("required", []),
                },
            }
            for t in tools
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
        client = self._get_client()
        anthropic_messages, system_prompt = self._convert_messages(messages)

        effective_max = max_tokens or 4096
        model_id = model.name

        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": effective_max,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        if tool_choice and isinstance(tool_choice, str):
            kwargs["tool_choice"] = {"type": tool_choice}
        if extra_headers:
            kwargs["extra_headers"] = extra_headers

        try:
            response = await client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/messages",
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
                endpoint=f"{self._provider.api_base}/messages",
                error=request_error,
                model=model_id,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

        # Parse response
        text_parts: list[str] = []
        tool_calls_list: list[ToolCall] = []
        reasoning_parts: list[str] = []

        for block in response.content:
            match block.type:
                case "text":
                    text_parts.append(block.text)
                case "tool_use":
                    tool_calls_list.append(
                        ToolCall(
                            id=block.id,
                            type="function",
                            function=FunctionCall(
                                name=block.name, arguments=json.dumps(block.input)
                            ),
                        )
                    )
                case "thinking":
                    reasoning_parts.append(block.thinking)

        message = LLMMessage(
            role=Role.assistant,
            content="".join(text_parts) if text_parts else None,
            reasoning_content="".join(reasoning_parts) if reasoning_parts else None,
            tool_calls=tool_calls_list or None,
        )

        usage = LLMUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

        return LLMChunk(message=message, usage=usage)

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
        anthropic_messages, system_prompt = self._convert_messages(messages)

        effective_max = max_tokens or 4096
        model_id = model.name

        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": effective_max,
            "messages": anthropic_messages,
            "temperature": temperature,
            "stream": True,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        if tool_choice and isinstance(tool_choice, str):
            kwargs["tool_choice"] = {"type": tool_choice}
        if extra_headers:
            kwargs["extra_headers"] = extra_headers

        try:
            async with client.messages.stream(**kwargs) as raw_stream:
                async for event in cast(AsyncGenerator[Any, None], raw_stream):
                    if chunk := self._process_stream_event(event):
                        yield chunk

        except anthropic.APIStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._provider.api_base}/messages",
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
                endpoint=f"{self._provider.api_base}/messages",
                error=request_error,
                model=model_id,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

    @staticmethod
    def _process_stream_event(event: Any) -> LLMChunk | None:
        event_type = getattr(event, "type", "")
        if (delta := getattr(event, "delta", None)) is not None:
            delta_type = getattr(delta, "type", "")
            if delta_type == "text_delta":
                return LLMChunk(
                    message=LLMMessage(
                        role=Role.assistant, content=str(getattr(delta, "text", ""))
                    ),
                    usage=None,
                )
            if delta_type == "thinking_delta":
                return LLMChunk(
                    message=LLMMessage(
                        role=Role.assistant,
                        reasoning_content=str(getattr(delta, "thinking", "")),
                    ),
                    usage=None,
                )
            if delta_type == "input_json_delta":
                return LLMChunk(
                    message=LLMMessage(
                        role=Role.assistant,
                        tool_calls=[
                            ToolCall(
                                id="",
                                type="function",
                                function=FunctionCall(
                                    name="",
                                    arguments=str(getattr(delta, "partial_json", "")),
                                ),
                            )
                        ],
                    ),
                    usage=None,
                )
        elif event_type == "content_block_start":
            if (block := getattr(event, "content_block", None)) is not None:
                return LLMChunk(
                    message=LLMMessage(
                        role=Role.assistant,
                        tool_calls=[
                            ToolCall(
                                id=str(getattr(block, "id", "")),
                                type="function",
                                function=FunctionCall(
                                    name=str(getattr(block, "name", "")), arguments=""
                                ),
                            )
                        ],
                    ),
                    usage=None,
                )
        elif event_type == "message_delta":
            if (usage_obj := getattr(event, "usage", None)) is not None:
                return LLMChunk(
                    message=LLMMessage(role=Role.assistant, content=""),
                    usage=LLMUsage(
                        prompt_tokens=0,
                        completion_tokens=int(getattr(usage_obj, "output_tokens", 0)),
                    ),
                )
        return None

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

    async def __aenter__(self) -> AnthropicBackend:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.close()
