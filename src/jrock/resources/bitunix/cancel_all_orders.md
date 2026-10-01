# Cancel All Orders

Source: https://www.bitunix.com/api-docs/futures/trade/cancel_all_orders.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Cancel all orders. Successful interface response is not necessarily equal to success of the operation; use WebSocket push messages as accurate judgment.

## HTTP Request

- POST /api/v1/futures/trade/cancel_all_orders

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| successList | list | Successful order list |
| >id | string | Order id |
| >clientId | string | Client id |
| failureList | list | Failed order list |
| >id | string | Order id |
| >clientId | string | Client id |
| >errorMsg | string | Error message |
| >errorCode | string | Error code |

## Response Example

```json
{
  "code": 0,
  "data": {
    "successList": [
      {
        "orderId": "11111",
        "clientId": "22222"
      }
    ],
    "failureList": [
      {
        "orderId": "11112",
        "clientId": "22223",
        "errorMsg": "Order status error",
        "errorCode": 10013
      }
    ]
  },
  "msg": "Success"
}
```
