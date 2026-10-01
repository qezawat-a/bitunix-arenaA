# position WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/private/Position%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: True

## Description

Subscribe position channel. Pushed when open/close orders created, filled, canceled. Position WS lacks liqPrice and avgOpenPrice; reconcile REST rather than inventing them.

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel name: position |
| ts | Int64 | Timestamp |
| data | <Object> | Subscription data |
| >event | String | OPEN/UPDATE/CLOSE |
| >positionId | String | Position id |
| >marginMode | String | ISOLATION/CROSS |
| >positionMode | String | ONE_WAY/HEDGE |
| >side | String | SHORT/LONG |
| >leverage | String | Leverage |
| >margin | String | Margin |
| >ctime | String | Create time |
| >qty | String | Open position size |
| >symbol | String | Symbol |
| >realizedPNL | String | Realized PnL excluding funding and transaction fee |
| >unrealizedPNL | String | Unrealized PnL |
| >funding | String | Total funding fee during the position |
| >fee | String | Deducted transaction fees during the position |
