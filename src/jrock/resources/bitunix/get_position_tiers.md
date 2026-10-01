# Get Position Tiers

Source: https://www.bitunix.com/api-docs/futures/position/get_position_tiers.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get position tiers

## HTTP Request

- GET /api/v1/futures/position/get_position_tiers

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair, based on symbolName, e.g. BTCUSDT |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| symbol | string | Trading pair |
| level | int32 | Level |
| startValue | string | Minimum value |
| endValue | string | Maximum value |
| leverage | int32 | Leverage |
| maintenanceMarginRate | string | Maintenance margin rate for position quantity tier. Below this rate triggers forced partial or full liquidation. |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "symbol": "BTCUSDT",
      "level": 1,
      "startValue": "0",
      "endValue": "50000",
      "leverage": 125,
      "maintenanceMarginRate": "0.004"
    },
    {
      "symbol": "BTCUSDT",
      "level": 2,
      "startValue": "50000",
      "endValue": "200000",
      "leverage": 100,
      "maintenanceMarginRate": "0.005"
    }
  ],
  "msg": "Success"
}
```
