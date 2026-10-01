import hashlib

import httpx
import pytest

from jrock.exchange.catalog import Documentation
from jrock.exchange.client import AmbiguousMutation, BitunixClient, ExchangeError
from jrock.exchange.signing import compact_body, query_signature, sign, websocket_login
from jrock.exchange.websocket import WSState, business_time_ns


def test_catalog_covers_every_endpoint_and_manifest():
    docs = Documentation()
    assert len(docs.rest) == 35
    assert len(docs.ws) == 10
    assert len(docs.manifest["documents"]) == 52
    assert docs.manifest["unavailable_supplied_pages"] == []
    assert docs.verify() == []
    assert sum(len(x["parameters"]) for x in docs.rest.values()) == 176
    assert "starTime" in [p["name"] for p in docs.rest["get_funding_rate_history"]["parameters"]]
    assert len(docs.errors) == 76


def test_signature_matches_official_example():
    body = '{"uid":"2899","arr":[{"id":1,"name":"maple"},{"id":2,"name":"lily"}]}'
    first = hashlib.sha256(("123456" + "20241120123045" + "yourApiKey" + "id1uid200" + body).encode()).hexdigest()
    assert sign("yourApiKey", "yourSecretKey", "123456", "20241120123045", "id1uid200", body) == hashlib.sha256((first + "yourSecretKey").encode()).hexdigest()
    assert query_signature({"uid": 200, "id": 1, "includeSubAccounts": False}) == "id1includeSubAccountsfalseuid200"
    assert compact_body({"note": "keep this space", "qty": "0.1"}) == '{"note":"keep this space","qty":"0.1"}'
    args = websocket_login("key", "secret")["args"][0]
    assert args["timestamp"] < 10_000_000_000
    assert args["sign"] == sign("key", "secret", args["nonce"], str(args["timestamp"]))


async def test_signed_body_is_exact_wire_and_unknown_fields_rejected():
    requests = []
    def handler(r):
        requests.append(r)
        h = r.headers
        assert h["sign"] == sign("key", "secret", h["nonce"], h["timestamp"], "", r.content.decode())
        return httpx.Response(200, json={"code": 0, "data": {"orderId": "1"}})
    client = BitunixClient(api_key="key", secret="secret", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), mutation_guard=lambda: True)
    await client.place_order(symbol="BTCUSDT", qty="0.1", side="BUY", tradeSide="OPEN", orderType="MARKET")
    assert requests[0].content == b'{"symbol":"BTCUSDT","qty":"0.1","side":"BUY","tradeSide":"OPEN","orderType":"MARKET"}'
    with pytest.raises(ValueError):
        await client.get_funding_rate_history(symbol="BTCUSDT", startTime=1)
    await client.close()


async def test_paper_never_sends_private_mutation():
    def handler(r):
        pytest.fail("Paper client must not send POST")
    client = BitunixClient(api_key="key", secret="secret", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(ExchangeError):
        await client.flash_close_position(positionId="1")
    await client.close()


async def test_timeout_never_retries_post_and_business_errors_checked():
    calls = 0
    def handler(r):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout")
    client = BitunixClient(api_key="key", secret="secret", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), mutation_guard=lambda: True)
    with pytest.raises(AmbiguousMutation):
        await client.flash_close_position(positionId="1")
    assert calls == 1
    await client.close()
    def error_handler(r):
        return httpx.Response(200, json={"code": 20003, "data": None, "msg": "secret might be echoed"})
    client = BitunixClient(client=httpx.AsyncClient(transport=httpx.MockTransport(error_handler)))
    with pytest.raises(ExchangeError, match="Insufficient balance"):
        await client.get_tickers()
    await client.close()


def test_nested_parameters_conditionals_precision_types():
    docs = Documentation()
    docs.validate("cancel_orders", {"symbol": "BTCUSDT", "orderList": [{"clientId": "a"}]})
    docs.validate("batch_order", {"symbol": "BTCUSDT", "orderList": [{"qty": "1", "orderType": "MARKET", "side": "BUY"}]})
    for name, params in [
        ("place_order", {"symbol": "BTCUSDT", "qty": 1, "side": "BUY", "orderType": "MARKET"}),
        ("place_order", {"symbol": "BTCUSDT", "qty": "1", "side": "BUY", "orderType": "LIMIT"}),
        ("get_order_detail", {}),
        ("place_tp_sl_order", {"symbol": "BTCUSDT", "positionId": "1", "slPrice": "2"}),
        ("get_kline", {"symbol": "BTCUSDT", "interval": "3m"}),
        ("get_depth", {"symbol": "BTCUSDT", "limit": "100"}),
        ("cancel_orders", {"symbol": "BTCUSDT", "orderList": [{}]}),
    ]:
        with pytest.raises(ValueError):
            docs.validate(name, params)


def test_ws_tpsl_trigger_not_position_fill_and_ordering():
    state = WSState()
    event = {"ch": "tpsl", "ts": 1, "data": {"orderId": "tp1", "event": "CLOSE", "status": "FILLED"}}
    state.apply(event)
    assert state.tpsl["tp1"]["status"] == "FILLED"
    assert state.orders == {}
    state.apply({"ch": "tpsl", "data": {"orderId": "tp1", "event": "CREATE", "status": "NEW"}})
    assert state.tpsl["tp1"]["status"] == "FILLED"
    with pytest.raises(ExchangeError):
        state.apply({"ch": "tpsl", "data": []})
    newer = {"orderId": "o1", "orderStatus": "FILLED", "mtime": "2024-05-16T08:13:09.123456789Z"}
    state.apply({"ch": "order", "ts": 1, "data": newer})
    state.apply({"ch": "order", "ts": 999999999, "data": {**newer, "orderStatus": "NEW", "mtime": "2024-05-16T08:13:09.123456788Z"}})
    assert state.orders["o1"]["orderStatus"] == "FILLED"
    assert business_time_ns(newer["mtime"]) % 1_000_000_000 == 123456789


def test_depth_updates_remove_zero_and_reconnect_discards_state():
    state = WSState()
    state.apply({"ch": "depth_books", "symbol": "BTCUSDT", "data": {"a": [["10", "1"]], "b": [["9", "2"]]}})
    state.apply({"ch": "depth_books", "symbol": "BTCUSDT", "data": {"a": [["10", "0"], ["11", "3"]]}})
    assert len(state.depth["BTCUSDT"]["a"]) == 1
    state.reconnect()
    assert not state.depth
