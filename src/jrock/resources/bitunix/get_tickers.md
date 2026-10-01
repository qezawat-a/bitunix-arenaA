# Get Tickers

Source: https://www.bitunix.com/api-docs/futures/market/get_tickers.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get future trading pair tickers

## HTTP Request

- GET /api/v1/futures/market/tickers

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbols | string | false | Trading pairs, based on symbolName, i.e. BTCUSDT,ETHUSDT,XRPUSDT |

## Request example (query parameters or body)

```json
{
  "symbols": "BTCUSDT,ETHUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| symbol | string | Coin pair name i.e. BTCUSDT |
| markPrice | string | Mark price |
| lastPrice | string | Last price |
| open | string | Entry price of last 24 hours |
| last | string | Last price |
| quoteVol | string | Trading volume of the coin (last 24 hours), source wording |
| baseVol | string | Trading volume of last 24 hours |
| high | string | 24-hour high |
| low | string | 24-hour low |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "symbol": "BTCUSDT",
      "markPrice": "57892.1",
      "lastPrice": "57891.2",
      "open": "6.31",
      "last": "6.31",
      "quoteVol": "0",
      "baseVol": "0",
      "high": "6.31",
      "low": "6.31"
    },
    {
      "symbol": "ETHUSDT",
      "markPrice": "2000",
      "lastPrice": "2020.1",
      "open": "6.31",
      "last": "6.31",
      "quoteVol": "0",
      "baseVol": "0",
      "high": "6.31",
      "low": "6.31"
    }
  ],
  "msg": "Success"
}
```
