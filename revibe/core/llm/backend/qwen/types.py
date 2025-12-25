"""Qwen Code provider types and constants.

Based on Roo-Code qwen-code.ts implementation:
https://github.com/RooCodeInc/Roo-Code/blob/main/src/api/providers/qwen-code.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# HTTP Status codes
HTTP_OK = 200

# OAuth Configuration
QWEN_OAUTH_BASE_URL = "https://chat.qwen.ai"
QWEN_OAUTH_TOKEN_ENDPOINT = f"{QWEN_OAUTH_BASE_URL}/api/v1/oauth2/token"
QWEN_OAUTH_CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
QWEN_DIR = ".qwen"
QWEN_CREDENTIAL_FILENAME = "oauth_creds.json"

# Default API Base URLs
QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_INTL_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Token refresh buffer (30 seconds)
TOKEN_REFRESH_BUFFER_MS = 30 * 1000


@dataclass
class QwenOAuthCredentials:
    """OAuth credentials for Qwen Code API."""

    access_token: str
    refresh_token: str
    token_type: str
    expiry_date: int  # Timestamp in milliseconds
    resource_url: str | None = None


@dataclass
class QwenModelInfo:
    """Model information for Qwen Code models."""

    id: str
    name: str
    context_window: int = 131072
    max_output: int = 16384
    input_price: float = 0.0  # Per million tokens
    output_price: float = 0.0  # Per million tokens
    supports_native_tools: bool = True
    supports_thinking: bool = True


# Stream chunk types (matching Roo-Code stream.ts)
StreamChunkType = Literal[
    "text",
    "reasoning",
    "thinking_complete",
    "usage",
    "tool_call",
    "tool_call_start",
    "tool_call_delta",
    "tool_call_end",
    "tool_call_partial",
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
    signature: str | None = None


@dataclass
class StreamUsageChunk:
    """Token usage information."""

    type: Literal["usage"] = "usage"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int | None = None
    cache_read_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass
class StreamToolCallPartialChunk:
    """Partial tool call chunk from streaming."""

    type: Literal["tool_call_partial"] = "tool_call_partial"
    index: int = 0
    id: str | None = None
    name: str | None = None
    arguments: str | None = None


@dataclass
class StreamErrorChunk:
    """Error chunk."""

    type: Literal["error"] = "error"
    error: str = ""
    message: str = ""
