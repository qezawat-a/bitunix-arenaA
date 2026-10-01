# Get Pending Tp Sl Order

Source: https://www.bitunix.com/api-docs/futures/tp_sl/get_pending_tp_sl_order.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get pending TP/SL orders

## HTTP Request

- GET /api/v1/futures/tpsl/get_pending_orders

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |
| positionId | string | false | Position id |
| side | int32 | false | Order side |
| positionMode | int32 | false | Order position mode |
| skip | int64 | false | Skip order count; default: 0 |
| limit | int64 | false | Number of queries: maximum 100, default 10 |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| id | string | Order id |
| positionId | string | Position id |
| symbol | string | Coin pair |
| base | string | Base |
| quote | string | Quote |
| tpPrice | string | Take-profit trigger price |
| tpStopType | string | LAST_PRICE or MARK_PRICE |
| slPrice | string | Stop-loss trigger price |
| slStopType | string | LAST_PRICE or MARK_PRICE |
| tpOrderType | string | LIMIT or MARKET; default market |
| tpOrderPrice | string | Take-profit order price |
| slOrderType | string | LIMIT or MARKET; default market |
| slOrderPrice | string | Stop-loss order price |
| tpQty | string | Take-profit order quantity (base coin). At least one of tpQty or slQty is required. |
| slQty | string | Stop-loss order quantity (base coin). At least one of tpQty or slQty is required. |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "id": "123",
      "positionId": "12345678",
      "symbol": "BTCUSDT",
      "base": "BTC",
      "quote": "USDT",
      "tpPrice": "50000",
      "tpStopType": "LAST_PRICE",
      "slPrice": "70000",
      "slStopType": "LAST_PRICE",
      "tpOrderType": "LIMIT",
      "tpOrderPrice": "50000",
      "slOrderType": "LIMIT",
      "slOrderPrice": "70000",
      "tpQty": "0.01",
      "slQty": "0.01"
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

side and positionMode are documented as integers but enum mapping is not provided here; engine queries by positionId instead of guessing values.
