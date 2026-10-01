# Change Margin Mode

Source: https://www.bitunix.com/api-docs/futures/account/change_margin_mode.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Cannot be used while user has an open position or order

## HTTP Request

- POST /api/v1/futures/account/change_margin_mode

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| marginMode | string | true | ISOLATION or CROSS |
| symbol | string | true | Trading pair |
| marginCoin | string | true | Margin coin |

## Request example (query parameters or body)

```json
{
  "marginMode": "ISOLATION",
  "symbol": "BTCUSDT",
  "marginCoin": "USDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| marginMode | string | ISOLATION or CROSS |
| symbol | string | Trading pair |
| marginCoin | string | Margin coin |

## Response Example

```json
{
  "code": 0,
  "data": {
    "marginCoin": "USDT",
    "symbol": "BTCUSDT",
    "marginMode": "ISOLATION"
  },
  "msg": "Success"
}
```
