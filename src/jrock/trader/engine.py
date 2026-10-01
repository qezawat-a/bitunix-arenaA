from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urlparse

from jrock.config import Settings
from jrock.exchange.client import AmbiguousMutation, BitunixClient, ExchangeError
from jrock.exchange.websocket import BitunixWebSocket, WSState
from jrock.storage import Store
from jrock.trader.broker import LiveBroker, PaperBroker, ProtectionFailure
from jrock.trader.market import MarketData
from jrock.trader.models import D, Position, Signal, TradeConfig, decimal
from jrock.trader.risk import AccountSnapshot, RiskRejected, create_plan, managed_stop
from jrock.trader.strategies import combine


class TradingEngine:
    """Independent engine. No Telegram or LLM import; integration is dependency injection.

    Restart never resumes live authorization or auto-trading. Intent/portfolio/config journals persist.
    Native stops remain at the exchange when the local service stops. Local trailing/account logic does not.
    """

    def __init__(self, settings: Settings, store: Store | None = None, client: BitunixClient | None = None):
        self.settings = settings
        settings.initialize_directories()
        self.store = store or Store(settings.data_dir / "trader.db")
        self.owns_store = store is None
        self.config = TradeConfig.model_validate(self.store.get("trade:config", TradeConfig.from_settings(settings).model_dump()))
        self.mode = settings.trading_mode
        self.enabled = False
        self.scan_on = False
        self.autotrade = False
        self.report_on = False
        self.live_authorized = False
        self.one_shot_mutation = False
        self.authorized_profile: str | None = None
        self.authorized_owner: int | None = None
        self.revision = 0
        self.client = client or BitunixClient(settings.bitunix_base_url, settings.bitunix_api_key.get_secret_value(),
                    settings.bitunix_api_secret.get_secret_value(), mutation_guard=self.can_mutate)
        # Even an injected client cannot bypass the engine's paper/live gate.
        self.client.mutation_guard = self.can_mutate
        self.market = MarketData(self.client)
        self.broker = PaperBroker(self.store, self.config) if self.mode == "paper" else LiveBroker(self.store, self.config, self.client)
        if isinstance(self.broker, LiveBroker):
            self.broker.entry_guard = self.can_open
        self.signals: dict[str, Signal] = {}
        self.cached_positions: list[Position] = []
        self.cached_account: AccountSnapshot | None = None
        self.circuit = self.store.get("trade:circuit")
        self.cooldowns: dict[str, float] = self.store.get("trade:cooldowns", {})
        self.last_error: str | None = None
        self.last_scan: float | None = None
        self.scan_duration_sec: float | None = None
        self.scan_progress: str | None = None
        self.last_guard: float | None = None
        self.last_funding_check = 0.0
        self.execution_lock = asyncio.Lock()
        self.stop = asyncio.Event()
        self.tasks: list[asyncio.Task] = []
        self.reporter: Callable[[dict], Awaitable[None]] | None = None
        self.notifications: Callable[[str], Awaitable[None]] | None = None
        self.ws_state = WSState()
        parsed = urlparse(settings.bitunix_base_url)
        ws_origin = ("wss" if parsed.scheme == "https" else "ws") + "://" + parsed.netloc
        self.public_ws = BitunixWebSocket(ws_origin + "/public/")
        self.private_ws = BitunixWebSocket(ws_origin + "/private/", True,
                        settings.bitunix_api_key.get_secret_value(), settings.bitunix_api_secret.get_secret_value())

    def profile(self) -> str:
        return hashlib.sha256(json.dumps(self.config.model_dump(), sort_keys=True).encode()).hexdigest()

    def can_mutate(self) -> bool:
        return self.mode == "live" and self.settings.live_trading_enabled and (self.live_authorized or self.one_shot_mutation)

    def can_open(self) -> bool:
        return self.enabled and self.scan_on and self.autotrade and not self.circuit and (
            self.mode == "paper" or (self.can_mutate() and self.authorized_profile == self.profile()))

    async def authorize_live(self, owner: int, expected_profile: str, autotrade: bool = True) -> dict:
        if self.mode != "live" or not self.settings.live_trading_enabled:
            raise RiskRejected("Set TRADING_MODE=live and LIVE_TRADING_ENABLED=true locally first, then restart")
        if not self.settings.bitunix_api_key.get_secret_value() or not self.settings.bitunix_api_secret.get_secret_value():
            raise RiskRejected("Bitunix credentials are not configured")
        if expected_profile != self.profile():
            raise RiskRejected("Trading settings changed after approval. Request a fresh approval")
        if self.circuit and autotrade:
            raise RiskRejected("Circuit breaker is open. Reconcile/reset explicitly before authorization")
        if autotrade and isinstance(self.broker, LiveBroker) and self.broker.unresolved():
            raise RiskRejected("Unresolved order intents exist; /reconcile before new exposure")
        await self.refresh_portfolio()
        self.live_authorized = True
        self.authorized_profile, self.authorized_owner = expected_profile, owner
        self.enabled, self.scan_on, self.autotrade = True, True, autotrade
        self.store.event("live_authorization", {"owner": owner, "profile": expected_profile, "autotrade": autotrade})
        return {"live_authorized": True, "autotrade": autotrade, "profile": expected_profile,
                "scope": "session-only; configured entries and reducing guards; never resumed after restart"}

    def enable_paper(self) -> None:
        if self.mode != "paper":
            raise RiskRejected("Live trading requires exact human authorization")
        if self.circuit:
            raise RiskRejected("Circuit breaker open; investigate and reset before trading")
        self.enabled, self.scan_on, self.autotrade = True, True, True

    def configure(self, updates: dict) -> dict:
        new = TradeConfig.model_validate({**self.config.model_dump(), **updates})
        # Fail BEFORE mutation if invalid, then stop entries immediately on any config change.
        self.autotrade = False
        self.authorized_profile = None
        self.revision += 1
        self.config = new
        self.broker.config = new
        self.market.candle_cache.clear()
        self.store.set("trade:config", new.model_dump())
        self.store.event("trade_config", {"fields": list(updates), "entries_paused": True})
        return {"settings": new.model_dump(), "autotrade": False, "notice": "Entries paused; /autotrade on with a fresh live approval to resume. Existing stops are never loosened."}

    def stop_entries(self, engine_off: bool = False) -> dict:
        self.autotrade = False
        if engine_off:
            self.enabled = self.scan_on = self.report_on = False
        return {"autotrade": False, "engine": self.enabled,
                "notice": "No new entries. In-flight exchange requests cannot be recalled. Native stops remain; authorized reducing guards continue for open positions."}

    async def trip(self, reason: str) -> None:
        self.autotrade = False
        self.circuit = reason
        self.store.set("trade:circuit", reason)
        self.store.event("circuit", {"reason": reason})
        if self.notifications:
            await self.notifications("TRADING CIRCUIT OPEN: " + reason + "\nInspect /status and exchange. No new entries.")

    async def reset_circuit(self) -> None:
        if isinstance(self.broker, LiveBroker) and self.broker.unresolved():
            raise RiskRejected("Unresolved live intents remain. Reconcile on the exchange first")
        account = await self.refresh_portfolio()
        if account.daily_realized <= -(account.day_start_equity or account.equity) * decimal(self.config.max_daily_loss_pct) / 100:
            raise RiskRejected("Daily loss limit still exceeded; cannot reset it by restarting")
        self.circuit = None
        self.store.set("trade:circuit", None)
        self.autotrade = False

    def daily_risk(self, account: AccountSnapshot) -> AccountSnapshot:
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        baseline = self.store.get("trade:day_baseline", {})
        if baseline.get("day") != day:
            baseline = {"day": day, "equity": str(account.equity)}
            self.store.set("trade:day_baseline", baseline)
        account.day_start_equity = decimal(baseline["equity"])
        kinds = ("paper_open", "paper_close", "paper_funding") if self.mode == "paper" else ("live_history",)
        rows = self.store.db.execute("SELECT payload FROM events WHERE created>=? AND kind IN (" +
                ",".join("?" for _ in kinds) + ")", (start, *kinds))
        account.daily_realized = sum((decimal(json.loads(r[0]).get("net_pnl", json.loads(r[0]).get("conservative_net_pnl", 0))) for r in rows), D(0))
        if self.mode == "live":
            # Include realized partial-position losses and deducted costs while the position is still open.
            # Conservatively count lifetime losses for positions spanning UTC midnight (never credit unknown funding sign).
            for p in account.positions:
                if p.managed:
                    account.daily_realized += min(D(0), decimal(p.raw.get("realizedPNL", 0))) - abs(decimal(p.raw.get("fee", 0))) - abs(decimal(p.raw.get("funding", 0)))
        return account

    async def refresh_portfolio(self) -> AccountSnapshot:
        self.broker.mark(self.market.tickers)
        account = self.daily_risk(await self.broker.account())
        self.cached_positions, self.cached_account = account.positions, account
        return account

    async def scan_once(self) -> None:
        if not self.scan_on or not self.enabled:
            return
        start = time.monotonic()
        revision = self.revision
        cfg = self.config.model_copy(deep=True)
        await self.market.refresh()
        universe = self.market.universe(cfg)
        # Keep the WS universe bounded, no invented candle-close flags; indicators use REST.
        args = [{"symbol": s, "ch": ch} for s in universe for ch in ("price", "tickers")]
        old = [arg for arg in self.public_ws.subscriptions if arg not in args]
        if old:
            await self.public_ws.unsubscribe(old)
        if args:
            await self.public_ws.subscribe(args)
        for i, symbol in enumerate(universe):
            if not self.scan_on or not self.enabled or revision != self.revision:
                break
            self.scan_progress = f"{i + 1}/{len(universe)} {symbol}"
            try:
                frames = await self.market.frames(symbol, cfg)
                funding = self.market.funding.get(symbol, {}).get("fundingRate")
                signal = combine(symbol, frames, float(funding) if funding is not None else None, cfg)
                self.signals[symbol] = signal
                self.store.event("signal", signal.public())
                if signal.direction != "NEUTRAL" and self.can_open() and revision == self.revision:
                    await self.enter(signal, frames[cfg.timeframes[0]], revision)
            except RiskRejected as exc:
                self.store.event("risk_rejection", {"symbol": symbol, "reason": str(exc)})
            except (ExchangeError, ValueError) as exc:
                # Invalid/missing data never becomes a neutral placeholder permitting other trades.
                self.signals.pop(symbol, None)
                self.last_error = str(exc)
                self.store.event("scan_error", {"symbol": symbol, "error": type(exc).__name__})
        self.last_scan = time.time()
        self.scan_duration_sec = round(time.monotonic() - start, 2)
        self.scan_progress = None
        # Remove signals for symbols no longer in the configured liquid universe.
        self.signals = {s: v for s, v in self.signals.items() if s in universe}

    async def enter(self, signal: Signal, candles: list, revision: int) -> None:
        async with self.execution_lock:
            if not self.can_open() or revision != self.revision:
                return
            if time.time() < self.cooldowns.get(signal.symbol, 0):
                raise RiskRejected("Symbol is in cooldown")
            if self.mode == "live" and not (self.private_ws.connected and self.private_ws.authenticated):
                raise RiskRejected("Private WebSocket is not authenticated; entries blocked until reconciliation feed is healthy")
            if time.monotonic() - self.market.updated > self.config.max_market_data_age_sec:
                raise RiskRejected("Market snapshot is stale")
            if int(time.time() * 1000) - signal.timestamp_ms > self.config.max_market_data_age_sec * 1000:
                raise RiskRejected("Signal is stale")
            # Re-fetch prices/depth immediately before order; scanners can take longer than their requested cadence.
            tickers = await self.client.get_tickers(symbols=signal.symbol)
            if not tickers or not isinstance(tickers, list):
                raise RiskRejected("Current ticker missing")
            ticker = next((t for t in tickers if t["symbol"] == signal.symbol), None)
            if ticker is None:
                raise RiskRejected("Requested symbol absent from current ticker response")
            last, mark = decimal(ticker["lastPrice"]), decimal(ticker["markPrice"])
            if last <= 0 or mark <= 0 or signal.price <= 0:
                raise RiskRejected("Nonpositive current price")
            if abs(last / decimal(signal.price) - 1) * 100 > decimal(self.config.max_price_deviation_pct):
                raise RiskRejected("Price moved too far from closed-candle signal")
            depth = await self.client.get_depth(symbol=signal.symbol, limit="5")
            if not depth.get("asks") or not depth.get("bids"):
                raise RiskRejected("Order book unavailable")
            ask, bid = decimal(depth["asks"][0][0]), decimal(depth["bids"][0][0])
            if bid <= 0 or ask < bid or (ask - bid) / ((ask + bid) / 2) * 10000 > decimal(self.config.max_spread_bps):
                raise RiskRejected("Spread exceeds safety limit or book invalid")
            metadata = await self.client.get_trading_pairs(symbols=signal.symbol)
            from jrock.trader.models import PairRules
            rules = PairRules.from_api(next(r for r in metadata if r["symbol"] == signal.symbol))
            tiers = await self.client.get_position_tiers(symbol=signal.symbol)
            self.market.tickers[signal.symbol] = ticker
            account = await self.refresh_portfolio()
            plan = create_plan(signal, account, rules, tiers, self.config, candles, last)
            if (plan.side == "LONG" and plan.stop_loss >= mark) or (plan.side == "SHORT" and plan.stop_loss <= mark):
                raise RiskRejected("Stop is invalid against current MARK price")
            if not self.can_open() or revision != self.revision:
                return
            try:
                await self.broker.open(plan, rules)
            except (AmbiguousMutation, ProtectionFailure) as exc:
                await self.trip(str(exc))
                return
            self.cooldowns[signal.symbol] = time.time() + self.config.cooldown_sec
            self.store.set("trade:cooldowns", self.cooldowns)
            await self.refresh_portfolio()

    async def close_managed(self, p: Position, reason: str) -> None:
        if self.mode == "live" and not self.can_mutate():
            self.last_error = "LIVE REDUCING GUARD NOT AUTHORIZED. Native exchange stops remain. /engine authorize to enable session guards."
            return
        try:
            await self.broker.close_position(p.id, reason)
            self.cooldowns[p.symbol] = time.time() + self.config.cooldown_sec
            self.store.set("trade:cooldowns", self.cooldowns)
        except (AmbiguousMutation, ProtectionFailure) as exc:
            await self.trip(str(exc))

    async def guard_once(self) -> None:
        async with self.execution_lock:
            # Guards run independently of scanner and autotrade switches if positions remain.
            if time.monotonic() - self.market.updated > self.config.guard_interval_sec:
                await self.market.refresh()
            account = await self.refresh_portfolio()
            positions = account.positions
            tracked = positions if self.config.account_guard_scope == "ALL" else [p for p in positions if p.managed]
            pnl = sum((p.unrealized for p in tracked), D(0))
            account_exit = (self.config.account_tp_usdt > 0 and pnl >= decimal(self.config.account_tp_usdt)) or (
                            self.config.account_sl_usdt > 0 and pnl <= -decimal(self.config.account_sl_usdt))
            if account_exit and tracked:
                self.autotrade = False
                for p in tracked:
                    await self.close_managed(p, "Account PnL threshold")
                await self.trip("Account PnL threshold reached; entries paused")
            else:
                for p in positions:
                    if not p.managed:
                        continue
                    if p.symbol not in self.market.tickers:
                        self.last_error = f"No current mark for {p.symbol}; local guard cannot infer a price"
                        continue
                    breached = p.stop_loss is not None and (p.mark <= p.stop_loss if p.side == "LONG" else p.mark >= p.stop_loss)
                    tp_hit = p.take_profit is not None and (p.mark >= p.take_profit if p.side == "LONG" else p.mark <= p.take_profit)
                    if breached or tp_hit:
                        await self.close_managed(p, "Stop loss" if breached else "Take profit")
                        continue
                    if isinstance(self.broker, PaperBroker):
                        for rung in p.raw.get("ladder", []):
                            if p.id not in self.broker.open_positions:
                                break
                            hit = p.mark >= decimal(rung["price"]) if p.side == "LONG" else p.mark <= decimal(rung["price"])
                            if hit and not rung["done"]:
                                # Journal before later guards; quantity capped to remaining exposure.
                                await self.broker.close_position(p.id, "Partial TP", min(p.qty, decimal(rung["quantity"])))
                                rung["done"] = True
                                self.broker.persist()
                    if isinstance(self.broker, LiveBroker):
                        # Verify SL still exists on exchange. Never trust a TPSL FILLED message as full close.
                        orders = await self.client.get_pending_tp_sl_order(positionId=p.id, limit=100)
                        stop_exists = any(o.get("slPrice") and o.get("slStopType") == "MARK_PRICE" and decimal(o["slPrice"]) > 0 and
                                (not o.get("slQty") or decimal(o["slQty"]) >= p.qty) for o in orders)
                        if not stop_exists:
                            await self.close_managed(p, "Native stop missing or child trigger pending; fail closed")
                            await self.trip("Position has no verified native stop; emergency close attempted")
            # Detect exchange-native closures so daily loss checks persist across restarts.
            if isinstance(self.broker, LiveBroker):
                ids = {p.id for p in positions}
                for pid in list(self.broker.managed):
                    if pid not in ids:
                        meta = self.broker.managed[pid]
                        intent = self.broker.intents.get(meta.get("client_id"), {})
                        await self.broker.record_history(pid, intent.get("symbol", ""))
                        self.broker.managed.pop(pid, None)
                        if intent:
                            intent["state"] = "confirmed_closed"
                        self.broker.persist()
            if account.daily_realized <= -(account.day_start_equity or account.equity) * decimal(self.config.max_daily_loss_pct) / 100:
                if self.circuit != "Daily loss limit reached":
                    await self.trip("Daily loss limit reached")
            self.last_guard = time.time()

    async def manage_once(self) -> None:
        async with self.execution_lock:
            if time.monotonic() - self.market.updated > self.config.max_market_data_age_sec:
                return  # Never move a stop using stale prices.
            account = await self.refresh_portfolio()
            for p in account.positions:
                if not p.managed or p.symbol not in self.market.rules or p.symbol not in self.market.tickers:
                    continue
                signal = self.signals.get(p.symbol)
                fresh = signal is not None and int(time.time() * 1000) - signal.timestamp_ms <= self.config.max_market_data_age_sec * 1000
                if self.config.reversal_enabled and fresh and signal.direction not in {p.side, "NEUTRAL"}:
                    await self.close_managed(p, "Confirmed opposing multi-timeframe consensus; reversal entry only on later fresh scan/risk checks")
                    continue
                current_atr = decimal(signal.atr) if fresh and signal.atr > 0 else None
                try:
                    candidate = managed_stop(p, self.config, current_atr, self.market.rules[p.symbol])
                except RiskRejected:
                    await self.close_managed(p, "Stop/liquidation safety buffer breached")
                    continue
                if candidate is not None and candidate != p.stop_loss:
                    if self.mode == "live" and not self.can_mutate():
                        continue
                    try:
                        await self.broker.set_stop(p, candidate)
                    except (AmbiguousMutation, ProtectionFailure) as exc:
                        await self.trip(str(exc))
                        await self.close_managed(p, "Stop management failure")
            if isinstance(self.broker, PaperBroker) and time.monotonic() - self.last_funding_check > 60:
                for p in await self.broker.positions():
                    try:
                        history = await self.client.get_funding_rate_history(symbol=p.symbol, starTime=p.raw["opened_at"],
                                       endTime=int(time.time() * 1000), limit=100)
                        for row in history:
                            await self.broker.apply_funding(p.symbol, decimal(row["fundingRate"]),
                                                           decimal(row["markPrice"]), int(row["fundingTime"]))
                    except (ExchangeError, ValueError, KeyError):
                        self.last_error = "Paper funding history unavailable; no funding invented. starTime is the documented field; confirm with Bitunix if rejected."
                self.last_funding_check = time.monotonic()

    async def report_once(self) -> None:
        if self.report_on and self.reporter:
            await self.reporter(self.report())

    def report(self) -> dict:
        return {"mode": self.mode, "timestamp": datetime.now(UTC).isoformat(),
                "signals": [s.public() for s in self.signals.values()],
                "prices": {s: {k: row[k] for k in ("lastPrice", "markPrice") if k in row} for s, row in self.market.tickers.items()
                           if s in self.signals or s in {p.symbol for p in self.cached_positions}},
                "positions": [p.public() for p in self.cached_positions],
                "unrealized_pnl_usdt": str(sum((p.unrealized for p in self.cached_positions), D(0))),
                "daily_realized_conservative_usdt": str(self.cached_account.daily_realized) if self.cached_account else None,
                "market_data_age_sec": round(time.monotonic() - self.market.updated, 1) if self.market.updated else None,
                "confidence_is_heuristic_not_probability": True}

    def status(self) -> dict:
        return {"mode": self.mode, "engine": self.enabled, "scanner": self.scan_on, "autotrade": self.autotrade,
                "reports": self.report_on, "live_environment_gate": self.settings.live_trading_enabled,
                "live_session_authorized": self.live_authorized, "authorized_profile_matches": self.authorized_profile == self.profile(),
                "circuit": self.circuit, "last_error": self.last_error, "last_scan": self.last_scan,
                "scan_duration_sec": self.scan_duration_sec, "scan_progress": self.scan_progress, "last_guard": self.last_guard,
                "public_ws": self.public_ws.status(), "private_ws": self.private_ws.status(),
                "unresolved_intents": self.broker.unresolved() if isinstance(self.broker, LiveBroker) else [],
                "settings": self.config.model_dump(), **self.report()}

    async def _loop(self, name: str, fn: Callable[[], Awaitable[None]], interval_field: str) -> None:
        while not self.stop.is_set():
            start = time.monotonic()
            try:
                if name in {"guard", "manage"}:
                    if self.mode == "paper" and not self.broker.open_positions:
                        pass
                    elif self.mode == "live" and not self.settings.bitunix_api_key.get_secret_value():
                        pass
                    else:
                        await fn()
                else:
                    await fn()
            except asyncio.CancelledError:
                raise
            except (AmbiguousMutation, ProtectionFailure) as exc:
                await self.trip(str(exc))
            except Exception as exc:
                self.last_error = str(exc) if isinstance(exc, (ExchangeError, RiskRejected)) else type(exc).__name__
                self.store.event("engine_error", {"loop": name, "error": type(exc).__name__})
                if name in {"guard", "manage"}:
                    self.autotrade = False  # Loss of protective monitoring blocks new entries.
            delay = max(0.1, getattr(self.config, interval_field) - (time.monotonic() - start))
            try:
                await asyncio.wait_for(self.stop.wait(), delay)
            except TimeoutError:
                pass

    async def _ws_event(self, data: dict) -> None:
        self.ws_state.apply(data)
        # REST still provides missing liquidation/entry fields. No lossy WS portfolio reconstruction.

    async def _reconcile_loop(self) -> None:
        while not self.stop.is_set():
            try:
                await asyncio.wait_for(self.ws_state.dirty.wait(), 30)
                self.ws_state.dirty.clear()
                if self.mode == "live" and self.settings.bitunix_api_key.get_secret_value():
                    await self.guard_once()
            except TimeoutError:
                pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = type(exc).__name__
                self.autotrade = False

    async def start(self) -> None:
        if self.tasks:
            raise ValueError("Engine already started")
        for name, fn, interval in (
            ("scan", self.scan_once, "scan_interval_sec"), ("guard", self.guard_once, "guard_interval_sec"),
            ("manage", self.manage_once, "management_interval_sec"), ("report", self.report_once, "report_interval_sec"),
        ):
            self.tasks.append(asyncio.create_task(self._loop(name, fn, interval), name="trader:" + name))
        self.tasks.append(asyncio.create_task(self.public_ws.run(self._ws_event, self.stop, self.ws_state.reconnect)))
        if self.mode == "live" and self.settings.bitunix_api_key.get_secret_value():
            # Private channels are automatically pushed after login per TPSL docs; no invented subscribe requirement.
            self.tasks.append(asyncio.create_task(self.private_ws.run(self._ws_event, self.stop, self.ws_state.reconnect)))
            self.tasks.append(asyncio.create_task(self._reconcile_loop()))

    async def shutdown(self) -> None:
        self.stop_entries(True)
        self.stop.set()
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self.tasks.clear()
        self.live_authorized = self.one_shot_mutation = False
        await self.client.close()
        if self.owns_store:
            self.store.close()
