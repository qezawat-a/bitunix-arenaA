# Get Depth

Source: https://www.bitunix.com/api-docs/futures/market/get_depth.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get future order book

## HTTP Request

- GET /api/v1/futures/market/depth

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | true | Trading pair, based on symbolName, e.g. BTCUSDT |
| limit | string | false | Fixed enumeration 1/5/15/50/max. max returns maximum gear. Actual depth returned if below requested limit. |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT",
  "limit": "max"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| asks.index[0] | string | Ask price |
| asks.index[1] | string | Ask amount |
| bids.index[0] | string | Bid price |
| bids.index[1] | string | Bid amount |

## Response Example

```json
{
  "code": 0,
  "data": {
    "asks": [
      [
        0.1001,
        0.1
      ],
      [
        0.1002,
        10
      ]
    ],
    "bids": [
      [
        0.1,
        1
      ],
      [
        0.0999,
        10.23
      ]
    ]
  },
  "msg": "Success"
}
```
