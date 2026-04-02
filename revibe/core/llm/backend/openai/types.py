"""OpenAI provider types and constants.

Based on OEvortex/better-copilot-chat openaiTypes.ts implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Default API Base URLs
OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"

# Timeout settings
DEFAULT_TIMEOUT = 60.0  # 60 seconds

# Stream chunk types
StreamChunkType = Literal[
    "text",
    "reasoning",
    "usage",
    "tool_call",
    "tool_call_start",
    "tool_call_delta",
    "tool_call_end",
    "tool_call_complete",
    "error",
]


@dataclass
class StreamTextChunk:
    """Text content chunk."""

    type: Literal["text"] = "text"
    text: str = ""


@dataclass
class StreamReasoningChunk:
    """Reasoning/thinking content chunk."""

    type: Literal["reasoning"] = "reasoning"
    text: str = ""


@dataclass
class StreamUsageChunk:
    """Token usage information from streaming response."""

    type: Literal["usage"] = "usage"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int | None = None
    cache_read_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass
class StreamToolCallStartChunk:
    """Tool call start chunk."""

    type: Literal["tool_call_start"] = "tool_call_start"
    index: int = 0
    id: str | None = None
    name: str | None = None


@dataclass
class StreamToolCallDeltaChunk:
    """Tool call delta/partial chunk."""

    type: Literal["tool_call_delta"] = "tool_call_delta"
    index: int = 0
    arguments: str = ""


@dataclass
class StreamToolCallEndChunk:
    """Tool call end/complete chunk."""

    type: Literal["tool_call_end"] = "tool_call_end"
    index: int = 0
    id: str | None = None
    name: str | None = None
    arguments: str = ""


@dataclass
class StreamToolCallCompleteChunk:
    """Complete tool call chunk with all data."""

    type: Literal["tool_call_complete"] = "tool_call_complete"
    index: int = 0
    id: str | None = None
    name: str | None = None
    arguments: str = ""


@dataclass
class StreamErrorChunk:
    """Error chunk."""

    type: Literal["error"] = "error"
    error: str = ""
    message: str = ""


@dataclass
class ModelInfo:
    """Model information for OpenAI-compatible models."""

    id: str
    name: str
    context_window: int = 128_000
    max_output: int = 16_384
    supports_thinking: bool = False
    supports_native_tools: bool = True


@dataclass
class SSEParseState:
    """State for SSE parsing."""

    buffer: str = ""
    in_thinking_block: bool = False
    seen_finish_reason: dict[int, bool] = field(default_factory=dict)
    last_chunk_id: str = ""
    last_model: str = ""
    pending_line: str = ""


@dataclass
class ToolCallState:
    """State tracker for tool call parsing."""

    ids: dict[int, str] = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)
    arguments: dict[int, str] = field(default_factory=dict)
    completed: set[int] = field(default_factory=set)
