#!/usr/bin/env python3
"""WebSocket table transcription, retrieved 2026-10-01; no omitted supplied channel."""
import hashlib
import json

from build_catalog import BASE, OUT, rows, table

CHANNELS = {}


def channel(name, source, private, request, push, description="", example=None, notes=""):
    CHANNELS[name] = {"name": name, "source": BASE + source + ".html", "private": private,
        "request_parameters": [{**r, "required_literal": "Yes", "required": True} for r in rows(request, True)],
        "push_parameters": rows(push), "description": description, "push_example": example, "notes": notes}


COMMON = "op|String|true|Operation: subscribe or unsubscribe\nargs|List<Object>|true|List of channels to request subscription"
SYMBOL = ">symbol|String|true|Product ID e.g. ETHUSDT"
PUBLIC_PUSH = "ch|String|Channel name\nsymbol|String|Product ID e.g. ETHUSDT\nts|int64|Timestamp\ndata|List<String>|Subscription data"
TICKER_FIELDS = """>s|String|Symbol e.g. ETHUSDT
>o|String|Opening price
>h|String|Highest price
>l|String|Lowest price
>la|String|Last price
>b|String|Trading volume of the coin
>q|String|Trading volume of quote currency
>r|String|24-hour fluctuations"""
TICKER_SAMPLE = {"s": "BTCUSDT", "la": "68650.9", "o": "69141.6", "h": "70319.9", "l": "68241.9", "b": "26295.3977", "q": "1823374525.0193", "r": "-0.7097029863"}
channel("balance", "websocket/private/Balance%20Channel", True, "",
"""ch|String|Channel name: balance
ts|Int64|Timestamp
data|<Object>|
>coin|String|Coin
>available|String|Available
>frozen|String|frozen = isolationFrozen + crossFrozen
>isolationFrozen|String|Freeze on a per warehouse basis
>crossFrozen|String|Full warehouse entrusted freeze
>margin|String|Margin
>isolationMargin|String|Warehouse by warehouse margin
>crossMargin|String|Full warehouse margin
>expMoney|String|Experience money""", "Balance")
channel("position", "websocket/private/Position%20Channel", True, "",
"""ch|String|Channel name: position
ts|Int64|Timestamp
data|<Object>|Subscription data
>event|String|OPEN/UPDATE/CLOSE
>positionId|String|Position id
>marginMode|String|ISOLATION/CROSS
>positionMode|String|ONE_WAY/HEDGE
>side|String|SHORT/LONG
>leverage|String|Leverage
>margin|String|Margin
>ctime|String|Create time
>qty|String|Open position size
>symbol|String|Symbol
>realizedPNL|String|Realized PnL excluding funding and transaction fee
>unrealizedPNL|String|Unrealized PnL
>funding|String|Total funding fee during the position
>fee|String|Deducted transaction fees during the position""",
"Subscribe position channel. Pushed when open/close orders created, filled, canceled. Position WS lacks liqPrice and avgOpenPrice; reconcile REST rather than inventing them.")
channel("order", "websocket/private/Order%20Channel", True, "",
"""ch|String|Channel name: order
ts|Int64|Gateway send time in milliseconds; not business event time; do not confuse with ctime/mtime.
data|<Object>|Subscription data
>event|String|CREATE/UPDATE/CLOSE
>orderId|String|Order id
>symbol|String|Symbol
>positionType|String|Margin mode ISOLATION/CROSS
>positionMode|String|ONE_WAY/HEDGE
>side|String|BUY/SELL
>effect|String|Required for LIMIT. IOC immediate or cancel; FOK fill or kill; GTC(default); POST_ONLY.
>type|String|LIMIT/MARKET
>qty|String|Amount (base coin)
>price|String|Price of order; required for LIMIT
>ctime|String|ISO-8601 nanosecond create time, e.g. 2024-05-16T08:13:09.123456789Z
>mtime|String|ISO-8601 nanosecond last modify time; same as ctime. REST order APIs use millisecond integers.
>leverage|String|Leverage
>orderStatus|String|INIT/NEW/PART_FILLED/CANCELED/FILLED/PART_FILLED_CANCELED
>fee|String|Deducted transaction fees during position
>averagePrice|String|Average price
>dealAmount|String|Deal amount
>clientId|String|Client ID
>tpStopType|String|MARK_PRICE/LAST_PRICE
>tpPrice|String|Take profit trigger price
>tpOrderType|String|LIMIT/MARKET
>tpOrderPrice|String|Take profit order price LIMIT/MARKET (source wording)
>slStopType|String|MARK_PRICE/LAST_PRICE
>slPrice|String|Stop loss trigger price
>slOrderType|String|LIMIT/MARKET
>slOrderPrice|String|Stop loss order price LIMIT/MARKET (source wording)""",
"Subscribe order channel. Pushed when open/close orders are created/filled/canceled.")
channel("tpsl", "websocket/private/Tp%20Sl%20Channel", True, "",
"""ch|String|Channel name: tpsl
ts|Int64|Gateway send time, Unix milliseconds. Do not use to order business events.
data|<Object>|Always an object, not an array
>event|String|CREATE/UPDATE/CLOSE
>positionId|String|Position id
>orderId|String|Order id
>symbol|String|Symbol
>leverage|String|Leverage
>side|String|BUY/SELL
>positionMode|String|ONE_WAY/HEDGE
>status|String|NEW/CANCELED/SYSTEM_CANCELED/FILLED/FAILED
>ctime|String|ISO-8601 nanosecond create time, e.g. 2024-05-16T08:13:09.123456789Z. REST history uses milliseconds.
>type|String|LIMIT/MARKET
>tpQty|String|Take-profit quantity (base coin); omitted if unused
>slQty|String|Stop-loss quantity (base coin); omitted if unused. Never Boolean or JSON null; string 0 sent as string 0.
>tpStopType|String|MARK_PRICE/LAST_PRICE
>tpPrice|String|Take profit trigger price
>tpOrderType|String|LIMIT/MARKET
>tpOrderPrice|String|Take profit order price
>slStopType|String|MARK_PRICE/LAST_PRICE
>slPrice|String|Stop loss trigger price
>slOrderType|String|LIMIT/MARKET
>slOrderPrice|String|Stop loss order price""",
"After private login succeeds, channel tpsl is pushed automatically. data is ALWAYS object. CLOSE alone is not a final state: read event together with status. FILLED means TP/SL triggered and CHILD ORDER PLACED, NOT child full fill. Child fills are order channel or REST. INIT/PENDING_CANCEL/TRIGGER_WAIT_PLACE are not pushed; PART_FILLED is not a TPSL status.",
notes="Event/status: CREATE+NEW effective; UPDATE+NEW modified; CLOSE+CANCELED user canceled; CLOSE+SYSTEM_CANCELED system canceled; CLOSE+FILLED trigger succeeded/child placed; CLOSE+FAILED trigger failed.")
channel("depth", "websocket/public/depth%20channel", False,
COMMON + "\n>ch|String|true|depth_books,depth_book1,depth_book5,depth_book15\n" + SYMBOL,
"""ch|Object|Channel name (source type)
symbol|String|Product ID
ts|Int64|Timestamp
data|String|Subscription data (source type)
>a|List<String>|Seller depth
>b|List<String>|Buyer depth""",
"books: first full snapshot then changed depth; book1/book5/book15: respective levels pushed each time.",
{"ch": "depth_book1", "symbol": "BTCUSDT", "ts": 1775541541009, "data": {"b": [["7403.89", "0.002"]], "a": [["7405.96", "3.340"]]}},
"Tables type ch as Object, data as String; examples are string and object. For books apply deltas, zero qty removes price; rebuild on reconnect. No sequence ID/checksum is documented here; use REST refresh to recover uncertainty.")
intervals = ["1min", "3min", "5min", "15min", "30min", "60min", "2h", "4h", "6h", "8h", "12h", "1day", "3day", "1week", "1month"]
channel("kline", "websocket/public/kline%20channel", False,
COMMON + "\n>ch|String|true|" + ",".join(f"{p}_kline_{i}" for i in intervals for p in ("market", "mark")) + "\n" + SYMBOL,
PUBLIC_PUSH + "\n" + """>o|String|Opening price
>h|String|Highest price
>l|String|Lowest price
>c|String|Closing price
>b|String|Trading volume of the coin
>q|String|Trading volume of quote currency""",
"Candlestick push every 500 ms; snapshot then updates. MUST unsubscribe previous interval before subscribing new interval on same socket.",
{"ch": "market_kline_1min", "symbol": "BTCUSDT", "ts": 1775541412718, "data": {"o": "68581.4", "c": "68583.4", "h": "68590", "l": "68579.5", "b": "5.2395", "q": "359348.14078"}},
"Unlike REST, WS documents 3min. No candle start time or closed flag in supplied push schema. Engine uses closed REST candles for indicators; never treats gateway ts as a closed-candle marker.")
channel("price", "websocket/public/MarketPrice%20Channel", False, COMMON + "\n" + SYMBOL + "\n>ch|String|true|Channel price",
PUBLIC_PUSH + "\n" + """>mp|String|Market price
>ip|String|Index price
>fr|String|Funding rate
>ft|String|Funding rate settlement time
>nft|String|Next funding rate settlement time""", "Market price channel",
{"ch": "price", "symbol": "BNBUSDT", "ts": 1732178884994, "data": {"ip": "0.0010", "mp": "10000", "fr": "0.013461", "ft": "2024-12-04T11:00:00Z", "nft": "2024-12-04T12:00:00Z"}},
"Table says data List<String>, example is object; preserve received format.")
channel("ticker", "websocket/public/Ticker%20Channel", False, COMMON + "\n" + SYMBOL + "\n>ch|String|true|Channel ticker",
PUBLIC_PUSH + "\n" + TICKER_FIELDS,
"24-hour rolling mini-ticker statistics; NOT UTC calendar-day statistics.",
{"ch": "ticker", "symbol": "BNBUSDT", "ts": 1732178884994, "data": TICKER_SAMPLE},
"Table data List<String>, example object. Example envelope symbol BNBUSDT differs from data.s BTCUSDT; do not assign price to a guessed symbol.")
channel("tickers", "websocket/public/Tickers%20Channel", False, COMMON + "\n" + SYMBOL + "\n>ch|String|true|Channel tickers",
PUBLIC_PUSH.replace("symbol|String|Product ID e.g. ETHUSDT\n", "") + "\n" + TICKER_FIELDS + "\n" +
""">bd|String|Best bid price
>ak|String|Best ask price
>bv|String|Best bid volume
>av|String|Best ask volume""", "Aggregated 24-hour rolling statistics; data structure differs from ticker; NOT UTC daily data.",
{"ch": "tickers", "ts": 1732178884994, "data": [{**TICKER_SAMPLE, "bd": "68650.9", "ak": "68651", "bv": "0.9747", "av": "2.3606"},
{"s": "ETHUSDT", "la": "2104.61", "o": "2128.49", "h": "2173.75", "l": "2086.79", "b": "945498.652", "q": "2018286647.13588", "r": "-1.1219221138", "bd": "2104.6", "ak": "2104.61", "bv": "27.789", "av": "7.905"}]})
channel("trade", "websocket/public/Trade%20Channel", False, COMMON + "\n" + SYMBOL + "\n>ch|String|true|Channel trade",
"""ch|String|Channel trade
symbol|String|Symbol e.g. ETHUSDT
ts|String|Timestamp
data|List<Object>|Data
>p|String|Filled price
>v|String|Filled amount
>s|String|Filled side sell/buy
>t|String|Timestamp""", "Get public trade data",
{"ch": "trade", "symbol": "BTCUSDT", "ts": 1775540872598, "data": [{"t": "2026-04-07T05:47:52Z", "p": "68621.4", "v": "0.7142", "s": "buy"}, {"t": "2026-04-07T05:47:52Z", "p": "68621.4", "v": "0.0018", "s": "sell"}]})


