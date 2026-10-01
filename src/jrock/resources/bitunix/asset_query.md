# Asset Query

Source: https://www.bitunix.com/api-docs/futures/copyTrading/asset/asset_query.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Asset query

## HTTP Request

- GET /api/v1/cp/asset/query

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |

## Request example (query parameters or body)

```json
{}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| available | string | Futures available |
| maxTransfer | string | Maximum transfer amount |

## Response Example

```json
{
  "code": 0,
  "data": {
    "available": "54.20916",
    "maxTransfer": "52.20916"
  },
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Source response has additional outer success:true and msg:"result.success".
