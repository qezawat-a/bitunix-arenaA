from __future__ import annotations

import json
import re

from jrock.agent.runtime import AgentRuntime
from jrock.agent.tools import Tool, obj, string
from jrock.exchange.catalog import Documentation
from jrock.security import PermissionDenied
from jrock.telegram.controller import pretty, switch
from jrock.trader.broker import LiveBroker
from jrock.trader.engine import TradingEngine
from jrock.trader.models import TradeConfig, decimal
from jrock.trader.risk import RiskRejected, create_plan, order_units
from jrock.trader.strategies import combine

TRADE_HELP = """J+rock · Bitunix futures
/autotrade on|off · /start_trading · /stop_trading · /engine on|off|authorize|disarm
/status · /report on|off · /report interval sec 30
/settings_trade [key value] · /settings trade [key value]
/scan on|off|now · /scans interval sec 15 · /guard interval sec 15
/mid_management_position sec 15
/breakeven_threshold_pct 3 · /trailing_trigger_stop_roi_pct 5
/trailing_stop_pct 1 · /trailing_distance_pct 1 · /liq_sl_distance_pct 2
/min_agreeing_strategies 2 · /min_confidence 80 · /tf_min_confidence 60
/timeframes 1m,3m,5m,15m · /symbols BTCUSDT,ETHUSDT (or all)
/max_positions 2 · /leverage 1 · /reversal on|off
/tpsl · /tp_mode POSITION|PARTIAL|TRAILING|ACCOUNT
/tpsl_method ADAPTIVE|FIXED_R · /partial_tp_ladder 30@1,40@2
/trailing_method ATR|RATIO|INTERVAL · /trailing_callback 2
/account_tp_usdt 0 · /account_sl_usdt 0 · /account_guard_scope MANAGED|ALL
/universe_rank VOLUME|GAINERS|LOSERS|MOVERS · /min_24h_volume_usd 1000000
/positions_history · /close_position <id> [qty] · /cancels order|tpsl <symbol> <id>
/cancels all [symbol] · /reconcile · /reset_circuit
/order_units <symbol> QUANTITY|NOMINAL|COST <amount> [leverage]
/bitunix <endpoint> <JSON parameters> · /bitunix_docs [coverage|query|document-id]
All TradeConfig keys also work as commands. Settings changes pause entries.
Natural command equivalents (e.g. "Start trading", "Report interval sec 30") are accepted.
Paper by default. Live needs local gate + exact approval. /engine off leaves reducing guards active.
Trailing/account guards run locally, require uptime, and keep native stops.
"""

ALIASES = {
    "symbol": "symbols", "scans": "scan", "settings_trade": "trade_settings",
    "trade_settings": "trade_settings", "mid_management_position": "management_interval_sec",
    "trailing_trigger_stop_roi_pct": "trailing_trigger_roi_pct",
    "trailing_trigger_stop_roi": "trailing_trigger_roi_pct", "scans_interval_sec": "scan_interval_sec",
    "scans_interval": "scan_interval_sec", "report_interval": "report_interval_sec",
    "scan_interval": "scan_interval_sec", "guard_interval": "guard_interval_sec",
    "positions_history": "positions_history", "position_history": "positions_history",
    "docs": "bitunix_docs", "compatibility": "compat",
}

# Full-string matching only. The LLM cannot turn conversational text into control commands.
NATURAL = [
    (r"start trading(?: \(autotrade on\))?", "autotrade", "on"),
    (r"stop trading(?: \(autotrade off\))?", "autotrade", "off"),
    (r"(?:engine|report|scan|scans) (on|off)", None, None),
    (r"status", "status", ""),
    (r"settings trade(?: (.*))?", "trade_settings", None),
    (r"(?:report|scans?|guard) interval(?: sec)? (\d+(?:\.\d+)?)", None, None),
    (r"mid management position(?: sec)? (\d+(?:\.\d+)?)", "management_interval_sec", None),
    (r"positions? history", "positions_history", ""),
    (r"close position (.+)", "close_position", None),
    (r"cancels (.+)", "cancels", None),
]
NATURAL_FIELDS = {
    "breakeven threshold pct": "breakeven_threshold_pct", "trailing trigger stop roi pct": "trailing_trigger_roi_pct",
    "trailing stop pct": "trailing_stop_pct", "trailing distance pct": "trailing_distance_pct",
    "liq sl distance pct": "liq_sl_distance_pct", "min agreeing strategies": "min_agreeing_strategies",
    "min confidence": "min_confidence", "tf min confidence": "tf_min_confidence",
    "timeframes": "timeframes", "symbols": "symbols", "symbol": "symbols", "max positions": "max_positions",
}


