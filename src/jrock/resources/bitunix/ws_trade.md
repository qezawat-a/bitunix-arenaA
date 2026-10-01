# trade WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/public/Trade%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: False

## Description

Get public trade data

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | Operation: subscribe or unsubscribe |
| args | List<Object> | Yes | List of channels to request subscription |
| >symbol | String | Yes | Product ID e.g. ETHUSDT |
| >ch | String | Yes | Channel trade |

## Request Example

```json
{
  "op": "subscribe",
  "args": [
    {
      "symbol": "BTCUSDT",
      "ch": "trade"
    }
  ]
}
```

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel trade |
| symbol | String | Symbol e.g. ETHUSDT |
| ts | String | Timestamp |
| data | List<Object> | Data |
| >p | String | Filled price |
| >v | String | Filled amount |
| >s | String | Filled side sell/buy |
| >t | String | Timestamp |

## Push Example

```json
{
  "ch": "trade",
  "symbol": "BTCUSDT",
  "ts": 1775540872598,
  "data": [
    {
      "t": "2026-04-07T05:47:52Z",
      "p": "68621.4",
      "v": "0.7142",
      "s": "buy"
    },
    {
      "t": "2026-04-07T05:47:52Z",
      "p": "68621.4",
      "v": "0.0018",
      "s": "sell"
    }
  ]
}
```
