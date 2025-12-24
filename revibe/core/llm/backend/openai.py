from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import os
import types
from typing import TYPE_CHECKING, Any

import httpx
import openai

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


class OpenAIMapper:
    def prepare_message(self, msg: LLMMessage) -> dict[str, Any]:
        """Convert LLMMessage to OpenAI message format."""
        message: dict[str, Any] = {"role": msg.role.value, "content": msg.content or ""}
        
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
        """Convert AvailableTool to OpenAI tool format."""
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
        """Convert tool choice to OpenAI format."""
        if isinstance(tool_choice, str):
            return tool_choice
        
        return {
            "type": "function",
            "function": {"name": tool_choice.function.name},
        }

    def parse_content(self, content: str | None) -> Content:
        """Parse OpenAI response content."""
        return content or ""

    def parse_tool_calls(self, tool_calls: list[dict[str, Any]] | None) -> list[ToolCall]:
        """Parse OpenAI tool calls to ToolCall format."""
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


class OpenAIBackend:
    def __init__(self, provider: ProviderConfig, timeout: float = 720.0) -> None:
        self._client: openai.AsyncOpenAI | None = None
        self._provider = provider
        self._mapper = OpenAIMapper()
        self._api_key = (
            os.getenv(self._provider.api_key_env_var)
            if self._provider.api_key_env_var
            else None
        )
        self._api_base = self._provider.api_base
        self._timeout = timeout

    async def __aenter__(self) -> OpenAIBackend:
        self._client = openai.AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._api_base,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        # OpenAI client doesn't need explicit cleanup
        pass

    def _get_client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._api_base,
                timeout=self._timeout,
            )
        return self._client

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
            response = await self._get_client().chat.completions.create(
                model=model.name,
                messages=[self._mapper.prepare_message(msg) for msg in messages],
                temperature=temperature,
                tools=[self._mapper.prepare_tool(tool) for tool in tools]
                if tools
                else None,
                max_tokens=max_tokens,
                tool_choice=self._mapper.prepare_tool_choice(tool_choice)
                if tool_choice
                else None,
                extra_headers=extra_headers,
                stream=False,
            )

            return LLMChunk(
                message=LLMMessage(
                    role=Role.assistant,
                    content=self._mapper.parse_content(response.choices[0].message.content),
                    tool_calls=self._mapper.parse_tool_calls(
                        response.choices[0].message.tool_calls
                    )
                    if response.choices[0].message.tool_calls
                    else None,
                ),
                usage=LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                ),
            )

        except openai.APIError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=self._api_base,
                response=e.response if hasattr(e, "response") else None,
                headers=getattr(e.response, "headers", {}) if hasattr(e, "response") else {},
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=self._api_base,
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
            async for chunk in await self._get_client().chat.completions.create(
                model=model.name,
                messages=[self._mapper.prepare_message(msg) for msg in messages],
                temperature=temperature,
                tools=[self._mapper.prepare_tool(tool) for tool in tools]
                if tools
                else None,
                max_tokens=max_tokens,
                tool_choice=self._mapper.prepare_tool_choice(tool_choice)
                if tool_choice
                else None,
                extra_headers=extra_headers,
                stream=True,
            ):
                yield LLMChunk(
                    message=LLMMessage(
                        role=Role.assistant,
                        content=self._mapper.parse_content(
                            chunk.choices[0].delta.content
                        ),
                        tool_calls=self._mapper.parse_tool_calls(
                            chunk.choices[0].delta.tool_calls
                        )
                        if chunk.choices[0].delta.tool_calls
                        else None,
                    ),
                    usage=LLMUsage(
                        prompt_tokens=chunk.usage.prompt_tokens if chunk.usage else 0,
                        completion_tokens=chunk.usage.completion_tokens if chunk.usage else 0,
                    ),
                )

        except openai.APIError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=self._api_base,
                response=e.response if hasattr(e, "response") else None,
                headers=getattr(e.response, "headers", {}) if hasattr(e, "response") else {},
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=self._api_base,
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