# Get History Trades

Source: https://www.bitunix.com/api-docs/futures/trade/get_history_trades.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get history trades; sort by create time descending

## HTTP Request

- GET /api/v1/futures/trade/get_history_trades

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |
| orderId | string | false | Order id |
| positionId | string | false | Position id |
| startTime | int64 | false | Start timestamp. Unix timestamp in milliseconds, e.g. 1597026383085 |
| endTime | int64 | false | Start timestamp (source wording). Unix timestamp in milliseconds, e.g. 1597026683085 |
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
| tradeList | list | Trade list |
| >tradeId | string | Trade id |
| >orderId | string | Order id |
| >symbol | string | Trading pair |
| >qty | string | Amount (base coin) |
| >positionMode | string | ONE_WAY or HEDGE |
| >marginMode | string | ISOLATION or CROSS |
| >leverage | int | Leverage |
| >price | string | Order price. Required for LIMIT. |
| >side | string | Order direction BUY or SELL |
| >orderType | string | LIMIT or MARKET |
| >effect | string | IOC/FOK/GTC(default)/POST_ONLY. Required for LIMIT. |
| >clientId | string | Customize order ID |
| >reduceOnly | boolean | Whether or not to just reduce position |
| >fee | string | Fee |
| >realizedPNL | string | Realized PnL |
| >ctime | int64 | Create timestamp |
| >roleType | string | Trader tag: TAKER: maker; MAKER: maker (source wording) |
| total | int64 | Total count |

## Response Example

```json
{
  "code": 0,
  "data": {
    "tradeList": [
      {
        "tradeId": "123",
        "orderId": "11111",
        "qty": "1",
        "price": "60000",
        "symbol": "BTCUSDT",
        "positionMode": "HEDGE",
        "marginMode": "ISOLATION",
        "leverage": 15,
        "fee": "0.01",
        "realizedPNL": "1.78",
        "type": "LIMIT",
        "effect": "GTC",
        "reduceOnly": false,
        "clientId": "22222",
        "source": "api",
        "ctime": 1597026383085,
        "roleType": "TAKER"
      }
    ],
    "total": 10
  },
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Tables use MARK_PRICE/LAST_PRICE and orderType; examples use MARK/LAST and type/source. modify_order example includes symbol absent from its request table. No guessed fields are sent by the engine. roleType labels have an upstream typo; not corrected in transcription.
