# Get History Tp Sl Order

Source: https://www.bitunix.com/api-docs/futures/tp_sl/get_history_tp_sl_order.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get history TP/SL orders

## HTTP Request

- GET /api/v1/futures/tpsl/get_history_orders

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |
| side | int32 | false | Order side |
| positionMode | int32 | false | Order position mode |
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
| orderList | list | TP/SL order list |
| >id | string | Order id |
| >positionId | string | Position id |
| >symbol | string | Coin pair |
| >base | string | Base |
| >quote | string | Quote |
| >tpPrice | string | Take-profit trigger price |
| >tpStopType | string | LAST_PRICE or MARK_PRICE |
| >slPrice | string | Stop-loss trigger price |
| >slStopType | string | LAST_PRICE or MARK_PRICE |
| >tpOrderType | string | LIMIT or MARKET; default market |
| >tpOrderPrice | string | Take-profit order price |
| >slOrderType | string | LIMIT or MARKET; default market |
| >slOrderPrice | string | Stop-loss order price |
| >tpQty | string | Take-profit order quantity (base coin). At least one of tpQty or slQty is required. |
| >slQty | string | Stop-loss order quantity (base coin). At least one of tpQty or slQty is required. |
| >status | string | TP/SL order status |
| >ctime | int64 | Create timestamp |
| >triggerTime | int64 | Trigger timestamp |
| total | int64 | Total |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "positionId": "12345678",
      "symbol": "BTCUSDT",
      "qty": "0.5",
      "entryValue": "30000",
      "side": "LONG",
      "positionMode": "HEDGE",
      "marginMode": "ISOLATION",
      "leverage": 100,
      "fee": "0.1",
      "funding": "-0.2",
      "realizedPNL": "102.9",
      "margin": "300",
      "unrealizedPNL": "1.5",
      "liqPrice": "22209",
      "marginRate": "0.01",
      "ctime": 1691382137448,
      "mtime": 1691382137448
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Response example is a positions array, inconsistent with its orderList/total response table. Adapter preserves raw response; no lossy guessed conversion.
