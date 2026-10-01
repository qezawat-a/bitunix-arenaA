# balance WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/private/Balance%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: True

## Description

Balance

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel name: balance |
| ts | Int64 | Timestamp |
| data | <Object> |  |
| >coin | String | Coin |
| >available | String | Available |
| >frozen | String | frozen = isolationFrozen + crossFrozen |
| >isolationFrozen | String | Freeze on a per warehouse basis |
| >crossFrozen | String | Full warehouse entrusted freeze |
| >margin | String | Margin |
| >isolationMargin | String | Warehouse by warehouse margin |
| >crossMargin | String | Full warehouse margin |
| >expMoney | String | Experience money |
