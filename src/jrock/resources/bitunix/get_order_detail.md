# Get Order Detail

Source: https://www.bitunix.com/api-docs/futures/trade/get_order_detail.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get order detail

## HTTP Request

- GET /api/v1/futures/trade/get_order_detail

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| orderId | string | false | At least one of orderId/clientId is required |
| clientId | string | false | At least one of orderId/clientId is required |

## Request example (query parameters or body)

```json
{
  "orderId": "12345"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| orderId | string | Order id |
| symbol | string | Trading pair |
| qty | string | Amount (base coin) |
| tradeQty | string | Fill amount (base coin) |
| positionMode | string | ONE_WAY or HEDGE |
| marginMode | string | ISOLATION or CROSS |
| leverage | int | Leverage |
| price | string | Price of order. Required if orderType is LIMIT. |
| side | string | Order direction BUY or SELL |
| orderType | string | LIMIT: limit orders; MARKET: market orders |
| effect | string | IOC immediate or cancel; FOK fill or kill; GTC good till canceled (default); POST_ONLY. Required for LIMIT. |
| clientId | string | Customize order ID |
| reduceOnly | boolean | Whether or not to just reduce the position |
| status | string | INIT prepare; NEW pending; PART_FILLED partially filled; CANCELED canceled; FILLED all filled |
| fee | string | Fee |
| realizedPNL | string | Realized PnL |
| tpPrice | string | Take profit trigger price |
| tpStopType | string | MARK_PRICE or LAST_PRICE |
| tpOrderType | string | LIMIT or MARKET |
| tpOrderPrice | string | Take profit order price; required for LIMIT |
| slPrice | string | Stop loss trigger price |
| slStopType | string | MARK_PRICE or LAST_PRICE |
| slOrderType | string | LIMIT or MARKET |
| slOrderPrice | string | Stop loss order price; required for LIMIT |
| ctime | int64 | Create timestamp |
| mtime | int64 | Latest modify timestamp |

## Response Example

```json
{
  "code": 0,
  "data": {
    "orderId": "11111",
    "qty": "1",
    "tradeQty": "0.5",
    "price": "60000",
    "symbol": "BTCUSDT",
    "positionMode": "HEDGE",
    "marginMode": "ISOLATION",
    "leverage": 15,
    "status": "PART_FILLED",
    "fee": "0.01",
    "realizedPNL": "1.78",
    "type": "LIMIT",
    "effect": "GTC",
    "reduceOnly": false,
    "clientId": "22222",
    "tpPrice": "61000",
    "tpStopType": "MARK",
    "tpOrderType": "LIMIT",
    "tpOrderPrice": "61000.1",
    "slPrice": "59000",
    "slStopType": "MARK",
    "slOrderType": "LIMIT",
    "slOrderPrice": "59000.1",
    "source": "api",
    "ctime": 1597026383085,
    "mtime": 1597026383085
  },
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Tables use MARK_PRICE/LAST_PRICE and orderType; examples use MARK/LAST and type/source. modify_order example includes symbol absent from its request table. No guessed fields are sent by the engine.
