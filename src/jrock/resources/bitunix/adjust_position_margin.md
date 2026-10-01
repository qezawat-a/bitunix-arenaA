# Adjust Position Margin

Source: https://www.bitunix.com/api-docs/futures/account/adjust_position_margin.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 5 req/sec/uid

## Description

Add/reduce margin (isolated margin mode only)

## HTTP Request

- POST /api/v1/futures/account/adjust_position_margin

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair |
| marginCoin | string | true | Margin coin |
| amount | string | true | Margin amount; positive increases, negative decreases |
| side | string | false | Position side LONG or SHORT. Either side or positionId required. |
| positionId | string | false | Position id. Either side or positionId required. |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "amount": "-100",
  "marginCoin": "USDT",
  "side": "LONG"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| N/A |  |  |

## Response Example

```json
{
  "code": 0,
  "data": "",
  "msg": "Success"
}
```
