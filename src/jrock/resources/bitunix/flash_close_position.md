# Flash Close Position

Source: https://www.bitunix.com/api-docs/futures/trade/flash_close_position.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 5 req/sec/uid

## Description

Close position by position id

## HTTP Request

- POST /api/v1/futures/trade/flash_close_position

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| positionId | String | true | Position id |

## Request example (query parameters or body)

```json
{
  "positionId": "19848247723672"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| positionId | string | Position ID |

## Response Example

```json
{
  "code": 0,
  "data": {
    "positionId": "19848247723672"
  },
  "msg": "Success"
}
```
