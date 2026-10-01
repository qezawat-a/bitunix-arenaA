# Get Leverage And Margin Mode

Source: https://www.bitunix.com/api-docs/futures/account/get_leverage_and_margin_mode.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get leverage and margin mode

## HTTP Request

- GET /api/v1/futures/account/get_leverage_margin_mode

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair |
| marginCoin | string | true | Margin coin |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "marginCoin": "USDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| symbol | string | Trading pair |
| marginCoin | string | Margin coin |
| leverage | int | Leverage |
| marginMode | string | ISOLATION or CROSS |

## Response Example

```json
{
  "code": 0,
  "data": {
    "symbol": "BTCUSDT",
    "marginCoin": "USDT",
    "leverage": 10,
    "marginMode": "ISOLATION"
  },
  "msg": "Success"
}
```
