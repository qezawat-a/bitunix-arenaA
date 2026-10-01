# Close All Position

Source: https://www.bitunix.com/api-docs/futures/trade/close_all_position.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 1 req/sec/uid

## Description

Close all positions

## HTTP Request

- POST /api/v1/futures/trade/close_all_position

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |

## Response Example

```json
{
  "code": 0,
  "data": "",
  "msg": "Success"
}
```
