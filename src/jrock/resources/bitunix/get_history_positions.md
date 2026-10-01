# Get History Positions

Source: https://www.bitunix.com/api-docs/futures/position/get_history_positions.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get history positions

## HTTP Request

- GET /api/v1/futures/position/get_history_positions

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |
| positionId | string | false | Position id |
| startTime | int64 | false | Start timestamp (position create time). Unix timestamp in milliseconds, e.g. 1597026383085 |
| endTime | int64 | false | Start timestamp (source wording). Unix timestamp in milliseconds, e.g. 1597026683085 |
| skip | int64 | false | Skip order count; default: 0 |
| limit | int64 | false | Number of queries: maximum 100, default 10 |
| subAccountId | int64 | false | With subAccountUid: historical positions for that sub-account only. Without it: main account (source wording). |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| positionList | list | Position list |
| >positionId | string | Position id |
| >symbol | string | Trading pair |
| >maxQty | string | Max position amount |
| >entryPrice | string | Average entry price |
| >closePrice | string | Average close price |
| >liqQty | string | Liquidate quantity |
| >side | string | LONG or SHORT |
| >marginMode | string | ISOLATION or CROSS |
| >positionMode | string | ONE_WAY or HEDGE |
| >leverage | int32 | Leverage |
| >fee | string | Deducted transaction fees during position |
| >funding | string | Total funding fee during position |
| >realizedPNL | string | Realized PnL excluding funding and transaction fees |
| >liqPrice | string | Estimated liquidation price. <=0 means low risk and no liquidation price at this time. |
| >ctime | int64 | Create timestamp |
| >mtime | int64 | Latest modify timestamp |
| >subAccountId | int64 | Position account id |
| total | int64 | Total count |

## Response Example

```json
{
  "code": 0,
  "data": {
    "positionList": [
      {
        "positionId": "12345678",
        "symbol": "BTCUSDT",
        "maxQty": "0.5",
        "entryPrice": "60000",
        "closePrice": "61000",
        "liqQty": "0",
        "side": "LONG",
        "positionMode": "HEDGE",
        "marginMode": "ISOLATION",
        "leverage": 100,
        "fee": "0.1",
        "funding": "-0.2",
        "realizedPNL": "102.9",
        "liqPrice": "22209",
        "ctime": 1691382137448,
        "mtime": 1691382137448
      }
    ],
    "total": 12
  },
  "msg": "Success"
}
```
