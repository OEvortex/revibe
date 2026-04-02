from __future__ import annotations

import json
from logging import getLogger
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from revibe.core.config import MCPServer

logger = getLogger("vibe")

MCP_CACHE_FILE = "mcp_cache.json"
MCP_CACHE_TTL_SECONDS = 3600


class MCPCacheEntry:
    def __init__(self, tools: list[dict[str, Any]], timestamp: float) -> None:
        self.tools = tools
        self.timestamp = timestamp

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > MCP_CACHE_TTL_SECONDS

    def to_dict(self) -> dict[str, Any]:
        return {"tools": self.tools, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPCacheEntry:
        return cls(tools=data["tools"], timestamp=data["timestamp"])


class MCPRegistry:
    """Registry for MCP servers with caching support.

    Caches discovered tools to improve startup performance.
    Cache is persisted to disk and invalidated after TTL.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or Path.home() / ".revibe" / "cache"
        self._cache: dict[str, MCPCacheEntry] = {}
        self._load_cache()

    def _cache_file_path(self) -> Path:
        return self._cache_dir / MCP_CACHE_FILE

    def _load_cache(self) -> None:
        cache_path = self._cache_file_path()
        if not cache_path.exists():
            return
        try:
            data = json.loads(cache_path.read_text())
            for server_name, entry_data in data.items():
                self._cache[server_name] = MCPCacheEntry.from_dict(entry_data)
        except (json.JSONDecodeError, OSError):
            self._cache = {}

    def _save_cache(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_data = {name: entry.to_dict() for name, entry in self._cache.items()}
        try:
            self._cache_file_path().write_text(json.dumps(cache_data, indent=2))
        except OSError:
            pass

    def get_cached_tools(self, server_name: str) -> list[dict[str, Any]] | None:
        entry = self._cache.get(server_name)
        if entry and not entry.is_expired():
            return entry.tools
        if entry and entry.is_expired():
            del self._cache[server_name]
        return None

    def cache_tools(self, server_name: str, tools: list[dict[str, Any]]) -> None:
        self._cache[server_name] = MCPCacheEntry(tools=tools, timestamp=time.time())
        self._save_cache()

    def invalidate(self, server_name: str | None = None) -> None:
        if server_name:
            self._cache.pop(server_name, None)
        else:
            self._cache.clear()
        self._save_cache()

    async def discover_tools_stdio(
        self, server_name: str, command: list[str]
    ) -> list[Any]:
        cached = self.get_cached_tools(server_name)
        if cached:
            logger.info("Using cached MCP tools for stdio server: %s", server_name)
            from revibe.core.tools.mcp import RemoteTool

            return [RemoteTool.model_validate(t) for t in cached]

        logger.info("Discovering MCP tools for stdio server: %s", server_name)
        try:
            params = StdioServerParameters(command=command[0], args=command[1:])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_resp = await session.list_tools()
                    tools = [t for t in tools_resp.tools]

                    tool_dicts = [
                        t.model_dump() if hasattr(t, "model_dump") else t for t in tools
                    ]
                    self.cache_tools(server_name, tool_dicts)
                    return tools
        except Exception as exc:
            logger.warning("MCP stdio discovery failed for %r: %s", command, exc)
            return []

    async def discover_tools_http(
        self, server_name: str, url: str, headers: dict[str, str] | None = None
    ) -> list[Any]:
        cached = self.get_cached_tools(server_name)
        if cached:
            logger.info("Using cached MCP tools for HTTP server: %s", server_name)
            from revibe.core.tools.mcp import RemoteTool

            return [RemoteTool.model_validate(t) for t in cached]

        logger.info("Discovering MCP tools for HTTP server: %s", server_name)
        try:
            async with streamablehttp_client(url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_resp = await session.list_tools()
                    tools = [t for t in tools_resp.tools]

                    tool_dicts = [
                        t.model_dump() if hasattr(t, "model_dump") else t for t in tools
                    ]
                    self.cache_tools(server_name, tool_dicts)
                    return tools
        except Exception as exc:
            logger.warning("MCP HTTP discovery failed for %s: %s", url, exc)
            return []

    async def discover_tools(self, server: MCPServer) -> list[Any]:
        match server.transport:
            case "stdio":
                from revibe.core.config import MCPStdio

                stdio_server = server
                if isinstance(stdio_server, MCPStdio):
                    cmd = stdio_server.argv()
                    if cmd:
                        return await self.discover_tools_stdio(server.name, cmd)
            case "http" | "streamable-http":
                from revibe.core.config import MCPHttp, MCPStreamableHttp

                http_server = server
                if isinstance(http_server, MCPHttp | MCPStreamableHttp):
                    url = (http_server.url or "").strip()
                    if url:
                        headers = http_server.http_headers()
                        return await self.discover_tools_http(server.name, url, headers)
        return []


mcp_registry = MCPRegistry()
