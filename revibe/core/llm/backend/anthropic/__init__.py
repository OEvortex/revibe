from __future__ import annotations

from collections.abc import Callable
import json
import os
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Protocol, TypeVar

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
    from revibe.core.config import ProviderConfigUnion


class PreparedRequest(NamedTuple):
    endpoint: str
    headers: dict[str, str]
    body: bytes


class AnthropicAdapterProtocol(Protocol):
    """Protocol for Anthropic API adapters."""

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

    def parse_stream_chunk(self, data: dict[str, Any]) -> LLMChunk | None: ...

    def build_headers(self, api_key: str | None = None) -> dict[str, str]: ...


T = TypeVar("T", bound="AnthropicAdapterProtocol")


def register_anthropic_adapter(
    adapters: dict[str, AnthropicAdapterProtocol], name: str
) -> Callable[[type[T]], type[T]]:
    """Decorator to register an Anthropic API adapter."""

    def decorator(cls: type[T]) -> type[T]:
        adapters[name] = cls()
        return cls

    return decorator


def _sanitize_tool_call_id(tool_id: str) -> str:
    """Sanitize tool call ID to match Anthropic's required pattern: ^[a-zA-Z0-9_-]+$"""
    sanitized = tool_id.replace(r"[^a-zA-Z0-9_-]", "_")
    return sanitized or f"tool_{os.urandom(4).hex()}"


# Types that don't support cache control
_UNSUPPORTED_CACHE_CONTROL_TYPES = frozenset({"thinking", "redacted_thinking"})

# Roles that map to "user" in Anthropic format
_TOOL_ROLES = frozenset({Role.user, Role.tool})


def _extract_text_from_part(part: Any) -> str | None:
    """Extract text from a content part."""
    if isinstance(part, dict):
        return part.get("text")
    if isinstance(part, str):
        return part
    return None


def _convert_message_to_anthropic_content(message: LLMMessage) -> list[dict[str, Any]]:
    """Convert a single LLMMessage to Anthropic content blocks."""
    if isinstance(message.content, str):
        return [{"type": "text", "text": message.content}] if message.content else []

    if not isinstance(message.content, list):
        return []

    return [block for part in message.content if (block := _part_to_content_block(part)) is not None]


def _part_to_content_block(part: Any) -> dict[str, Any] | None:
    """Convert a single content part to an Anthropic content block."""
    if not isinstance(part, dict):
        return {"type": "text", "text": part} if isinstance(part, str) and part else None

    part_type = part.get("type")

    match part_type:
        case "text" if part.get("text"):
            return {"type": "text", "text": part["text"]}
        case "tool_use":
            return {
                "type": "tool_use",
                "id": _sanitize_tool_call_id(part.get("id", "")),
                "input": part.get("input", {}),
                "name": part.get("name", ""),
            }
        case "tool_result":
            tool_content = [
                {"type": "text", "text": _extract_text_from_part(rp) or ""}
                for rp in part.get("content", [])
            ]
            return {
                "type": "tool_result",
                "tool_use_id": _sanitize_tool_call_id(part.get("tool_use_id", "")),
                "content": tool_content,
            }
        case "image":
            source = part.get("source", {})
            return {
                "type": "image",
                "source": {
                    "type": source.get("type", "base64"),
                    "data": source.get("data", ""),
                    "media_type": source.get("media_type", "image/jpeg"),
                },
            }
        case "thinking":
            return {"type": "thinking", "thinking": part.get("thinking", "")}
        case "redacted_thinking":
            return {"type": "redacted_thinking", "data": part.get("data", "")}

    return None


def _convert_tools_to_anthropic(tools: list[AvailableTool]) -> list[dict[str, Any]]:
    """Convert available tools to Anthropic format."""
    return [
        {
            "name": tool.function.name,
            "description": tool.function.description or "",
            "input_schema": {
                "type": "object",
                "properties": tool.function.parameters.get("properties", {}),
                "required": tool.function.parameters.get("required", []),
            },
        }
        for tool in tools
    ]


def _get_text_content(msg: LLMMessage) -> str | None:
    """Extract text content from a system message."""
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text", "")
    return None


def _create_tool_call(tool_id: str, name: str, arguments: str) -> ToolCall:
    """Create a ToolCall instance."""
    return ToolCall(
        id=tool_id,
        type="function",
        function=FunctionCall(name=name, arguments=arguments),
    )


