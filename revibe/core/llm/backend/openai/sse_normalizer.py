"""SSE (Server-Sent Events) normalizer for OpenAI-compatible responses.

Based on OEvortex/better-copilot-chat openaiSseNormalizer.ts implementation.
Handles parsing and normalizing SSE streams from various providers.
"""

from __future__ import annotations

import json
import re
from typing import Any

from revibe.core.utils import logger


def try_normalize_python_style_completion_chunk(
    raw_text: str,
    last_chunk_id: str,
    last_model: str,
) -> dict[str, Any] | None:
    """Try to normalize a Python-style completion chunk (dict-like) to OpenAI format.

    Args:
        raw_text: The raw text to parse (may be malformed).
        last_chunk_id: Last known chunk ID.
        last_model: Last known model name.

    Returns:
        Normalized chunk dict or None if parsing fails.
    """
    try:
        # Try to find a JSON object in the text
        json_match = re.search(r"\{[^{}]*\}", raw_text, re.DOTALL)
        if not json_match:
            return None

        obj = json.loads(json_match.group())

        # Check if it looks like a completion chunk
        if "choices" not in obj:
            return None

        # Generate IDs if missing
        if "id" not in obj or not obj["id"]:
            obj["id"] = last_chunk_id or f"chatcmpl-{id(raw_text)}"

        if "model" not in obj or not obj["model"]:
            obj["model"] = last_model or "unknown"

        # Ensure choices array exists
        if not isinstance(obj.get("choices"), list):
            return None

        for choice in obj["choices"]:
            # Ensure choice has proper structure
            if "index" not in choice:
                choice["index"] = 0

            # Handle old format: message instead of delta
            if "message" in choice and "delta" not in choice:
                choice["delta"] = choice.pop("message")

            # Ensure delta exists if finish_reason exists
            if "finish_reason" in choice and not choice.get("delta"):
                choice["delta"] = {}

            # Add role to delta if missing
            if "delta" in choice and "role" not in choice["delta"]:
                choice["delta"]["role"] = "assistant"

            # Ensure tool_calls have type
            if "delta" in choice and choice["delta"].get("tool_calls"):
                for tc in choice["delta"]["tool_calls"]:
                    if "type" not in tc:
                        tc["type"] = "function"

        return obj

    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        logger.debug(f"SSE normalization failed: {e}")
        return None


def fix_sse_data_prefix(chunk: str) -> str:
    """Fix SSE format: ensure there is a space after 'data:'.

    Handles "data:{json}" -> "data: {json}"

    Args:
        chunk: The raw SSE chunk.

    Returns:
        Fixed chunk with proper spacing.
    """
    return re.sub(r"^data:([^\s])", r"data: \1", chunk, flags=re.MULTILINE)


def remove_sse_comments(chunk: str) -> str:
    """Remove SSE comment lines (e.g., ':cost:0.00084:7').

    Args:
        chunk: The raw SSE chunk.

    Returns:
        Chunk with comment lines removed.
    """
    return re.sub(r"^:.*$", "", chunk, flags=re.MULTILINE)


def is_complete_json(text: str) -> bool:
    """Check if text contains a complete JSON object.

    Args:
        text: Text to check.

    Returns:
        True if text starts with { and ends with }.
    """
    trimmed = text.strip()
    return trimmed.startswith("{") and trimmed.endswith("}")


def parse_sse_data_line(line: str) -> str | None:
    """Parse a single SSE data line.

    Args:
        line: SSE line like "data: {json}" or "data: [DONE]".

    Returns:
        The JSON string or None if not a data line.
    """
    if not line.startswith("data:"):
        return None

    data = line[5:].strip()
    if data == "[DONE]":
        return None

    return data


def extract_json_objects(text: str) -> list[tuple[int, int, str]]:
    """Extract complete JSON objects from text.

    Args:
        text: Text containing potentially multiple JSON objects.

    Returns:
        List of (start, end, json_str) tuples for complete objects.
    """
    results: list[tuple[int, int, str]] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False

    for i, char in enumerate(text):
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

        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start != -1:
                results.append((start, i + 1, text[start : i + 1]))

    return results


def normalize_chunk_structure(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize a chunk's structure to ensure proper format.

    Args:
        obj: Raw chunk object.

    Returns:
        Normalized chunk object.
    """
    modified = False
    result = dict(obj)

    # Convert old format: choice.message -> choice.delta
    if "choices" in result:
        for i, choice in enumerate(result["choices"]):
            if "message" in choice and "delta" not in choice:
                result["choices"][i] = dict(choice)
                result["choices"][i]["delta"] = result["choices"][i].pop("message")
                modified = True

            choice = result["choices"][i]

            # Fix choice index
            if choice.get("index") is None or choice["index"] != 0:
                result["choices"][i]["index"] = 0
                modified = True

            # Handle finish_reason with empty delta
            if choice.get("finish_reason"):
                if not choice.get("delta") or not choice["delta"]:
                    result["choices"][i]["delta"] = {"role": "assistant", "content": ""}
                    modified = True
                elif "role" not in choice["delta"]:
                    result["choices"][i]["delta"]["role"] = "assistant"
                    modified = True

            # Ensure tool_calls have type: function
            if choice.get("delta", {}).get("tool_calls"):
                for tc in choice["delta"]["tool_calls"]:
                    if "type" not in tc:
                        tc["type"] = "function"
                        modified = True

    return result if modified else obj
