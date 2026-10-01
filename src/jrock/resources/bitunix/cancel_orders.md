# Cancel Orders

Source: https://www.bitunix.com/api-docs/futures/trade/cancel_orders.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 5 req/sec/uid

## Description

Cancel orders. Successful interface response is not necessarily equal to success of the operation; use WebSocket push messages as accurate judgment.

## HTTP Request

- POST /api/v1/futures/trade/cancel_orders

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair |
| orderList | list | true | Order parameter list |
| orderId | string | false | Either orderId or clientId required. orderId prevails if both entered. These fields belong in orderList per example. |
| clientId | string | false | Customize order ID. Either orderId or clientId required. orderId prevails if both entered. These fields belong in orderList per example. |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "orderList": [
    {
      "orderId": "11111"
    },
    {
      "clientId": "22223"
    }
  ]
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

## Upstream inconsistencies / implementation notes

Request table does not indent orderId/clientId but example nests them. Validator follows the documented example's orderList structure; both raw rows are retained.
