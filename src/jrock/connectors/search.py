from __future__ import annotations

import httpx

from jrock.agent.tools import Tool, ToolRegistry, obj, string
from jrock.config import Settings


class SearchConnector:
    """Configurable POST search API contract: {query,limit} -> {results:[{title,url,snippet}]}.

    Results are untrusted text with explicit URLs, never instructions or fabricated sources.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=30, follow_redirects=False)

    async def search(self, owner: int, args: dict) -> list[dict]:
        if not self.settings.search_url:
            raise ValueError("Set SEARCH_URL (and optionally SEARCH_API_KEY) locally. No search results fabricated.")
        headers = {}
        if key := self.settings.search_api_key.get_secret_value():
            headers["Authorization"] = f"Bearer {key}"
        r = await self.client.post(self.settings.search_url, headers=headers,
                                  json={"query": args["query"], "limit": 8})
        if r.is_error:
            raise RuntimeError(f"Search HTTP {r.status_code}")
        results = r.json().get("results", [])
        return [{"title": str(x.get("title", ""))[:500], "url": x["url"],
                 "snippet": str(x.get("snippet", ""))[:4000]}
                for x in results[:8] if str(x.get("url", "")).startswith(("https://", "http://"))]

    def register(self, registry: ToolRegistry) -> None:
        # External queries can transmit data, so they need explicit human approval.
        registry.register(Tool("web_search", "Search external sources; query is sent to configured search API.",
                               obj({"query": string()}), self.search, "connector"))

    async def close(self) -> None:
        await self.client.aclose()
