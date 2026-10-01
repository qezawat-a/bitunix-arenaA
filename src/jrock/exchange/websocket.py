from __future__ import annotations

import asyncio
import contextlib
import json
import random
import re
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from decimal import Decimal

import websockets

from jrock.exchange.catalog import Documentation
from jrock.exchange.client import ExchangeError, RateLimiter
from jrock.exchange.signing import websocket_login


def business_time_ns(value: str | int) -> int:
    """REST milliseconds or WS ISO-8601 nanoseconds, without confusing gateway ts."""
    if isinstance(value, int) or str(value).isdigit():
        return int(value) * 1_000_000
    match = re.fullmatch(r"(.+?)(?:\.(\d{1,9}))?Z", str(value))
    if not match:
        raise ValueError("Unsupported business timestamp")
    dt = datetime.fromisoformat(match[1] + "+00:00")
    return int(dt.timestamp()) * 1_000_000_000 + int((match[2] or "").ljust(9, "0") or "0")


class WSState:
    """Cache for monitoring/reconciliation, NOT a substitute for authoritative REST positions."""

    def __init__(self):
        self.prices: dict[str, dict] = {}
        self.orders: dict[str, dict] = {}
        self.tpsl: dict[str, dict] = {}
        self.depth: dict[str, dict[str, dict[Decimal, Decimal]]] = {}
        self.last_event: dict[str, float] = {}
        self.last_business_time: dict[str, int] = {}
        self.dirty = asyncio.Event()

    def reconnect(self) -> None:
        self.depth.clear()
        self.prices.clear()
        self.dirty.set()

    def apply(self, event: dict) -> None:
        ch, data = event.get("ch", ""), event.get("data")
        self.last_event[ch] = time.monotonic()
        if ch in {"order", "tpsl", "balance", "position"}:
            self.dirty.set()
        if ch == "tpsl":
            if not isinstance(data, dict):
                raise ExchangeError("ws_protocol", "TPSL data must be an object, not an array")
            if data.get("status") not in {"NEW", "CANCELED", "SYSTEM_CANCELED", "FILLED", "FAILED"}:
                return
            oid = str(data.get("orderId", ""))
            old = self.tpsl.get(oid, {})
            if old.get("status") in {"CANCELED", "SYSTEM_CANCELED", "FILLED", "FAILED"} and data.get("status") == "NEW":
                return
            # FILLED means trigger -> child placed; never change a position quantity here.
            self.tpsl[oid] = data
        elif ch == "order" and isinstance(data, dict):
            oid = str(data.get("orderId", ""))
            timestamp = data.get("mtime") or data.get("ctime")
            if timestamp:
                try:
                    ts = business_time_ns(timestamp)
                except ValueError:
                    return
                if ts < self.last_business_time.get(oid, 0):
                    return
                self.last_business_time[oid] = ts
            old = self.orders.get(oid, {})
            finals = {"CANCELED", "FILLED", "PART_FILLED_CANCELED", "EXPIRED"}
            if old.get("orderStatus") in finals and data.get("orderStatus") not in finals:
                return
            self.orders[oid] = data
        elif ch == "price" and isinstance(data, dict) and event.get("symbol"):
            self.prices[event["symbol"]] = {**data, "received": time.monotonic()}
        elif ch.startswith("depth_") and isinstance(data, dict):
            symbol = event.get("symbol")
            if not symbol:
                return
            if ch != "depth_books" or symbol not in self.depth:
                self.depth[symbol] = {"a": {}, "b": {}}
            book = self.depth[symbol]
            for side in ("a", "b"):
                for row in data.get(side, []):
                    price, qty = Decimal(str(row[0])), Decimal(str(row[1]))
                    if qty == 0:
                        book[side].pop(price, None)
                    else:
                        book[side][price] = qty


