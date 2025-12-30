from __future__ import annotations

from fnmatch import fnmatch
from functools import lru_cache
import html
import json
import re
from uuid import uuid4
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from revibe.core.tools.base import BaseTool
from revibe.core.types import (
    AvailableFunction,
    AvailableTool,
    LLMMessage,
    Role,
    StrToolChoice,
)

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig
    from revibe.core.tools.manager import ToolManager


def _is_regex_hint(pattern: str) -> bool:
    """Heuristically detect whether a pattern looks like a regex.

    - Explicit regex: starts with 're:'
    - Heuristic regex: contains common regex metachars or '.*'
    """
    if pattern.startswith("re:"):
        return True
    return bool(re.search(r"[().+|^$]", pattern) or ".*" in pattern)


@lru_cache(maxsize=256)
def _compile_icase(expr: str) -> re.Pattern | None:
    try:
        return re.compile(expr, re.IGNORECASE)
    except re.error:
        return None


def _regex_match_icase(expr: str, s: str) -> bool:
    rx = _compile_icase(expr)
    return rx is not None and rx.fullmatch(s) is not None


def _name_matches(name: str, patterns: list[str]) -> bool:
    """Check if a tool name matches any of the provided patterns.

    Supports three forms (case-insensitive):
    - Exact names (no wildcards/regex tokens)
    - Glob wildcards using fnmatch (e.g., 'serena_*')
    - Regex when prefixed with 're:'
      or when the pattern looks regex-y (e.g., 'serena.*')
    """
    n = name.lower()
    for raw in patterns:
        if not (p := (raw or "").strip()):
            continue

        match p:
            case _ if p.startswith("re:"):
                if _regex_match_icase(p.removeprefix("re:"), name):
                    return True
            case _ if _is_regex_hint(p):
                if _regex_match_icase(p, name):
                    return True
            case _:
                if fnmatch(n, p.lower()):
                    return True

    return False


def get_active_tool_classes(
    tool_manager: ToolManager, config: VibeConfig
) -> list[type[BaseTool]]:
    """Returns a list of active tool classes based on the configuration.

    Args:
        tool_manager: ToolManager instance with discovered tools
        config: VibeConfig with enabled_tools/disabled_tools settings
    """
    all_tools = list(tool_manager.available_tools().values())

    if config.enabled_tools:
        return [
            tool_class
            for tool_class in all_tools
            if _name_matches(tool_class.get_name(), config.enabled_tools)
        ]

    if config.disabled_tools:
        return [
            tool_class
            for tool_class in all_tools
            if not _name_matches(tool_class.get_name(), config.disabled_tools)
        ]

    return all_tools


class ParsedToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_name: str
    raw_args: dict[str, Any]
    call_id: str = ""


class ResolvedToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    tool_name: str
    tool_class: type[BaseTool]
    validated_args: BaseModel
    call_id: str = ""

    @property
    def args_dict(self) -> dict[str, Any]:
        return self.validated_args.model_dump()


class FailedToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_name: str
    call_id: str
    error: str


class ParsedMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_calls: list[ParsedToolCall]


class ResolvedMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_calls: list[ResolvedToolCall]
    failed_calls: list[FailedToolCall] = Field(default_factory=list)


