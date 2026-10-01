# Cancel Tp Sl Order

Source: https://www.bitunix.com/api-docs/futures/tp_sl/cancel_tp_sl_order.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Cancel TP/SL order. Successful interface response is not necessarily equal to success of the operation; use WebSocket push messages as accurate judgment.

## HTTP Request

- POST /api/v1/futures/tpsl/cancel_order

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Coin pair |
| orderId | string | true | TP/SL Order ID |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "orderId": "12"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| orderId | string | TP/SL Order ID |

## Response Example

```json
{
  "code": 0,
  "data": {
    "orderId": "11111"
  },
  "msg": "Success"
}
```
