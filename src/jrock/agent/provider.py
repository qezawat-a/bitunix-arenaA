from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass

import httpx

from jrock.config import Settings
from jrock.storage import Store


class ProviderError(RuntimeError):
    pass


@dataclass
class ModelProbe:
    id: str
    chat: bool
    tools: bool
    latency_ms: int
    error: str | None = None


class ModelProvider:
    """Discover IDs from YOUR endpoint and probe YOUR key; never invent or fall back to an ID.

    Discovery costs a small request per advertised model (and per successful tool probe).
    A successful probe is a point-in-time permission/capability check, not a future guarantee.
    """

    def __init__(self, settings: Settings, store: Store, client: httpx.AsyncClient | None = None):
        self.settings, self.store = settings, store
        self.client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
        self.probes: dict[str, ModelProbe] = {}
        self.model: str | None = None
        self.compat = store.get("provider:compat", "tools")
        self.thinking = store.get("provider:thinking", False)
        self._discovery_lock = asyncio.Lock()

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.settings.ai_api_key.get_secret_value()}",
                "Content-Type": "application/json"}

    def url(self, path: str) -> str:
        if not self.settings.ai_base_url or not self.settings.ai_api_key.get_secret_value():
            raise ProviderError("Set AI_BASE_URL and AI_API_KEY in the server .env first")
        return self.settings.ai_base_url + path

    async def _post(self, payload: dict) -> dict:
        try:
            response = await self.client.post(self.url(self.settings.ai_chat_path),
                                              headers=self.headers(), json=payload)
            if response.is_error:
                # Do NOT expose raw provider errors: some echo request headers or credentials.
                raise ProviderError(f"Provider HTTP {response.status_code}; no fallback used")
            data = response.json()
            if not isinstance(data, dict) or not data.get("choices"):
                raise ProviderError("Provider returned no chat choices; no fallback used")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Provider request failed ({type(exc).__name__}); no fallback used") from exc

    async def advertised(self) -> list[str]:
        try:
            r = await self.client.get(self.url(self.settings.ai_models_path), headers=self.headers())
            if r.is_error:
                raise ProviderError(f"Model discovery HTTP {r.status_code}; no hardcoded model used")
            data = r.json()
            rows = data.get("data", data.get("models", []))
            if not isinstance(rows, list):
                raise ProviderError("Model listing is not an OpenAI-compatible list")
            ids = sorted({row["id"] for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)})
            if not ids:
                raise ProviderError("No model IDs advertised by this endpoint; no model selected")
            if len(ids) > self.settings.ai_discovery_max_models:
                raise ProviderError(f"Endpoint lists {len(ids)} models. Increase AI_DISCOVERY_MAX_MODELS to explicitly allow probe costs")
            return ids
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Model discovery failed ({type(exc).__name__}); no fallback used") from exc

    async def probe(self, model: str, semaphore: asyncio.Semaphore) -> ModelProbe:
        async with semaphore:
            start = time.monotonic()
            payload = {"model": model, "messages": [{"role": "user", "content": "Reply OK."}],
                       "stream": False, **self.settings.ai_extra_body}
            try:
                data = await self._post(payload)
                message = data["choices"][0].get("message", {})
                if not isinstance(message.get("content"), str) or not message["content"].strip():
                    raise ProviderError("Empty chat response")
            except (ProviderError, KeyError, TypeError, IndexError) as exc:
                return ModelProbe(model, False, False, int((time.monotonic() - start) * 1000), str(exc))
            tool = {"type": "function", "function": {"name": "capability_probe", "description": "Return OK",
                     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}
            tools = False
            try:
                result = await self._post({**payload, "messages": [{"role": "user", "content": "Call capability_probe."}],
                                           "tools": [tool], "tool_choice": {"type": "function", "function": {"name": "capability_probe"}}})
                calls = result["choices"][0].get("message", {}).get("tool_calls", [])
                tools = any(c.get("function", {}).get("name") == "capability_probe" for c in calls)
            except (ProviderError, KeyError, TypeError, IndexError):
                pass
            return ModelProbe(model, True, tools, int((time.monotonic() - start) * 1000))

    async def discover(self) -> list[dict]:
        async with self._discovery_lock:
            # Reset first: a failed new discovery must NOT keep an obsolete model alive.
            self.model = None
            self.probes = {}
            ids = await self.advertised()
            sem = asyncio.Semaphore(self.settings.ai_probe_concurrency)
            results = await asyncio.gather(*(self.probe(mid, sem) for mid in ids))
            self.probes = {p.id: p for p in results}
            self.store.set("provider:probes", [asdict(p) for p in results])
            usable = [p for p in results if p.chat and (self.compat == "text" or p.tools)]
            if not usable:
                raise ProviderError("No verified compatible model for this key. Use /compat text for chat-only models, then /models refresh. No fallback used.")
            previous = self.store.get("provider:selected")
            # Keep an explicitly selected ID only if freshly verified. Otherwise select deterministically
            # from verified tool-capable IDs; IDs themselves are never part of source code.
            chosen = next((p for p in usable if p.id == previous), sorted(usable, key=lambda p: (not p.tools, p.id))[0])
            self.model = chosen.id
            self.store.set("provider:selected", chosen.id)
            return [asdict(p) for p in results]

    def select(self, model: str) -> None:
        p = self.probes.get(model)
        if not p or not p.chat or (self.compat == "tools" and not p.tools):
            raise ProviderError("Model not freshly verified for this API key and compatibility mode")
        self.model = model
        self.store.set("provider:selected", model)

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        if self.model is None:
            await self.discover()
        if not self.model:
            raise ProviderError("No verified model selected")
        payload = {"model": self.model, "messages": messages, "stream": False}
        if tools and self.compat == "tools":
            if not self.probes[self.model].tools:
                raise ProviderError("Selected model does not support tools; explicitly choose /compat text")
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        # Provider-specific reasoning is opt-in. Never fabricate support for a thinking parameter.
        if self.thinking:
            if not self.settings.ai_extra_body:
                raise ProviderError("Configure documented AI_EXTRA_BODY thinking fields before /thinking on")
            payload.update(self.settings.ai_extra_body)
        data = await self._post(payload)
        return data["choices"][0]["message"]

    async def close(self) -> None:
        await self.client.aclose()
