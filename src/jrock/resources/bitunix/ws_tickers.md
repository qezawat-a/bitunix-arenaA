# tickers WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/public/Tickers%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: False

## Description

Aggregated 24-hour rolling statistics; data structure differs from ticker; NOT UTC daily data.

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | Operation: subscribe or unsubscribe |
| args | List<Object> | Yes | List of channels to request subscription |
| >symbol | String | Yes | Product ID e.g. ETHUSDT |
| >ch | String | Yes | Channel tickers |

## Request Example

```json
{
  "op": "subscribe",
  "args": [
    {
      "symbol": "BTCUSDT",
      "ch": "tickers"
    },
    {
      "symbol": "ETHUSDT",
      "ch": "tickers"
    }
  ]
}
```

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel name |
| ts | int64 | Timestamp |
| data | List<String> | Subscription data |
| >s | String | Symbol e.g. ETHUSDT |
| >o | String | Opening price |
| >h | String | Highest price |
| >l | String | Lowest price |
| >la | String | Last price |
| >b | String | Trading volume of the coin |
| >q | String | Trading volume of quote currency |
| >r | String | 24-hour fluctuations |
| >bd | String | Best bid price |
| >ak | String | Best ask price |
| >bv | String | Best bid volume |
| >av | String | Best ask volume |

## Push Example

```json
{
  "ch": "tickers",
  "ts": 1732178884994,
  "data": [
    {
      "s": "BTCUSDT",
      "la": "68650.9",
      "o": "69141.6",
      "h": "70319.9",
      "l": "68241.9",
      "b": "26295.3977",
      "q": "1823374525.0193",
      "r": "-0.7097029863",
      "bd": "68650.9",
      "ak": "68651",
      "bv": "0.9747",
      "av": "2.3606"
    },
    {
      "s": "ETHUSDT",
      "la": "2104.61",
      "o": "2128.49",
      "h": "2173.75",
      "l": "2086.79",
      "b": "945498.652",
      "q": "2018286647.13588",
      "r": "-1.1219221138",
      "bd": "2104.6",
      "ak": "2104.61",
      "bv": "27.789",
      "av": "7.905"
    }
  ]
}
```
