# Get History Orders

Source: https://www.bitunix.com/api-docs/futures/trade/get_history_orders.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get history orders; sort by create time descending

## HTTP Request

- GET /api/v1/futures/trade/get_history_orders

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |
| orderId | string | false | Order id |
| clientId | string | false | Client id |
| status | string | false | FILLED CANCELED PART_FILLED_CANCELED EXPIRED |
| type | string | false | LIMIT or MARKET; default all |
| startTime | int64 | false | Start timestamp. Unix timestamp in milliseconds, e.g. 1597026383085 |
| endTime | int64 | false | Start timestamp (source wording). Unix timestamp in milliseconds, e.g. 1597026683085 |
| skip | int64 | false | Skip order count; default: 0 |
| limit | int64 | false | Number of queries: maximum 100, default 10 |
| subAccountId | int64 | false | With subAccountUid: historical orders for sub-account only. Without it: main account (source wording). |
| queryCanceled | boolean | false | Default false. true: canceled only, last 3 days. false: excludes canceled, last 90 days. |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| orderList | list | Order list |
| >orderId | string | Order id |
| >symbol | string | Trading pair |
| >qty | string | Amount (base coin) |
| >tradeQty | string | Fill amount (base coin) |
| >positionMode | string | ONE_WAY or HEDGE |
| >marginMode | string | ISOLATION or CROSS |
| >leverage | int | Leverage |
| >price | string | Price of order. Required if orderType is LIMIT. |
| >side | string | Order direction BUY or SELL |
| >orderType | string | LIMIT: limit orders; MARKET: market orders |
| >effect | string | IOC immediate or cancel; FOK fill or kill; GTC good till canceled (default); POST_ONLY. Required for LIMIT. |
| >clientId | string | Customize order ID |
| >reduceOnly | boolean | Whether or not to just reduce the position |
| >status | string | INIT prepare; NEW pending; PART_FILLED partially filled; CANCELED canceled; FILLED all filled |
| >fee | string | Fee |
| >realizedPNL | string | Realized PnL |
| >tpPrice | string | Take profit trigger price |
| >tpStopType | string | MARK_PRICE or LAST_PRICE |
| >tpOrderType | string | LIMIT or MARKET |
| >tpOrderPrice | string | Take profit order price; required for LIMIT |
| >slPrice | string | Stop loss trigger price |
| >slStopType | string | MARK_PRICE or LAST_PRICE |
| >slOrderType | string | LIMIT or MARKET |
| >slOrderPrice | string | Stop loss order price; required for LIMIT |
| >ctime | int64 | Create timestamp |
| >mtime | int64 | Latest modify timestamp |
| >subAccountId | int64 | Order account id |
| total | int64 | Total count |

## Response Example

```json
{
  "code": 0,
  "data": {
    "orderList": [
      {
        "orderId": "11111",
        "qty": "1",
        "tradeQty": "0.5",
        "price": "60000",
        "symbol": "BTCUSDT",
        "positionMode": "HEDGE",
        "marginMode": "ISOLATION",
        "leverage": 15,
        "status": "CANCELED",
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
      }
    ],
    "total": 10
  },
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Tables use MARK_PRICE/LAST_PRICE and orderType; examples use MARK/LAST and type/source. modify_order example includes symbol absent from its request table. No guessed fields are sent by the engine.
