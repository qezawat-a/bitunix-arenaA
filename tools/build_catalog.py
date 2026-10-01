#!/usr/bin/env python3
"""Reproducible table transcription of Bitunix pages retrieved 2026-10-01.

All supplied REST endpoints and every request/response table row are retained.
Navigation removed; duplicate examples are normalized to JSON bodies/query objects.
Do not silently 'correct' upstream parameter spellings or example/table conflicts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src/jrock/resources/bitunix"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://www.bitunix.com/api-docs/futures/"
REST = {}


def rows(text, request=False):
    result = []
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3 if request else 2)
        if request:
            name, kind, required, description = parts
            result.append({"name": name, "type": kind, "required": required == "true",
                           "required_literal": required, "description": description})
        else:
            name, kind, description = parts
            result.append({"name": name, "type": kind, "description": description})
    return result


def endpoint(name, source, method, path, params="", response="", description="", example=None,
             response_example=None, rate=10, public=False, notes=""):
    REST[name] = {"name": name, "source": BASE + source + ".html", "method": method, "path": path,
                  "public": public, "rate_per_second": rate, "description": description,
                  "parameters": rows(params, True), "response_parameters": rows(response),
                  "request_example": example, "response_example": response_example, "notes": notes}


SYMBOL = "symbol|string|true|Trading pair, based on symbolName, e.g. BTCUSDT"
SYMBOL_OPT = "symbol|string|false|Trading pair"
SYMBOLS = "symbols|string|false|Trading pairs, based on symbolName, i.e. BTCUSDT,ETHUSDT,XRPUSDT"
PAGE = """skip|int64|false|Skip order count; default: 0
limit|int64|false|Number of queries: maximum 100, default 10"""
TIME = """startTime|int64|false|Start timestamp. Unix timestamp in milliseconds, e.g. 1597026383085
endTime|int64|false|Start timestamp (source wording). Unix timestamp in milliseconds, e.g. 1597026683085"""
TRIGGERS = """tpPrice|string|false|Take-profit trigger price. At least one of tpPrice or slPrice is required.
tpStopType|string|false|Take-profit trigger type: LAST_PRICE, MARK_PRICE. Default is market price.
slPrice|string|false|Stop-loss trigger price. At least one of tpPrice or slPrice is required.
slStopType|string|false|Stop-loss trigger type: LAST_PRICE, MARK_PRICE. Default is market price."""
TPSL_EXTRA = """tpOrderType|string|false|Take-profit order type LIMIT or MARKET. Default is market.
tpOrderPrice|string|false|Take-profit order price
slOrderType|string|false|Stop-loss order type LIMIT or MARKET. Default is market.
slOrderPrice|string|false|Stop-loss order price
tpQty|string|false|Take-profit order quantity (base coin). At least one of tpQty or slQty is required.
slQty|string|false|Stop-loss order quantity (base coin). At least one of tpQty or slQty is required."""
ORDER_TRIGGERS = """tpPrice|string|false|Take profit trigger price
tpStopType|string|false|Take profit trigger type: MARK_PRICE or LAST_PRICE
tpOrderType|string|false|Take profit trigger place order type: LIMIT or MARKET
tpOrderPrice|string|false|Take profit trigger place order price. Required if tpOrderType is LIMIT.
slPrice|string|false|Stop loss trigger price
slStopType|string|false|Stop loss trigger type: MARK_PRICE or LAST_PRICE
slOrderType|string|false|Stop loss trigger place order type: LIMIT or MARKET
slOrderPrice|string|false|Stop loss trigger place order price. Required if slOrderType is LIMIT."""
ORDER_PARAMS = """qty|string|true|Amount (base coin)
price|string|false|Price of the order. Required if orderType is LIMIT.
side|string|true|Order direction: BUY or SELL
tradeSide|string|true|Only required in hedge-mode. Open long BUY/OPEN; open short SELL/OPEN; close long BUY/CLOSE; close short SELL/CLOSE.
positionId|string|false|Position ID. Required when tradeSide is CLOSE.
orderType|string|true|LIMIT: limit orders; MARKET: market orders
effect|string|false|Order expiration. Required if orderType is LIMIT. IOC immediate or cancel; FOK fill or kill; GTC good till canceled (default); POST_ONLY.
clientId|string|false|Customize order ID
reduceOnly|boolean|false|Whether or not to just reduce the position""" + "\n" + ORDER_TRIGGERS
ORDER_RESULT = "orderId|string|Order id\nclientId|string|Client id"
BATCH_RESULT = """successList|list|Successful order list
>id|string|Order id
>clientId|string|Client id
failureList|list|Failed order list
>clientId|string|Client id
>errorMsg|string|Error message
>errorCode|string|Error code"""
CANCEL_RESULT = BATCH_RESULT.replace("failureList|list|Failed order list", "failureList|list|Failed order list\n>id|string|Order id")
ORDER_RESPONSE = """orderId|string|Order id
symbol|string|Trading pair
qty|string|Amount (base coin)
tradeQty|string|Fill amount (base coin)
positionMode|string|ONE_WAY or HEDGE
marginMode|string|ISOLATION or CROSS
leverage|int|Leverage
price|string|Price of order. Required if orderType is LIMIT.
side|string|Order direction BUY or SELL
orderType|string|LIMIT: limit orders; MARKET: market orders
effect|string|IOC immediate or cancel; FOK fill or kill; GTC good till canceled (default); POST_ONLY. Required for LIMIT.
clientId|string|Customize order ID
reduceOnly|boolean|Whether or not to just reduce the position
status|string|INIT prepare; NEW pending; PART_FILLED partially filled; CANCELED canceled; FILLED all filled
fee|string|Fee
realizedPNL|string|Realized PnL
tpPrice|string|Take profit trigger price
tpStopType|string|MARK_PRICE or LAST_PRICE
tpOrderType|string|LIMIT or MARKET
tpOrderPrice|string|Take profit order price; required for LIMIT
slPrice|string|Stop loss trigger price
slStopType|string|MARK_PRICE or LAST_PRICE
slOrderType|string|LIMIT or MARKET
slOrderPrice|string|Stop loss order price; required for LIMIT
ctime|int64|Create timestamp
mtime|int64|Latest modify timestamp"""
TPSL_RESPONSE = """id|string|Order id
positionId|string|Position id
symbol|string|Coin pair
base|string|Base
quote|string|Quote
tpPrice|string|Take-profit trigger price
tpStopType|string|LAST_PRICE or MARK_PRICE
slPrice|string|Stop-loss trigger price
slStopType|string|LAST_PRICE or MARK_PRICE
tpOrderType|string|LIMIT or MARKET; default market
tpOrderPrice|string|Take-profit order price
slOrderType|string|LIMIT or MARKET; default market
slOrderPrice|string|Stop-loss order price
tpQty|string|Take-profit order quantity (base coin). At least one of tpQty or slQty is required.
slQty|string|Stop-loss order quantity (base coin). At least one of tpQty or slQty is required."""
FUNDING_RESPONSE = """symbol|string|Coin pair
markPrice|decimal|Mark price
lastPrice|decimal|Last price
indexPrice|decimal|Index price
fundingRate|decimal|Current funding rates
nextFundingTime|int64|Next funding settlement time (milliseconds)
fundingInterval|int32|Funding settlement interval (hours)
maxFundingRate|decimal|Max current funding rate
minFundingRate|decimal|Min current funding rate"""
ORDER_EXAMPLE = {"orderId": "11111", "qty": "1", "tradeQty": "0.5", "price": "60000", "symbol": "BTCUSDT",
                 "positionMode": "HEDGE", "marginMode": "ISOLATION", "leverage": 15, "status": "PART_FILLED",
                 "fee": "0.01", "realizedPNL": "1.78", "type": "LIMIT", "effect": "GTC", "reduceOnly": False,
                 "clientId": "22222", "tpPrice": "61000", "tpStopType": "MARK", "tpOrderType": "LIMIT",
                 "tpOrderPrice": "61000.1", "slPrice": "59000", "slStopType": "MARK", "slOrderType": "LIMIT",
                 "slOrderPrice": "59000.1", "source": "api", "ctime": 1597026383085, "mtime": 1597026383085}
POSITION_EXAMPLE = {"positionId": "12345678", "symbol": "BTCUSDT", "qty": "0.5", "entryValue": "30000",
                    "side": "LONG", "positionMode": "HEDGE", "marginMode": "ISOLATION", "leverage": 100,
                    "fee": "0.1", "funding": "-0.2", "realizedPNL": "102.9", "margin": "300", "unrealizedPNL": "1.5",
                    "liqPrice": "22209", "marginRate": "0.01", "avgOpenPrice": "1.0", "ctime": 1691382137448, "mtime": 1691382137448}
MUTATION_NOTICE = "Successful interface response is not necessarily equal to success of the operation; use WebSocket push messages as accurate judgment."
ORDER_CONFLICT = "Tables use MARK_PRICE/LAST_PRICE and orderType; examples use MARK/LAST and type/source. modify_order example includes symbol absent from its request table. No guessed fields are sent by the engine."

endpoint("get_tickers", "market/get_tickers", "GET", "/api/v1/futures/market/tickers", SYMBOLS,
"""symbol|string|Coin pair name i.e. BTCUSDT
markPrice|string|Mark price
lastPrice|string|Last price
open|string|Entry price of last 24 hours
last|string|Last price
quoteVol|string|Trading volume of the coin (last 24 hours), source wording
baseVol|string|Trading volume of last 24 hours
high|string|24-hour high
low|string|24-hour low""", "Get future trading pair tickers", {"symbols": "BTCUSDT,ETHUSDT"},
[{"symbol": "BTCUSDT", "markPrice": "57892.1", "lastPrice": "57891.2", "open": "6.31", "last": "6.31", "quoteVol": "0", "baseVol": "0", "high": "6.31", "low": "6.31"},
 {"symbol": "ETHUSDT", "markPrice": "2000", "lastPrice": "2020.1", "open": "6.31", "last": "6.31", "quoteVol": "0", "baseVol": "0", "high": "6.31", "low": "6.31"}], public=True)
endpoint("get_depth", "market/get_depth", "GET", "/api/v1/futures/market/depth", SYMBOL + "\nlimit|string|false|Fixed enumeration 1/5/15/50/max. max returns maximum gear. Actual depth returned if below requested limit.",
"""asks.index[0]|string|Ask price
asks.index[1]|string|Ask amount
bids.index[0]|string|Bid price
bids.index[1]|string|Bid amount""", "Get future order book", {"symbol": "BTCUSDT", "limit": "max"},
{"asks": [[0.1001, 0.1], [0.1002, 10]], "bids": [[0.1, 1], [0.0999, 10.23]]}, public=True)
fund_example = [{"symbol": "BTCUSDT", "markPrice": "60000", "lastPrice": "60001", "indexPrice": "60001", "fundingRate": "0.0005", "fundingInterval": 8, "nextFundingTime": "1770710400000", "maxFundingRate": "0.3", "minFundingRate": "-0.3"}]
endpoint("get_funding_rate", "market/get_funding_rate", "GET", "/api/v1/futures/market/funding_rate", SYMBOL, FUNDING_RESPONSE,
         "Get current funding rate of the contract", {"symbol": "BTCUSDT"}, fund_example, public=True)
endpoint("get_funding_rate_batch", "market/get_funding_rate_batch", "GET", "/api/v1/futures/market/funding_rate/batch", "", FUNDING_RESPONSE,
         "Get current funding rates of contracts", {}, fund_example, public=True)
endpoint("get_funding_rate_history", "market/get_funding_rate_history", "GET", "/api/v1/futures/market/get_funding_rate_history", SYMBOL + "\n" +
"""starTime|int64|false|Start timestamp (funding settle time). Unix timestamp in milliseconds, e.g. 1597026383085.
endTime|int64|fasle|End timestamp (funding settle time). Unix timestamp in milliseconds, e.g. 1597026383085.
limit|int32|false|Default: 100; maximum: 200""",
"""markPrice|string|Mark price
fundingRate|string|Funding rate
fundingTime|int64|Funding timestamp""", "Get historical funding rate", {"symbol": "BTCUSDT", "limit": 10},
[{"fundingRate": "-0.00001191", "fundingTime": "1772449200000", "markPrice": "66286.6"}], public=True,
notes="Source spells starTime (not startTime) and fasle (not false); retained exactly in schema. Confirm with exchange if rejected.")
endpoint("get_kline", "market/get_kline", "GET", "/api/v1/futures/market/kline", SYMBOL + "\n" +
"""startTime|int64|false|Query k-lines after this time; Unix timestamp in milliseconds, e.g. 1672410780000
endTime|int64|false|Query k-lines before this time; Unix timestamp in milliseconds, e.g. 1672410780000
interval|string|true|1m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M
limit|int|false|Default 100; maximum 200
type|string|false|Kline type LAST_PRICE or MARK_PRICE; default LAST_PRICE""",
"""open|string|Open price
high|string|High price
low|string|Low price
close|string|Close price
quoteVol|string|Trading amount (quote currency turnover) for kline period
baseVol|string|Trading volume (base coin) for kline period""", "Get future kline history", {"symbol": "BTCUSDT", "startTime": 1, "endTime": 10234, "interval": "15m"},
[{"open": "60000", "high": "60001", "close": "60000", "low": "59989.2", "time": 111111, "quoteVol": "1", "baseVol": "60000", "type": "LAST_PRICE"}],
public=True, notes="Response example has time and type absent from table. 3m is NOT documented: constructed locally from complete closed 1m candles.")
endpoint("get_trading_pairs", "market/get_trading_pairs", "GET", "/api/v1/futures/market/trading_pairs", SYMBOLS,
"""symbol|string|Coin pair name i.e. BTCUSDT
base|string|Base currency; ETH in ETHUSDT
quote|string|Base currency (source wording); USDT in ETHUSDT
minTradeVolume|string|Minimum opening amount (base currency)
minBuyPriceOffset|string|Minimum price offset for buy orders
maxSellPriceOffset|string|Maximum price offset for sell orders
maxLimitOrderVolume|string|Maximum limit order base amount
maxMarketOrderVolume|string|Maximum market order base amount
basePrecision|int|Max precision of opening amount
quotePrecision|int|Max precision of order price
maxLeverage|int|Max leverage
minLeverage|int|Min leverage
defaultLeverage|int|Default leverage
defaultMarginMode|string|Default margin mode Isolation or Cross
priceProtectScope|string|Price protection scope. Mark 10000, scope 0.02: minimum sell 10000*(1-0.02)=9800; maximum buy 10000*(1+0.02)=10200.
symbolStatus|string|OPEN: trading normal; CANCEL_ONLY: cancel only; STOP: cannot open/close
isApiSupported|bool|true: API trading enabled; false: disabled
maxFundingRate|decimal|Max current funding rate
minFundingRate|decimal|Min current funding rate
launchTime|long|Contract launch time. Unix milliseconds UTC. null if not configured.
delistTime|long|Scheduled delisting time. Unix milliseconds UTC. Omitted if not configured or cleared.""", "Get future trading pair details", {"symbols": "BTCUSDT,ETHUSDT"},
[{"symbol": "BTCUSDT", "base": "BTC", "quote": "USDT", "minTradeVolume": "0.0001", "minBuyPriceOffset": "-0.95", "maxSellPriceOffset": "100", "maxLimitOrderVolume": "100000", "maxMarketOrderVolume": "50000", "basePrecision": 4, "quotePrecision": 1, "minLeverage": 1, "maxLeverage": 125, "defaultLeverage": 20, "defaultMarginMode": 1, "priceProtectScope": "0.02", "symbolStatus": "OPEN", "isApiSupported": True, "maxFundingRate": "0.3", "minFundingRate": "-0.3"}], public=True,
notes="defaultMarginMode example is numeric 1, but table lists string values. Engine explicitly sets ISOLATION rather than assuming defaults.")

endpoint("adjust_position_margin", "account/adjust_position_margin", "POST", "/api/v1/futures/account/adjust_position_margin",
"""symbol|string|true|Trading pair
marginCoin|string|true|Margin coin
amount|string|true|Margin amount; positive increases, negative decreases
side|string|false|Position side LONG or SHORT. Either side or positionId required.
positionId|string|false|Position id. Either side or positionId required.""", "N/A||", "Add/reduce margin (isolated margin mode only)",
{"symbol": "BTCUSDT", "amount": "-100", "marginCoin": "USDT", "side": "LONG"}, "", rate=5)
endpoint("change_leverage", "account/change_leverage", "POST", "/api/v1/futures/account/change_leverage",
"""marginCoin|string|true|Margin coin
symbol|string|true|Trading pair
leverage|int|true|Leverage""", "marginCoin|string|Margin coin\nsymbol|string|Trading pair\nleverage|int|Leverage",
"Adjust leverage on given symbol", {"symbol": "BTCUSDT", "leverage": 12, "marginCoin": "USDT"}, [{"marginCoin": "USDT", "leverage": 12, "symbol": "BTCUSDT"}])
endpoint("change_margin_mode", "account/change_margin_mode", "POST", "/api/v1/futures/account/change_margin_mode",
"""marginMode|string|true|ISOLATION or CROSS
symbol|string|true|Trading pair
marginCoin|string|true|Margin coin""", "marginMode|string|ISOLATION or CROSS\nsymbol|string|Trading pair\nmarginCoin|string|Margin coin",
"Cannot be used while user has an open position or order", {"marginMode": "ISOLATION", "symbol": "BTCUSDT", "marginCoin": "USDT"},
{"marginCoin": "USDT", "symbol": "BTCUSDT", "marginMode": "ISOLATION"})
endpoint("change_position_mode", "account/change_position_mode", "POST", "/api/v1/futures/account/change_position_mode",
"positionMode|string|true|Position mode: ONE_WAY or HEDGE", "positionMode|string|ONE_WAY or HEDGE",
"Adjust position mode between one-way and hedge across all symbol futures. May fail if any positions or orders exist.",
{"positionMode": "HEDGE"}, [{"positionMode": "HEDGE"}], notes='Source also gives error {"code":200014,"data":null,"msg":"Existing positions or orders, unable to switch holding mode."}; number conflicts with error-code table (20014).')
endpoint("get_leverage_and_margin_mode", "account/get_leverage_and_margin_mode", "GET", "/api/v1/futures/account/get_leverage_margin_mode",
"symbol|string|true|Trading pair\nmarginCoin|string|true|Margin coin",
"symbol|string|Trading pair\nmarginCoin|string|Margin coin\nleverage|int|Leverage\nmarginMode|string|ISOLATION or CROSS",
"Get leverage and margin mode", {"symbol": "BTCUSDT", "marginCoin": "USDT"}, {"symbol": "BTCUSDT", "marginCoin": "USDT", "leverage": 10, "marginMode": "ISOLATION"})
endpoint("get_single_account", "account/get_single_account", "GET", "/api/v1/futures/account", "marginCoin|string|true|Margin coin",
"""marginCoin|string|Margin coin
available|string|Available quantity. This + crossUnrealizedPNL = actual maximum open amount.
frozen|string|Locked quantity of orders
margin|string|Locked quantity of positions
transfer|string|Maximum transferable amount
positionMode|string|ONE_WAY or HEDGE
crossUnrealizedPNL|string|Unrealized PnL for cross positions
isolationUnrealizedPNL|string|Unrealized PnL for isolated positions
bonus|string|Futures bonus""", "Get account details for marginCoin", {"marginCoin": "USDT"},
[{"marginCoin": "USDT", "available": "1000", "frozen": "0", "margin": "10", "transfer": "1000", "positionMode": "HEDGE", "crossUnrealizedPNL": "2", "isolationUnrealizedPNL": "0", "bonus": "0"}])
endpoint("asset_query", "copyTrading/asset/asset_query", "GET", "/api/v1/cp/asset/query", "", "available|string|Futures available\nmaxTransfer|string|Maximum transfer amount",
"Asset query", {}, {"available": "54.20916", "maxTransfer": "52.20916"}, notes='Source response has additional outer success:true and msg:"result.success".')

endpoint("get_pending_positions", "position/get_pending_positions", "GET", "/api/v1/futures/position/get_pending_positions",
SYMBOL_OPT + "\n" + """positionId|string|false|Position id
subAccountId|int64|false|With subAccountUid: positions for that sub-account only. Without subAccountUid: main account and all sub-accounts the current key can access (source wording).
includeSubAccounts|bool|false|Enable or disable sub-account query""",
"""positionId|string|Position id
symbol|string|Trading pair
qty|string|Position amount
entryValue|string|Available amount for positions
side|string|LONG or SHORT
marginMode|string|ISOLATION or CROSS
positionMode|string|ONE_WAY or HEDGE
leverage|int32|Leverage
fee|string|Deducted transaction fees during position
funding|string|Total funding fee during position
realizedPNL|string|Realized PnL excluding funding and transaction fee
margin|string|Locked asset of position
unrealizedPNL|string|Unrealized PnL
liqPrice|string|Estimated liquidation price. <=0 means low risk and no liquidation price at this time.
marginRate|string|Margin ratio
avgOpenPrice|string|Average open price
ctime|int64|Create timestamp
mtime|int64|Latest modify timestamp
subAccountId|int64|Position account id""", "Get pending positions", {"symbol": "BTCUSDT"}, [POSITION_EXAMPLE],
notes="Descriptions refer to subAccountUid but actual parameter row is subAccountId. Engine includes includeSubAccounts=false to avoid managing sub-accounts.")
endpoint("get_history_positions", "position/get_history_positions", "GET", "/api/v1/futures/position/get_history_positions",
SYMBOL_OPT + "\npositionId|string|false|Position id\n" + TIME.replace("Start timestamp.", "Start timestamp (position create time).") + "\n" + PAGE + "\nsubAccountId|int64|false|With subAccountUid: historical positions for that sub-account only. Without it: main account (source wording).",
"""positionList|list|Position list
>positionId|string|Position id
>symbol|string|Trading pair
>maxQty|string|Max position amount
>entryPrice|string|Average entry price
>closePrice|string|Average close price
>liqQty|string|Liquidate quantity
>side|string|LONG or SHORT
>marginMode|string|ISOLATION or CROSS
>positionMode|string|ONE_WAY or HEDGE
>leverage|int32|Leverage
>fee|string|Deducted transaction fees during position
>funding|string|Total funding fee during position
>realizedPNL|string|Realized PnL excluding funding and transaction fees
>liqPrice|string|Estimated liquidation price. <=0 means low risk and no liquidation price at this time.
>ctime|int64|Create timestamp
>mtime|int64|Latest modify timestamp
>subAccountId|int64|Position account id
total|int64|Total count""", "Get history positions", {"symbol": "BTCUSDT"},
{"positionList": [{"positionId": "12345678", "symbol": "BTCUSDT", "maxQty": "0.5", "entryPrice": "60000", "closePrice": "61000", "liqQty": "0", "side": "LONG", "positionMode": "HEDGE", "marginMode": "ISOLATION", "leverage": 100, "fee": "0.1", "funding": "-0.2", "realizedPNL": "102.9", "liqPrice": "22209", "ctime": 1691382137448, "mtime": 1691382137448}], "total": 12})
endpoint("get_position_tiers", "position/get_position_tiers", "GET", "/api/v1/futures/position/get_position_tiers", SYMBOL,
"""symbol|string|Trading pair
level|int32|Level
startValue|string|Minimum value
endValue|string|Maximum value
leverage|int32|Leverage
maintenanceMarginRate|string|Maintenance margin rate for position quantity tier. Below this rate triggers forced partial or full liquidation.""",
"Get position tiers", {"symbol": "BTCUSDT"},
[{"symbol": "BTCUSDT", "level": 1, "startValue": "0", "endValue": "50000", "leverage": 125, "maintenanceMarginRate": "0.004"}, {"symbol": "BTCUSDT", "level": 2, "startValue": "50000", "endValue": "200000", "leverage": 100, "maintenanceMarginRate": "0.005"}], public=True)

endpoint("place_order", "trade/place_order", "POST", "/api/v1/futures/trade/place_order", "symbol|string|true|Trading pair\n" + ORDER_PARAMS, ORDER_RESULT, "Place order",
{"symbol": "BTCUSDT", "side": "BUY", "price": "60000", "qty": "0.5", "positionId": "111", "tradeSide": "CLOSE", "orderType": "LIMIT", "reduceOnly": False, "effect": "GTC", "clientId": "1110000aaa", "tpPrice": "61000", "tpStopType": "MARK", "tpOrderType": "LIMIT", "tpOrderPrice": "61000.1"},
{"orderId": "11111", "clientId": "22222"}, notes=ORDER_CONFLICT)
endpoint("batch_order", "trade/batch_order", "POST", "/api/v1/futures/trade/batch_order", "symbol|string|true|Trading pair\norderList|list|true|Order list; maximum length 5\n" + "\n".join(">" + line for line in ORDER_PARAMS.splitlines()), BATCH_RESULT, "Place orders", rate=1,
example={"symbol": "BTCUSDT", "orderList": [{"side": "BUY", "price": "60000", "qty": "0.5", "orderType": "LIMIT", "reduceOnly": False, "effect": "GTC", "clientId": "c12345", "tpPrice": "61000", "tpStopType": "MARK", "tpOrderType": "LIMIT", "tpOrderPrice": "61000.1", "slPrice": "59000", "slStopType": "LAST", "slOrderType": "MARKET"}, {"side": "SELL", "price": "61000", "qty": "0.5", "orderType": "LIMIT", "reduceOnly": False, "effect": "IOC", "clientId": "c12346"}]},
response_example={"successList": [{"id": "11111", "clientId": "22222"}], "failureList": [{"clientId": "22222", "errorMsg": "Insufficient balance", "errorCode": 10012}]}, notes=ORDER_CONFLICT)
endpoint("cancel_orders", "trade/cancel_orders", "POST", "/api/v1/futures/trade/cancel_orders",
"""symbol|string|true|Trading pair
orderList|list|true|Order parameter list
orderId|string|false|Either orderId or clientId required. orderId prevails if both entered. These fields belong in orderList per example.
clientId|string|false|Customize order ID. Either orderId or clientId required. orderId prevails if both entered. These fields belong in orderList per example.""", CANCEL_RESULT,
"Cancel orders. " + MUTATION_NOTICE, {"symbol": "BTCUSDT", "orderList": [{"orderId": "11111"}, {"clientId": "22223"}]},
{"successList": [{"orderId": "11111", "clientId": "22222"}], "failureList": [{"orderId": "11112", "clientId": "22223", "errorMsg": "Order status error", "errorCode": 10013}]}, rate=5,
notes="Request table does not indent orderId/clientId but example nests them. Validator follows the documented example's orderList structure; both raw rows are retained.")
endpoint("cancel_all_orders", "trade/cancel_all_orders", "POST", "/api/v1/futures/trade/cancel_all_orders", SYMBOL_OPT, CANCEL_RESULT,
"Cancel all orders. " + MUTATION_NOTICE, {"symbol": "BTCUSDT"}, REST["cancel_orders"]["response_example"])
endpoint("close_all_position", "trade/close_all_position", "POST", "/api/v1/futures/trade/close_all_position", SYMBOL_OPT, "", "Close all positions",
{"symbol": "BTCUSDT"}, "", rate=1)
endpoint("flash_close_position", "trade/flash_close_position", "POST", "/api/v1/futures/trade/flash_close_position", "positionId|String|true|Position id", "positionId|string|Position ID",
"Close position by position id", {"positionId": "19848247723672"}, {"positionId": "19848247723672"}, rate=5)
endpoint("modify_order", "trade/modify_order", "POST", "/api/v1/futures/trade/modify_order",
"""orderId|string|false|Either orderId or clientId required. orderId prevails if both entered.
clientId|string|false|Customize order ID. Either orderId or clientId required. orderId prevails if both entered.
qty|string|true|Amount (base coin)
price|string|true|Price of order. Required if orderType is LIMIT.""" + "\n" + ORDER_TRIGGERS, ORDER_RESULT,
"Modify pending order TP/SL and/or price/qty. " + MUTATION_NOTICE,
{"orderId": "1111", "symbol": "BTCUSDT", "price": "60000", "qty": "0.5", "tpPrice": "61000", "tpStopType": "MARK", "tpOrderType": "LIMIT", "tpOrderPrice": "61000.1"},
{"orderId": "11111", "clientId": "22222"}, notes=ORDER_CONFLICT + " Table marks price always required; descriptive condition says LIMIT only. Generic validator conservatively requires the table field.")
endpoint("get_order_detail", "trade/get_order_detail", "GET", "/api/v1/futures/trade/get_order_detail",
"orderId|string|false|At least one of orderId/clientId is required\nclientId|string|false|At least one of orderId/clientId is required",
ORDER_RESPONSE, "Get order detail", {"orderId": "12345"}, ORDER_EXAMPLE, notes=ORDER_CONFLICT)
endpoint("get_pending_orders", "trade/get_pending_orders", "GET", "/api/v1/futures/trade/get_pending_orders",
SYMBOL_OPT + "\norderId|string|false|Order id\nclientId|string|false|Client id\nstatus|string|false|NEW or PART_FILLED\n" + TIME + "\n" + PAGE,
"orderList|list|Order list\n" + "\n".join(">" + line for line in ORDER_RESPONSE.splitlines()) + "\ntotal|int64|Total count",
"Get pending orders; sort by create time descending", {"symbol": "BTCUSDT"}, {"orderList": [{**ORDER_EXAMPLE, "status": "NEW"}], "total": 10}, notes=ORDER_CONFLICT)
endpoint("get_history_orders", "trade/get_history_orders", "GET", "/api/v1/futures/trade/get_history_orders",
SYMBOL_OPT + "\norderId|string|false|Order id\nclientId|string|false|Client id\nstatus|string|false|FILLED CANCELED PART_FILLED_CANCELED EXPIRED\ntype|string|false|LIMIT or MARKET; default all\n" + TIME + "\n" + PAGE + "\n" +
"""subAccountId|int64|false|With subAccountUid: historical orders for sub-account only. Without it: main account (source wording).
queryCanceled|boolean|false|Default false. true: canceled only, last 3 days. false: excludes canceled, last 90 days.""",
"orderList|list|Order list\n" + "\n".join(">" + line for line in ORDER_RESPONSE.splitlines()) + "\n>subAccountId|int64|Order account id\ntotal|int64|Total count",
"Get history orders; sort by create time descending", {"symbol": "BTCUSDT"}, {"orderList": [{**ORDER_EXAMPLE, "status": "CANCELED"}], "total": 10}, notes=ORDER_CONFLICT)
endpoint("get_history_trades", "trade/get_history_trades", "GET", "/api/v1/futures/trade/get_history_trades",
SYMBOL_OPT + "\norderId|string|false|Order id\npositionId|string|false|Position id\n" + TIME + "\n" + PAGE,
"""tradeList|list|Trade list
>tradeId|string|Trade id
>orderId|string|Order id
>symbol|string|Trading pair
>qty|string|Amount (base coin)
>positionMode|string|ONE_WAY or HEDGE
>marginMode|string|ISOLATION or CROSS
>leverage|int|Leverage
>price|string|Order price. Required for LIMIT.
>side|string|Order direction BUY or SELL
>orderType|string|LIMIT or MARKET
>effect|string|IOC/FOK/GTC(default)/POST_ONLY. Required for LIMIT.
>clientId|string|Customize order ID
>reduceOnly|boolean|Whether or not to just reduce position
>fee|string|Fee
>realizedPNL|string|Realized PnL
>ctime|int64|Create timestamp
>roleType|string|Trader tag: TAKER: maker; MAKER: maker (source wording)
total|int64|Total count""", "Get history trades; sort by create time descending", {"symbol": "BTCUSDT"},
{"tradeList": [{"tradeId": "123", "orderId": "11111", "qty": "1", "price": "60000", "symbol": "BTCUSDT", "positionMode": "HEDGE", "marginMode": "ISOLATION", "leverage": 15, "fee": "0.01", "realizedPNL": "1.78", "type": "LIMIT", "effect": "GTC", "reduceOnly": False, "clientId": "22222", "source": "api", "ctime": 1597026383085, "roleType": "TAKER"}], "total": 10}, notes=ORDER_CONFLICT + " roleType labels have an upstream typo; not corrected in transcription.")

for name, suffix in (("place_position_tp_sl_order", "place_order"), ("modify_position_tp_sl_order", "modify_order")):
    endpoint(name, "tp_sl/" + name, "POST", "/api/v1/futures/tpsl/position/" + suffix,
        "symbol|string|true|Trading pair\npositionId|string|true|Position ID associated with TP/SL\n" + TRIGGERS,
        "orderId|string|TP/SL Order ID",
        "Place position TP/SL: triggered closes current whole position at market; only one position TP/SL per position." if suffix == "place_order" else "Modify position TP/SL order",
        {"symbol": "BTCUSDT", "positionId": "111" if suffix == "place_order" else "11", "tpPrice": "12", "tpStopType": "LAST_PRICE", "slPrice": "9", "slStopType": "LAST_PRICE"}, {"orderId": "11111"})
for name, suffix in (("place_tp_sl_order", "place_order"), ("modify_tp_sl_order", "modify_order")):
    params = "symbol|string|true|Trading pair\npositionId|string|true|Position ID associated with TP/SL" if suffix == "place_order" else "orderId|string|true|TP/SL Order ID"
    example = {"symbol": "BTCUSDT", "positionId": "111"} if suffix == "place_order" else {"orderId": "123"}
    endpoint(name, "tp_sl/" + name, "POST", "/api/v1/futures/tpsl/" + suffix, params + "\n" + TRIGGERS + "\n" + TPSL_EXTRA,
        "orderId|string|TP/SL Order ID", "Place TP/SL order" if suffix == "place_order" else "Modify TP/SL order",
        {**example, "tpPrice": "12", "tpStopType": "LAST_PRICE", "slPrice": "9", "slStopType": "LAST_PRICE", "tpOrderType": "LIMIT", "tpOrderPrice": "11", "slOrderType": "LIMIT", "slOrderPrice": "8", "tpQty": "1", "slQty": "1"}, {"orderId": "11111"})
endpoint("cancel_tp_sl_order", "tp_sl/cancel_tp_sl_order", "POST", "/api/v1/futures/tpsl/cancel_order", "symbol|string|true|Coin pair\norderId|string|true|TP/SL Order ID", "orderId|string|TP/SL Order ID",
"Cancel TP/SL order. " + MUTATION_NOTICE, {"symbol": "BTCUSDT", "orderId": "12"}, {"orderId": "11111"})
endpoint("get_pending_tp_sl_order", "tp_sl/get_pending_tp_sl_order", "GET", "/api/v1/futures/tpsl/get_pending_orders",
SYMBOL_OPT + "\npositionId|string|false|Position id\nside|int32|false|Order side\npositionMode|int32|false|Order position mode\n" + PAGE,
TPSL_RESPONSE, "Get pending TP/SL orders", {"symbol": "BTCUSDT"},
[{"id": "123", "positionId": "12345678", "symbol": "BTCUSDT", "base": "BTC", "quote": "USDT", "tpPrice": "50000", "tpStopType": "LAST_PRICE", "slPrice": "70000", "slStopType": "LAST_PRICE", "tpOrderType": "LIMIT", "tpOrderPrice": "50000", "slOrderType": "LIMIT", "slOrderPrice": "70000", "tpQty": "0.01", "slQty": "0.01"}],
notes="side and positionMode are documented as integers but enum mapping is not provided here; engine queries by positionId instead of guessing values.")
endpoint("get_history_tp_sl_order", "tp_sl/get_history_tp_sl_order", "GET", "/api/v1/futures/tpsl/get_history_orders",
SYMBOL_OPT + "\nside|int32|false|Order side\npositionMode|int32|false|Order position mode\n" + TIME + "\n" + PAGE,
"orderList|list|TP/SL order list\n" + "\n".join(">" + line for line in TPSL_RESPONSE.splitlines()) + "\n>status|string|TP/SL order status\n>ctime|int64|Create timestamp\n>triggerTime|int64|Trigger timestamp\ntotal|int64|Total",
"Get history TP/SL orders", {"symbol": "BTCUSDT"}, [{k: v for k, v in POSITION_EXAMPLE.items() if k != "avgOpenPrice"}],
notes="Response example is a positions array, inconsistent with its orderList/total response table. Adapter preserves raw response; no lossy guessed conversion.")


def table(data, request):
    names = ["Parameter", "Type", "Required", "Description"] if request else ["Parameter", "Type", "Description"]
    text = "| " + " | ".join(names) + " |\n| " + " | ".join(["---"] * len(names)) + " |\n"
    for row in data:
        cols = [row["name"], row["type"]]
        if request:
            cols.append(row["required_literal"])
        cols.append(row["description"].replace("|", "\\|"))
        text += "| " + " | ".join(cols) + " |\n"
    return text


def build():
    manifest = []
    for name, ep in REST.items():
        text = f"# {name.replace('_', ' ').title()}\n\nSource: {ep['source']}\n\nRetrieved: 2026-10-01 UTC. Table transcription, navigation removed.\n\n"
        text += f"Rate Limit: {ep['rate_per_second']} req/sec/{'ip' if ep['public'] else 'uid'}\n\n"
        text += f"## Description\n\n{ep['description']}\n\n## HTTP Request\n\n- {ep['method']} {ep['path']}\n\n"
        text += "## Request Parameters\n\n" + table(ep["parameters"], True)
        text += "\n## Request example (query parameters or body)\n\n```json\n" + json.dumps(ep["request_example"], indent=2) + "\n```\n"
        text += "\n## Response Parameters\n\n" + table(ep["response_parameters"], False)
        text += "\n## Response Example\n\n```json\n" + json.dumps({"code": 0, "data": ep["response_example"], "msg": "Success"}, indent=2) + "\n```\n"
        if ep["notes"]:
            text += "\n## Upstream inconsistencies / implementation notes\n\n" + ep["notes"] + "\n"
        p = OUT / f"{name}.md"
        p.write_text(text)
        manifest.append({"id": name, "url": ep["source"], "file": p.name,
                         "sha256": hashlib.sha256(text.encode()).hexdigest(), "status": "table-transcription",
                         "request_parameters": len(ep["parameters"]), "response_parameters": len(ep["response_parameters"])})
    (OUT / "rest_catalog.json").write_text(json.dumps(REST, indent=2) + "\n")
    (OUT / "manifest.json").write_text(json.dumps({"retrieved": "2026-10-01", "rest_count": len(REST), "documents": manifest}, indent=2) + "\n")
    print(f"Built {len(REST)} REST endpoints; {sum(len(ep['parameters']) for ep in REST.values())} request table rows; {sum(len(ep['response_parameters']) for ep in REST.values())} response table rows")


if __name__ == "__main__":
    build()
