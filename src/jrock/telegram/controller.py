from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from jrock.agent.runtime import AgentRuntime
from jrock.security import PermissionDenied

HELP = """J+rock · AI agent
/models [refresh] · /set models <verified-id> · /provider · /set-api-key
/compat tools|text · /auto-compat · /thinking on|off · /harness
/skills · /skills add <name> <workspace.md> · /skills use <name>
/soul · /soul add <name> <workspace.md> · /soul use <name>
/mcp · /mcp add <workspace.json> · /app_connector add <workspace.json>
/memory [add <note>|search <text>|forget <id>] · /learning on|off · /dream
/deepsearch <query> · /bugfixes <task> · /code-review <task>
/agents build|plan · /team <task> · /tools · /config
/generator image <prompt> · /generator tts <text> · /generator video <prompt>
/generator files|codes|docs <path> <prompt>
/auto_approve_on_edit on|off · /approval <id> · /approve <id> · /deny <id>
/sessions · /resume-session <id> · /new-session · /quit
Keys stay in the server's .env, not Telegram. /quit cancels agent work, NOT trading.
"""


def normalize(text: str) -> tuple[str, str]:
    token, _, args = text.strip().partition(" ")
    token = token.split("@", 1)[0].lstrip("/").lower().replace("-", "_")
    if token.startswith("soul("):
        args = "use " + token[5:].rstrip(")").replace("_", "-")
        token = "soul"
    return token, args.strip()


