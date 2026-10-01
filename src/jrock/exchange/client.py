from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Callable

import httpx

from jrock.exchange.catalog import Documentation
from jrock.exchange.signing import compact_body, rest_headers, wire_value


class ExchangeError(RuntimeError):
    def __init__(self, code: int | str, description: str):
        self.code = code
        super().__init__(f"Bitunix {code}: {description}")


class AmbiguousMutation(ExchangeError):
    """A POST may have reached the exchange. NEVER retry blindly."""


class RateLimiter:
    def __init__(self):
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.calls: dict[str, deque] = defaultdict(deque)

    async def wait(self, bucket: str, limit: int) -> None:
        async with self.locks[bucket]:
            calls = self.calls[bucket]
            while True:
                now = time.monotonic()
                while calls and now - calls[0] >= 1:
                    calls.popleft()
                if len(calls) < limit:
                    calls.append(now)
                    return
                await asyncio.sleep(max(0.001, 1 - (now - calls[0])))


class BitunixClient:
    """All 35 documented endpoints; exact wire keys; lossless response data.

    Named methods are resolved from the packaged catalog, e.g.
    await client.get_funding_rate_history(symbol='BTCUSDT', starTime=...).
    Mutation permission is a runtime gate, OFF by default. No POST retries.
    """

    def __init__(self, base_url: str = "https://fapi.bitunix.com", api_key: str = "", secret: str = "",
                 client: httpx.AsyncClient | None = None, mutation_guard: Callable[[], bool] | None = None):
        self.base_url, self.api_key, self.secret = base_url.rstrip("/"), api_key, secret
        self.client = client or httpx.AsyncClient(timeout=15, follow_redirects=False)
        self.docs = Documentation()
        self.limiter = RateLimiter()
        self.mutation_guard = mutation_guard or (lambda: False)

    def __getattr__(self, name: str):
        docs = self.__dict__.get("docs")
        if docs and name in docs.rest:
            async def endpoint(**params):
                return await self.request(name, params)
            return endpoint
        raise AttributeError(name)

    async def request(self, name: str, params: dict | None = None):
        params = {} if params is None else params
        ep = self.docs.endpoint(name)
        self.docs.validate(name, params)
        mutation = ep["method"] != "GET"
        if mutation and not self.mutation_guard():
            raise ExchangeError("permission", "Exchange mutations disabled: paper mode or live authorization missing")
        if not ep["public"] and not (self.api_key and self.secret):
            raise ExchangeError("configuration", "Set Bitunix credentials locally; never in Telegram")
        query = params if not mutation else {}
        body = compact_body(params) if mutation else ""
        attempts = 1 if mutation else 3
        for attempt in range(attempts):
            await self.limiter.wait(name, ep["rate_per_second"])
            # Conservative shared rate budget protects aggregate market polling across endpoints.
            await self.limiter.wait("public" if ep["public"] else "private", 8)
            headers = {"language": "en-US", "Content-Type": "application/json"}
            if not ep["public"]:
                headers = rest_headers(self.api_key, self.secret, query, body)
            try:
                r = await self.client.request(ep["method"], self.base_url + ep["path"], headers=headers,
                    params={k: wire_value(v) for k, v in query.items()}, content=body.encode() if mutation else None)
            except httpx.HTTPError as exc:
                if mutation:
                    raise AmbiguousMutation("transport", "Result unknown; reconcile order/position by clientId. No blind retry.") from exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.25 * 2**attempt)
                    continue
                raise ExchangeError("transport", "Read request failed; check connectivity") from exc
            if r.status_code == 429 or r.status_code >= 500:
                if mutation:
                    raise AmbiguousMutation(r.status_code, "Mutation outcome unknown; reconcile before another action")
                if attempt + 1 < attempts:
                    await asyncio.sleep(min(3, 0.5 * 2**attempt))
                    continue
            if r.is_error:
                raise ExchangeError(r.status_code, "HTTP request rejected")
            try:
                data = r.json()
                code = int(data["code"])
            except (ValueError, TypeError, KeyError) as exc:
                cls = AmbiguousMutation if mutation else ExchangeError
                raise cls("protocol", "Invalid exchange response envelope") from exc
            if code != 0:
                if not mutation and code in {10005, 10006} and attempt + 1 < attempts:
                    await asyncio.sleep(0.5 * 2**attempt)
                    continue
                # Known descriptions are local, so echoed secrets never enter Telegram/logs.
                description = self.docs.errors.get(str(code), {}).get("description", "Unknown exchange error (see local logs/docs)")
                raise ExchangeError(code, description)
            return data.get("data")
        raise ExchangeError("transport", "Read request retry budget exhausted")

    async def paginate(self, name: str, params: dict | None = None, list_key: str = "orderList", max_pages: int = 100):
        params = dict(params or {})
        params["limit"] = 100
        skip = int(params.get("skip", 0))
        for _ in range(max_pages):
            page = await self.request(name, {**params, "skip": skip})
            values = page.get(list_key, []) if isinstance(page, dict) else page
            if not isinstance(values, list):
                raise ExchangeError("protocol", "Expected paginated array")
            for value in values:
                yield value
            skip += len(values)
            if len(values) < 100 or (isinstance(page, dict) and skip >= int(page.get("total", 2**63))):
                return
        raise ExchangeError("pagination", "Maximum pages exceeded; narrow time range")

    async def close(self) -> None:
        await self.client.aclose()
