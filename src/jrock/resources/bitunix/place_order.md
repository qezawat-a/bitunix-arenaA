# Place Order

Source: https://www.bitunix.com/api-docs/futures/trade/place_order.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Place order

## HTTP Request

- POST /api/v1/futures/trade/place_order

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair |
| qty | string | true | Amount (base coin) |
| price | string | false | Price of the order. Required if orderType is LIMIT. |
| side | string | true | Order direction: BUY or SELL |
| tradeSide | string | true | Only required in hedge-mode. Open long BUY/OPEN; open short SELL/OPEN; close long BUY/CLOSE; close short SELL/CLOSE. |
| positionId | string | false | Position ID. Required when tradeSide is CLOSE. |
| orderType | string | true | LIMIT: limit orders; MARKET: market orders |
| effect | string | false | Order expiration. Required if orderType is LIMIT. IOC immediate or cancel; FOK fill or kill; GTC good till canceled (default); POST_ONLY. |
| clientId | string | false | Customize order ID |
| reduceOnly | boolean | false | Whether or not to just reduce the position |
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
  "symbol": "BTCUSDT",
  "side": "BUY",
  "price": "60000",
  "qty": "0.5",
  "positionId": "111",
  "tradeSide": "CLOSE",
  "orderType": "LIMIT",
  "reduceOnly": false,
  "effect": "GTC",
  "clientId": "1110000aaa",
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

Tables use MARK_PRICE/LAST_PRICE and orderType; examples use MARK/LAST and type/source. modify_order example includes symbol absent from its request table. No guessed fields are sent by the engine.
