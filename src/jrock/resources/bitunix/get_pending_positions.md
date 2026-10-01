# Get Pending Positions

Source: https://www.bitunix.com/api-docs/futures/position/get_pending_positions.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/uid

## Description

Get pending positions

## HTTP Request

- GET /api/v1/futures/position/get_pending_positions

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbol | string | false | Trading pair |
| positionId | string | false | Position id |
| subAccountId | int64 | false | With subAccountUid: positions for that sub-account only. Without subAccountUid: main account and all sub-accounts the current key can access (source wording). |
| includeSubAccounts | bool | false | Enable or disable sub-account query |

## Request example (query parameters or body)

```json
{
  "symbol": "BTCUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| positionId | string | Position id |
| symbol | string | Trading pair |
| qty | string | Position amount |
| entryValue | string | Available amount for positions |
| side | string | LONG or SHORT |
| marginMode | string | ISOLATION or CROSS |
| positionMode | string | ONE_WAY or HEDGE |
| leverage | int32 | Leverage |
| fee | string | Deducted transaction fees during position |
| funding | string | Total funding fee during position |
| realizedPNL | string | Realized PnL excluding funding and transaction fee |
| margin | string | Locked asset of position |
| unrealizedPNL | string | Unrealized PnL |
| liqPrice | string | Estimated liquidation price. <=0 means low risk and no liquidation price at this time. |
| marginRate | string | Margin ratio |
| avgOpenPrice | string | Average open price |
| ctime | int64 | Create timestamp |
| mtime | int64 | Latest modify timestamp |
| subAccountId | int64 | Position account id |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "positionId": "12345678",
      "symbol": "BTCUSDT",
      "qty": "0.5",
      "entryValue": "30000",
      "side": "LONG",
      "positionMode": "HEDGE",
      "marginMode": "ISOLATION",
      "leverage": 100,
      "fee": "0.1",
      "funding": "-0.2",
      "realizedPNL": "102.9",
      "margin": "300",
      "unrealizedPNL": "1.5",
      "liqPrice": "22209",
      "marginRate": "0.01",
      "avgOpenPrice": "1.0",
      "ctime": 1691382137448,
      "mtime": 1691382137448
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

Descriptions refer to subAccountUid but actual parameter row is subAccountId. Engine includes includeSubAccounts=false to avoid managing sub-accounts.
