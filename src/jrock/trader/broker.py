from __future__ import annotations

import asyncio
import time
import uuid
from decimal import Decimal

from jrock.exchange.client import AmbiguousMutation, BitunixClient, ExchangeError
from jrock.storage import Store
from jrock.trader.models import D, PairRules, Position, TradeConfig, TradePlan, decimal, fmt
from jrock.trader.risk import AccountSnapshot, RiskRejected, liquidation_safe_stop, make_ladder


class ProtectionFailure(RuntimeError):
    pass


def position_from_state(row: dict) -> Position:
    decimals = {"qty", "entry", "mark", "margin", "unrealized", "liquidation_price", "stop_loss",
                "take_profit", "best_price", "initial_qty", "initial_risk"}
    return Position(**{key: decimal(value) if key in decimals and value is not None else value
                       for key, value in row.items()})


class PaperBroker:
    """Paper USDT linear futures ledger. No credential and no exchange mutation path.

    Fill/fee/slippage assumptions are simulated; funding applied only from verified history.
    No fake liquidation price is synthesized. Stops are local and sampled, not guaranteed fills.
    """

    def __init__(self, store: Store, config: TradeConfig):
        self.store, self.config = store, config
        state = store.get("paper:state", {"cash": str(config.paper_balance_usdt), "positions": []})
        self.cash = decimal(state["cash"])
        self.open_positions = {p["id"]: position_from_state(p) for p in state["positions"]}
        self.lock = asyncio.Lock()

    def persist(self) -> None:
        self.store.set("paper:state", {"cash": fmt(self.cash), "positions": [p.public() for p in self.open_positions.values()]})

    def mark(self, tickers: dict[str, dict]) -> None:
        for p in self.open_positions.values():
            row = tickers.get(p.symbol)
            if not row or "markPrice" not in row:
                continue
            p.mark = decimal(row["markPrice"])
            if p.mark <= 0:
                raise ValueError("Nonpositive mark price")
            p.unrealized = (p.mark - p.entry) * p.qty * (1 if p.side == "LONG" else -1)
            p.best_price = max(p.best_price or p.entry, p.mark) if p.side == "LONG" else min(p.best_price or p.entry, p.mark)
        self.persist()

    async def positions(self) -> list[Position]:
        return list(self.open_positions.values())

    async def account(self) -> AccountSnapshot:
        positions = await self.positions()
        equity = self.cash + sum((p.unrealized for p in positions), D(0))
        available = self.cash - sum((p.margin for p in positions), D(0))
        return AccountSnapshot(equity, available, positions)

    async def open(self, plan: TradePlan, rules: PairRules) -> Position:
        async with self.lock:
            if any(p.symbol == plan.symbol for p in self.open_positions.values()):
                raise RiskRejected("Duplicate paper position")
            direction = 1 if plan.side == "LONG" else -1
            entry = plan.entry * (1 + direction * decimal(self.config.paper_slippage_bps) / 10000)
            fee, margin = entry * plan.qty * decimal(self.config.taker_fee_rate), entry * plan.qty / plan.leverage
            available = (await self.account()).available
            if margin + fee > available:
                raise RiskRejected("Insufficient paper available margin")
            if (plan.side == "LONG" and plan.stop_loss >= entry) or (plan.side == "SHORT" and plan.stop_loss <= entry):
                raise RiskRejected("Invalid stop relative to simulated fill")
            p = Position(uuid.uuid4().hex[:16], plan.symbol, plan.side, plan.qty, entry, plan.entry,
                         plan.leverage, margin, (plan.entry - entry) * plan.qty * direction, None,
                         plan.stop_loss, plan.take_profit if plan.mode == "POSITION" else None,
                         entry, plan.qty, abs(entry - plan.stop_loss), raw={"mode": plan.mode,
                         "opened_at": int(time.time() * 1000), "funding_applied": [],
                         "ladder": [{"quantity": fmt(r.quantity), "price": fmt(r.price), "done": False} for r in plan.ladder]})
            self.cash -= fee
            self.open_positions[p.id] = p
            self.store.event("paper_open", {"id": p.id, "symbol": p.symbol, "side": p.side,
                    "entry": entry, "qty": plan.qty, "fee": fee, "net_pnl": -fee})
            self.persist()
            return p

    async def close_position(self, pid: str, reason: str, quantity: Decimal | None = None) -> dict:
        async with self.lock:
            p = self.open_positions.get(pid)
            if not p:
                raise ValueError("Paper position not found")
            qty = p.qty if quantity is None else quantity
            if qty <= 0 or qty > p.qty:
                raise ValueError("Close quantity must be positive and <= current position")
            direction = 1 if p.side == "LONG" else -1
            fill = p.mark * (1 - direction * decimal(self.config.paper_slippage_bps) / 10000)
            gross = (fill - p.entry) * qty * direction
            fee = fill * qty * decimal(self.config.taker_fee_rate)
            self.cash += gross - fee
            old_qty = p.qty
            p.qty -= qty
            p.margin *= p.qty / old_qty
            p.unrealized = (p.mark - p.entry) * p.qty * direction
            event = {"id": pid, "symbol": p.symbol, "side": p.side, "qty": qty, "entry": p.entry,
                     "exit": fill, "realizedPNL": gross, "fee": fee, "net_pnl": gross - fee,
                     "reason": reason, "remaining_qty": p.qty, "mode": "paper"}
            self.store.event("paper_close", event)
            if p.qty == 0:
                del self.open_positions[pid]
            self.persist()
            return event

    async def set_stop(self, position: Position, stop: Decimal) -> None:
        async with self.lock:
            p = self.open_positions.get(position.id)
            if not p:
                return
            if p.stop_loss is not None and ((p.side == "LONG" and stop < p.stop_loss) or (p.side == "SHORT" and stop > p.stop_loss)):
                raise RiskRejected("Stop widening is prohibited")
            p.stop_loss = stop
            self.persist()

    async def apply_funding(self, symbol: str, rate: Decimal, mark: Decimal, settled_at: int) -> None:
        async with self.lock:
            for p in self.open_positions.values():
                if p.symbol != symbol or settled_at <= p.raw["opened_at"] or settled_at in p.raw["funding_applied"]:
                    continue
                delta = -p.qty * mark * rate * (1 if p.side == "LONG" else -1)
                self.cash += delta
                p.raw["funding_applied"].append(settled_at)
                self.store.event("paper_funding", {"id": p.id, "symbol": symbol, "funding": delta,
                                 "settled_at": settled_at, "net_pnl": delta})
            self.persist()


