import math

import numpy as np
import pytest

from jrock.trader.indicators import atr, ema, ichimoku, macd, rsi
from jrock.trader.market import aggregate_3m, closed_candles
from jrock.trader.models import Candle, D, PairRules, Position, Signal, TradeConfig, parse_ladder
from jrock.trader.risk import (
    AccountSnapshot,
    RiskRejected,
    create_plan,
    liquidation_safe_stop,
    managed_stop,
    order_units,
)
from jrock.trader.strategies import STRATEGY_NAMES, combine, evaluate


def candles(n=150, up=True):
    return [Candle(i * 60_000, 100 + i * (0.1 if up else -0.1), 101 + i * (0.1 if up else -0.1),
                   99 + i * (0.1 if up else -0.1), 100.5 + i * (0.1 if up else -0.1), 100 + i) for i in range(n)]


@pytest.fixture
def rules():
    return PairRules("BTCUSDT", 4, 2, D("0.0001"), D("100"), 1, 125, "OPEN", True, "USDT")


def test_all_ten_strategies_and_insufficient_data_abstain():
    votes = evaluate(candles(), 0.0001)
    assert {v.strategy for v in votes} == set(STRATEGY_NAMES)
    assert all(math.isfinite(v.confidence) and 0 <= v.confidence <= 95 for v in votes)
    assert all(v.direction == "NEUTRAL" for v in evaluate(candles(20), None))
    assert next(v for v in evaluate(candles(), None) if v.strategy == "funding_rate").direction == "NEUTRAL"


def test_flat_data_no_division_by_zero():
    flat = [Candle(i * 60_000, 100, 100, 100, 100, 0) for i in range(150)]
    assert all(v.direction == "NEUTRAL" for v in evaluate(flat, 0))
    assert rsi(np.ones(50) * 100)[-1] == 50


def test_indicator_reference_values_and_no_future_cloud():
    values = np.arange(1, 101, dtype=float)
    assert ema(values, 9)[8] == 5
    assert rsi(values)[-1] == 100
    assert atr(values + 1, values - 1, values)[-1] == pytest.approx(2)
    line, signal, hist = macd(values)
    assert hist[-1] == pytest.approx(line[-1] - signal[-1])
    _, _, a, b = ichimoku(values + 1, values - 1)
    assert np.isnan(b[76]) and np.isfinite(b[77])
    _, _, a2, b2 = ichimoku(np.r_[values + 1, 9999], np.r_[values - 1, 1])
    assert a2[-2] == a[-1] and b2[-2] == b[-1]


def test_multitimeframe_thresholds_reject_missing_or_disagreement():
    config = TradeConfig(min_confidence=60)
    partial = combine("BTCUSDT", {"1m": candles()}, None, config)
    assert partial.direction == "NEUTRAL"
    frames = {tf: candles() for tf in config.timeframes}
    signal = combine("BTCUSDT", frames, None, config)
    assert signal.timestamp_ms > 0
    assert signal.confidence <= 95


def test_3m_closed_resampling_requires_complete_groups():
    values = candles(6)
    aggregated = aggregate_3m(values, now_ms=360_000)
    assert len(aggregated) == 2
    assert aggregated[0].open == values[0].open
    assert aggregated[0].close == values[2].close
    assert aggregated[0].volume == sum(v.volume for v in values[:3])
    assert len(aggregate_3m(values[:5], now_ms=360_000)) == 1
    assert not aggregate_3m(values[:3], now_ms=179_999)
    rows = [{"time": 0, "open": "100", "high": "102", "low": "99", "close": "101", "baseVol": "10"}]
    assert not closed_candles(rows, 60_000, 59_999)
    assert len(closed_candles(rows, 60_000, 60_000)) == 1


def test_order_unit_examples_and_fee_aware_cost(rules):
    assert order_units("NOMINAL", D(1000), D(10000), 10, rules)["qty"] == D("0.1")
    assert order_units("COST", D(1000), D(10000), 10, rules)["qty"] == D(1)
    assert order_units("QUANTITY", D(1), D(10000), 10, rules)["cost_usdt"] == D(1000)
    cost = order_units("COST", D(1000), D(10000), 10, rules, D("0.001"))
    assert cost["cost_usdt"] <= 1000 and cost["qty"] < 1
    with pytest.raises(ValueError):
        order_units("NOMINAL", D("0.1"), D(10000), 10, rules)


def test_risk_sizing_and_all_four_tpsl_modes(rules):
    signal = Signal("BTCUSDT", "LONG", 90, 5, {}, 1, 100, 1)
    account = AccountSnapshot(D(1000), D(1000), [])
    tiers = [{"startValue": "0", "endValue": "50000", "leverage": 125}]
    for mode in ("POSITION", "PARTIAL", "TRAILING", "ACCOUNT"):
        cfg = TradeConfig(tp_mode=mode, tpsl_method="FIXED_R")
        plan = create_plan(signal, account, rules, tiers, cfg, [], D(100))
        assert plan.risk_usdt <= D(5)
        assert plan.margin_usdt <= D(100)
        assert plan.stop_loss < plan.entry < plan.take_profit
        if mode == "PARTIAL":
            assert sum(r.quantity for r in plan.ladder) <= plan.qty
            assert plan.ladder[0].share_pct == 30
    bad = AccountSnapshot(D(1000), D(1000), [], D(-40), D(1000))
    with pytest.raises(RiskRejected, match="Daily loss"):
        create_plan(signal, bad, rules, tiers, TradeConfig(), [], D(100))
    with pytest.raises(RiskRejected, match="tiered"):
        create_plan(signal, account, rules, [{"startValue": "0", "endValue": "10", "leverage": 1}], TradeConfig(), [], D(100))


def test_ladders_and_config_bounds():
    for invalid in ("101@1", "60@1,50@2", "30@2,40@1", "0@1", "30@0", "NaN@1"):
        with pytest.raises(ValueError):
            parse_ladder(invalid)
    for kwargs in ({"scan_interval_sec": 1}, {"min_confidence": 101}, {"symbols": []}, {"timeframes": ["1m"]}, {"trailing_callback": float("nan")}):
        with pytest.raises(ValueError):
            TradeConfig(**kwargs)


def test_liquidation_stop_and_never_widen(rules):
    assert liquidation_safe_stop(D(90), "LONG", D(95), 2, D(100)) == D("96.9")
    assert liquidation_safe_stop(D(110), "SHORT", D(105), 2, D(100)) == D("102.9")
    assert liquidation_safe_stop(D(90), "LONG", D(0), 2, D(100)) == 90
    with pytest.raises(RiskRejected):
        liquidation_safe_stop(D(90), "LONG", D(99), 2, D(100))
    p = Position("1", "BTCUSDT", "LONG", D(1), D(100), D(110), 10, D(10), D(10), None,
                 stop_loss=D(98), best_price=D(110))
    cfg = TradeConfig(trailing_method="RATIO", trailing_callback=1)
    stop = managed_stop(p, cfg, D(1), rules)
    assert stop > D(100)
    p.stop_loss, p.mark = stop, D("109.5")
    stop2 = managed_stop(p, cfg, D(4), rules)
    assert stop2 >= stop
