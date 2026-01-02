"""Backend for Antigravity Unified Gateway API.

Features:
- OAuth2 PKCE authentication with Google
- Streaming support with SSE
- Native tool calls support
- Token usage tracking
- Thinking/reasoning content support
- Multi-model support (Claude, Gemini, GPT-OSS)

Available Models:
- gemini-3-flash, gemini-3-pro-low, gemini-3-pro-high
- claude-sonnet-4-5, claude-sonnet-4-5-thinking-low/medium/high
- claude-opus-4-5-thinking-low/medium/high
"""

from __future__ import annotations

import asyncio
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
    supported_formats: ClassVar[list[str]] = ["native", "xml"]

    """Backend for Antigravity Unified Gateway API.

    Features:
    - Google OAuth2 PKCE authentication
    - Streaming with SSE
    - Native tool calls support
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
        headers = {
            "Content-Type": "application/json",
            **ANTIGRAVITY_DEFAULT_HEADERS,
        }

        access_token = await self._oauth_manager.ensure_authenticated(
            force_refresh=force_refresh
        )
        headers["Authorization"] = f"Bearer {access_token}"

        return headers

    def _prepare_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert LLMMessages to Antigravity format.

        Uses role "user" or "model" only.
        """
        result = []
        for msg in messages:
            # Antigravity uses "user" and "model" roles
            role = "model" if msg.role == Role.assistant else "user"
            content_parts: list[dict[str, Any]] = []

            if msg.content:
                content_parts.append({"text": msg.content})

            if msg.tool_calls:
                # Add tool calls as function responses
                for tc in msg.tool_calls:
                    # Arguments must be serialized to JSON string for the API
                    args = tc.function.arguments
                    if args is not None and not isinstance(args, str):
                        args = json.dumps(args)
                    content_parts.append({
                        "functionResponse": {
                            "name": tc.function.name,
                            "response": {"result": args or ""},
                        }
                    })

            result.append({"role": role, "parts": content_parts})

        return result

    def _prepare_tools(
        self, tools: list[AvailableTool] | None
    ) -> list[dict[str, Any]] | None:
        """Convert tools to function declarations format.

        Returns wrapped in functionDeclarations key.
        The API expects: [{ functionDeclarations: [...] }]
        """
        if not tools:
            return None

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
                func_def["parameters"] = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

                props = cast(dict[str, Any], params.get("properties") or {})
                required_fields = cast(list[str], params.get("required") or [])

                for name, prop in props.items():
                    prop_data = cast(dict[str, Any], prop)
                    prop_type = prop_data.get("type", "string")
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

    def _prepare_tool_config(
        self, tool_choice: StrToolChoice | AvailableTool | None
    ) -> dict[str, Any] | None:
        """Convert tool choice to toolConfig format.

        Returns: {"functionCallingConfig": {"mode": "..."}} or None
        """
        if tool_choice is None:
            return None

        mode_map: dict[str, str] = {
            "auto": "AUTO",
            "none": "NONE",
            "any": "ANY",
            "required": "REQUIRED",
        }

        if isinstance(tool_choice, str):
            mode = mode_map.get(tool_choice, "AUTO")
            return {"functionCallingConfig": {"mode": mode}}

        # AvailableTool case
        return {
            "functionCallingConfig": {
                "mode": "ANY",
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

            # Get arguments - try multiple keys
            # Gemini API uses "args", OpenAI format uses "arguments"
            args = fc.get("args") or fc.get("arguments")

            # Convert dict args to JSON string
            if isinstance(args, dict):
                args = json.dumps(args)
            elif args is None:
                # If args is None, check if it's an empty object that should be {}
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
                    maxOutputTokens?: number,
                }
            }
        }
        """
        # Build generation config with camelCase keys
        generation_config: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens

        # Build request payload
        request_body: dict[str, Any] = {
            "contents": self._prepare_messages(messages),
            "generationConfig": generation_config,
        }

        # Tools go INSIDE the request object (not at top level)
        if tools:
            request_body["tools"] = self._prepare_tools(tools)

        # ToolConfig goes inside request object
        tool_config = self._prepare_tool_config(tool_choice)
        if tool_config:
            request_body["toolConfig"] = tool_config

        import secrets
        payload: dict[str, Any] = {
            "model": model.name,
            "userAgent": "antigravity",
            "requestId": f"py-{secrets.token_hex(8)}",
            "request": request_body,
        }

        # Include project if available
        if project_id:
            payload["project"] = project_id

        return payload

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
        force_refresh = _retry_count > 0
        headers = await self._get_auth_headers(force_refresh=force_refresh)
        if extra_headers:
            headers.update(extra_headers)

        # Get project ID
        access_token = headers["Authorization"].replace("Bearer ", "")
        project_id = await self._ensure_project_id(access_token)

        url = f"{self._oauth_manager.get_api_endpoint()}:generateContent"

        # Build request payload
        payload = self._build_request_payload(
            model, messages, temperature, tools, max_tokens, tool_choice, project_id
        )

        try:
            client = self._get_client()
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                body_text = response.text[:200] if response.text else "(empty response)"
                raise ValueError(f"Invalid JSON response from API: {body_text}") from e

            # Parse response - extract from response wrapper
            response_data = data.get("response", data)
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise ValueError(f"API response missing candidates: {data}")

            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            # Extract text and reasoning content
            text_content = ""
            reasoning_content = None

            for part in parts:
                if part.get("text"):
                    text_content += part["text"]
                if part.get("thought"):
                    reasoning_content = part.get("text")

            # Parse tool calls
            tool_calls = None
            for part in parts:
                if part.get("functionCall"):
                    tool_calls = self._parse_tool_calls([part["functionCall"]])
                    break

            # Extract usage metadata
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
        force_refresh = _retry_count > 0
        headers = await self._get_auth_headers(force_refresh=force_refresh)
        if extra_headers:
            headers.update(extra_headers)

        # Get project ID
        access_token = headers["Authorization"].replace("Bearer ", "")
        project_id = await self._ensure_project_id(access_token)

        # Build URL with SSE parameter
        url = f"{self._oauth_manager.get_api_endpoint()}:streamGenerateContent"

        # Build request payload
        payload = self._build_request_payload(
            model, messages, temperature, tools, max_tokens, tool_choice, project_id
        )

        # Track tool call indices across chunks to ensure unique indices per tool call
        # Key: tool name, Value: assigned index
        tool_call_index_tracker: dict[str, int] = {}
        next_tool_call_index = 0

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

                content_type = response.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    await self._handle_non_streaming_response(response)
                    return

                async for line in response.aiter_lines():
                    parsed = self._parse_sse_line(line)
                    if not parsed:
                        continue

                    key, value = parsed
                    if key != "data":
                        continue
                    if not value or value == "[DONE]":
                        continue

                    chunk_data = self._parse_chunk_data(value)
                    if chunk_data is None:
                        continue

                    if "error" in chunk_data:
                        self._handle_chunk_error(chunk_data)

                    content, reasoning_content, tool_calls, usage = (
                        self._handle_chunk_data(chunk_data)
                    )

                    # Assign unique indices to tool calls based on their name
                    if tool_calls:
                        for tc in tool_calls:
                            tool_name = tc.function.name
                            if tool_name:
                                if tool_name not in tool_call_index_tracker:
                                    tool_call_index_tracker[tool_name] = next_tool_call_index
                                    next_tool_call_index += 1
                                tc.index = tool_call_index_tracker[tool_name]

                    yield self._create_llm_chunk(
                        content, reasoning_content, tool_calls, usage
                    )

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