class LiveBroker:
    """Live execution adapter. Intents persisted before POST; no mutation is retried blindly.

    Stop protection is verified before an open is declared successful. If protection fails,
    attempt a reducing emergency close and trip the engine's circuit breaker.
    Exchange positions, mark prices and liquidation prices are authoritative.
    """

    def __init__(self, store: Store, config: TradeConfig, client: BitunixClient):
        self.store, self.config, self.client = store, config, client
        self.managed: dict = store.get("live:managed", {})
        self.intents: dict = store.get("live:intents", {})
        self.marks: dict = {}
        self.last_account: dict = {}
        self.entry_guard = lambda: False

    def persist(self) -> None:
        self.store.set("live:managed", self.managed)
        self.store.set("live:intents", self.intents)

    def mark(self, tickers: dict[str, dict]) -> None:
        self.marks = tickers

    async def positions(self) -> list[Position]:
        rows = await self.client.get_pending_positions(includeSubAccounts=False)
        if not isinstance(rows, list):
            raise ExchangeError("protocol", "Positions response must be an array")
        result = []
        for row in rows:
            qty = decimal(row["qty"])
            if qty <= 0:
                continue
            pid, symbol = str(row["positionId"]), row["symbol"]
            meta = self.managed.get(pid, {})
            mark = decimal(self.marks.get(symbol, {}).get("markPrice", row["avgOpenPrice"]))
            entry, liq = decimal(row["avgOpenPrice"]), decimal(row["liqPrice"])
            p = Position(pid, symbol, row["side"], qty, entry, mark, int(row["leverage"]),
                         decimal(row["margin"]), decimal(row["unrealizedPNL"]), liq if liq > 0 else None,
                         decimal(meta["stop_loss"]) if meta.get("stop_loss") else None,
                         decimal(meta["take_profit"]) if meta.get("take_profit") else None,
                         decimal(meta.get("best_price", entry)), decimal(meta.get("initial_qty", qty)),
                         decimal(meta["initial_risk"]) if meta.get("initial_risk") else None,
                         managed=bool(meta), raw=row)
            result.append(p)
        return result

    async def account(self) -> AccountSnapshot:
        result = await self.client.get_single_account(marginCoin="USDT")
        row = result[0] if isinstance(result, list) and result else result
        if not isinstance(row, dict):
            raise ExchangeError("protocol", "Account data missing")
        self.last_account = row
        unrealized = decimal(row["crossUnrealizedPNL"]) + decimal(row["isolationUnrealizedPNL"])
        # available+frozen+margin is account balance; unrealized contributes to equity.
        equity = decimal(row["available"]) + decimal(row["frozen"]) + decimal(row["margin"]) + unrealized
        # Conservative availability: don't fund new exposure with unverified cross PnL.
        return AccountSnapshot(equity, decimal(row["available"]), await self.positions())

    async def configure_symbol(self, symbol: str) -> str:
        account = await self.client.get_single_account(marginCoin="USDT")
        account = account[0] if isinstance(account, list) and account else account
        mode = account["positionMode"]
        if mode not in {"ONE_WAY", "HEDGE"}:
            raise ExchangeError("mode", "Unknown position mode; no order sent")
        current = await self.client.get_leverage_and_margin_mode(symbol=symbol, marginCoin="USDT")
        if current["marginMode"] != "ISOLATION" or int(current["leverage"]) != self.config.leverage:
            positions = await self.client.get_pending_positions(symbol=symbol, includeSubAccounts=False)
            pending = await self.client.get_pending_orders(symbol=symbol, limit=100)
            if positions or (pending.get("orderList") if isinstance(pending, dict) else pending):
                raise RiskRejected("Symbol has positions/orders; do not change its leverage/margin mode")
            if current["marginMode"] != "ISOLATION":
                await self.client.change_margin_mode(symbol=symbol, marginCoin="USDT", marginMode="ISOLATION")
            if int(current["leverage"]) != self.config.leverage:
                await self.client.change_leverage(symbol=symbol, marginCoin="USDT", leverage=self.config.leverage)
            verified = await self.client.get_leverage_and_margin_mode(symbol=symbol, marginCoin="USDT")
            if verified["marginMode"] != "ISOLATION" or int(verified["leverage"]) != self.config.leverage:
                raise ProtectionFailure("Leverage/margin change not confirmed; no order placed")
        return mode

    async def reconcile_order(self, client_id: str, deadline_sec: float = 12) -> dict | None:
        deadline = time.monotonic() + deadline_sec
        while time.monotonic() < deadline:
            try:
                order = await self.client.get_order_detail(clientId=client_id)
                status = order.get("status") or order.get("orderStatus")
                if status in {"FILLED", "PART_FILLED", "CANCELED", "PART_FILLED_CANCELED", "EXPIRED"}:
                    return order
            except ExchangeError as exc:
                if exc.code != 20007:
                    raise
            await asyncio.sleep(0.5)
        return None

    async def open(self, plan: TradePlan, rules: PairRules) -> Position:
        if any(p.symbol == plan.symbol for p in await self.positions()):
            raise RiskRejected("Position already exists in symbol")
        mode = await self.configure_symbol(plan.symbol)
        pending = await self.client.get_pending_orders(symbol=plan.symbol, limit=100)
        if (pending.get("orderList") if isinstance(pending, dict) else pending):
            raise RiskRejected("Pending orders in symbol; no additional exposure allowed")
        client_id = "jr-" + uuid.uuid4().hex[:24]
        payload = {"symbol": plan.symbol, "qty": fmt(plan.qty), "side": "BUY" if plan.side == "LONG" else "SELL",
                   "tradeSide": "OPEN", "orderType": "MARKET", "clientId": client_id,
                   "slPrice": fmt(plan.stop_loss), "slStopType": "MARK_PRICE", "slOrderType": "MARKET"}
        if plan.mode == "POSITION":
            payload.update(tpPrice=fmt(plan.take_profit), tpStopType="MARK_PRICE", tpOrderType="MARKET")
        self.intents[client_id] = {"state": "submitted", "symbol": plan.symbol, "side": plan.side,
                                  "plan": plan.public(), "created": time.time(), "position_mode": mode}
        self.persist()  # Before any financial mutation.
        if not self.entry_guard():
            self.intents[client_id]["state"] = "rejected"
            self.persist()
            raise RiskRejected("Entry authorization revoked before POST")
        try:
            await self.client.place_order(**payload)
        except AmbiguousMutation:
            # Same ID is queried, NEVER submitted again.
            pass
        except ExchangeError:
            self.intents[client_id]["state"] = "rejected"
            self.persist()
            raise
        order = await self.reconcile_order(client_id)
        if not order:
            raise AmbiguousMutation("reconciliation", f"Order {client_id} unconfirmed. Intent saved; no resubmission.")
        if (order.get("status") or order.get("orderStatus")) == "PART_FILLED":
            # Cancel remaining opening quantity once, then reconcile; never assume cancellation succeeded.
            await self.client.cancel_orders(symbol=plan.symbol, orderList=[{"clientId": client_id}])
            final = await self.reconcile_order(client_id)
            if not final or (final.get("status") or final.get("orderStatus")) == "PART_FILLED":
                raise AmbiguousMutation("partial", "Partial-fill remainder cancellation not confirmed")
        matches = [p for p in await self.positions() if p.symbol == plan.symbol and p.side == plan.side]
        if len(matches) != 1:
            self.intents[client_id]["state"] = "needs_reconciliation"
            self.persist()
            raise AmbiguousMutation("position", "Filled order has no unique confirmed position; manual reconciliation needed")
        p = matches[0]
        self.managed[p.id] = {"client_id": client_id, "stop_loss": fmt(plan.stop_loss),
                "take_profit": fmt(plan.take_profit) if plan.mode == "POSITION" else None,
                "best_price": fmt(p.entry), "initial_qty": fmt(p.qty), "initial_risk": fmt(abs(p.entry - plan.stop_loss)),
                "mode": plan.mode, "opened_at": int(time.time() * 1000)}
        self.intents[client_id]["position_id"] = p.id
        self.persist()
        try:
            if p.qty > plan.qty or p.margin > plan.margin_usdt * D("1.05"):
                raise ProtectionFailure("Filled exposure/margin exceeds planned bounds")
            safe_stop = liquidation_safe_stop(plan.stop_loss, p.side, p.liquidation_price,
                                               self.config.liq_sl_distance_pct, p.mark)
            p.stop_loss, p.managed = safe_stop, True
            await self.ensure_protection(p, safe_stop, plan.take_profit if plan.mode == "POSITION" else None)
            if plan.mode == "PARTIAL":
                # Real fill quantity/entry can differ from estimates; rebuild/validate ladder after fill.
                for rung in make_ladder(self.config, p.side, p.entry, safe_stop, p.qty, rules):
                    await self.client.place_tp_sl_order(symbol=p.symbol, positionId=p.id, tpPrice=fmt(rung.price),
                            tpStopType="MARK_PRICE", tpOrderType="MARKET", tpQty=fmt(rung.quantity))
                rows = await self.client.get_pending_tp_sl_order(positionId=p.id, limit=100)
                for rung in make_ladder(self.config, p.side, p.entry, safe_stop, p.qty, rules):
                    if not any(decimal(row.get("tpPrice", 0)) == rung.price and decimal(row.get("tpQty", 0)) == rung.quantity for row in rows):
                        raise ProtectionFailure("Partial TP ladder not confirmed by exchange")
        except (ValueError, RuntimeError) as exc:
            self.intents[client_id]["state"] = "protection_failed"
            self.persist()
            try:
                await self.close_position(p.id, "Emergency: stop/ladder protection failure")
            except (ValueError, RuntimeError):
                self.store.event("critical", {"position_id": p.id, "reason": "Emergency close unconfirmed. Inspect exchange immediately."})
            raise ProtectionFailure("Protection verification failed; emergency close attempted. Inspect exchange and reconciliation log.") from exc
        self.intents[client_id]["state"] = "filled_protected"
        self.persist()
        self.store.event("live_open", {"id": p.id, "symbol": p.symbol, "client_id": client_id, "qty": p.qty,
                          "entry": p.entry, "protected": True})
        return next(position for position in await self.positions() if position.id == p.id)

    async def ensure_protection(self, p: Position, stop: Decimal, tp: Decimal | None = None) -> None:
        rows = await self.client.get_pending_tp_sl_order(positionId=p.id, limit=100)
        existing = next((row for row in rows if row.get("slPrice") and
                        (not row.get("slQty") or decimal(row["slQty"]) >= p.qty)), None)
        if existing:
            meta = self.managed[p.id]
            meta["stop_order_id"] = str(existing.get("id", existing.get("orderId", "")))
            meta["stop_kind"] = "partial" if existing.get("slQty") else "position"
            self.persist()
            if decimal(existing["slPrice"]) != stop or existing.get("slStopType") != "MARK_PRICE":
                await self.set_stop(p, stop)
        else:
            payload = {"symbol": p.symbol, "positionId": p.id, "slPrice": fmt(stop), "slStopType": "MARK_PRICE"}
            if tp:
                payload.update(tpPrice=fmt(tp), tpStopType="MARK_PRICE")
            response = await self.client.place_position_tp_sl_order(**payload)
            self.managed[p.id].update(stop_order_id=response["orderId"], stop_kind="position")
            self.persist()
        confirmed = await self.client.get_pending_tp_sl_order(positionId=p.id, limit=100)
        valid = any(row.get("slPrice") and row.get("slStopType") == "MARK_PRICE" and decimal(row["slPrice"]) == stop and
                    (not row.get("slQty") or decimal(row["slQty"]) >= p.qty) for row in confirmed)
        if not valid:
            raise ProtectionFailure("Exchange stop not confirmed; cannot declare position protected")
        self.managed[p.id]["stop_loss"] = fmt(stop)
        self.persist()

    async def set_stop(self, p: Position, stop: Decimal) -> None:
        meta = self.managed.get(p.id)
        if not meta:
            raise RiskRejected("Unmanaged position: explicit adoption required")
        old = decimal(meta["stop_loss"])
        if (p.side == "LONG" and stop < old) or (p.side == "SHORT" and stop > old):
            raise RiskRejected("Stop widening is prohibited")
        if meta.get("stop_kind") == "partial":
            await self.client.modify_tp_sl_order(orderId=meta["stop_order_id"], slPrice=fmt(stop),
                    slStopType="MARK_PRICE", slOrderType="MARKET", slQty=fmt(p.qty))
        else:
            payload = {"symbol": p.symbol, "positionId": p.id, "slPrice": fmt(stop), "slStopType": "MARK_PRICE"}
            if meta.get("take_profit"):
                payload.update(tpPrice=meta["take_profit"], tpStopType="MARK_PRICE")
            await self.client.modify_position_tp_sl_order(**payload)
        confirmed = await self.client.get_pending_tp_sl_order(positionId=p.id, limit=100)
        if not any(row.get("slPrice") and row.get("slStopType") == "MARK_PRICE" and decimal(row["slPrice"]) == stop and
                   (not row.get("slQty") or decimal(row["slQty"]) >= p.qty) for row in confirmed):
            raise ProtectionFailure("Stop modification not confirmed; old native stop is not canceled by this engine")
        meta["stop_loss"], meta["best_price"] = fmt(stop), fmt(p.best_price or p.mark)
        self.persist()

    async def close_position(self, pid: str, reason: str, quantity: Decimal | None = None) -> dict:
        positions = await self.positions()
        p = next((p for p in positions if p.id == pid), None)
        if not p:
            return {"id": pid, "confirmed_closed": True, "already_absent": True}
        if quantity is not None and (quantity <= 0 or quantity > p.qty):
            raise ValueError("Close quantity must be positive and <= current position")
        if quantity is None or quantity == p.qty:
            await self.client.flash_close_position(positionId=pid)
        else:
            hedge = p.raw["positionMode"] == "HEDGE"
            side = ("BUY" if p.side == "LONG" else "SELL") if hedge else ("SELL" if p.side == "LONG" else "BUY")
            await self.client.place_order(symbol=p.symbol, positionId=pid, side=side, tradeSide="CLOSE", orderType="MARKET",
                                         qty=fmt(quantity), reduceOnly=True, clientId="jr-close-" + uuid.uuid4().hex[:20])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            current = next((pos for pos in await self.positions() if pos.id == pid), None)
            if current is None or (quantity is not None and current.qty <= p.qty - quantity):
                result = {"id": pid, "symbol": p.symbol, "confirmed_closed": current is None,
                          "remaining_qty": current.qty if current else D(0), "reason": reason}
                self.store.event("live_close", result)
                if current is None:
                    self.managed.pop(pid, None)
                    self.persist()
                    await self.record_history(pid, p.symbol)
                return result
            await asyncio.sleep(0.5)
        raise AmbiguousMutation("close", "Close not confirmed by positions; no repeated close submitted")

    async def record_history(self, pid: str, symbol: str) -> None:
        data = await self.client.get_history_positions(positionId=pid, symbol=symbol, limit=100)
        rows = data.get("positionList", []) if isinstance(data, dict) else data
        for row in rows:
            if str(row.get("positionId")) == pid:
                self.store.event("live_history", {"id": pid, "raw": row,
                    # Conservative loss budget; no assumed funding sign is credited.
                    "conservative_net_pnl": decimal(row["realizedPNL"]) - abs(decimal(row["fee"])) - abs(decimal(row["funding"]))})
                return

    def unresolved(self) -> list[dict]:
        return [{"client_id": cid, **intent} for cid, intent in self.intents.items()
                if intent["state"] not in {"rejected", "filled_protected", "confirmed_closed"}]

    async def reconcile_intents(self) -> list[dict]:
        # Read-only reconciliation after restart/ambiguous POST; never auto-resubmits or auto-arms.
        for intent in self.unresolved():
            cid = intent["client_id"]
            order = await self.client.get_order_detail(clientId=cid)
            matches = [p for p in await self.positions() if p.symbol == intent["symbol"] and p.side == intent["side"]]
            if not matches and (order.get("status") in {"CANCELED", "EXPIRED", "FILLED", "PART_FILLED_CANCELED"}):
                self.intents[cid]["state"] = "confirmed_closed"
            else:
                self.intents[cid]["state"] = "needs_reconciliation"
                self.intents[cid]["order"] = order
            self.persist()
        return self.unresolved()