if __name__ == "__main__":
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["documents"] = [d for d in manifest["documents"] if not d["id"].startswith("ws_")]
    for name, channel in CHANNELS.items():
        text = f"# {name} WebSocket channel\n\nSource: {channel['source']}\n\nRetrieved: 2026-10-01 UTC. Table transcription, navigation removed.\n\n"
        text += f"Private: {channel['private']}\n\n## Description\n\n{channel['description']}\n\n"
        text += "## Request Parameters\n\n" + table(channel["request_parameters"], True)
        if not channel["private"]:
            ch = {"depth": "depth_book1", "kline": "market_kline_1min"}.get(name, name)
            req = {"op": "subscribe", "args": [{"symbol": "BTCUSDT", "ch": ch}]}
            if name == "tickers":
                req["args"].append({"symbol": "ETHUSDT", "ch": "tickers"})
            text += "\n## Request Example\n\n```json\n" + json.dumps(req, indent=2) + "\n```\n"
        text += "\n## Push Parameters\n\n" + table(channel["push_parameters"], False)
        if channel["push_example"]:
            text += "\n## Push Example\n\n```json\n" + json.dumps(channel["push_example"], indent=2) + "\n```\n"
        if channel["notes"]:
            text += "\n## Semantics / upstream inconsistencies\n\n" + channel["notes"] + "\n"
        p = OUT / ("ws_" + name + ".md")
        p.write_text(text)
        manifest["documents"].append({"id": "ws_" + name, "url": channel["source"], "file": p.name,
            "sha256": hashlib.sha256(text.encode()).hexdigest(), "status": "table-transcription",
            "request_parameters": len(channel["request_parameters"]), "push_parameters": len(channel["push_parameters"])})
    manifest["websocket_channels"] = len(CHANNELS)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "ws_catalog.json").write_text(json.dumps(CHANNELS, indent=2) + "\n")
    print("Built", len(CHANNELS), "WebSocket channels")