class APIToolFormatHandler:
    @property
    def name(self) -> str:
        return "api"

    def get_available_tools(
        self, tool_manager: ToolManager, config: VibeConfig
    ) -> list[AvailableTool]:
        active_tools = get_active_tool_classes(tool_manager, config)

        return [
            AvailableTool(
                function=AvailableFunction(
                    name=tool_class.get_name(),
                    description=tool_class.description,
                    parameters=tool_class.get_parameters(),
                )
            )
            for tool_class in active_tools
        ]

    def get_tool_choice(self) -> StrToolChoice | AvailableTool:
        return "auto"

    def process_api_response_message(self, message: Any) -> LLMMessage:
        clean_message = {
            "role": message.role,
            "content": message.content,
            "reasoning_content": getattr(message, "reasoning_content", None),
        }

        if message.tool_calls:
            clean_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "index": tc.index,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        return LLMMessage.model_validate(clean_message)

    def parse_message(self, message: LLMMessage) -> ParsedMessage:
        tool_calls = []

        api_tool_calls = message.tool_calls or []
        for tc in api_tool_calls:
            if not (function_call := tc.function):
                continue
            try:
                args = json.loads(function_call.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            tool_calls.append(
                ParsedToolCall(
                    tool_name=function_call.name or "",
                    raw_args=args,
                    call_id=tc.id or "",
                )
            )

        return ParsedMessage(tool_calls=tool_calls)

    def resolve_tool_calls(
        self, parsed: ParsedMessage, tool_manager: ToolManager, config: VibeConfig
    ) -> ResolvedMessage:
        resolved_calls = []
        failed_calls = []

        active_tools = {
            tool_class.get_name(): tool_class
            for tool_class in get_active_tool_classes(tool_manager, config)
        }

        for parsed_call in parsed.tool_calls:
            tool_class = active_tools.get(parsed_call.tool_name)
            if not tool_class:
                failed_calls.append(
                    FailedToolCall(
                        tool_name=parsed_call.tool_name,
                        call_id=parsed_call.call_id,
                        error=f"Unknown tool '{parsed_call.tool_name}'",
                    )
                )
                continue

            args_model, _ = tool_class._get_tool_args_results()
            try:
                validated_args = args_model.model_validate(parsed_call.raw_args)
                resolved_calls.append(
                    ResolvedToolCall(
                        tool_name=parsed_call.tool_name,
                        tool_class=tool_class,
                        validated_args=validated_args,
                        call_id=parsed_call.call_id,
                    )
                )
            except ValidationError as e:
                failed_calls.append(
                    FailedToolCall(
                        tool_name=parsed_call.tool_name,
                        call_id=parsed_call.call_id,
                        error=f"Invalid arguments: {e}",
                    )
                )

        return ResolvedMessage(tool_calls=resolved_calls, failed_calls=failed_calls)

    def create_tool_response_message(
        self, tool_call: ResolvedToolCall, result_text: str
    ) -> LLMMessage:
        return LLMMessage(
            role=Role.tool,
            tool_call_id=tool_call.call_id,
            name=tool_call.tool_name,
            content=result_text,
        )

    def create_failed_tool_response_message(
        self, failed: FailedToolCall, error_content: str
    ) -> LLMMessage:
        return LLMMessage(
            role=Role.tool,
            content=error_content,
            tool_call_id=failed.call_id,
        )

    def is_tool_response(self, message: LLMMessage) -> bool:
        """Check if message is a tool result."""
        return message.role == Role.tool


class XMLToolFormatHandler:
    """Handles XML-based tool calling format.

    Tool definitions are embedded in the system prompt using XML tags.
    The model responds with XML tool calls like:

    <tool_call>
    <tool_name>bash</tool_name>
    <parameters>
    <command>ls -la</command>
    </parameters>
    </tool_call>

    This format is compatible with models that don't support native function calling.
    """

    # Regex patterns for parsing XML tool calls
    TOOL_CALL_PATTERN = re.compile(
        r'<tool_call>(.*?)</tool_call>',
        re.DOTALL | re.IGNORECASE
    )
    TOOL_NAME_PATTERN = re.compile(
        r'<tool_name>(.*?)</tool_name>',
        re.DOTALL | re.IGNORECASE
    )
    PARAMETERS_PATTERN = re.compile(
        r'<parameters>(.*?)</parameters>',
        re.DOTALL | re.IGNORECASE
    )
    PARAM_PATTERN = re.compile(
        r'<(\w+)>(.*?)</\1>',
        re.DOTALL
    )

    @property
    def name(self) -> str:
        return "xml"

    def get_available_tools(
        self, tool_manager: ToolManager, config: VibeConfig
    ) -> list[AvailableTool] | None:
        """Return None - tools are embedded in system prompt for XML mode."""
        return None

    def get_tool_choice(self) -> StrToolChoice | AvailableTool | None:
        """Return None - no tool choice in XML mode."""
        return None

    def get_tool_definitions_xml(
        self, tool_manager: ToolManager, config: VibeConfig
    ) -> str:
        """Generate XML tool definitions for embedding in system prompt."""
        active_tools = get_active_tool_classes(tool_manager, config)

        if not active_tools:
            return ""

        lines = ["<tools>"]

        for tool_class in active_tools:
            tool_name = tool_class.get_name()
            description = tool_class.description
            parameters = tool_class.get_parameters()

            lines.append(f'  <tool name="{html.escape(tool_name)}">')
            lines.append(f'    <description>{html.escape(description)}</description>')

            # Add parameters section
            props = parameters.get("properties", {})
            required = parameters.get("required", [])

            if props:
                lines.append("    <parameters>")
                for param_name, param_info in props.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required
                    req_str = "true" if is_required else "false"

                    lines.append(
                        f'      <parameter name="{html.escape(param_name)}" '
                        f'type="{html.escape(param_type)}" required="{req_str}">'
                    )
                    if param_desc:
                        lines.append(f'        <description>{html.escape(param_desc)}</description>')

                    # Add default value if present
                    if "default" in param_info:
                        default_val = param_info["default"]
                        lines.append(f'        <default>{html.escape(str(default_val))}</default>')

                    # Add enum values if present
                    if "enum" in param_info:
                        enum_vals = ", ".join(str(v) for v in param_info["enum"])
                        lines.append(f'        <enum>{html.escape(enum_vals)}</enum>')

                    lines.append("      </parameter>")
                lines.append("    </parameters>")

            lines.append("  </tool>")

        lines.append("</tools>")
        return "\n".join(lines)

    def process_api_response_message(self, message: Any) -> LLMMessage:
        """Process API response - in XML mode, tool calls are in content."""
        return LLMMessage(
            role=getattr(message, "role", Role.assistant),
            content=getattr(message, "content", "") or "",
            reasoning_content=getattr(message, "reasoning_content", None),
            tool_calls=None,  # XML mode doesn't use native tool_calls
        )

    def parse_message(self, message: LLMMessage) -> ParsedMessage:
        """Parse XML tool calls from message content."""
        tool_calls = []
        content = message.content or ""

        # Find all <tool_call> blocks in content
        for match in self.TOOL_CALL_PATTERN.finditer(content):
            block = match.group(1)

            # Extract tool name
            name_match = self.TOOL_NAME_PATTERN.search(block)
            if not name_match:
                continue
            tool_name = name_match.group(1).strip()

            # Extract parameters
            raw_args: dict[str, Any] = {}
            params_match = self.PARAMETERS_PATTERN.search(block)
            if params_match:
                params_block = params_match.group(1)
                # Parse individual parameters
                for param_match in self.PARAM_PATTERN.finditer(params_block):
                    param_name = param_match.group(1)
                    param_value = param_match.group(2).strip()
                    # Try to parse as JSON for complex types
                    try:
                        raw_args[param_name] = json.loads(param_value)
                    except (json.JSONDecodeError, ValueError):
                        raw_args[param_name] = param_value

            # Generate a unique call ID
            call_id = f"xml_{uuid4().hex[:12]}"

            tool_calls.append(
                ParsedToolCall(
                    tool_name=tool_name,
                    raw_args=raw_args,
                    call_id=call_id,
                )
            )

        return ParsedMessage(tool_calls=tool_calls)

    def resolve_tool_calls(
        self, parsed: ParsedMessage, tool_manager: ToolManager, config: VibeConfig
    ) -> ResolvedMessage:
        """Resolve parsed tool calls to actual tool instances."""
        resolved_calls = []
        failed_calls = []

        active_tools = {
            tool_class.get_name(): tool_class
            for tool_class in get_active_tool_classes(tool_manager, config)
        }

        for parsed_call in parsed.tool_calls:
            tool_class = active_tools.get(parsed_call.tool_name)
            if not tool_class:
                failed_calls.append(
                    FailedToolCall(
                        tool_name=parsed_call.tool_name,
                        call_id=parsed_call.call_id,
                        error=f"Unknown tool '{parsed_call.tool_name}'",
                    )
                )
                continue

            args_model, _ = tool_class._get_tool_args_results()
            try:
                validated_args = args_model.model_validate(parsed_call.raw_args)
                resolved_calls.append(
                    ResolvedToolCall(
                        tool_name=parsed_call.tool_name,
                        tool_class=tool_class,
                        validated_args=validated_args,
                        call_id=parsed_call.call_id,
                    )
                )
            except ValidationError as e:
                failed_calls.append(
                    FailedToolCall(
                        tool_name=parsed_call.tool_name,
                        call_id=parsed_call.call_id,
                        error=f"Invalid arguments: {e}",
                    )
                )

        return ResolvedMessage(tool_calls=resolved_calls, failed_calls=failed_calls)

    def create_tool_response_message(
        self, tool_call: ResolvedToolCall, result_text: str
    ) -> LLMMessage:
        """Create a tool response message in XML format.

        Returns as a user message since XML mode doesn't use the tool role.
        """
        xml_result = (
            f'<tool_result name="{html.escape(tool_call.tool_name)}" '
            f'call_id="{html.escape(tool_call.call_id)}">\n'
            f'<status>success</status>\n'
            f'<output>\n{result_text}\n</output>\n'
            f'</tool_result>'
        )
        return LLMMessage(
            role=Role.user,
            content=xml_result,
        )

    def create_failed_tool_response_message(
        self, failed: FailedToolCall, error_content: str
    ) -> LLMMessage:
        """Create a failed tool response message in XML format."""
        xml_result = (
            f'<tool_result name="{html.escape(failed.tool_name)}" '
            f'call_id="{html.escape(failed.call_id)}">\n'
            f'<status>error</status>\n'
            f'<error>\n{error_content}\n</error>\n'
            f'</tool_result>'
        )
        return LLMMessage(
            role=Role.user,
            content=xml_result,
        )

    def is_tool_response(self, message: LLMMessage) -> bool:
        """Check if message is an XML tool result."""
        return (
            message.role == Role.user
            and message.content is not None
            and message.content.strip().startswith("<tool_result")
        )
