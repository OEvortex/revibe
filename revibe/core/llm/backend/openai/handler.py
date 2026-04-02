"""OpenAI Backend Handler.

Implements streaming chat completion using OpenAI-compatible API.
Based on OEvortex/better-copilot-chat openaiHandler.ts implementation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import re
from typing import TYPE_CHECKING, Any

import httpx

from revibe.core.llm.backend.openai.sse_normalizer import (
    fix_sse_data_prefix,
    normalize_chunk_structure,
    parse_sse_data_line,
    remove_sse_comments,
    try_normalize_python_style_completion_chunk,
)
from revibe.core.llm.backend.openai.types import ToolCallState
from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableTool,
    LLMChunk,
    LLMMessage,
    LLMUsage,
    Role,
    StrToolChoice,
)

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, ProviderConfigUnion


# Constants for code clarity
_CODE_FENCE_LEN = 3
_MAX_DUP_CHECK_LEN = 50


class OpenAIHandler:
    """Handler for OpenAI-compatible API requests.

    Features:
    - Streaming with SSE normalization
    - Native tool calls support
    - Token usage tracking
    - Python-style completion chunk handling
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        headers: dict[str, str],
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the handler.

        Args:
            client: HTTP client to use.
            base_url: Base URL for API requests.
            headers: Default headers for requests.
        """
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._headers = headers
        self._extra_body = extra_body or {}

    def _build_headers(self, api_key: str | None = None) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self._headers)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _build_payload(
        self,
        model_name: str,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        enable_streaming: bool,
    ) -> dict[str, Any]:
        """Build request payload."""
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [msg.model_dump(exclude_none=True) for msg in messages],
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

        if enable_streaming:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}

        self._merge_dicts(payload, self._extra_body)
        return payload

    @staticmethod
    def _merge_dicts(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                OpenAIHandler._merge_dicts(target[key], value)
            else:
                target[key] = value

    async def _preprocess_sse_chunk(self, text: str) -> str:
        """Preprocess SSE chunk to fix non-standard formats."""
        text = fix_sse_data_prefix(text)
        text = remove_sse_comments(text)
        return text

    def _parse_stream_chunk(
        self,
        data: dict[str, Any],
        tool_state: ToolCallState,
    ) -> LLMChunk | None:
        """Parse a streaming chunk and extract LLMChunk."""
        usage_data = data.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )

        choices = data.get("choices", [])
        if not choices:
            return None

        # Handle tool calls
        for choice in choices:
            delta = choice.get("delta", {})
            if delta.get("tool_calls"):
                for tc in delta["tool_calls"]:
                    idx = tc.get("index")
                    if idx is not None:
                        if tc.get("id"):
                            tool_state.ids[idx] = tc["id"]
                        func = tc.get("function", {})
                        if func.get("name"):
                            tool_state.names[idx] = func["name"]
                        if func.get("arguments"):
                            existing = tool_state.arguments.get(idx, "")
                            tool_state.arguments[idx] = existing + func["arguments"]

            # Handle finish_reason
            if choice.get("finish_reason"):
                idx = choice.get("index", 0)
                tool_state.completed.add(idx)

        # Extract message
        first_choice = data.get("choices", [{}])[0] if data.get("choices") else {}
        if "message" in first_choice:
            message = first_choice["message"]
        elif "delta" in first_choice:
            message = first_choice["delta"]
        else:
            message = {"role": "assistant", "content": ""}

        # Normalize message
        if isinstance(message, dict):
            message.setdefault("content", "")
            message.setdefault("role", "assistant")

        llm_message = LLMMessage.model_validate(message)
        return LLMChunk(message=llm_message, usage=usage)

    async def complete(
        self,
        *,
        model_name: str,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        api_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> LLMChunk:
        """Make a non-streaming completion request."""
        headers = self._build_headers(api_key)
        payload = self._build_payload(
            model_name,
            messages,
            temperature,
            tools,
            max_tokens,
            tool_choice,
            enable_streaming=False,
        )

        url = f"{self._base_url}/chat/completions"

        if extra_headers:
            headers.update(extra_headers)

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return self._parse_non_streaming_response(data)

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider="openai",
                endpoint=url,
                response=e.response,
                headers=e.response.headers,
                model=model_name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider="openai",
                endpoint=url,
                error=e,
                model=model_name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

    async def complete_streaming(
        self,
        *,
        model_name: str,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        api_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> AsyncGenerator[LLMChunk, None]:
        """Make a streaming completion request."""
        headers = self._build_headers(api_key)
        payload = self._build_payload(
            model_name,
            messages,
            temperature,
            tools,
            max_tokens,
            tool_choice,
            enable_streaming=True,
        )

        url = f"{self._base_url}/chat/completions"
        tool_state = ToolCallState()
        last_chunk_id = ""
        last_model = ""

        if extra_headers:
            headers.update(extra_headers)

        try:
            async with self._client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    data_str = parse_sse_data_line(line)
                    if data_str is None:
                        continue

                    preprocessed = await self._preprocess_sse_chunk(f"data: {data_str}")
                    if preprocessed.startswith("data:"):
                        data_str = preprocessed[5:].strip()

                    # Try to parse JSON
                    data: dict[str, Any] | None = None
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        normalized = try_normalize_python_style_completion_chunk(
                            data_str, last_chunk_id, last_model
                        )
                        if normalized:
                            data = normalized
                        else:
                            continue

                    if data is None:
                        continue

                    if data.get("id"):
                        last_chunk_id = data["id"]
                    if data.get("model"):
                        last_model = data["model"]

                    data = normalize_chunk_structure(data)
                    chunk = self._parse_stream_chunk(data, tool_state)
                    if chunk:
                        yield chunk

        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider="openai",
                endpoint=url,
                response=e.response,
                headers=e.response.headers,
                model=model_name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider="openai",
                endpoint=url,
                error=e,
                model=model_name,
                messages=messages,
                temperature=temperature,
                tool_choice=tool_choice,
            ) from e

    def _parse_non_streaming_response(self, data: dict[str, Any]) -> LLMChunk:
        """Parse a non-streaming response."""
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice:
                message = LLMMessage.model_validate(choice["message"])
            elif "delta" in choice:
                message = LLMMessage.model_validate(choice["delta"])
            elif "content" in choice or "content" in choice.get("message", {}):
                msg_data = choice.get("message", choice)
                message = LLMMessage.model_validate(msg_data)
            else:
                message = LLMMessage(role=Role.assistant, content="")
        elif "message" in data:
            message = LLMMessage.model_validate(data["message"])
        else:
            message = LLMMessage(role=Role.assistant, content="")

        usage_data = data.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )

        return LLMChunk(message=message, usage=usage)

    def recover_tool_arguments_json(self, input_str: str) -> str | None:
        """Try to recover valid JSON from malformed tool arguments."""
        candidate = input_str.strip()
        if not candidate:
            return None

        # Remove markdown code fences
        if (
            candidate.startswith("```")
            and candidate.endswith("```")
            and len(candidate) > _CODE_FENCE_LEN * 2
        ):
            candidate = candidate[_CODE_FENCE_LEN:-_CODE_FENCE_LEN].strip()

        # Find first JSON object/array
        first_object = candidate.find("{")
        first_array = candidate.find("[")
        if first_object == -1 and first_array == -1:
            return None

        first_json = first_object if first_array == -1 else min(first_object, first_array)
        if first_json > 0:
            candidate = candidate[first_json:]

        # Try to find balanced closing bracket
        depth = 0
        in_string = False
        escaped = False
        end_index = -1

        for i, char in enumerate(candidate):
            if escaped:
                escaped = False
                continue
            if char == "\\" and in_string:
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char in "{[":
                depth += 1
            elif char in "}]":
                depth -= 1
                if depth == 0:
                    end_index = i + 1
                    break

        if end_index == -1:
            return None

        balanced = candidate[:end_index]
        balanced = re.sub(r",\s*([}\]])", r"\1", balanced)

        try:
            json.loads(balanced)
            return balanced
        except json.JSONDecodeError:
            return None

    def fix_tool_arguments_duplication(self, args: str) -> str:
        """Fix common duplication patterns in tool arguments."""
        # Check for {}{} pattern
        if "}{" in args:
            depth = 0
            first_obj_end = -1
            for i, char in enumerate(args):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        first_obj_end = i
                        break

            if first_obj_end != -1 and first_obj_end < len(args) - 1:
                return args[: first_obj_end + 1]

        # Check for prefix repetition
        max_check = min(_MAX_DUP_CHECK_LEN, len(args) // 2)
        for length in range(max_check, 4, -1):
            prefix = args[:length]
            rest = args[length:]
            dup_idx = rest.find(prefix)
            if dup_idx != -1:
                return args[length + dup_idx :]

        return args
