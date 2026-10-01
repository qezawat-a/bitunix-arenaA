# Get Funding Rate History

Source: https://www.bitunix.com/api-docs/futures/market/get_funding_rate_history.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get historical funding rate

## HTTP Request

- GET /api/v1/futures/market/get_funding_rate_history

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair, based on symbolName, e.g. BTCUSDT |
| starTime | int64 | false | Start timestamp (funding settle time). Unix timestamp in milliseconds, e.g. 1597026383085. |
| endTime | int64 | fasle | End timestamp (funding settle time). Unix timestamp in milliseconds, e.g. 1597026383085. |
| limit | int32 | false | Default: 100; maximum: 200 |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "limit": 10
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| markPrice | string | Mark price |
| fundingRate | string | Funding rate |
| fundingTime | int64 | Funding timestamp |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "fundingRate": "-0.00001191",
      "fundingTime": "1772449200000",
      "markPrice": "66286.6"
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Source spells starTime (not startTime) and fasle (not false); retained exactly in schema. Confirm with exchange if rejected.
