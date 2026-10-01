import time

import httpx
import pytest

from jrock.config import Settings
from jrock.exchange.client import BitunixClient
from jrock.storage import Store
from jrock.trader.broker import PaperBroker
from jrock.trader.engine import TradingEngine
from jrock.trader.market import INTERVAL_MS
from jrock.trader.models import D, PairRules, TradeConfig, TradePlan
from jrock.trader.risk import RiskRejected, make_ladder

PAIR = {"symbol": "BTCUSDT", "base": "BTC", "quote": "USDT", "basePrecision": 4, "quotePrecision": 2,
        "minTradeVolume": "0.0001", "maxMarketOrderVolume": "100", "minLeverage": 1, "maxLeverage": 125,
        "symbolStatus": "OPEN", "isApiSupported": True}
TICKER = {"symbol": "BTCUSDT", "markPrice": "100", "lastPrice": "100", "open": "90", "quoteVol": "2000000"}
TIERS = [{"startValue": "0", "endValue": "50000", "leverage": 125, "maintenanceMarginRate": "0.004"}]


def market_handler(mutations, ticker=None):
    ticker = ticker or TICKER
    def handler(request):
        path, params = request.url.path, request.url.params
        if request.method == "POST":
            mutations.append(path)
            pytest.fail("Paper engine sent a financial mutation")
        data = None
        if path.endswith("/tickers"):
            data = [ticker]
        elif path.endswith("/trading_pairs"):
            data = [PAIR]
        elif path.endswith("/batch"):
            data = [{"symbol": "BTCUSDT", "fundingRate": "0.0001", "markPrice": "100", "nextFundingTime": str(int(time.time() * 1000) + 3600000)}]
        elif path.endswith("/get_position_tiers"):
            data = TIERS
        elif path.endswith("/depth"):
            data = {"asks": [["100.01", "10"]], "bids": [["99.99", "10"]]}
        elif path.endswith("/kline"):
            interval = INTERVAL_MS[params["interval"]]
            now = int(time.time() * 1000)
            end = min(int(params.get("endTime", now)), now)
            start = min((now // interval - 1) * interval, (end // interval) * interval)
            rows = []
            for i in range(int(params.get("limit", 121))):
                ts = start - i * interval
                # Price slope uses time, so back-pagination cannot fabricate a different price for same candle.
                age = (now // interval * interval - ts) // interval
                price = 100 - age * 0.02
                rows.append({"time": ts, "open": str(price - 0.005), "close": str(price),
                             "high": str(price + 0.006), "low": str(price - 0.006), "baseVol": "100", "quoteVol": "10000"})
            data = rows
        elif path.endswith("/get_funding_rate_history"):
            data = []
        else:
            pytest.fail(f"Unexpected path {path}")
        return httpx.Response(200, json={"code": 0, "data": data})
    return handler


def settings(tmp_path, **kwargs):
    return Settings(_env_file=None, data_dir=tmp_path / "data", workspace_dir=tmp_path / "workspace",
                    symbols=["BTCUSDT"], **kwargs)


async def test_end_to_end_paper_scan_risk_execution_guard_and_restart(tmp_path):
    mutations = []
    client = BitunixClient(client=httpx.AsyncClient(transport=httpx.MockTransport(market_handler(mutations))))
    # Bypass rate waits in unit tests only; transport still observes every actual request.
    async def no_wait(*args):
        pass
    client.limiter.wait = no_wait
    engine = TradingEngine(settings(tmp_path), client=client)
    engine.enable_paper()
    await engine.scan_once()
    assert engine.signals["BTCUSDT"].direction == "LONG"
    positions = await engine.broker.positions()
    assert len(positions) == 1
    p = positions[0]
    assert p.stop_loss < p.entry
    assert p.liquidation_price is None
    assert mutations == []
    await engine.shutdown()
    restarted = TradingEngine(settings(tmp_path))
    assert not restarted.autotrade and not restarted.enabled and not restarted.live_authorized
    assert (await restarted.broker.positions())[0].id == p.id
    await restarted.shutdown()


async def test_partial_ladder_single_execution_and_funding_idempotence(tmp_path):
    store = Store(tmp_path / "paper.db")
    cfg = TradeConfig(tp_mode="PARTIAL")
    broker = PaperBroker(store, cfg)
    rules = PairRules.from_api(PAIR)
    plan = TradePlan("BTCUSDT", "LONG", D(100), D(1), D(98), D(104), D(2), D(100), 1, 90, D(1), "PARTIAL")
    plan.ladder = make_ladder(cfg, "LONG", D(100), D(98), D(1), rules)
    p = await broker.open(plan, rules)
    broker.mark({"BTCUSDT": {"markPrice": "106"}})
    for rung in p.raw["ladder"]:
        await broker.close_position(p.id, "Partial TP", D(rung["quantity"]))
        rung["done"] = True
    assert p.qty == D("0.3")
    cash = broker.cash
    settled = p.raw["opened_at"] + 1000
    await broker.apply_funding("BTCUSDT", D("0.001"), D(106), settled)
    expected = cash - p.qty * 106 * D("0.001")
    assert broker.cash == expected
    await broker.apply_funding("BTCUSDT", D("0.001"), D(106), settled)
    assert broker.cash == expected
    await broker.close_position(p.id, "Final")
    assert not await broker.positions()
    broker.persist()
    assert PaperBroker(store, cfg).cash == broker.cash
    store.close()


async def test_account_tp_guard_and_engine_off_still_protects(tmp_path):
    ticker = {**TICKER, "markPrice": "106", "lastPrice": "106"}
    client = BitunixClient(client=httpx.AsyncClient(transport=httpx.MockTransport(market_handler([], ticker))))
    engine = TradingEngine(settings(tmp_path), client=client)
    engine.configure({"account_tp_usdt": 2, "tp_mode": "ACCOUNT"})
    plan = TradePlan("BTCUSDT", "LONG", D(100), D(1), D(98), D(104), D(2), D(100), 1, 90, D(1), "ACCOUNT")
    await engine.broker.open(plan, PairRules.from_api(PAIR))
    engine.stop_entries(engine_off=True)
    await engine.guard_once()
    assert not await engine.broker.positions()
    assert not engine.autotrade and engine.circuit
    await engine.shutdown()


async def test_invalid_settings_atomic_and_changes_stop_entries(tmp_path):
    engine = TradingEngine(settings(tmp_path))
    engine.enable_paper()
    with pytest.raises(ValueError):
        engine.configure({"max_positions": 0})
    assert engine.autotrade and engine.config.max_positions == 2
    engine.configure({"leverage": 3})
    assert not engine.autotrade and engine.config.leverage == 3
    await engine.shutdown()


async def test_live_cannot_mutate_without_env_gate_and_session_authorization(tmp_path):
    engine = TradingEngine(settings(tmp_path, trading_mode="live", bitunix_api_key="key", bitunix_api_secret="secret"))
    assert not engine.can_mutate()
    with pytest.raises(RiskRejected):
        await engine.authorize_live(1, engine.profile())
    with pytest.raises(RuntimeError):
        await engine.client.flash_close_position(positionId="1")
    await engine.shutdown()


async def test_loss_circuit_persists_and_restart_does_not_reset_baseline(tmp_path):
    engine = TradingEngine(settings(tmp_path))
    await engine.refresh_portfolio()
    engine.store.event("paper_close", {"net_pnl": "-40"})
    await engine.trip("Daily loss limit reached")
    await engine.shutdown()
    engine = TradingEngine(settings(tmp_path))
    assert engine.circuit == "Daily loss limit reached"
    with pytest.raises(RiskRejected, match="Daily loss"):
        await engine.reset_circuit()
    await engine.shutdown()


async def test_reducing_close_is_exact_quantity_and_no_double_close(tmp_path):
    store = Store(tmp_path / "state.db")
    broker = PaperBroker(store, TradeConfig())
    plan = TradePlan("BTCUSDT", "SHORT", D(100), D(1), D(102), D(96), D(2), D(100), 1, 90, D(1), "POSITION")
    p = await broker.open(plan, PairRules.from_api(PAIR))
    with pytest.raises(ValueError):
        await broker.close_position(p.id, "bad", D(2))
    assert p.qty == 1
    broker.mark({"BTCUSDT": {"markPrice": "96"}})
    await broker.close_position(p.id, "TP")
    with pytest.raises(ValueError):
        await broker.close_position(p.id, "duplicate")
    assert broker.cash > 1000
    store.close()
