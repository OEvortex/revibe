from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import os
import types
from typing import TYPE_CHECKING, Any, ClassVar

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
from revibe.core.utils import async_generator_retry, async_retry

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfig


class OAIBackend:
    """Backend for OpenAI Responses-compatible APIs."""

    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    def __init__(
        self,
        provider: ProviderConfig,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 720.0,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._provider = provider
        self._timeout = timeout

    def _provider_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        headers.update(getattr(self._provider, "custom_header", {}) or {})
        return headers

    def _provider_extra_body(self) -> dict[str, Any]:
        return dict(getattr(self._provider, "extra_body", {}) or {})

    async def __aenter__(self) -> OAIBackend:
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

    def _get_api_key(self) -> str | None:
        if self._provider.api_key_env_var:
            return os.getenv(self._provider.api_key_env_var)
        return None

    @staticmethod
    def _merge_dicts(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                OAIBackend._merge_dicts(target[key], value)
            else:
                target[key] = value

    def _build_payload(
        self,
        *,
        model_name: str,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        enable_streaming: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model_name,
            "input": [msg.model_dump(exclude_none=True) for msg in messages],
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = [tool.model_dump(exclude_none=True) for tool in tools]
        if tool_choice:
            payload["tool_choice"] = (
                tool_choice
                if isinstance(tool_choice, str)
                else tool_choice.model_dump()
            )
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens
        if enable_streaming:
            payload["stream"] = True

        self._merge_dicts(payload, self._provider_extra_body())
        return payload

    def _extract_tool_call(self, data: dict[str, Any], index: int) -> ToolCall | None:
        name = data.get("name") or data.get("function", {}).get("name")
        if not name:
            return None

        arguments = data.get("arguments")
        if arguments is None:
            arguments = data.get("function", {}).get("arguments")
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)
        if arguments is None:
            arguments = ""

        return ToolCall(
            id=data.get("id") or data.get("call_id"),
            index=index,
            function=FunctionCall(name=name, arguments=arguments),
        )

    def _parse_response(self, data: dict[str, Any]) -> LLMChunk:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        output_text = data.get("output_text")
        if isinstance(output_text, str):
            text_parts.append(output_text)

        output_items = data.get("output", [])
        if isinstance(output_items, list):
            for item_index, item in enumerate(output_items):
                if not isinstance(item, dict):
                    continue
                item_type = item.get("type")
                match item_type:
                    case "message":
                        content = item.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if not isinstance(block, dict):
                                    continue
                                block_type = block.get("type")
                                if block_type in {"output_text", "text"}:
                                    text = block.get("text", "")
                                    if text:
                                        text_parts.append(text)
                                elif block_type in {"function_call", "tool_call"}:
                                    if tool_call := self._extract_tool_call(
                                        block, item_index
                                    ):
                                        tool_calls.append(tool_call)
                    case "function_call" | "tool_call":
                        if tool_call := self._extract_tool_call(item, item_index):
                            tool_calls.append(tool_call)

        message = LLMMessage(
            role=Role.assistant,
            content="".join(text_parts),
            tool_calls=tool_calls or None,
        )

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
        )
        return LLMChunk(message=message, usage=usage)

    def _parse_stream_chunk(self, data: dict[str, Any]) -> LLMChunk | None:
        event_type = data.get("type")
        match event_type:
            case "response.output_text.delta" | "output_text.delta":
                delta = data.get("delta") or data.get("text") or ""
                if delta:
                    return LLMChunk(
                        message=LLMMessage(role=Role.assistant, content=delta),
                        usage=None,
                    )
            case "response.output_text.done" | "output_text.done":
                delta = data.get("text") or ""
                if delta:
                    return LLMChunk(
                        message=LLMMessage(role=Role.assistant, content=delta),
                        usage=None,
                    )
            case "response.completed":
                usage_data = data.get("usage", {})
                return LLMChunk(
                    message=LLMMessage(role=Role.assistant, content=""),
                    usage=LLMUsage(
                        prompt_tokens=usage_data.get("input_tokens", 0),
                        completion_tokens=usage_data.get("output_tokens", 0),
                    ),
                )

        if "choices" in data:
            first_choice = data.get("choices", [{}])[0] or {}
            if message := first_choice.get("message") or first_choice.get("delta"):
                return LLMChunk(message=LLMMessage.model_validate(message), usage=None)

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
        api_key = self._get_api_key()
        payload = self._build_payload(
            model_name=model.name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            enable_streaming=False,
        )

        headers = self._provider_headers()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self._provider.api_base.rstrip('/')}/responses"

        try:
            client = self._get_client()
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return self._parse_response(response.json())
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
        api_key = self._get_api_key()
        payload = self._build_payload(
            model_name=model.name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            enable_streaming=True,
        )

        headers = self._provider_headers()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self._provider.api_base.rstrip('/')}/responses"

        try:
            client = self._get_client()
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip() or not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if raw == "[DONE]":
                        return
                    chunk = self._parse_stream_chunk(json.loads(raw))
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

    @async_retry(tries=3)
    async def _make_request(
        self, url: str, data: dict[str, Any], headers: dict[str, str]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        client = self._get_client()
        response = await client.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json(), dict(response.headers.items())

    @async_generator_retry(tries=3)
    async def _make_streaming_request(
        self, url: str, data: dict[str, Any], headers: dict[str, str]
    ) -> AsyncGenerator[dict[str, Any], None]:
        client = self._get_client()
        async with client.stream("POST", url, json=data, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip() == "":
                    continue
                if not line.startswith("data:"):
                    continue
                raw = line.removeprefix("data:").strip()
                if raw == "[DONE]":
                    return
                yield json.loads(raw)

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
            msg = "Missing usage in non streaming completion"
            raise ValueError(msg)
        return result.usage.prompt_tokens

    async def list_models(self) -> list[str]:
        api_key = self._get_api_key()
        headers = self._provider_headers()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        url = f"{self._provider.api_base.rstrip('/')}/models"
        try:
            client = self._get_client()
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return [m["id"] for m in data if isinstance(m, dict) and "id" in m]
            if isinstance(data, dict) and "data" in data:
                return [
                    m["id"] for m in data["data"] if isinstance(m, dict) and "id" in m
                ]
            return []
        except Exception:
            return []

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
