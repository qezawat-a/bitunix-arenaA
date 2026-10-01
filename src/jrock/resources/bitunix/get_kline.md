# Get Kline

Source: https://www.bitunix.com/api-docs/futures/market/get_kline.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get future kline history

## HTTP Request

- GET /api/v1/futures/market/kline

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair, based on symbolName, e.g. BTCUSDT |
| startTime | int64 | false | Query k-lines after this time; Unix timestamp in milliseconds, e.g. 1672410780000 |
| endTime | int64 | false | Query k-lines before this time; Unix timestamp in milliseconds, e.g. 1672410780000 |
| interval | string | true | 1m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M |
| limit | int | false | Default 100; maximum 200 |
| type | string | false | Kline type LAST_PRICE or MARK_PRICE; default LAST_PRICE |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "startTime": 1,
  "endTime": 10234,
  "interval": "15m"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| open | string | Open price |
| high | string | High price |
| low | string | Low price |
| close | string | Close price |
| quoteVol | string | Trading amount (quote currency turnover) for kline period |
| baseVol | string | Trading volume (base coin) for kline period |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "open": "60000",
      "high": "60001",
      "close": "60000",
      "low": "59989.2",
      "time": 111111,
      "quoteVol": "1",
      "baseVol": "60000",
      "type": "LAST_PRICE"
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Response example has time and type absent from table. 3m is NOT documented: constructed locally from complete closed 1m candles.