def pretty(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def switch(args: str) -> bool:
    if args not in {"on", "off"}:
        raise ValueError("Use on or off")
    return args == "on"


class AgentController:
    def __init__(self, runtime: AgentRuntime):
        self.r = runtime
        self.extra: Callable[[int, str, str], Awaitable[str | None]] | None = None
        self.approve_extra: Callable[[int, str], Awaitable[object]] | None = None

    async def handle(self, owner: int, text: str) -> str:
        self.r.permissions.authorize(owner)
        if not text.startswith("/"):
            if self.extra:
                result = await self.extra(owner, "natural", text)
                if result is not None:
                    return result
            return await self.r.harness.respond(owner, text)
        command, args = normalize(text)
        if command in {"start", "help"}:
            return HELP
        if command == "harness":
            return pretty({"mode": self.r.store.get(f"agent:{owner}", "build"), "model": self.r.provider.model,
                "compat": self.r.provider.compat, "tools": len(self.r.tools.tools),
                "tool_round_budget": self.r.settings.ai_max_tool_rounds, "terminal_requires_exact_approval": True,
                "host_terminal_enabled": self.r.permissions.host_terminal,
                "auto_approve_edits": owner in self.r.permissions.edit_auto, "session": self.r.store.active(owner)})
        if command == "models":
            if args not in {"", "refresh"}:
                raise ValueError("Use /models or /models refresh")
            if args == "refresh" or not self.r.provider.probes:
                await self.r.provider.discover()
            return pretty({"selected": self.r.provider.model, "verified": [vars(p) for p in self.r.provider.probes.values()]})
        if command == "set":
            sub, _, value = args.partition(" ")
            if sub not in {"model", "models"} or not value:
                raise ValueError("Use /set models <verified-id>")
            self.r.provider.select(value)
            return "Selected verified model: " + value
        if command == "provider":
            if args:
                raise ValueError("Provider URLs and keys are configured locally in .env. Use /set-api-key reload after editing it.")
            return pretty({"base_url": self.r.settings.ai_base_url, "model": self.r.provider.model,
                "models_path": self.r.settings.ai_models_path, "key_configured": bool(self.r.settings.ai_api_key.get_secret_value()),
                "model_fallback": False, "protocol": "OpenAI-compatible", "native_apis": "Use a compatible gateway or app connector"})
        if command == "set_api_key":
            if args not in {"", "reload"}:
                raise PermissionDenied("Don't send API keys in Telegram. Set them locally in .env, then /set-api-key reload")
            fresh = type(self.r.settings)()
            for key in ("ai_api_key", "ai_base_url", "ai_models_path", "ai_chat_path", "ai_extra_body"):
                setattr(self.r.settings, key, getattr(fresh, key))
            self.r.provider.model = None
            self.r.provider.probes = {}
            await self.r.provider.discover()
            return "Local AI configuration reloaded and verified. Selected: " + str(self.r.provider.model)
        if command == "compat":
            if args not in {"tools", "text"}:
                return "Compatibility: " + self.r.provider.compat + ". Use /compat tools|text. Text mode disables agent tool calls."
            self.r.provider.compat = args
            self.r.store.set("provider:compat", args)
            await self.r.provider.discover()
            return "Compatibility explicitly set to " + args + "; selected " + str(self.r.provider.model)
        if command == "auto_compat":
            if not self.r.provider.probes:
                try:
                    await self.r.provider.discover()
                except RuntimeError:
                    if not self.r.provider.probes:
                        raise
            tools = any(p.chat and p.tools for p in self.r.provider.probes.values())
            mode = "tools" if tools else "text"
            self.r.provider.compat = mode
            self.r.store.set("provider:compat", mode)
            usable = sorted(p.id for p in self.r.provider.probes.values() if p.chat and (mode == "text" or p.tools))
            if not usable:
                raise ValueError("No verified chat model works with this key; no fallback selected")
            self.r.provider.select(usable[0])
            return f"Verified compatibility: {mode}; model: {self.r.provider.model}. No model/API fallback."
        if command == "thinking":
            enabled = switch(args)
            if enabled and not self.r.settings.ai_extra_body:
                raise ValueError("Set documented provider reasoning fields in AI_EXTRA_BODY first. Hidden reasoning is not displayed.")
            self.r.provider.thinking = enabled
            self.r.store.set("provider:thinking", enabled)
            return "Provider reasoning request " + args + ". You receive conclusions and brief rationale, not hidden chain-of-thought."
        if command in {"skills", "soul"}:
            kind = "skills" if command == "skills" else "souls"
            sub, _, rest = args.partition(" ")
            if not sub:
                return pretty({"available": self.r.extensions.names(kind),
                    "active": self.r.store.get(f"soul:{owner}", "fable-5.1") if kind == "souls" else self.r.store.get(f"agent:{owner}", "build")})
            if sub == "add":
                name, _, path = rest.partition(" ")
                if not path:
                    raise ValueError(f"Use /{command} add <name> <workspace.md>")
                imported = self.r.extensions.import_from_workspace(owner, kind, name, path)
                return f"Imported {imported}. Reference text only; permissions and safety rules cannot be overridden."
            if sub == "use":
                self.r.extensions.read(kind, rest)
                if kind == "skills" and rest not in {"build", "plan", "bugfixes", "code-review"}:
                    self.r.store.set(f"custom_skill:{owner}", rest)
                else:
                    self.r.store.set(f"soul:{owner}" if kind == "souls" else f"agent:{owner}", rest)
                return "Active " + command + ": " + rest
            raise ValueError("Use add or use")
        if command in {"mcp", "app_connector"}:
            if not args:
                return pretty(self.r.store.get("connectors", {}))
            sub, _, path = args.partition(" ")
            if sub != "add" or not path:
                raise ValueError(f"Use /{command} add <workspace.json>")
            p = self.r.permissions.safe_path(path)
            if p.stat().st_size > 64_000:
                raise ValueError("Connector configuration exceeds 64 KB")
            config = json.loads(p.read_text())
            config["protocol"] = "mcp" if command == "mcp" else "http"
            from jrock.connectors.http import ConnectorSpec
            ConnectorSpec.parse(config)
            a = self.r.permissions.request(owner, "connector_add", config,
                f"Connect to {config['url']}, authentication env reference: {config.get('auth_env') or 'none'}. This server will receive that credential and approved tool inputs. Review /approval <id>.")
            return f"{a.description}\n/approve {a.id}\n/deny {a.id}"
        if command == "memory":
            sub, _, rest = args.partition(" ")
            if sub == "add" and rest:
                return "Saved note: " + self.r.store.memory(owner, "user", rest)
            if sub == "forget":
                return "Deleted." if self.r.store.forget(owner, rest) else "Memory not found."
            if sub in {"", "search"}:
                return pretty(self.r.store.memories(owner, rest))
            raise ValueError("Use /memory [add <note>|search <text>|forget <id>]")
        if command == "learning":
            self.r.store.set(f"learning:{owner}", switch(args))
            return "Learning " + args + ". Opt-in experience notes only; no autonomous weight training or risk/permission changes."
        if command == "dream":
            return await self.r.harness.dream(owner)
        if command in {"deepsearch", "bugfixes", "code_review"}:
            if not args:
                raise ValueError("Provide a task/query")
            mode = {"bugfixes": "bugfixes", "code_review": "code-review", "deepsearch": "build"}[command]
            if command == "deepsearch":
                args = "Research this query with web_search, compare sources and cite only real URLs. Ask for query transmission approval first: " + args
            return await self.r.harness.respond(owner, args, mode)
        if command == "agents":
            if args not in {"build", "plan"}:
                return "Available agents: build (permissioned tools), plan (read-only). /agents build|plan"
            self.r.store.set(f"agent:{owner}", args)
            return "Selected " + args + " agent."
        if command == "team":
            if not args:
                raise ValueError("Use /team <task>; plan first, build second, shared session")
            return await self.r.harness.team(owner, args)
        if command == "tools":
            return pretty([{"name": t.name, "permission": t.permission, "description": t.description} for t in self.r.tools.tools.values()])
        if command == "config":
            if args:
                raise ValueError("Agent settings are in local .env; trading settings use /settings_trade")
            return pretty(self.r.settings.public_dict())
        if command in {"auto_approve_on_edit", "to_auto_approve_on_edit"}:
            if switch(args):
                self.r.permissions.edit_auto.add(owner)
            else:
                self.r.permissions.edit_auto.discard(owner)
            return "Workspace-only auto edit approval " + args + ". Terminal, generation, connectors and trading are NOT auto-approved."
        if command == "generator":
            kind, _, rest = args.partition(" ")
            if kind in {"image", "tts"} and rest.startswith("model "):
                model = rest[6:].strip()
                await self.r.generators._verified_id(model)
                setattr(self.r.settings, f"{kind}_model", model)
                return f"Configured {kind} advertised model {model} for this process; capability verified only when generation succeeds."
            if kind == "tts" and rest.startswith("voice "):
                self.r.settings.tts_voice = rest[6:].strip()
                return "TTS voice updated; the provider will validate it."
            if kind in {"image", "tts", "video"} and rest:
                tool = "generate_" + kind
                param = "text" if kind == "tts" else "prompt"
                return pretty(await self.r.tools.invoke(owner, tool, {param: rest}))
            if kind in {"files", "codes", "docs", "file", "code"}:
                path, _, prompt = rest.partition(" ")
                if prompt:
                    return pretty(await self.r.tools.invoke(owner, "generate_document", {"path": path, "prompt": prompt}))
            raise ValueError("Use /generator image|tts|video <prompt> or /generator files|codes|docs <path> <prompt>")
        if command == "approval":
            a = self.r.permissions.pending.get(args)
            if not a or a.owner != owner:
                raise PermissionDenied("Approval not found or not owned by you")
            return pretty({"id": a.id, "action": a.action, "exact_payload": a.payload,
                           "sha256": a.digest, "expires": a.expires, "state": a.state})
        if command == "feedback":
            if not self.r.store.get(f"learning:{owner}", self.r.settings.learning_enabled):
                return "Learning is off; feedback was not retained. Use /learning on or explicitly save a /memory add note."
            if not args:
                raise ValueError("Use /feedback <correction or experience note>")
            return "Saved user feedback: " + self.r.store.memory(owner, "feedback", args) + ". No model weights or trading limits changed."
        if command == "approve":
            a = self.r.permissions.pending.get(args)
            if not a or a.owner != owner:
                raise PermissionDenied("Approval not found or not owned by you")
            if a.action == "tool":
                result = await self.r.tools.approved(owner, args)
            elif a.action == "connector_add":
                self.r.permissions.approve(owner, args)
                self.r.permissions.consume(owner, args, a.action, a.payload)
                result = await self.r.connectors.add(a.payload)
            elif self.approve_extra:
                result = await self.approve_extra(owner, args)
            else:
                raise ValueError("Unsupported approval type")
            self.r.store.message(self.r.store.active(owner), {"role": "user", "content": "Human approval execution result (untrusted reference): " + pretty(result)})
            return pretty(result)
        if command == "deny":
            self.r.permissions.deny(owner, args)
            return "Denied; no action executed."
        if command == "sessions":
            return pretty(self.r.store.sessions(owner))
        if command == "resume_session":
            self.r.store.resume(owner, args)
            return "Resumed session " + args
        if command == "new_session":
            return "New session: " + self.r.store.new_session(owner, args or "New conversation")
        if command == "quit":
            return self.r.harness.quit(owner)
        if self.extra:
            result = await self.extra(owner, command, args)
            if result is not None:
                return result
        return "Unknown command. /help shows agent commands; /trade_help shows trading commands when integrated."
