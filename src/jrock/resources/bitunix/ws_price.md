# price WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/public/MarketPrice%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: False

## Description

Market price channel

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | Operation: subscribe or unsubscribe |
| args | List<Object> | Yes | List of channels to request subscription |
| >symbol | String | Yes | Product ID e.g. ETHUSDT |
| >ch | String | Yes | Channel price |

## Request Example

```json
{
  "op": "subscribe",
  "args": [
    {
      "symbol": "BTCUSDT",
      "ch": "price"
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
| >mp | String | Market price |
| >ip | String | Index price |
| >fr | String | Funding rate |
| >ft | String | Funding rate settlement time |
| >nft | String | Next funding rate settlement time |

## Push Example

```json
{
  "ch": "price",
  "symbol": "BNBUSDT",
  "ts": 1732178884994,
  "data": {
    "ip": "0.0010",
    "mp": "10000",
    "fr": "0.013461",
    "ft": "2024-12-04T11:00:00Z",
    "nft": "2024-12-04T12:00:00Z"
  }
}
```

## Semantics / upstream inconsistencies

Table says data List<String>, example is object; preserve received format.