@register_anthropic_adapter(ANTHROPIC_ADAPTERS := {}, "anthropic")
class AnthropicMessagesAdapter:
    """Adapter for Anthropic's messages API."""

    endpoint: ClassVar[str] = "/messages"

    def build_payload(
        self,
        model_name: str,
        anthropic_messages: list[dict[str, Any]],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Build Anthropic API payload."""
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": anthropic_messages,
            "temperature": temperature,
        }

        if system:
            payload["system"] = [{"type": "text", "text": system}]

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = _convert_tools_to_anthropic(tools)

        return payload

    def build_headers(self, api_key: str | None = None) -> dict[str, str]:
        """Build Anthropic API headers."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if api_key:
            headers["x-api-key"] = api_key
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _convert_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert messages to Anthropic format, separating system prompt."""
        anthropic_messages: list[dict[str, Any]] = []
        system_parts: list[str] = []

        for msg in messages:
            if msg.role == Role.system:
                if text := _get_text_content(msg):
                    system_parts.append(text)
            else:
                anthropic_messages.append(self._convert_single_message(msg))

        system_prompt = "".join(system_parts) if system_parts else None
        return self._merge_consecutive_messages(anthropic_messages), system_prompt

    def _convert_single_message(self, msg: LLMMessage) -> dict[str, Any]:
        """Convert a single LLMMessage to Anthropic format."""
        is_tool_role = msg.role in _TOOL_ROLES
        role = "user" if is_tool_role else "assistant"
        content_blocks = _convert_message_to_anthropic_content(msg)

        if is_tool_role and msg.tool_call_id:
            return {"role": "user", "content": content_blocks}
        return {"role": role, "content": content_blocks}

    def _merge_consecutive_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge consecutive messages with the same role."""
        if not messages:
            return []

        merged: list[dict[str, Any]] = [messages[0]]

        for msg in messages[1:]:
            if merged[-1]["role"] == msg["role"]:
                prev_content = merged[-1]["content"]
                curr_content = msg["content"]
                if isinstance(prev_content, list) and isinstance(curr_content, list):
                    merged[-1]["content"] = prev_content + curr_content
            else:
                merged.append(msg)

        return merged

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
        """Prepare Anthropic API request."""
        anthropic_messages, system_prompt = self._convert_messages(messages)

        # If no max_tokens specified, use a reasonable default for streaming
        effective_max_tokens = max_tokens if max_tokens is not None else 4096

        payload = self.build_payload(
            model_name=model_name,
            anthropic_messages=anthropic_messages,
            temperature=temperature,
            tools=tools,
            max_tokens=effective_max_tokens,
            system=system_prompt,
        )

        if enable_streaming:
            payload["stream"] = True

        headers = self.build_headers(api_key)
        body = json.dumps(payload).encode("utf-8")

        return PreparedRequest(self.endpoint, headers, body)

    def _extract_usage(self, data: dict[str, Any]) -> LLMUsage:
        """Extract usage information from response."""
        usage_data = data.get("usage", {})
        return LLMUsage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
        )

    def parse_response(self, data: dict[str, Any]) -> LLMChunk:
        """Parse non-streaming Anthropic API response."""
        message_data = data.get("content", [])

        # Build message from content blocks
        text_parts: list[str] = []
        tool_calls_list: list[ToolCall] = []

        for block in message_data:
            block_type = block.get("type")

            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls_list.append(_create_tool_call(
                    tool_id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=json.dumps(block.get("input", {})),
                ))

        # Create LLMMessage
        message = LLMMessage(
            role=Role.assistant,
            content="".join(text_parts),
            tool_calls=tool_calls_list if tool_calls_list else None,
        )

        return LLMChunk(message=message, usage=self._extract_usage(data))

    def parse_stream_chunk(self, data: dict[str, Any]) -> LLMChunk | None:
        """Parse streaming Anthropic API response chunk."""
        event_type = data.get("type")

        match event_type:
            case "content_block_start":
                return self._handle_content_block_start(data)
            case "content_block_delta":
                return self._handle_content_block_delta(data)
            case "message_delta":
                return self._handle_message_delta(data)

        return None

    def _handle_content_block_start(self, data: dict[str, Any]) -> LLMChunk | None:
        """Handle content_block_start event."""
        content_block = data.get("content_block", {})
        block_type = content_block.get("type")

        if block_type == "tool_use":
            return LLMChunk(
                message=LLMMessage(
                    role=Role.assistant,
                    tool_calls=[_create_tool_call(
                        tool_id=content_block.get("id", ""),
                        name=content_block.get("name", ""),
                        arguments="",
                    )],
                ),
                usage=None,
            )

        return None

    def _handle_content_block_delta(self, data: dict[str, Any]) -> LLMChunk | None:
        """Handle content_block_delta event."""
        delta = data.get("delta", {})
        delta_type = delta.get("type")

        if delta_type == "text_delta":
            return LLMChunk(
                message=LLMMessage(role=Role.assistant, content=delta.get("text", "")),
                usage=None,
            )

        if delta_type == "input_json_delta":
            return LLMChunk(
                message=LLMMessage(
                    role=Role.assistant,
                    tool_calls=[_create_tool_call(
                        tool_id="",
                        name="",
                        arguments=delta.get("partial_json", ""),
                    )],
                ),
                usage=None,
            )

        if delta_type == "thinking_delta":
            thinking = delta.get("thinking", "")
            if thinking:
                return LLMChunk(
                    message=LLMMessage(
                        role=Role.assistant,
                        reasoning_content=thinking,
                    ),
                    usage=None,
                )

        return None

    def _handle_message_delta(self, data: dict[str, Any]) -> LLMChunk | None:
        """Handle message_delta event."""
        usage_data = data.get("usage", {})
        if usage_data:
            return LLMChunk(
                message=LLMMessage(role=Role.assistant, content=""),
                usage=LLMUsage(
                    prompt_tokens=0,
                    completion_tokens=usage_data.get("output_tokens", 0),
                ),
            )
        return None


# Backward compatibility alias
AnthropicAdapter = AnthropicMessagesAdapter
BACKEND_ADAPTERS: dict[str, AnthropicAdapterProtocol] = ANTHROPIC_ADAPTERS
