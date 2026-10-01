from __future__ import annotations

import asyncio
import json
import os
import signal
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from jrock.security import PermissionDenied, Permissions
from jrock.storage import Store


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[[int, dict], Awaitable[object]]
    permission: str = "read"

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description,
                                                  "parameters": self.parameters}}


def obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties, "required": required if required is not None else list(properties),
            "additionalProperties": False}


def string(description: str = "") -> dict:
    return {"type": "string", "description": description}


class ToolRegistry:
    def __init__(self, permissions: Permissions, store: Store):
        self.permissions, self.store = permissions, store
        self.tools: dict[str, Tool] = {}
        self.register(Tool("read_file", "Read UTF-8 text inside the workspace (no secrets).",
                           obj({"path": string()}), self.read))
        self.register(Tool("list_files", "List non-secret files in a workspace subdirectory.",
                           obj({"path": string()}, []), self.list_files))
        self.register(Tool("write_file", "Write a UTF-8 workspace file. Requires human edit approval.",
                           obj({"path": string(), "content": string()}), self.write, "edit"))
        self.register(Tool("terminal", "Run an exact shell command after human approval; not an OS sandbox.",
                           obj({"command": string(), "scope": {"type": "string", "enum": ["workspace", "host"]}}, ["command"]),
                           self.terminal, "terminal"))

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Duplicate tool {tool.name}")
        self.tools[tool.name] = tool

    def schemas(self, read_only: bool = False) -> list[dict]:
        return [tool.schema() for tool in self.tools.values() if not read_only or tool.permission == "read"]

    def _validate(self, tool: Tool, args: dict) -> None:
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object")
        props = tool.parameters.get("properties", {})
        if tool.parameters.get("additionalProperties") is False and set(args) - props.keys():
            raise ValueError("Unknown tool parameter")
        if set(tool.parameters.get("required", [])) - args.keys():
            raise ValueError("Missing tool parameter")
        for name, value in args.items():
            rule = props.get(name, {})
            kind = rule.get("type")
            types = {"string": str, "object": dict, "array": list, "boolean": bool, "integer": int, "number": (int, float)}
            if kind in types and not isinstance(value, types[kind]):
                raise ValueError(f"Invalid type for {name}")
            if "enum" in rule and value not in rule["enum"]:
                raise ValueError(f"Invalid value for {name}")

    async def invoke(self, owner: int, name: str, args: dict, approval_id: str | None = None,
                     read_only: bool = False) -> dict:
        self.permissions.authorize(owner)
        tool = self.tools.get(name)
        if not tool:
            raise ValueError("Unknown tool")
        self._validate(tool, args)
        if read_only and tool.permission != "read":
            raise PermissionDenied("This agent mode is read-only")
        payload = {"name": name, "args": args}
        needs_approval = tool.permission != "read" and not (
            tool.permission == "edit" and owner in self.permissions.edit_auto)
        if needs_approval:
            if not approval_id:
                # No content/keys are logged. Exact edit content is stored in memory for the user to approve.
                summary = (f"{name}: " + (args.get("command") or args.get("path") or json.dumps(args)))[:2000]
                if name == "terminal":
                    summary += "\nShell uses the hosting service's OS permissions, not an OS sandbox. It can access files outside the workspace."
                summary += "\nReview complete arguments with /approval <id> before approving."
                a = self.permissions.request(owner, "tool", payload, summary)
                return {"approval_required": a.id, "description": summary, "expires_in_seconds": 300}
            self.permissions.consume(owner, approval_id, "tool", payload)
        self.store.event("tool", {"owner": owner, "name": name, "approved": needs_approval})
        result = await tool.handler(owner, args)
        return {"result": result}

    async def approved(self, owner: int, aid: str) -> dict:
        a = self.permissions.approve(owner, aid)
        if a.action != "tool":
            raise PermissionDenied("Not a tool approval")
        return await self.invoke(owner, a.payload["name"], a.payload["args"], aid)

    async def read(self, owner: int, args: dict) -> str:
        p = self.permissions.safe_path(args["path"])
        if p.stat().st_size > 200_000:
            raise ValueError("File too large; read a smaller excerpt")
        return p.read_text()

    async def list_files(self, owner: int, args: dict) -> list[str]:
        p = self.permissions.safe_path(args.get("path", "."))
        results = []
        for child in sorted(p.iterdir()):
            try:
                safe = self.permissions.safe_path(str(child.relative_to(self.permissions.workspace)))
                results.append(str(safe.relative_to(self.permissions.workspace)) + ("/" if safe.is_dir() else ""))
            except PermissionDenied:
                continue
        return results[:500]

    async def write(self, owner: int, args: dict) -> str:
        p = self.permissions.safe_path(args["path"])
        if len(args["content"].encode()) > 1_000_000:
            raise ValueError("File writes are capped at 1 MB")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"])
        p.chmod(0o600)
        return f"Wrote {p.relative_to(self.permissions.workspace)}"

    async def terminal(self, owner: int, args: dict) -> dict:
        if not self.permissions.host_terminal:
            raise PermissionDenied("Shell access is disabled. Workspace cwd is not an OS sandbox. Set ALLOW_HOST_TERMINAL=true locally first, then approve each exact command")
        # A cwd is NOT containment. Even workspace shell can read the device as the service user.
        # Restrict privileges with a container/VM. Strip all inherited keys and tokens.
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "TERM"}}
        env["HOME"] = str(self.permissions.workspace)
        proc = await asyncio.create_subprocess_exec("/bin/sh", "-c", args["command"],
                cwd=self.permissions.workspace, env=env, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT, start_new_session=True)
        captured = bytearray()

        async def drain() -> None:
            assert proc.stdout is not None
            while chunk := await proc.stdout.read(8192):
                if len(captured) < 32_000:
                    captured.extend(chunk[:32_000 - len(captured)])
            await proc.wait()

        timed_out = False
        try:
            await asyncio.wait_for(drain(), 30)
        except (TimeoutError, asyncio.CancelledError) as exc:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await proc.wait()
            if isinstance(exc, asyncio.CancelledError):
                raise
        return {"exit_code": proc.returncode, "timeout": timed_out,
                "output": captured.decode(errors="replace")}
