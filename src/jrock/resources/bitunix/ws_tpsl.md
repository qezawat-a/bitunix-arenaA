# tpsl WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/private/Tp%20Sl%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: True

## Description

After private login succeeds, channel tpsl is pushed automatically. data is ALWAYS object. CLOSE alone is not a final state: read event together with status. FILLED means TP/SL triggered and CHILD ORDER PLACED, NOT child full fill. Child fills are order channel or REST. INIT/PENDING_CANCEL/TRIGGER_WAIT_PLACE are not pushed; PART_FILLED is not a TPSL status.

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel name: tpsl |
| ts | Int64 | Gateway send time, Unix milliseconds. Do not use to order business events. |
| data | <Object> | Always an object, not an array |
| >event | String | CREATE/UPDATE/CLOSE |
| >positionId | String | Position id |
| >orderId | String | Order id |
| >symbol | String | Symbol |
| >leverage | String | Leverage |
| >side | String | BUY/SELL |
| >positionMode | String | ONE_WAY/HEDGE |
| >status | String | NEW/CANCELED/SYSTEM_CANCELED/FILLED/FAILED |
| >ctime | String | ISO-8601 nanosecond create time, e.g. 2024-05-16T08:13:09.123456789Z. REST history uses milliseconds. |
| >type | String | LIMIT/MARKET |
| >tpQty | String | Take-profit quantity (base coin); omitted if unused |
| >slQty | String | Stop-loss quantity (base coin); omitted if unused. Never Boolean or JSON null; string 0 sent as string 0. |
| >tpStopType | String | MARK_PRICE/LAST_PRICE |
| >tpPrice | String | Take profit trigger price |
| >tpOrderType | String | LIMIT/MARKET |
| >tpOrderPrice | String | Take profit order price |
| >slStopType | String | MARK_PRICE/LAST_PRICE |
| >slPrice | String | Stop loss trigger price |
| >slOrderType | String | LIMIT/MARKET |
| >slOrderPrice | String | Stop loss order price |

## Semantics / upstream inconsistencies

Event/status: CREATE+NEW effective; UPDATE+NEW modified; CLOSE+CANCELED user canceled; CLOSE+SYSTEM_CANCELED system canceled; CLOSE+FILLED trigger succeeded/child placed; CLOSE+FAILED trigger failed.
