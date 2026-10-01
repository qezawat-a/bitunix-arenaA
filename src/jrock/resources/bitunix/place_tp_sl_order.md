# Place Tp Sl Order

Source: https://www.bitunix.com/api-docs/futures/tp_sl/place_tp_sl_order.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Place TP/SL order

## HTTP Request

- POST /api/v1/futures/tpsl/place_order

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair |
| positionId | string | true | Position ID associated with TP/SL |
| tpPrice | string | false | Take-profit trigger price. At least one of tpPrice or slPrice is required. |
| tpStopType | string | false | Take-profit trigger type: LAST_PRICE, MARK_PRICE. Default is market price. |
| slPrice | string | false | Stop-loss trigger price. At least one of tpPrice or slPrice is required. |
| slStopType | string | false | Stop-loss trigger type: LAST_PRICE, MARK_PRICE. Default is market price. |
| tpOrderType | string | false | Take-profit order type LIMIT or MARKET. Default is market. |
| tpOrderPrice | string | false | Take-profit order price |
| slOrderType | string | false | Stop-loss order type LIMIT or MARKET. Default is market. |
| slOrderPrice | string | false | Stop-loss order price |
| tpQty | string | false | Take-profit order quantity (base coin). At least one of tpQty or slQty is required. |
| slQty | string | false | Stop-loss order quantity (base coin). At least one of tpQty or slQty is required. |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "positionId": "111",
  "tpPrice": "12",
  "tpStopType": "LAST_PRICE",
  "slPrice": "9",
  "slStopType": "LAST_PRICE",
  "tpOrderType": "LIMIT",
  "tpOrderPrice": "11",
  "slOrderType": "LIMIT",
  "slOrderPrice": "8",
  "tpQty": "1",
  "slQty": "1"
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