class BitunixWebSocket:
    def __init__(self, url: str, private: bool = False, api_key: str = "", secret: str = "",
                 heartbeat_sec: float = 10):
        self.url, self.private, self.api_key, self.secret = url, private, api_key, secret
        self.heartbeat_sec = heartbeat_sec
        self.subscriptions: list[dict] = []
        self.ws = None
        self.connected = False
        self.authenticated = False
        self.last_message = 0.0
        self.reconnects = 0
        self.last_error: str | None = None
        self.limiter = RateLimiter()
        self.docs = Documentation()
        self._send_lock = asyncio.Lock()

    def validate_channels(self, args: list[dict]) -> None:
        if len(args) > 300:
            raise ValueError("At most 300 subscriptions per WebSocket connection")
        private = {"balance", "position", "order", "tpsl"}
        simple = {"price", "ticker", "tickers", "trade", "depth_books", "depth_book1", "depth_book5", "depth_book15"}
        intervals = {"1min", "3min", "5min", "15min", "30min", "60min", "2h", "4h", "6h", "8h", "12h", "1day", "3day", "1week", "1month"}
        for arg in args:
            if set(arg) - {"ch", "symbol"} or "ch" not in arg:
                raise ValueError("WS argument keys: ch, symbol")
            ch = arg["ch"]
            if self.private:
                if ch not in private:
                    raise ValueError("Unknown private channel")
            else:
                parts = ch.split("_kline_")
                kline = len(parts) == 2 and parts[0] in {"market", "mark"} and parts[1] in intervals
                if ch not in simple and not kline:
                    raise ValueError("Unknown public channel")
                if not arg.get("symbol"):
                    raise ValueError("Public channel requires symbol")

    async def send(self, payload: dict) -> None:
        async with self._send_lock:
            if self.ws is None:
                raise ExchangeError("ws", "WebSocket not connected")
            # 3 JSON messages/sec leaves room for automatic control-frame replies under server cap 5.
            await self.limiter.wait("ws", 3)
            await self.ws.send(json.dumps(payload, separators=(",", ":")))

    async def subscribe(self, args: list[dict]) -> None:
        new = [a for a in args if a not in self.subscriptions]
        self.validate_channels(self.subscriptions + new)
        self.subscriptions.extend(new)
        if self.connected and new:
            await self.send({"op": "subscribe", "args": new})

    async def unsubscribe(self, args: list[dict]) -> None:
        self.validate_channels(args)
        self.subscriptions = [a for a in self.subscriptions if a not in args]
        if self.connected:
            await self.send({"op": "unsubscribe", "args": args})

    async def switch_kline(self, symbol: str, old: str, new: str) -> None:
        await self.unsubscribe([{"symbol": symbol, "ch": old}])
        await self.subscribe([{"symbol": symbol, "ch": new}])

    async def heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_sec)
            await self.send({"op": "ping", "ping": int(time.time())})

    async def run(self, callback: Callable[[dict], Awaitable[None]], stop: asyncio.Event,
                  on_reconnect: Callable[[], None] | None = None) -> None:
        if self.private and not (self.api_key and self.secret):
            self.last_error = "Private WebSocket credentials missing"
            return
        delay = 1.0
        while not stop.is_set():
            heartbeat = None
            try:
                async with websockets.connect(self.url, ping_interval=None, open_timeout=15,
                        close_timeout=5, max_size=2_000_000, max_queue=64) as ws:
                    self.ws, self.connected = ws, True
                    self.authenticated = not self.private
                    if on_reconnect:
                        on_reconnect()
                    if self.private:
                        await self.send(websocket_login(self.api_key, self.secret))
                    if self.subscriptions:
                        await self.send({"op": "subscribe", "args": self.subscriptions})
                    heartbeat = asyncio.create_task(self.heartbeat())
                    while not stop.is_set():
                        message = json.loads(await asyncio.wait_for(ws.recv(), 35))
                        self.last_message = time.monotonic()
                        if self.private and (message.get("op") == "login" or message.get("event") == "login"):
                            if str(message.get("code", "0")) not in {"0", "200"}:
                                raise ExchangeError("ws_auth", "Private login rejected")
                            self.authenticated = True
                        if message.get("ch"):
                            if self.private:
                                # Receiving a private event is proof of login success if no ack envelope was documented.
                                self.authenticated = True
                            await callback(message)
                        delay = 1.0
                        self.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = type(exc).__name__  # Never log login payload/key.
                self.reconnects += 1
            finally:
                if heartbeat:
                    heartbeat.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await heartbeat
                self.ws, self.connected, self.authenticated = None, False, False
            try:
                await asyncio.wait_for(stop.wait(), delay + random.uniform(0, 0.25))
            except TimeoutError:
                pass
            delay = min(delay * 2, 30)

    def status(self) -> dict:
        return {"connected": self.connected, "authenticated": self.authenticated,
                "reconnects": self.reconnects, "last_error": self.last_error,
                "last_message_age_sec": round(time.monotonic() - self.last_message, 1) if self.last_message else None}
