from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from jrock.trader.models import (
    Candle,
    D,
    ExitRung,
    PairRules,
    Position,
    Signal,
    TradeConfig,
    TradePlan,
    decimal,
    parse_ladder,
    quantize,
)

ZERO = D(0)


class RiskRejected(RuntimeError):
    pass


@dataclass
class AccountSnapshot:
    equity: Decimal
    available: Decimal
    positions: list[Position]
    daily_realized: Decimal = D(0)
    day_start_equity: Decimal | None = None


def order_units(unit: str, amount: Decimal, price: Decimal, leverage: int, rules: PairRules,
                fee_rate: Decimal = ZERO) -> dict:
    if amount <= 0 or price <= 0 or leverage < 1 or fee_rate < 0:
        raise ValueError("Amount/price/leverage must be positive; fees nonnegative")
    if not rules.min_leverage <= leverage <= rules.max_leverage:
        raise ValueError("Leverage outside live symbol limits")
    unit = unit.upper()
    if unit == "QUANTITY":
        quantity = amount
    elif unit == "NOMINAL":
        quantity = amount / price
    elif unit == "COST":
        quantity = amount / (price / leverage + price * fee_rate)
    else:
        raise ValueError("Order unit must be QUANTITY, NOMINAL or COST")
    qty = rules.qty(quantity)
    nominal = qty * price
    margin, fee = nominal / leverage, nominal * fee_rate
    return {"qty": qty, "notional_usdt": nominal, "initial_margin_usdt": margin,
            "opening_fee_usdt": fee, "cost_usdt": margin + fee}


def liquidation_safe_stop(stop: Decimal, side: str, liquidation_price: Decimal | None,
                          distance_pct: float, current_mark: Decimal) -> Decimal:
    if liquidation_price is None or liquidation_price <= 0:
        result = stop
    elif side == "LONG":
        result = max(stop, liquidation_price * (1 + decimal(distance_pct) / 100))
    else:
        result = min(stop, liquidation_price * (1 - decimal(distance_pct) / 100))
    if result <= 0 or (side == "LONG" and result >= current_mark) or (side == "SHORT" and result <= current_mark):
        raise RiskRejected("Liquidation buffer/stop already breached; close instead of placing an invalid stop")
    return result


def make_ladder(config: TradeConfig, side: str, entry: Decimal, stop: Decimal,
                qty: Decimal, rules: PairRules) -> list[ExitRung]:
    risk = abs(entry - stop)
    direction = 1 if side == "LONG" else -1
    rungs = []
    for share, multiple in parse_ladder(config.partial_tp_ladder):
        rung_qty = rules.qty(qty * share / 100)
        price = quantize(entry + direction * risk * multiple, rules.quote_precision,
                         "floor" if side == "LONG" else "ceil")
        if price <= 0:
            raise RiskRejected("Invalid partial target price")
        rungs.append(ExitRung(share, multiple, rung_qty, price))
    if not rungs:
        raise RiskRejected("PARTIAL mode requires at least one ladder rung")
    # No rounded rung may increase requested share/exposure. Remainder always stays a protected runner.
    if sum(r.quantity for r in rungs) > qty:
        raise RiskRejected("Ladder quantities exceed position")
    return rungs


