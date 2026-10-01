from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from jrock.agent.tools import Tool, ToolRegistry, obj
from jrock.storage import Store


@dataclass
class ConnectorSpec:
    name: str
    url: str
    auth_env: str = ""
    protocol: str = "http"

    @classmethod
    def parse(cls, data: dict) -> ConnectorSpec:
        if set(data) - {"name", "url", "auth_env", "protocol"}:
            raise ValueError("Unknown connector configuration field")
        spec = cls(**data)
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,30}", spec.name):
            raise ValueError("Connector name must be a short lowercase identifier")
        u = urlparse(spec.url)
        if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password or u.fragment:
            raise ValueError("Connector URL must be http(s), with no embedded credentials or fragment")
        if u.scheme != "https" and u.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Remote connectors require HTTPS")
        if spec.auth_env and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,80}", spec.auth_env):
            raise ValueError("auth_env must name a locally set environment variable, not contain a key")
        if spec.protocol not in {"http", "mcp"}:
            raise ValueError("Supported protocols: http, mcp (streamable HTTP)")
        return spec


class HTTPConnector:
    def __init__(self, spec: ConnectorSpec, client: httpx.AsyncClient | None = None):
        self.spec = spec
        self.client = client or httpx.AsyncClient(timeout=45, follow_redirects=False)

    def headers(self) -> dict:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.spec.auth_env:
            key = os.getenv(self.spec.auth_env, "")
            if not key:
                raise ValueError(f"Set {self.spec.auth_env} on the server first (never in Telegram)")
            headers["Authorization"] = "Bearer " + key
        return headers

    async def call(self, body: dict) -> dict:
        r = await self.client.post(self.spec.url, headers=self.headers(), json=body)
        if r.is_error:
            raise RuntimeError(f"Connector HTTP {r.status_code}")
        if len(r.content) > 2_000_000:
            raise RuntimeError("Connector response exceeds 2 MB")
        return r.json()

    async def close(self) -> None:
        await self.client.aclose()


class MCPConnector(HTTPConnector):
    """MCP streamable HTTP only; intentionally no unaudited stdio command execution.

    Reads bounded JSON or SSE responses and retains the protocol's session header.
    All tool calls require approval, regardless of a server's readOnlyHint.
    """

    def __init__(self, spec: ConnectorSpec, client: httpx.AsyncClient | None = None):
        super().__init__(spec, client)
        self.session_id: str | None = None
        self.counter = 0
        self.ready = False
        self.protocol_version = "2025-03-26"
        self._lock = asyncio.Lock()

    async def rpc(self, method: str, params: dict, notification: bool = False) -> dict:
        self.counter += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            payload["id"] = self.counter
        headers = self.headers()
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.ready:
            headers["MCP-Protocol-Version"] = self.protocol_version
        async with self.client.stream("POST", self.spec.url, headers=headers, json=payload) as r:
            if r.is_error:
                raise RuntimeError(f"MCP HTTP {r.status_code}")
            if r.headers.get("Mcp-Session-Id"):
                self.session_id = r.headers["Mcp-Session-Id"]
            if notification or r.status_code == 202:
                return {}
            total = 0
            if "text/event-stream" in r.headers.get("content-type", ""):
                data_lines = []
                async for line in r.aiter_lines():
                    total += len(line)
                    if total > 2_000_000:
                        raise RuntimeError("MCP stream exceeds 2 MB")
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
                    elif not line and data_lines:
                        event = json.loads("\n".join(data_lines))
                        data_lines = []
                        if event.get("id") == payload.get("id"):
                            return self.result(event)
                raise RuntimeError("MCP stream ended without matching response")
            raw = bytearray()
            async for chunk in r.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > 2_000_000:
                    raise RuntimeError("MCP response exceeds 2 MB")
            data = json.loads(raw)
            if data.get("id") != payload.get("id"):
                raise RuntimeError("MCP response ID mismatch")
            return self.result(data)

    @staticmethod
    def result(data: dict) -> dict:
        if "error" in data:
            raise RuntimeError(f"MCP error code {data['error'].get('code', 'unknown')}")
        return data.get("result", {})

    async def initialize(self) -> None:
        if not self.ready:
            data = await self.rpc("initialize", {"protocolVersion": self.protocol_version,
                    "capabilities": {}, "clientInfo": {"name": "J+rock", "version": "0.1.0"}})
            self.protocol_version = data.get("protocolVersion", self.protocol_version)
            self.ready = True
            await self.rpc("notifications/initialized", {}, True)

    async def list_tools(self) -> list[dict]:
        async with self._lock:
            await self.initialize()
            tools = []
            cursor = None
            for _ in range(20):
                page = await self.rpc("tools/list", {"cursor": cursor} if cursor else {})
                tools.extend(page.get("tools", []))
                cursor = page.get("nextCursor")
                if not cursor:
                    return tools
            raise RuntimeError("MCP tool pagination exceeds 20 pages")

    async def call_tool(self, name: str, arguments: dict) -> dict:
        async with self._lock:
            await self.initialize()
            return await self.rpc("tools/call", {"name": name, "arguments": arguments})


class ConnectorManager:
    def __init__(self, store: Store, registry: ToolRegistry):
        self.store, self.registry = store, registry
        self.connectors: dict[str, HTTPConnector] = {}

    async def add(self, config: dict) -> dict:
        spec = ConnectorSpec.parse(config)
        if spec.name in self.connectors:
            raise ValueError("Connector already loaded; restart after editing its configuration")
        connector = MCPConnector(spec) if spec.protocol == "mcp" else HTTPConnector(spec)
        try:
            if isinstance(connector, MCPConnector):
                tools = await connector.list_tools()
                for tool in tools:
                    remote = tool["name"]
                    local = f"mcp_{spec.name}_{re.sub('[^a-zA-Z0-9_]', '_', remote)}"
                    if len(local) > 64:
                        raise ValueError("MCP tool name too long for compatible providers")

                    async def call(owner: int, args: dict, remote: str = remote, con: MCPConnector = connector):
                        return await con.call_tool(remote, args)

                    self.registry.register(Tool(local, f"UNTRUSTED MCP {spec.name}: {tool.get('description', '')}"[:1000],
                                                tool.get("inputSchema", obj({})), call, "connector"))
            else:
                async def call_http(owner: int, args: dict):
                    return await connector.call(args["payload"])
                self.registry.register(Tool(f"app_{spec.name}", f"Call configured app {spec.name}; human approval required.",
                        obj({"payload": {"type": "object", "description": "JSON body"}}), call_http, "connector"))
        except Exception:
            await connector.close()
            # Remove any partially registered tools on failure.
            for name in list(self.registry.tools):
                if name.startswith(f"mcp_{spec.name}_") or name == f"app_{spec.name}":
                    del self.registry.tools[name]
            raise
        self.connectors[spec.name] = connector
        specs = self.store.get("connectors", {})
        specs[spec.name] = config
        self.store.set("connectors", specs)
        return {"name": spec.name, "protocol": spec.protocol, "tools_registered":
                [n for n in self.registry.tools if n.startswith(f"mcp_{spec.name}_") or n == f"app_{spec.name}"]}

    async def restore(self) -> None:
        for config in self.store.get("connectors", {}).values():
            try:
                await self.add(config)
            except (RuntimeError, ValueError, httpx.HTTPError):
                self.store.event("connector_error", {"name": config.get("name"), "status": "restore_failed"})

    async def close(self) -> None:
        for connector in self.connectors.values():
            await connector.close()
