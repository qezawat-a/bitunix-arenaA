# depth WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/public/depth%20channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: False

## Description

books: first full snapshot then changed depth; book1/book5/book15: respective levels pushed each time.

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | Operation: subscribe or unsubscribe |
| args | List<Object> | Yes | List of channels to request subscription |
| >ch | String | Yes | depth_books,depth_book1,depth_book5,depth_book15 |
| >symbol | String | Yes | Product ID e.g. ETHUSDT |

## Request Example

```json
{
  "op": "subscribe",
  "args": [
    {
      "symbol": "BTCUSDT",
      "ch": "depth_book1"
    }
  ]
}
```

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | Object | Channel name (source type) |
| symbol | String | Product ID |
| ts | Int64 | Timestamp |
| data | String | Subscription data (source type) |
| >a | List<String> | Seller depth |
| >b | List<String> | Buyer depth |

## Push Example

```json
{
  "ch": "depth_book1",
  "symbol": "BTCUSDT",
  "ts": 1775541541009,
  "data": {
    "b": [
      [
        "7403.89",
        "0.002"
      ]
    ],
    "a": [
      [
        "7405.96",
        "3.340"
      ]
    ]
  }
}
```

## Semantics / upstream inconsistencies

Tables type ch as Object, data as String; examples are string and object. For books apply deltas, zero qty removes price; rebuild on reconnect. No sequence ID/checksum is documented here; use REST refresh to recover uncertainty.
