# Get Single Account

Source: https://www.bitunix.com/api-docs/futures/account/get_single_account.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get account details for marginCoin

## HTTP Request

- GET /api/v1/futures/account

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| marginCoin | string | true | Margin coin |

## Request example (query parameters or body)

```json
{
  "marginCoin": "USDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| marginCoin | string | Margin coin |
| available | string | Available quantity. This + crossUnrealizedPNL = actual maximum open amount. |
| frozen | string | Locked quantity of orders |
| margin | string | Locked quantity of positions |
| transfer | string | Maximum transferable amount |
| positionMode | string | ONE_WAY or HEDGE |
| crossUnrealizedPNL | string | Unrealized PnL for cross positions |
| isolationUnrealizedPNL | string | Unrealized PnL for isolated positions |
| bonus | string | Futures bonus |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "marginCoin": "USDT",
      "available": "1000",
      "frozen": "0",
      "margin": "10",
      "transfer": "1000",
      "positionMode": "HEDGE",
      "crossUnrealizedPNL": "2",
      "isolationUnrealizedPNL": "0",
      "bonus": "0"
    }
  ],
  "msg": "Success"
}
```
