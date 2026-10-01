# Change Position Mode

Source: https://www.bitunix.com/api-docs/futures/account/change_position_mode.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Adjust position mode between one-way and hedge across all symbol futures. May fail if any positions or orders exist.

## HTTP Request

- POST /api/v1/futures/account/change_position_mode

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| positionMode | string | true | Position mode: ONE_WAY or HEDGE |

## Request example (query parameters or body)

```json
{
  "positionMode": "HEDGE"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| positionMode | string | ONE_WAY or HEDGE |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "positionMode": "HEDGE"
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Source also gives error {"code":200014,"data":null,"msg":"Existing positions or orders, unable to switch holding mode."}; number conflicts with error-code table (20014).
