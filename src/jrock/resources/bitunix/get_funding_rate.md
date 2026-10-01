# Get Funding Rate

Source: https://www.bitunix.com/api-docs/futures/market/get_funding_rate.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get current funding rate of the contract

## HTTP Request

- GET /api/v1/futures/market/funding_rate

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
| symbol | string | Coin pair |
| markPrice | decimal | Mark price |
| lastPrice | decimal | Last price |
| indexPrice | decimal | Index price |
| fundingRate | decimal | Current funding rates |
| nextFundingTime | int64 | Next funding settlement time (milliseconds) |
| fundingInterval | int32 | Funding settlement interval (hours) |
| maxFundingRate | decimal | Max current funding rate |
| minFundingRate | decimal | Min current funding rate |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "symbol": "BTCUSDT",
      "markPrice": "60000",
      "lastPrice": "60001",
      "indexPrice": "60001",
      "fundingRate": "0.0005",
      "fundingInterval": 8,
      "nextFundingTime": "1770710400000",
      "maxFundingRate": "0.3",
      "minFundingRate": "-0.3"
    }
  ],
  "msg": "Success"
}
```
