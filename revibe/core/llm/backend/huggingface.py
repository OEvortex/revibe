from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import os
import types
from typing import TYPE_CHECKING, Any

import httpx

from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableTool,
    Content,
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


class HuggingFaceMapper:
    def prepare_message(self, msg: LLMMessage) -> dict[str, Any]:
        """Convert LLMMessage to HuggingFace message format."""
        message: dict[str, Any] = {"role": msg.role.value, "content": msg.content or ""}

        # HuggingFace has different tool call format
        if msg.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name or "",
                        "arguments": tc.function.arguments or "",
                    },
                }
                for tc in msg.tool_calls
            ]

        if msg.tool_call_id:
            message["tool_call_id"] = msg.tool_call_id

        return message

    def prepare_tool(self, tool: AvailableTool) -> dict[str, Any]:
        """Convert AvailableTool to HuggingFace tool format."""
        return {
            "type": "function",
            "function": {
                "name": tool.function.name,
                "description": tool.function.description,
                "parameters": tool.function.parameters,
            },
        }

    def prepare_tool_choice(
        self, tool_choice: StrToolChoice | AvailableTool
    ) -> str | dict[str, Any]:
        """Convert tool choice to HuggingFace format."""
        if isinstance(tool_choice, str):
            return tool_choice

        return {
            "type": "function",
            "function": {"name": tool_choice.function.name},
        }

    def parse_content(self, content: str | None) -> Content:
        """Parse HuggingFace response content."""
        return content or ""

    def parse_tool_calls(self, tool_calls: list[dict[str, Any]] | None) -> list[ToolCall]:
        """Parse HuggingFace tool calls to ToolCall format."""
        if not tool_calls:
            return []

        return [
            ToolCall(
                id=tool_call.get("id", ""),
                function=FunctionCall(
                    name=tool_call["function"]["name"],
                    arguments=tool_call["function"]["arguments"]
                    if isinstance(tool_call["function"]["arguments"], str)
                    else json.dumps(tool_call["function"]["arguments"]),
                ),
                index=tool_call.get("index", 0),
            )
            for tool_call in tool_calls
        ]


class HuggingFaceBackend:
    def __init__(self, provider: ProviderConfig, timeout: float = 720.0) -> None:
        self._client: httpx.AsyncClient | None = None
        self._provider = provider
        self._mapper = HuggingFaceMapper()
        self._api_key = (
            os.getenv(self._provider.api_key_env_var)
            if self._provider.api_key_env_var
            else None
        )
        self._api_base = self._provider.api_base
        self._timeout = timeout
        self._owns_client = True

    async def __aenter__(self) -> HuggingFaceBackend:
        self._client = httpx.AsyncClient(
            base_url=self._api_base,
            headers={
                "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
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

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._api_base,
                headers={
                    "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
            self._owns_client = True
        return self._client

    async def _make_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        stream: bool = False,
    ) -> Any:
        """Make HTTP request to HuggingFace API."""
        client = self._get_client()

        if stream:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return response
        else:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()

    async def complete(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        extra_headers: dict[str, str] | None,
    ) -> LLMChunk:
        try:
            payload = {
                "model": model.name,
                "messages": [self._mapper.prepare_message(msg) for msg in messages],
                "temperature": temperature,
                "stream": False,
            }

            if tools:
                payload["tools"] = [self._mapper.prepare_tool(tool) for tool in tools]
            if tool_choice:
                payload["tool_choice"] = self._mapper.prepare_tool_choice(tool_choice)
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if extra_headers:
                payload["extra_headers"] = extra_headers

            base_url = self._api_base.rstrip("/")
            response = await self._make_request(f"{base_url}/chat/completions", payload)

            return LLMChunk(
                message=LLMMessage(
                    role=Role.assistant,
                    content=self._mapper.parse_content(
                        response.get("choices", [{}])[0].get("message", {}).get("content")
                    ),
                    tool_calls=self._mapper.parse_tool_calls(
                        response.get("choices", [{}])[0].get("message", {}).get("tool_calls")
                    ),
                ),
                usage=LLMUsage(
                    prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=response.get("usage", {}).get("completion_tokens", 0),
                ),
            )

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._api_base}/chat/completions",
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
                endpoint=f"{self._api_base}/chat/completions",
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
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        extra_headers: dict[str, str] | None,
    ) -> AsyncGenerator[LLMChunk, None]:
        try:
            payload = {
                "model": model.name,
                "messages": [self._mapper.prepare_message(msg) for msg in messages],
                "temperature": temperature,
                "stream": True,
            }

            if tools:
                payload["tools"] = [self._mapper.prepare_tool(tool) for tool in tools]
            if tool_choice:
                payload["tool_choice"] = self._mapper.prepare_tool_choice(tool_choice)
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if extra_headers:
                payload["extra_headers"] = extra_headers

            base_url = self._api_base.rstrip("/")
            response = await self._make_request(f"{base_url}/chat/completions", payload, stream=True)

            async for line in response.aiter_lines():
                if line.strip() == "" or line.startswith("data: [DONE]"):
                    continue

                if line.startswith("data: "):
                    data = line[6:].strip()
                    try:
                        chunk = json.loads(data)

                        yield LLMChunk(
                            message=LLMMessage(
                                role=Role.assistant,
                                content=self._mapper.parse_content(
                                    chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                                ),
                                tool_calls=self._mapper.parse_tool_calls(
                                    chunk.get("choices", [{}])[0].get("delta", {}).get("tool_calls")
                                ),
                            ),
                            usage=LLMUsage(
                                prompt_tokens=chunk.get("usage", {}).get("prompt_tokens", 0),
                                completion_tokens=chunk.get("usage", {}).get("completion_tokens", 0),
                            ),
                        )
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=f"{self._api_base}/chat/completions",
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
                endpoint=f"{self._api_base}/chat/completions",
                error=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
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
        # Use a minimal completion to count tokens
        result = await self.complete(
            model=model,
            messages=messages,
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
        try:
            client = self._get_client()
            base_url = self._api_base.rstrip("/")
            response = await client.get(f"{base_url}/models")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return [m["id"] for m in data if "id" in m]
            if isinstance(data, dict) and "data" in data:
                return [m["id"] for m in data["data"] if "id" in m]
            return []
        except Exception:
            return []
