# Change Leverage

Source: https://www.bitunix.com/api-docs/futures/account/change_leverage.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Adjust leverage on given symbol

## HTTP Request

- POST /api/v1/futures/account/change_leverage

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| marginCoin | string | true | Margin coin |
| symbol | string | true | Trading pair |
| leverage | int | true | Leverage |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "leverage": 12,
  "marginCoin": "USDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| marginCoin | string | Margin coin |
| symbol | string | Trading pair |
| leverage | int | Leverage |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "marginCoin": "USDT",
      "leverage": 12,
      "symbol": "BTCUSDT"
    }
  ],
  "msg": "Success"
}
```
