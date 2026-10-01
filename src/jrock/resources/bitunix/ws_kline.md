# kline WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/public/kline%20channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: False

## Description

Candlestick push every 500 ms; snapshot then updates. MUST unsubscribe previous interval before subscribing new interval on same socket.

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | Operation: subscribe or unsubscribe |
| args | List<Object> | Yes | List of channels to request subscription |
| >ch | String | Yes | market_kline_1min,mark_kline_1min,market_kline_3min,mark_kline_3min,market_kline_5min,mark_kline_5min,market_kline_15min,mark_kline_15min,market_kline_30min,mark_kline_30min,market_kline_60min,mark_kline_60min,market_kline_2h,mark_kline_2h,market_kline_4h,mark_kline_4h,market_kline_6h,mark_kline_6h,market_kline_8h,mark_kline_8h,market_kline_12h,mark_kline_12h,market_kline_1day,mark_kline_1day,market_kline_3day,mark_kline_3day,market_kline_1week,mark_kline_1week,market_kline_1month,mark_kline_1month |
| >symbol | String | Yes | Product ID e.g. ETHUSDT |

## Request Example

```json
{
  "op": "subscribe",
  "args": [
    {
      "symbol": "BTCUSDT",
      "ch": "market_kline_1min"
    }
  ]
}
```

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel name |
| symbol | String | Product ID e.g. ETHUSDT |
| ts | int64 | Timestamp |
| data | List<String> | Subscription data |
| >o | String | Opening price |
| >h | String | Highest price |
| >l | String | Lowest price |
| >c | String | Closing price |
| >b | String | Trading volume of the coin |
| >q | String | Trading volume of quote currency |

## Push Example

```json
{
  "ch": "market_kline_1min",
  "symbol": "BTCUSDT",
  "ts": 1775541412718,
  "data": {
    "o": "68581.4",
    "c": "68583.4",
    "h": "68590",
    "l": "68579.5",
    "b": "5.2395",
    "q": "359348.14078"
  }
}
```

## Semantics / upstream inconsistencies

Unlike REST, WS documents 3min. No candle start time or closed flag in supplied push schema. Engine uses closed REST candles for indicators; never treats gateway ts as a closed-candle marker.