def create_plan(signal: Signal, account: AccountSnapshot, rules: PairRules, tiers: list[dict],
                config: TradeConfig, candles: list[Candle], entry: Decimal) -> TradePlan:
    if signal.direction not in {"LONG", "SHORT"}:
        raise RiskRejected("No actionable consensus")
    if signal.confidence < config.min_confidence or signal.agreeing < config.min_agreeing_strategies:
        raise RiskRejected("Signal below configured confidence/strategy threshold")
    if rules.status != "OPEN" or not rules.api_supported or rules.quote != "USDT":
        raise RiskRejected("Only open, API-enabled USDT futures are supported by the execution engine")
    if not rules.min_leverage <= config.leverage <= rules.max_leverage:
        raise RiskRejected("Leverage outside current pair bounds")
    if account.equity <= 0 or account.available <= 0:
        raise RiskRejected("No positive equity/available margin")
    if len(account.positions) >= config.max_positions:
        raise RiskRejected("Maximum position count reached (including unmanaged positions)")
    if any(p.symbol == signal.symbol for p in account.positions):
        raise RiskRejected("An existing position in this symbol prevents duplicate/opposing exposure")
    baseline = account.day_start_equity or account.equity
    if account.daily_realized <= -baseline * decimal(config.max_daily_loss_pct) / 100:
        raise RiskRejected("Daily loss circuit breaker reached")
    volatility = decimal(signal.atr)
    if entry <= 0 or volatility <= 0:
        raise RiskRejected("Invalid entry/ATR")
    direction = 1 if signal.direction == "LONG" else -1
    distance = volatility * decimal(config.atr_stop_multiple)
    if config.tpsl_method == "ADAPTIVE" and candles:
        structure = decimal(min(c.low for c in candles[-10:])) if direction == 1 else decimal(max(c.high for c in candles[-10:]))
        structure_distance = direction * (entry - structure) + volatility * D("0.2")
        distance = max(distance, structure_distance)
    raw_sl = entry - direction * distance
    stop = quantize(raw_sl, rules.quote_precision, "ceil" if direction == 1 else "floor")
    distance = abs(entry - stop)
    if stop <= 0 or distance <= 0 or distance / entry * 100 > decimal(config.max_stop_distance_pct):
        raise RiskRejected("Stop gap outside acceptable range")
    rr = decimal(config.fixed_r) if config.tpsl_method == "FIXED_R" else max(decimal(config.min_reward_risk), D("1.5") + decimal(signal.confidence) / 100 * 2)
    target = entry + direction * distance * rr
    if config.tpsl_method == "ADAPTIVE" and candles:
        structure = decimal(max(c.high for c in candles[-60:])) if direction == 1 else decimal(min(c.low for c in candles[-60:]))
        structure_rr = direction * (structure - entry) / distance
        if structure_rr >= decimal(config.min_reward_risk):
            target = min(target, structure) if direction == 1 else max(target, structure)
    target = quantize(target, rules.quote_precision, "floor" if direction == 1 else "ceil")
    if target <= 0 or direction * (target - entry) / distance < decimal(config.min_reward_risk):
        raise RiskRejected("Reward/risk too low after price rounding")
    # Include estimated round-trip fees and adverse execution in the sizing risk denominator.
    cost_per_unit = distance + entry * (2 * decimal(config.taker_fee_rate) + decimal(config.paper_slippage_bps) / 10000)
    risk_budget = account.equity * decimal(config.risk_per_trade_pct) / 100
    prior_risk = D(0)
    for p in account.positions:
        if p.stop_loss is None:
            raise RiskRejected("Existing position risk unknown/unprotected; reconcile before adding risk")
        prior_risk += max(D(0), (p.entry - p.stop_loss) if p.side == "LONG" else (p.stop_loss - p.entry)) * p.qty
    total_budget = account.equity * decimal(config.max_total_risk_pct) / 100
    risk_budget = min(risk_budget, total_budget - prior_risk)
    used_margin = sum((p.margin for p in account.positions), D(0))
    margin_budget = min(account.available, account.equity * decimal(config.max_margin_pct) / 100 - used_margin)
    if risk_budget <= 0 or margin_budget <= 0:
        raise RiskRejected("Portfolio risk/margin budget exhausted")
    quantity = min(risk_budget / cost_per_unit,
                   margin_budget / (entry / config.leverage + entry * decimal(config.taker_fee_rate)))
    try:
        qty = rules.qty(quantity)
    except ValueError as exc:
        raise RiskRejected(str(exc)) from exc
    notional = qty * entry
    tier = next((t for t in tiers if decimal(t["startValue"]) <= notional <= decimal(t["endValue"])), None)
    if tier is None or config.leverage > int(tier["leverage"]):
        raise RiskRejected("Position notional/leverage not supported by current tiered risk limits")
    plan = TradePlan(signal.symbol, signal.direction, entry, qty, stop, target,
                     qty * cost_per_unit, notional / config.leverage, config.leverage, signal.confidence,
                     volatility, config.tp_mode)
    if config.tp_mode == "PARTIAL":
        plan.ladder = make_ladder(config, plan.side, entry, stop, qty, rules)
    return plan


def managed_stop(position: Position, config: TradeConfig, current_atr: Decimal | None,
                 rules: PairRules) -> Decimal | None:
    """Monotonic stop tightening: never widen after break-even/trailing/liquidation adjustments."""
    if position.stop_loss is None:
        return None
    long = position.side == "LONG"
    best = max(position.best_price or position.entry, position.mark) if long else min(position.best_price or position.entry, position.mark)
    position.best_price = best
    stop = position.stop_loss
    if position.roi_pct >= decimal(config.breakeven_threshold_pct):
        fee_buffer = position.entry * decimal(config.taker_fee_rate) * 2
        breakeven = position.entry + fee_buffer if long else position.entry - fee_buffer
        stop = max(stop, breakeven) if long else min(stop, breakeven)
    if position.roi_pct >= decimal(config.trailing_trigger_roi_pct):
        if config.trailing_method == "ATR":
            if current_atr is not None and current_atr > 0:
                callback = current_atr * decimal(config.trailing_callback)
            else:
                callback = None  # Never invent ATR if data is unavailable.
        elif config.trailing_method == "RATIO":
            callback = best * decimal(config.trailing_callback) / 100
        else:
            callback = decimal(config.trailing_callback)
        # trailing_stop_pct is a price-change safety cap from entry after activation;
        # trailing_distance_pct caps callback distance from best for any trailing method.
        safety_stop = position.entry * (1 - decimal(config.trailing_stop_pct) / 100) if long else position.entry * (1 + decimal(config.trailing_stop_pct) / 100)
        stop = max(stop, safety_stop) if long else min(stop, safety_stop)
        if callback is not None:
            callback = min(callback, best * decimal(config.trailing_distance_pct) / 100)
            candidate = best - callback if long else best + callback
            stop = max(stop, candidate) if long else min(stop, candidate)
    stop = liquidation_safe_stop(stop, position.side, position.liquidation_price,
                                  config.liq_sl_distance_pct, position.mark)
    rounded = quantize(stop, rules.quote_precision, "ceil" if long else "floor")
    if (long and rounded >= position.mark) or (not long and rounded <= position.mark):
        raise RiskRejected("Rounded stop reaches current mark; close rather than submit an invalid trigger")
    return rounded