class TradeController:
    def __init__(self, runtime: AgentRuntime, engine: TradingEngine):
        self.r, self.e = runtime, engine
        self.docs = Documentation()
        self.report_owner: int | None = None
        self.register_tools()

    def register_tools(self) -> None:
        async def status(owner: int, args: dict):
            return self.e.status()
        async def docs(owner: int, args: dict):
            query = args.get("query", "")
            return self.docs.read(query) if query in {d["id"] for d in self.docs.manifest["documents"]} else self.docs.search(query)
        async def read(owner: int, args: dict):
            if self.docs.endpoint(args["endpoint"])["method"] != "GET":
                raise PermissionDenied("bitunix_read accepts documented GET endpoints only")
            return await self.e.client.request(args["endpoint"], args["parameters"])
        async def scan(owner: int, args: dict):
            return await self.preview(args["symbol"], plan=False)
        async def plan(owner: int, args: dict):
            return await self.preview(args["symbol"], plan=True)
        async def mutation(owner: int, args: dict):
            return await self.raw_mutation(owner, args["endpoint"], args["parameters"])
        self.r.tools.register(Tool("trade_status", "Read real cached engine status, signals, prices, PnL and settings (may be stale).", obj({}), status))
        self.r.tools.register(Tool("bitunix_docs", "Search/read ALL supplied packaged Bitunix documents. Empty query gives the complete index.",
                                   obj({"query": string()}, []), docs))
        self.r.tools.register(Tool("bitunix_read", "Call ANY documented Bitunix GET endpoint with exact documented parameter names.",
                                   obj({"endpoint": string(), "parameters": {"type": "object"}}), read))
        self.r.tools.register(Tool("trade_scan", "Read-only ten-strategy multi-timeframe scan; NEVER places a trade or turns autotrade on.",
                                   obj({"symbol": string()}), scan))
        self.r.tools.register(Tool("trade_preview", "Generate a deterministic risk-checked plan/TPSL from current signals; does NOT execute it.",
                                   obj({"symbol": string()}), plan))
        # Expert SDK operations remain available, but are disabled by a separate local environment gate.
        self.r.tools.register(Tool("bitunix_mutation", "EXPERT raw exchange mutation. Requires separate local ALLOW_RAW_EXCHANGE_MUTATIONS=true and exact human approval. Not scanner risk-checked.",
                                   obj({"endpoint": string(), "parameters": {"type": "object"}}), mutation, "trading"))

    async def preview(self, symbol: str, plan: bool = False) -> dict:
        symbol = symbol.upper()
        cfg = self.e.config.model_copy(deep=True)
        await self.e.market.refresh()
        if symbol not in self.e.market.universe(cfg):
            raise RiskRejected("Symbol not in current configured, API-enabled, liquid universe")
        frames = await self.e.market.frames(symbol, cfg)
        funding = self.e.market.funding.get(symbol, {}).get("fundingRate")
        signal = combine(symbol, frames, float(funding) if funding is not None else None, cfg)
        result = {"signal": signal.public(), "executed": False}
        if plan:
            async with self.e.execution_lock:
                account = await self.e.refresh_portfolio()
                ticker = self.e.market.tickers[symbol]
                trade_plan = create_plan(signal, account, self.e.market.rules[symbol],
                        await self.e.client.get_position_tiers(symbol=symbol), cfg,
                        frames[cfg.timeframes[0]], decimal(ticker["lastPrice"]))
                result["plan"] = trade_plan.public()
        return result

    @staticmethod
    def natural(text: str) -> tuple[str, str] | None:
        value = text.strip()
        for pattern, command, args in NATURAL:
            match = re.fullmatch(pattern, value, re.IGNORECASE)
            if not match:
                continue
            lower = value.lower()
            if command is None:
                token, _, rest = lower.partition(" ")
                return ALIASES.get(token, token), rest
            return command, args if args is not None else (match.group(1) or "")
        for prefix, command in sorted(NATURAL_FIELDS.items(), key=lambda pair: len(pair[0]), reverse=True):
            match = re.fullmatch(re.escape(prefix) + r"(?: (.+))?", value, re.IGNORECASE)
            if match:
                return command, match.group(1) or ""
        return None

    @staticmethod
    def value(field: str, text: str):
        text = text.strip()
        if field in {"symbols", "timeframes", "enabled_strategies"}:
            if field == "symbols" and text.lower() in {"all", "*"}:
                return ["*"]
            if text.startswith("["):
                return json.loads(text)
            return [x.strip() for x in text.split(",") if x.strip()]
        info = TradeConfig.model_fields[field]
        if info.annotation is bool:
            return switch(text.lower())
        if info.annotation in {float, int}:
            # Accept human phrasing "interval sec 15", "pct 2", without changing percent/fraction conventions.
            stripped = re.sub(r"^(?:interval\s+)?(?:sec\s+|pct\s+)?", "", text, flags=re.IGNORECASE)
            return info.annotation(stripped)
        if field == "partial_tp_ladder":
            return text
        return text.upper()

    async def setting(self, owner: int, field: str, text: str) -> str:
        if not text:
            return pretty({field: getattr(self.e.config, field)})
        value = self.value(field, text)
        # Validate full config before requesting permission so invalid pending actions are never offered.
        TradeConfig.model_validate({**self.e.config.model_dump(), field: value})
        updates = {field: value}
        if self.e.mode == "paper":
            return pretty(self.e.configure(updates))
        description = f"LIVE settings change: {pretty(updates)}. Pauses entries. New guard thresholds can close positions immediately. Account scope ALL includes unrelated manual positions. Native stops are never intentionally loosened."
        a = self.r.permissions.request(owner, "trade_config", {"updates": updates, "revision": self.e.revision}, description)
        return f"{description}\n/approve {a.id}\n/deny {a.id}"

    def request_live(self, owner: int, autotrade: bool) -> str:
        if self.e.mode != "live" or not self.e.settings.live_trading_enabled:
            raise RiskRejected("Default is PAPER. For live: edit local .env TRADING_MODE=live and LIVE_TRADING_ENABLED=true, restart, then request this approval again")
        payload = {"profile": self.e.profile(), "autotrade": autotrade}
        c = self.e.config
        description = (f"LIVE {'AUTOTRADE' if autotrade else 'REDUCING GUARDS ONLY'} approval. REAL MONEY, potential total loss.\n"
            f"Symbols: {c.symbols}; leverage: {c.leverage}x; max positions: {c.max_positions}; margin budget: {c.max_margin_pct}% equity; risk/trade: {c.risk_per_trade_pct}%; total risk budget: {c.max_total_risk_pct}%.\n"
            f"TP mode: {c.tp_mode}; account guard scope: {c.account_guard_scope}; account TP/SL: {c.account_tp_usdt}/{c.account_sl_usdt} USDT.\n"
            "Includes configuring isolated margin/leverage on eligible flat symbols, documented orders/TP/SL and reducing risk guards. Session only; never restored on restart. No withdrawal permission. Native stops don't guarantee execution.\n"
            f"Profile: {payload['profile']}")
        a = self.r.permissions.request(owner, "live_enable", payload, description)
        return f"{description}\n/approve {a.id}\n/deny {a.id}"

    async def raw_mutation(self, owner: int, endpoint: str, parameters: dict) -> dict:
        if self.e.mode != "live" or not self.e.settings.live_trading_enabled or not self.r.settings.allow_raw_exchange_mutations:
            raise PermissionDenied("Raw financial mutations disabled. Set ALLOW_RAW_EXCHANGE_MUTATIONS=true locally only if you understand this expert SDK path bypasses scanner plan checks. Paper mode NEVER sends exchange POSTs.")
        ep = self.docs.endpoint(endpoint)
        if ep["method"] != "POST":
            raise ValueError("Use bitunix_read for GET endpoints")
        self.docs.validate(endpoint, parameters)
        async with self.e.execution_lock:
            self.e.stop_entries()
            self.e.one_shot_mutation = True
            try:
                result = await self.e.client.request(endpoint, parameters)
            except Exception:
                await self.e.trip("Expert raw mutation failed or outcome unknown; inspect exchange before resuming")
                raise
            finally:
                self.e.one_shot_mutation = False
            await self.e.trip("Expert raw mutation executed; reconcile exchange state before automated trading")
            return {"exchange_acknowledgement": result, "confirmed_execution": False,
                    "notice": "Code 0 is not necessarily a confirmed fill/cancel. Reconcile with order/position REST and private WebSocket."}

    async def approve(self, owner: int, aid: str) -> object:
        a = self.r.permissions.pending.get(aid)
        if not a or a.owner != owner:
            raise PermissionDenied("Approval not found")
        self.r.permissions.approve(owner, aid)
        self.r.permissions.consume(owner, aid, a.action, a.payload)
        if a.action == "live_enable":
            return await self.e.authorize_live(owner, a.payload["profile"], a.payload["autotrade"])
        if a.action == "trade_config":
            if a.payload["revision"] != self.e.revision:
                raise RiskRejected("Settings changed; request a fresh approval")
            return self.e.configure(a.payload["updates"])
        if a.action == "close_position":
            async with self.e.execution_lock:
                self.e.stop_entries()
                if self.e.mode == "paper":
                    await self.e.market.refresh()
                    self.e.broker.mark(self.e.market.tickers)
                else:
                    if not self.e.settings.live_trading_enabled:
                        raise RiskRejected("Local live gate is off")
                    self.e.one_shot_mutation = True
                try:
                    qty = decimal(a.payload["qty"]) if a.payload.get("qty") else None
                    return await self.e.broker.close_position(a.payload["id"], "Human-approved close", qty)
                finally:
                    self.e.one_shot_mutation = False
                    await self.e.refresh_portfolio()
        if a.action == "cancel":
            async with self.e.execution_lock:
                if self.e.mode != "live" or not self.e.settings.live_trading_enabled:
                    raise RiskRejected("Paper mode has no exchange orders; no live cancellation sent")
                self.e.stop_entries()
                self.e.one_shot_mutation = True
                try:
                    result = await self.e.client.request(a.payload["endpoint"], a.payload["parameters"])
                finally:
                    self.e.one_shot_mutation = False
                await self.e.trip("Manual cancellation acknowledged. If a protective stop was canceled, reducing guards may close the position. Reconcile before entries.")
                return {"acknowledgement": result, "confirmed_canceled": False, "notice": "Check private WebSocket/REST for confirmation"}
        if a.action == "reset_circuit":
            await self.e.reset_circuit()
            return {"circuit": None, "autotrade": False}
        raise ValueError("Unknown trading approval action")

    async def handle(self, owner: int, command: str, args: str) -> str | None:
        self.r.permissions.authorize(owner)
        if command == "natural":
            result = self.natural(args)
            if not result:
                return None
            command, args = result
        command = ALIASES.get(command, command)
        if command == "trade_help":
            return TRADE_HELP
        if command in {"start_trading", "stop_trading"}:
            args, command = ("on" if command == "start_trading" else "off"), "autotrade"
        if command == "autotrade":
            if not args:
                return pretty({"autotrade": self.e.autotrade, "mode": self.e.mode})
            if not switch(args.lower()):
                return pretty(self.e.stop_entries())
            if self.e.mode == "paper":
                self.e.enable_paper()
                return "PAPER autotrade on. Simulated fills; NO exchange financial mutations. Scanner and guards enabled."
            return self.request_live(owner, True)
        if command == "engine":
            if args == "off":
                return pretty(self.e.stop_entries(True))
            if args == "on":
                self.e.enabled = self.e.scan_on = True
                return "Engine/scanner on. Autotrade is NOT implicitly enabled. Existing authorized reducing guards continue."
            if args == "authorize":
                return self.request_live(owner, False)
            if args == "disarm":
                self.e.stop_entries()
                self.e.live_authorized = False
                return "Live session disarmed. Native exchange stops remain. LOCAL trailing/account mutations are now disabled until /engine authorize."
            return pretty(self.e.status())
        if command == "status":
            return pretty(self.e.status())
        if command == "report":
            if args in {"on", "off"}:
                self.e.report_on, self.report_owner = switch(args), owner
                return f"Reports {args}; interval {self.e.config.report_interval_sec}s. Signals + actual cached prices + position PnL, with data age."
            if args.startswith("interval"):
                return await self.setting(owner, "report_interval_sec", args)
            return pretty(self.e.report())
        if command == "scan":
            if args in {"on", "off"}:
                self.e.scan_on = switch(args)
                if self.e.scan_on:
                    self.e.enabled = True
                else:
                    self.e.stop_entries()
                return f"Scanner {args}. Autotrade: {self.e.autotrade}."
            if args.startswith("interval"):
                return await self.setting(owner, "scan_interval_sec", args)
            if args == "now":
                results = []
                await self.e.market.refresh()
                for symbol in self.e.market.universe(self.e.config):
                    results.append(await self.preview(symbol))
                return pretty(results)
            return pretty({"scanner": self.e.scan_on, "interval_sec": self.e.config.scan_interval_sec})
        if command == "guard":
            if args.startswith("interval"):
                return await self.setting(owner, "guard_interval_sec", args)
            return "Protective guards remain active for existing positions when authorized. Use /guard interval sec 15."
        if command == "settings" and args.startswith("trade"):
            command, args = "trade_settings", args.removeprefix("trade").strip()
        if command == "trade_settings":
            if not args:
                return pretty(self.e.status())
            key, _, value = args.partition(" ")
            key = ALIASES.get(key.lower().replace("-", "_"), key.lower().replace("-", "_"))
            if key not in TradeConfig.model_fields:
                raise ValueError("Unknown trading setting; /settings_trade lists every key")
            return await self.setting(owner, key, value)
        if command == "reversal":
            return await self.setting(owner, "reversal_enabled", args)
        if command == "tpsl":
            if args:
                sub, _, value = args.partition(" ")
                key = {"mode": "tp_mode", "method": "tpsl_method", "ladder": "partial_tp_ladder"}.get(sub)
                if not key:
                    raise ValueError("Use /tpsl mode|method|ladder <value>")
                return await self.setting(owner, key, value)
            keys = ("tp_mode", "tpsl_method", "partial_tp_ladder", "trailing_method", "trailing_callback", "account_tp_usdt", "account_sl_usdt", "account_guard_scope")
            return pretty({**{k: getattr(self.e.config, k) for k in keys}, "local_features": ["trailing", "account"],
                          "native_features": ["position", "partial"], "documentation": "/bitunix_docs four_tpsl_methods"})
        if command in TradeConfig.model_fields:
            return await self.setting(owner, command, args)
        if command == "positions" and args == "history":
            command = "positions_history"
        if command == "positions_history":
            if self.e.mode == "paper":
                return pretty(self.e.store.events("paper_close", 100))
            params = json.loads(args) if args.startswith("{") else {"limit": 100}
            return pretty(await self.e.client.get_history_positions(**params))
        if command == "close_position":
            parts = args.split()
            if not 1 <= len(parts) <= 2:
                raise ValueError("Use /close_position <position-id> [base-coin qty]")
            qty = str(decimal(parts[1])) if len(parts) == 2 else None
            if qty is not None and decimal(qty) <= 0:
                raise ValueError("Close qty must be positive")
            payload = {"id": parts[0], "qty": qty}
            a = self.r.permissions.request(owner, "close_position", payload,
                f"{self.e.mode.upper()} close position {parts[0]}, quantity {qty or 'ALL'}, market execution, irreversible after submission.")
            return f"{a.description}\n/approve {a.id}\n/deny {a.id}"
        if command == "cancels":
            parts = args.split()
            if not parts:
                raise ValueError("Use /cancels order|tpsl <symbol> <id>, or /cancels all [symbol]")
            if parts[0] == "all" and len(parts) in {1, 2}:
                endpoint, parameters = "cancel_all_orders", ({"symbol": parts[1].upper()} if len(parts) == 2 else {})
            elif parts[0] in {"order", "tpsl"} and len(parts) == 3:
                endpoint = "cancel_orders" if parts[0] == "order" else "cancel_tp_sl_order"
                parameters = {"symbol": parts[1].upper(), **({"orderList": [{"orderId": parts[2]}]} if parts[0] == "order" else {"orderId": parts[2]})}
            else:
                raise ValueError("Use /cancels order|tpsl <symbol> <id>, or /cancels all [symbol]")
            self.docs.validate(endpoint, parameters)
            if self.e.mode == "paper":
                return "Paper engine has no exchange orders to cancel. Use /close_position to close a simulated position. No live request sent."
            a = self.r.permissions.request(owner, "cancel", {"endpoint": endpoint, "parameters": parameters},
                    "LIVE cancel: " + pretty(parameters) + ". Canceling a stop can remove protection; local guards may emergency-close. Entries will pause.")
            return f"{a.description}\n/approve {a.id}\n/deny {a.id}"
        if command == "order_units":
            parts = args.split()
            if len(parts) not in {3, 4}:
                raise ValueError("Use /order_units <symbol> QUANTITY|NOMINAL|COST <amount> [leverage]")
            symbol, unit, amount = parts[:3]
            leverage = int(parts[3]) if len(parts) == 4 else self.e.config.leverage
            await self.e.market.refresh()
            if symbol.upper() not in self.e.market.rules or symbol.upper() not in self.e.market.tickers:
                raise ValueError("Unknown current symbol")
            result = order_units(unit, decimal(amount), decimal(self.e.market.tickers[symbol.upper()]["lastPrice"]),
                                 leverage, self.e.market.rules[symbol.upper()], decimal(self.e.config.taker_fee_rate))
            return pretty({**result, "executed": False, "note": "Estimate only; no order placed"})
        if command == "bitunix_docs":
            if args == "coverage":
                return pretty({"rest_endpoints": len(self.docs.rest), "request_table_rows": sum(len(x["parameters"]) for x in self.docs.rest.values()),
                    "response_table_rows": sum(len(x["response_parameters"]) for x in self.docs.rest.values()), "ws_channels": len(self.docs.ws),
                    "documents": len(self.docs.manifest["documents"]), "missing_supplied_pages": self.docs.manifest["unavailable_supplied_pages"],
                    "hash_failures": self.docs.verify(), "retrieved": self.docs.manifest["retrieved"], "note": self.docs.manifest["transcription_note"]})
            return self.docs.read(args) if args in {d["id"] for d in self.docs.manifest["documents"]} else pretty(self.docs.search(args))
        if command == "bitunix":
            endpoint, _, params = args.partition(" ")
            if not endpoint:
                return pretty([{key: ep[key] for key in ("name", "method", "path", "source")} for ep in self.docs.rest.values()])
            parameters = json.loads(params or "{}")
            ep = self.docs.endpoint(endpoint)
            self.docs.validate(endpoint, parameters)
            tool = "bitunix_read" if ep["method"] == "GET" else "bitunix_mutation"
            return pretty(await self.r.tools.invoke(owner, tool, {"endpoint": endpoint, "parameters": parameters}))
        if command == "reconcile":
            if not isinstance(self.e.broker, LiveBroker):
                await self.e.refresh_portfolio()
                return pretty(self.e.status())
            async with self.e.execution_lock:
                unresolved = await self.e.broker.reconcile_intents()
                await self.e.refresh_portfolio()
                return pretty({"unresolved": unresolved, "entries_resumed": False,
                        "notice": "Read-only reconciliation. No POST was retried, no live session was re-armed. Inspect exchange if unresolved."})
        if command == "reset_circuit":
            a = self.r.permissions.request(owner, "reset_circuit", {}, "Reset circuit after investigation. Denied if unresolved intents or daily-loss limit remain. Does not resume entries.")
            return f"{a.description}\n/approve {a.id}\n/deny {a.id}"
        return None
