# Modify Order

Source: https://www.bitunix.com/api-docs/futures/trade/modify_order.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Modify pending order TP/SL and/or price/qty. Successful interface response is not necessarily equal to success of the operation; use WebSocket push messages as accurate judgment.

## HTTP Request

- POST /api/v1/futures/trade/modify_order

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| orderId | string | false | Either orderId or clientId required. orderId prevails if both entered. |
| clientId | string | false | Customize order ID. Either orderId or clientId required. orderId prevails if both entered. |
| qty | string | true | Amount (base coin) |
| price | string | true | Price of order. Required if orderType is LIMIT. |
| tpPrice | string | false | Take profit trigger price |
| tpStopType | string | false | Take profit trigger type: MARK_PRICE or LAST_PRICE |
| tpOrderType | string | false | Take profit trigger place order type: LIMIT or MARKET |
| tpOrderPrice | string | false | Take profit trigger place order price. Required if tpOrderType is LIMIT. |
| slPrice | string | false | Stop loss trigger price |
| slStopType | string | false | Stop loss trigger type: MARK_PRICE or LAST_PRICE |
| slOrderType | string | false | Stop loss trigger place order type: LIMIT or MARKET |
| slOrderPrice | string | false | Stop loss trigger place order price. Required if slOrderType is LIMIT. |

## Request example (query parameters or body)

```json
{
  "orderId": "1111",
  "symbol": "BTCUSDT",
  "price": "60000",
  "qty": "0.5",
  "tpPrice": "61000",
  "tpStopType": "MARK",
  "tpOrderType": "LIMIT",
  "tpOrderPrice": "61000.1"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| orderId | string | Order id |
| clientId | string | Client id |

## Response Example

```json
{
  "code": 0,
  "data": {
    "orderId": "11111",
    "clientId": "22222"
  },
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Tables use MARK_PRICE/LAST_PRICE and orderType; examples use MARK/LAST and type/source. modify_order example includes symbol absent from its request table. No guessed fields are sent by the engine. Table marks price always required; descriptive condition says LIMIT only. Generic validator conservatively requires the table field.
