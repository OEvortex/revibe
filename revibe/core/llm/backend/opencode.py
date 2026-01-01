from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
import json
import os
import types
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Protocol, TypeVar

import httpx

from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableTool,
    LLMChunk,
    LLMMessage,
    LLMUsage,
    Role,
    StrToolChoice,
)
from revibe.core.utils import async_generator_retry, async_retry

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfigUnion


class PreparedRequest(NamedTuple):
    endpoint: str
    headers: dict[str, str]
    body: bytes


class APIAdapter(Protocol):
    endpoint: ClassVar[str]

    def prepare_request(
        self,
        *,
        model_name: str,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        enable_streaming: bool,
        provider: ProviderConfigUnion,
        api_key: str | None = None,
    ) -> PreparedRequest: ...

    def parse_response(self, data: dict[str, Any]) -> LLMChunk: ...

    def build_headers(self, api_key: str | None = None) -> dict[str, str]: ...


BACKEND_ADAPTERS: dict[str, APIAdapter] = {}

T = TypeVar("T", bound=APIAdapter)


def register_adapter(
    adapters: dict[str, APIAdapter], name: str
) -> Callable[[type[T]], type[T]]:

    def decorator(cls: type[T]) -> type[T]:
        adapters[name] = cls()
        return cls

    return decorator


@register_adapter(BACKEND_ADAPTERS, "opencode")
class OpenCodeAdapter(APIAdapter):
    endpoint: ClassVar[str] = "/chat/completions"

    def _get_model_endpoint(self, model_name: str) -> str:
        """Determine the appropriate endpoint based on model family."""
        if model_name.startswith("claude"):
            return "/messages"
        elif model_name.startswith("gpt"):
            return "/responses"
        elif model_name.startswith("gemini"):
            # Special case for Gemini as per spec: /models/{model_id}
            return f"/models/{model_name.replace('opencode/', '')}"
        else:
            # All other models (GLM, Kimi, Qwen, Grok, Big Pickle) use /chat/completions
            return "/chat/completions"

    def build_payload(
        self,
        model_name: str,
        converted_messages: list[dict[str, Any]],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
    ) -> dict[str, Any]:
        payload = {
            "model": model_name,
            "messages": converted_messages,
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
            payload["max_tokens"] = max_tokens

        return payload

    def build_headers(self, api_key: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def prepare_request(
        self,
        *,
        model_name: str,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        enable_streaming: bool,
        provider: ProviderConfigUnion,
        api_key: str | None = None,
    ) -> PreparedRequest:
        converted_messages = [msg.model_dump(exclude_none=True) for msg in messages]

        payload = self.build_payload(
            model_name, converted_messages, temperature, tools, max_tokens, tool_choice
        )

        if enable_streaming:
            payload["stream"] = True
            stream_options = {"include_usage": True}
            payload["stream_options"] = stream_options

        headers = self.build_headers(api_key)

        body = json.dumps(payload).encode("utf-8")

        # Use model-specific endpoint
        endpoint = self._get_model_endpoint(model_name)

        return PreparedRequest(endpoint, headers, body)

    def parse_response(self, data: dict[str, Any]) -> LLMChunk:
        if data.get("choices"):
            if "message" in data["choices"][0]:
                message = LLMMessage.model_validate(data["choices"][0]["message"])
            elif "delta" in data["choices"][0]:
                message = LLMMessage.model_validate(data["choices"][0]["delta"])
            else:
                raise ValueError("Invalid response data")

        elif "message" in data:
            message = LLMMessage.model_validate(data["message"])
        elif "delta" in data:
            message = LLMMessage.model_validate(data["delta"])
        else:
            message = LLMMessage(role=Role.assistant, content="")

        usage_data = data.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )

        return LLMChunk(message=message, usage=usage)


class OpenCodeBackend:
    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    def __init__(
        self,
        provider: ProviderConfigUnion,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 720.0,
    ) -> None:
        """Initialize the OpenCode backend.

        Args:
            provider: The provider configuration
            client: Optional httpx client to use. If not provided, one will be created.
            timeout: Request timeout in seconds
        """
        self._client = client
        self._owns_client = client is None
        self._provider = provider
        self._timeout = timeout

    async def __aenter__(self) -> OpenCodeBackend:
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
        api_key = (
            os.getenv(self._provider.api_key_env_var)
            if self._provider.api_key_env_var
            else None
        )

        api_style = getattr(self._provider, "api_style", "opencode")
        adapter = BACKEND_ADAPTERS[api_style]

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

        if extra_headers:
            headers.update(extra_headers)

        base_url = self._provider.api_base.rstrip("/")
        endpoint = endpoint.lstrip("/")
        url = f"{base_url}/{endpoint}"

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
        api_key = (
            os.getenv(self._provider.api_key_env_var)
            if self._provider.api_key_env_var
            else None
        )

        api_style = getattr(self._provider, "api_style", "opencode")
        adapter = BACKEND_ADAPTERS[api_style]

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

        if extra_headers:
            headers.update(extra_headers)

        base_url = self._provider.api_base.rstrip("/")
        endpoint = endpoint.lstrip("/")
        url = f"{base_url}/{endpoint}"

        try:
            async for res_data in self._make_streaming_request(url, body, headers):
                yield adapter.parse_response(res_data)

        except httpx.HTTPStatusError as e:
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

    class HTTPResponse(NamedTuple):
        data: dict[str, Any]
        headers: dict[str, str]

    @async_retry(tries=3)
    async def _make_request(
        self, url: str, data: bytes, headers: dict[str, str]
    ) -> HTTPResponse:
        client = self._get_client()
        response = await client.post(url, content=data, headers=headers)
        response.raise_for_status()

        response_headers = dict(response.headers.items())
        response_body = response.json()
        return self.HTTPResponse(response_body, response_headers)

    @async_generator_retry(tries=3)
    async def _make_streaming_request(
        self, url: str, data: bytes, headers: dict[str, str]
    ) -> AsyncGenerator[dict[str, Any]]:
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
                    raise ValueError(
                        f"Stream chunk improperly formatted. "
                        f"Expected `key{DELIM_CHAR} value`, received `{line}`"
                    )
                delim_index = line.find(DELIM_CHAR)
                key = line[0:delim_index]
                value = line[delim_index + 2 :]

                if key != "data":
                    # This might be the case with openrouter, so we just ignore it
                    continue
                if value == "[DONE]":
                    return
                yield json.loads(value.strip())

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
            max_tokens=16,  # Minimal amount for token counting
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )
        if result.usage is None:
            raise ValueError("Missing usage in non streaming completion")

        return result.usage.prompt_tokens

    async def list_models(self) -> list[str]:
        """Return hardcoded list of available OpenCode models."""
        return [
            "claude-opus-4-5",
            "claude-opus-4-1",
            "claude-sonnet-4",
            "claude-sonnet-4-5",
            "claude-3-5-haiku",
            "claude-haiku-4-5",
            "gemini-3-pro",
            "gemini-3-flash",
            "gpt-5.2",
            "gpt-5.1",
            "gpt-5",
            "gpt-5.1-codex-max",
            "gpt-5.1-codex",
            "gpt-5-codex",
            "gpt-5.1-codex-mini",
            "gpt-5-nano",
            "qwen3-coder",
            "glm-4.6",
            "kimi-k2",
            "kimi-k2-thinking",
            "minimax-m2.1-free",
            "glm-4.7-free",
            "grok-code",
            "alpha-glm-4.7",
            "alpha-gd4",
            "big-pickle",
        ]

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
