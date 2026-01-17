"""Backend for Antigravity Unified Gateway API.

Features:
- OAuth2 PKCE authentication with Google
- Streaming support with SSE
- XML tool calls support
- Token usage tracking
- Thinking/reasoning content support
- Multi-model support (Claude, Gemini, GPT-OSS)

Available Models:
- gemini-3-flash, gemini-3-pro-low, gemini-3-pro-high
- claude-sonnet-4-5, claude-sonnet-4-5-thinking-low/medium/high
- claude-opus-4-5-thinking-low/medium/high
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import types
from typing import TYPE_CHECKING, Any, ClassVar, cast

import httpx

from revibe.core.llm.backend.antigravity.oauth import AntigravityOAuthManager
from revibe.core.llm.backend.antigravity.types import (
    ANTIGRAVITY_DEFAULT_ENDPOINT,
    ANTIGRAVITY_DEFAULT_HEADERS,
    ANTIGRAVITY_MODELS,
    DEFAULT_PROJECT_ID,
)
from revibe.core.llm.exceptions import BackendErrorBuilder
from revibe.core.types import (
    AvailableFunction,
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
    from revibe.core.config import ModelConfig, ProviderConfigUnion

# HTTP Status codes
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
# Retryable status codes (401 and 403 for auth/scope issues)
RETRYABLE_STATUS_CODES = frozenset({HTTP_UNAUTHORIZED, HTTP_FORBIDDEN})


class AntigravityBackend:
    supported_formats: ClassVar[list[str]] = ["xml"]

    """Backend for Antigravity Unified Gateway API.

    Features:
    - Google OAuth2 PKCE authentication
    - Streaming with SSE
    - XML tool calls support
    - Thinking/reasoning blocks
    - Token usage tracking
    - Multi-model support
    """

    def __init__(
        self,
        provider: ProviderConfigUnion,
        *,
        timeout: float = 720.0,
        oauth_path: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the Antigravity backend.

        Args:
            provider: Provider configuration.
            timeout: Request timeout in seconds.
            oauth_path: Optional custom path to OAuth credentials.
            client_id: OAuth client ID. Uses default if not provided.
            client_secret: OAuth client secret. Uses default if not provided.
            endpoint: API endpoint. Uses default if not provided.
        """
        self._provider = provider
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._owns_client = True
        self._project_id: str | None = None
        self._endpoint = endpoint or ANTIGRAVITY_DEFAULT_ENDPOINT

        # OAuth manager for Antigravity authentication
        self._oauth_manager = AntigravityOAuthManager(
            oauth_path,
            client_id=client_id,
            client_secret=client_secret,
            endpoint=self._endpoint,
        )

    async def __aenter__(self) -> AntigravityBackend:
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

    async def _get_auth_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """Get authentication headers.

        Args:
            force_refresh: If True, forces a token refresh for OAuth.

        Returns headers with OAuth token.
        """
        headers = {"Content-Type": "application/json", **ANTIGRAVITY_DEFAULT_HEADERS}

        access_token = await self._oauth_manager.ensure_authenticated(
            force_refresh=force_refresh
        )
        headers["Authorization"] = f"Bearer {access_token}"

        return headers

    def _extract_system_instruction(
        self, messages: list[LLMMessage]
    ) -> dict[str, Any] | None:
        system_instruction = None
        for msg in messages:
            if msg.role == Role.system and msg.content:
                system_instruction = {
                    "role": "user",
                    "parts": [{"text": msg.content}],
                }
        return system_instruction

    @staticmethod
    def _normalize_tool_args(args: Any) -> dict[str, Any]:
        if args is None:
            return {}
        if isinstance(args, str):
            try:
                return json.loads(args)
            except json.JSONDecodeError:
                return {"result": args}
        try:
            serialized = json.dumps(args)
        except TypeError:
            return {"result": str(args)}
        try:
            return json.loads(serialized)
        except json.JSONDecodeError:
            return {"result": serialized}

    def _format_tool_call(self, tool_call: ToolCall) -> dict[str, Any]:
        args_dict = self._normalize_tool_args(tool_call.function.arguments)
        return {
            "functionCall": {
                "name": tool_call.function.name,
                "args": args_dict,
                "id": tool_call.id or f"call_{tool_call.function.name}",
            }
        }

    def _build_content_parts(self, msg: LLMMessage) -> list[dict[str, Any]]:
        content_parts: list[dict[str, Any]] = []
        if msg.content:
            content_parts.append({"text": msg.content})

        if msg.tool_calls:
            content_parts.extend(
                [self._format_tool_call(tc) for tc in msg.tool_calls]
            )

        if msg.tool_call_id and msg.content:
            content_parts.append(
                {
                    "functionResponse": {
                        "name": msg.name or "unknown_function",
                        "response": {"result": msg.content},
                        "id": msg.tool_call_id,
                    }
                }
            )

        return content_parts

    def _prepare_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Convert LLMMessages to Antigravity format.

        Returns:
            Tuple of (contents, system_instruction)
            - contents: List of messages with "user" and "model" roles only
            - system_instruction: System prompt in proper format or None
        """
        contents: list[dict[str, Any]] = []
        system_instruction = self._extract_system_instruction(messages)

        for msg in messages:
            if msg.role == Role.system:
                continue
            role = "model" if msg.role == Role.assistant else "user"
            contents.append({"role": role, "parts": self._build_content_parts(msg)})

        return contents, system_instruction

    def _prepare_tools(
        self, tools: list[AvailableTool] | None
    ) -> list[dict[str, Any]] | None:
        """Convert tools to function declarations format.

        Returns wrapped in functionDeclarations key.
        The API expects: [{ functionDeclarations: [...]}]

        Note: Removes disallowed fields like $schema, $ref, $defs, const, anyOf, oneOf, allOf
        """
        if not tools:
            return None

        # Fields that are not allowed in Antigravity tool schemas
        disallowed_fields = {
            "$schema",
            "$ref",
            "$defs",
            "const",
            "anyOf",
            "oneOf",
            "allOf",
            "definitions",
            "title",
            "examples",
            "default",
        }

        def clean_schema(obj: Any) -> Any:
            """Recursively clean disallowed fields from schema."""
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    if key not in disallowed_fields:
                        result[key] = clean_schema(value)
                return result
            elif isinstance(obj, list):
                return [clean_schema(item) for item in obj]
            else:
                return obj

        # Build function declarations
        func_decls: list[dict[str, Any]] = []
        for tool in tools:
            func: AvailableFunction = tool.function

            # Build function declaration
            func_def: dict[str, Any] = {
                "name": func.name,
                "description": func.description or "",
            }

            if func.parameters:
                params = func.parameters
                # Clean the parameters schema to remove disallowed fields
                cleaned_params = clean_schema(params)

                func_def["parameters"] = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

                props = cast(dict[str, Any], cleaned_params.get("properties") or {})
                required_fields = cast(list[str], cleaned_params.get("required") or [])

                for name, prop in props.items():
                    prop_data = cast(dict[str, Any], prop)
                    prop_type = self._extract_property_type(prop_data)
                    prop_desc = prop_data.get("description")
                    # Explicitly type the properties dict
                    properties = cast(
                        dict[str, dict[str, Any]], func_def["parameters"]["properties"]
                    )
                    properties[name] = {"type": prop_type}
                    if prop_desc:
                        properties[name]["description"] = prop_desc
                    if name in required_fields:
                        required_list = cast(
                            list[str], func_def["parameters"]["required"]
                        )
                        required_list.append(name)

            func_decls.append(func_def)

        # Wrap in functionDeclarations key as per API spec
        return [{"functionDeclarations": func_decls}]

    def _extract_property_type(self, prop_data: dict[str, Any]) -> str:
        """Extract the property type from schema data, handling anyOf/oneOf."""
        # Direct type
        if "type" in prop_data:
            return prop_data["type"]

        # Handle anyOf (e.g., Optional[int] becomes anyOf: [{type: integer}, {type: null}])
        if "anyOf" in prop_data:
            for option in prop_data["anyOf"]:
                if isinstance(option, dict) and option.get("type") != "null":
                    return option.get("type", "string")

        # Handle oneOf similarly
        if "oneOf" in prop_data:
            for option in prop_data["oneOf"]:
                if isinstance(option, dict) and option.get("type") != "null":
                    return option.get("type", "string")

        return "string"

    def _prepare_tool_config(
        self,
        tool_choice: StrToolChoice | AvailableTool | None,
        model_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Convert tool choice to toolConfig format.

        Returns: {"functionCallingConfig": {"mode": "..."}} or None

        Note: Antigravity API requires VALIDATED mode for all models when tools are present.
        """
        if tool_choice is None:
            return None

        # Antigravity requires VALIDATED mode for all models with tools
        mode = "VALIDATED"

        if isinstance(tool_choice, str):
            return {"functionCallingConfig": {"mode": mode}}

        # AvailableTool case
        return {
            "functionCallingConfig": {
                "mode": mode,
                "allowedFunctionNames": [tool_choice.function.name],
            }
        }

    def _parse_tool_calls(
        self, tool_calls: list[dict[str, Any]] | None
    ) -> list[ToolCall] | None:
        """Parse tool calls from API response.

        Handles various formats:
        - Direct: {"name": "fn", "args": {...}}
        - Wrapped: {"functionCall": {"name": "fn", "args": {...}}}
        - With 'arguments' key: {"name": "fn", "arguments": {...}}
        """
        if not tool_calls:
            return None

        result = []
        for idx, tc in enumerate(tool_calls):
            # Handle wrapped format: {"functionCall": {...}}
            if "functionCall" in tc:
                fc = tc["functionCall"]
            else:
                fc = tc

            # Get function name
            name = fc.get("name")
            if not name:
                # Skip tool calls without a function name
                continue

            # Get arguments - try multiple keys
            # Gemini API uses "args", OpenAI format uses "arguments"
            args = fc.get("args") or fc.get("arguments")

            # Convert dict args to JSON string
            if isinstance(args, dict):
                if not args:  # Empty dict
                    args = "{}"
                else:
                    args = json.dumps(args)
            elif args is None:
                # If args is None, use empty object JSON
                args = "{}"

            # Get ID from various locations
            tc_id = tc.get("id") or fc.get("id")

            # Get index, fallback to enumeration index
            tc_index = tc.get("index")
            if tc_index is None:
                tc_index = fc.get("index")
            if tc_index is None:
                tc_index = idx

            result.append(
                ToolCall(
                    id=tc_id,
                    index=tc_index,
                    function=FunctionCall(name=name, arguments=args),
                )
            )
        return result if result else None

    async def _ensure_project_id(self, access_token: str) -> str:
        """Ensure we have a valid project ID.

        Returns:
            Project ID string (may be empty for free tier).
        """
        if self._project_id:
            return self._project_id

        # Check OAuth manager for cached project ID
        cached_project = self._oauth_manager.get_project_id()
        if cached_project:
            self._project_id = cached_project
            return cached_project

        # Fall back to default project ID
        self._project_id = DEFAULT_PROJECT_ID
        return self._project_id

    def _build_request_payload(
        self,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        project_id: str,
        user_prompt_id: str = "",
    ) -> dict[str, Any]:
        """Build the request payload for Antigravity API.

        Format:
        {
            model: string,
            project?: string,
            userAgent: string,
            requestId?: string,
            request: {
                contents: Content[],
                systemInstruction?: Content,
                tools?: ToolListUnion,
                toolConfig?: ToolConfig,
                generationConfig?: {
                    temperature?: number,
                    thinkingConfig?: {
                        thinkingBudget: number,
                        includeThoughts?: boolean,
                    },
                },
                sessionId?: string
            }
        }
        """
        # Build generation config with camelCase keys
        # Note: maxOutputTokens is NOT included as per Antigravity API requirements
        generation_config: dict[str, Any] = {"temperature": temperature}

        # Add thinkingConfig for thinking-capable models
        if model.supports_thinking:
            generation_config["thinkingConfig"] = {
                "thinkingBudget": -1,
                "includeThoughts": True,
            }

        # Build request payload
        messages_contents, system_instruction = self._prepare_messages(messages)
        request_body: dict[str, Any] = {
            "contents": messages_contents,
            "generationConfig": generation_config,
        }

        # Add system instruction if present
        if system_instruction:
            request_body["systemInstruction"] = system_instruction

        # Add sessionId (required by Antigravity API)
        import random

        session_id = f"-{random.randint(1000000000000000000, 9999999999999999999)}"
        request_body["sessionId"] = session_id

        # Tools go INSIDE the request object (not at top level)
        if tools:
            request_body["tools"] = self._prepare_tools(tools)

        # ToolConfig goes inside request object
        tool_config = self._prepare_tool_config(tool_choice, model.name)
        if tool_config:
            request_body["toolConfig"] = tool_config

        # Generate unique request ID
        import secrets

        request_id = f"py-{secrets.token_hex(8)}"

        # Build payload according to Antigravity API spec
        payload: dict[str, Any] = {
            "model": model.name,
            "userAgent": "antigravity",
            "requestId": request_id,
            "request": request_body,
        }

        # Include project if available
        if project_id:
            payload["project"] = project_id

        return payload

    async def _build_headers(
        self, extra_headers: dict[str, str] | None, retry_count: int
    ) -> dict[str, str]:
        headers = await self._get_auth_headers(force_refresh=retry_count > 0)
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _build_payload_with_project(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        access_token = headers["Authorization"].replace("Bearer ", "")
        project_id = await self._ensure_project_id(access_token)
        return self._build_request_payload(
            model, messages, temperature, tools, max_tokens, tool_choice, project_id
        )

    async def _post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        client = self._get_client()
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError as e:
            body_text = response.text[:200] if response.text else "(empty response)"
            raise ValueError(f"Invalid JSON response from API: {body_text}") from e

    def _extract_completion_parts(
        self, parts: list[dict[str, Any]]
    ) -> tuple[str, str | None, list[ToolCall] | None]:
        text_content = ""
        reasoning_content: str | None = None
        tool_calls: list[ToolCall] | None = None

        for part in parts:
            if text := part.get("text"):
                text_content += text
            if part.get("thought"):
                reasoning_content = part.get("text")
            if tool_calls is None and part.get("functionCall"):
                tool_calls = self._parse_tool_calls([part["functionCall"]])

        return text_content, reasoning_content, tool_calls

    def _parse_completion_response(self, data: dict[str, Any]) -> LLMChunk:
        response_data = data.get("response", data)
        candidates = response_data.get("candidates", [])
        if not candidates:
            raise ValueError(f"API response missing candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_content, reasoning_content, tool_calls = self._extract_completion_parts(
            parts
        )

        usage_data = data.get("usageMetadata", {})
        prompt_tokens = usage_data.get("promptTokenCount", 0)
        completion_tokens = usage_data.get("candidatesTokenCount", 0)

        return LLMChunk(
            message=LLMMessage(
                role=Role.assistant,
                content=text_content if text_content else None,
                reasoning_content=reasoning_content,
                tool_calls=tool_calls,
            ),
            usage=LLMUsage(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
            ),
        )

    @staticmethod
    def _assign_tool_call_indices(
        tool_calls: list[ToolCall],
        tracker: dict[str, int],
        next_index: int,
    ) -> int:
        for tc in tool_calls:
            tool_name = tc.function.name
            if not tool_name:
                continue
            if tool_name not in tracker:
                tracker[tool_name] = next_index
                next_index += 1
            tc.index = tracker[tool_name]
        return next_index

    async def _stream_sse_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[LLMChunk, None]:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" not in content_type:
            await self._handle_non_streaming_response(response)
            return

        tool_call_index_tracker: dict[str, int] = {}
        next_tool_call_index = 0

        async for line in response.aiter_lines():
            parsed = self._parse_sse_line(line)
            if not parsed:
                continue
            key, value = parsed
            if key != "data" or not value or value == "[DONE]":
                continue
            chunk_data = self._parse_chunk_data(value)
            if chunk_data is None:
                continue
            if "error" in chunk_data:
                self._handle_chunk_error(chunk_data)

            content, reasoning_content, tool_calls, usage = self._handle_chunk_data(
                chunk_data
            )
            if tool_calls:
                next_tool_call_index = self._assign_tool_call_indices(
                    tool_calls, tool_call_index_tracker, next_tool_call_index
                )

            yield self._create_llm_chunk(
                content, reasoning_content, tool_calls, usage
            )

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
        """Complete a chat request (non-streaming).

        Args:
            model: Model configuration.
            messages: Chat messages.
            temperature: Sampling temperature.
            tools: Available tools.
            max_tokens: Maximum output tokens.
            tool_choice: Tool selection strategy.
            extra_headers: Additional HTTP headers.

        Returns:
            LLMChunk with the completion.
        """
        return await self._complete_with_retry(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )

    async def _complete_with_retry(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        _retry_count: int = 0,
    ) -> LLMChunk:
        """Internal complete method with retry logic for auth failures."""
        headers = await self._build_headers(extra_headers, _retry_count)
        url = f"{self._oauth_manager.get_api_endpoint()}:generateContent"
        payload = await self._build_payload_with_project(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            headers=headers,
        )

        try:
            data = await self._post_json(url, headers, payload)
            return self._parse_completion_response(data)

        except httpx.HTTPStatusError as e:
            # Retry once with fresh token on 401 Unauthorized or 403 Forbidden
            if e.response.status_code in RETRYABLE_STATUS_CODES and _retry_count == 0:
                return await self._complete_with_retry(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    tools=tools,
                    max_tokens=max_tokens,
                    tool_choice=tool_choice,
                    extra_headers=extra_headers,
                    _retry_count=1,
                )
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
        """Complete a chat request with streaming.

        Args:
            model: Model configuration.
            messages: Chat messages.
            temperature: Sampling temperature.
            tools: Available tools.
            max_tokens: Maximum output tokens.
            tool_choice: Tool selection strategy.
            extra_headers: Additional HTTP headers.

        Yields:
            LLMChunk objects as they arrive.
        """
        async for chunk in self._complete_streaming_with_retry(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
            _retry_count=0,
        ):
            yield chunk

    def _parse_sse_line(self, line: str) -> tuple[str, str] | None:
        """Parse an SSE line and return (key, value) if valid."""
        if not line.strip():
            return None

        if ":" not in line:
            return None

        delim_index = line.find(":")
        key = line[:delim_index].strip()
        value = line[delim_index + 1 :].lstrip()

        return key, value

    def _handle_chunk_data(
        self, chunk_data: dict[str, Any]
    ) -> tuple[str, str, list[ToolCall] | None, dict[str, Any] | None]:
        """Handle chunk data and extract content, reasoning, tool calls, and usage."""
        content = ""
        reasoning_content = ""
        tool_calls: list[ToolCall] | None = None
        usage: dict[str, Any] | None = None

        response_data = chunk_data.get("response", chunk_data)
        candidates = response_data.get("candidates", [])
        candidate = candidates[0] if candidates else {}

        content_data = candidate.get("content", {})
        parts = content_data.get("parts", [])

        for part in parts:
            # Handle text content
            if part.get("text"):
                content += part["text"]

            # Handle thinking content
            if part.get("thought"):
                reasoning_content = part.get("text", "")

            # Handle function calls
            if part.get("functionCall"):
                tool_calls = self._parse_tool_calls([part["functionCall"]])

        # Extract usage from the last chunk
        if chunk_data.get("usageMetadata"):
            usage = chunk_data["usageMetadata"]

        return content, reasoning_content, tool_calls, usage

    def _create_llm_chunk(
        self,
        content: str,
        reasoning_content: str,
        tool_calls: list[ToolCall] | None,
        usage: dict[str, Any] | None,
    ) -> LLMChunk:
        """Create an LLMChunk from the parsed data."""
        return LLMChunk(
            message=LLMMessage(
                role=Role.assistant,
                content=content if content else None,
                reasoning_content=reasoning_content if reasoning_content else None,
                tool_calls=tool_calls,
            ),
            usage=LLMUsage(
                prompt_tokens=usage.get("promptTokenCount", 0) if usage else 0,
                completion_tokens=usage.get("candidatesTokenCount", 0) if usage else 0,
            ),
        )

    async def _complete_streaming_with_retry(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        _retry_count: int = 0,
    ) -> AsyncGenerator[LLMChunk, None]:
        """Internal streaming method with retry logic for auth failures."""
        headers = await self._build_headers(extra_headers, _retry_count)
        url = f"{self._oauth_manager.get_api_endpoint()}:streamGenerateContent"
        payload = await self._build_payload_with_project(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            headers=headers,
        )

        try:
            client = self._get_client()
            async with client.stream(
                method="POST",
                url=url,
                headers=headers,
                json=payload,
                params={"alt": "sse"},
            ) as response:
                response.raise_for_status()
                async for chunk in self._stream_sse_response(response):
                    yield chunk

        except httpx.HTTPStatusError as e:
            # Retry once with fresh token on 401 Unauthorized or 403 Forbidden
            if e.response.status_code in RETRYABLE_STATUS_CODES and _retry_count == 0:
                async for chunk in self._complete_streaming_with_retry(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    tools=tools,
                    max_tokens=max_tokens,
                    tool_choice=tool_choice,
                    extra_headers=extra_headers,
                    _retry_count=1,
                ):
                    yield chunk
                return
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

    async def _handle_non_streaming_response(self, response: httpx.Response) -> None:
        """Handle non-streaming response, raising appropriate errors."""
        body = await response.aread()
        body_text = body.decode("utf-8")
        if not body_text:
            return
        try:
            error_data = json.loads(body_text)
            error_msg = (
                error_data.get("error", {}).get("message")
                or error_data.get("message")
                or error_data.get("detail")
                or str(error_data)
            )
            raise ValueError(f"API returned error: {error_msg}")
        except json.JSONDecodeError:
            raise ValueError(f"Unexpected API response: {body_text[:200]}")

    def _parse_chunk_data(self, value: str) -> dict[str, Any] | None:
        """Parse chunk data from SSE value, returning None on JSON error."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def _handle_chunk_error(self, chunk_data: dict[str, Any]) -> None:
        """Handle error in chunk data."""
        error_info = chunk_data.get("error") or chunk_data.get("error", {})
        error_msg = (
            error_info.get("message")
            if isinstance(error_info, dict)
            else str(error_info)
        )
        raise ValueError(f"API error: {error_msg}")

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
        """Count tokens for a request.

        Uses a minimal completion to get token count from usage info.
        """
        probe_messages = list(messages)
        if not probe_messages or probe_messages[-1].role != Role.user:
            probe_messages.append(LLMMessage(role=Role.user, content=""))

        result = await self.complete(
            model=model,
            messages=probe_messages,
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
        """List available models from the Antigravity API."""
        return list(ANTIGRAVITY_MODELS.keys())

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
