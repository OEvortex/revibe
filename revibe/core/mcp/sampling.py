from __future__ import annotations

import asyncio
import json
from logging import getLogger
from typing import TYPE_CHECKING, Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from revibe.core.config import MCPServer, ProviderConfig, VibeConfig
    from revibe.core.types import LLMMessage

logger = getLogger("vibe")


class MCPSamplingResult:
    def __init__(self, content: str, role: str = "assistant") -> None:
        self.content = content
        self.role = role


class MCPSamplingHandler:
    """Handles MCP sampling requests from MCP servers.

    Allows MCP servers to request LLM completions through the revibe agent.
    Implements the MCP sampling protocol.
    """

    def __init__(self, config: VibeConfig) -> None:
        self.config = config
        self._sampling_enabled_servers: set[str] = set()

    def register_sampling_server(self, server_name: str) -> None:
        """Register a server as eligible for sampling."""
        self._sampling_enabled_servers.add(server_name)

    def unregister_sampling_server(self, server_name: str) -> None:
        """Unregister a server from sampling."""
        self._sampling_enabled_servers.discard(server_name)

    def is_sampling_enabled(self, server_name: str) -> bool:
        """Check if a server has sampling enabled."""
        return server_name in self._sampling_enabled_servers

    async def handle_sampling_request(
        self,
        server_name: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> MCPSamplingResult | None:
        """Handle a sampling request from an MCP server.

        Args:
            server_name: Name of the requesting MCP server
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt override

        Returns:
            MCPSamplingResult with the generated content, or None on failure
        """
        if not self.is_sampling_enabled(server_name):
            logger.warning(
                "Sampling request from non-registered server: %s", server_name
            )
            return None

        try:
            from revibe.core.llm.backend.factory import get_backend_for_provider

            active_model = self.config.get_active_model()
            provider = self.config.get_provider_for_model(active_model)

            llm_messages: list[LLMMessage] = []
            for msg in messages:
                from revibe.core.types import LLMMessage, Role

                role = msg.get("role", "user")
                content = msg.get("content", "")
                llm_messages.append(
                    LLMMessage(
                        role=Role(role) if hasattr(Role, role) else Role.user,
                        content=content,
                    )
                )

            if system_prompt:
                from revibe.core.types import LLMMessage, Role

                llm_messages.insert(
                    0, LLMMessage(role=Role.system, content=system_prompt)
                )

            timeout = self.config.api_timeout
            backend_cls = get_backend_for_provider(provider)
            backend = backend_cls(provider=provider, timeout=timeout)

            async with backend as b:
                result = await b.complete(
                    model=active_model,
                    messages=llm_messages,
                    temperature=temperature or active_model.temperature,
                    tools=None,
                    tool_choice=None,
                    extra_headers=None,
                    max_tokens=max_tokens,
                )

            content = result.message.content or ""
            return MCPSamplingResult(content=content, role="assistant")

        except Exception as exc:
            logger.error("MCP sampling failed for %s: %s", server_name, exc)
            return None


async def setup_mcp_sampling_for_server(
    server: MCPServer, sampling_handler: MCPSamplingHandler
) -> None:
    """Set up sampling callback for an MCP server.

    This connects the MCP server's sampling requests to our handler.
    """
    match server.transport:
        case "stdio":
            from revibe.core.config import MCPStdio

            if isinstance(server, MCPStdio):
                cmd = server.argv()
                if cmd:
                    await _setup_stdio_sampling(cmd, server.name, sampling_handler)
        case "http" | "streamable-http":
            from revibe.core.config import MCPHttp, MCPStreamableHttp

            if isinstance(server, MCPHttp | MCPStreamableHttp):
                url = (server.url or "").strip()
                if url:
                    headers = server.http_headers()
                    await _setup_http_sampling(
                        url, server.name, sampling_handler, headers
                    )


async def _setup_stdio_sampling(
    command: list[str], server_name: str, sampling_handler: MCPSamplingHandler
) -> None:
    """Set up sampling for stdio MCP server."""
    sampling_handler.register_sampling_server(server_name)
    logger.info("Registered sampling for stdio MCP server: %s", server_name)


async def _setup_http_sampling(
    url: str,
    server_name: str,
    sampling_handler: MCPSamplingHandler,
    headers: dict[str, str] | None = None,
) -> None:
    """Set up sampling for HTTP MCP server."""
    sampling_handler.register_sampling_server(server_name)
    logger.info("Registered sampling for HTTP MCP server: %s", server_name)
