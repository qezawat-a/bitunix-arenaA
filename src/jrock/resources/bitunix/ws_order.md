# order WebSocket channel

Source: https://www.bitunix.com/api-docs/futures/websocket/private/Order%20Channel.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Private: True

## Description

Subscribe order channel. Pushed when open/close orders are created/filled/canceled.

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |

## Push Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| ch | String | Channel name: order |
| ts | Int64 | Gateway send time in milliseconds; not business event time; do not confuse with ctime/mtime. |
| data | <Object> | Subscription data |
| >event | String | CREATE/UPDATE/CLOSE |
| >orderId | String | Order id |
| >symbol | String | Symbol |
| >positionType | String | Margin mode ISOLATION/CROSS |
| >positionMode | String | ONE_WAY/HEDGE |
| >side | String | BUY/SELL |
| >effect | String | Required for LIMIT. IOC immediate or cancel; FOK fill or kill; GTC(default); POST_ONLY. |
| >type | String | LIMIT/MARKET |
| >qty | String | Amount (base coin) |
| >price | String | Price of order; required for LIMIT |
| >ctime | String | ISO-8601 nanosecond create time, e.g. 2024-05-16T08:13:09.123456789Z |
| >mtime | String | ISO-8601 nanosecond last modify time; same as ctime. REST order APIs use millisecond integers. |
| >leverage | String | Leverage |
| >orderStatus | String | INIT/NEW/PART_FILLED/CANCELED/FILLED/PART_FILLED_CANCELED |
| >fee | String | Deducted transaction fees during position |
| >averagePrice | String | Average price |
| >dealAmount | String | Deal amount |
| >clientId | String | Client ID |
| >tpStopType | String | MARK_PRICE/LAST_PRICE |
| >tpPrice | String | Take profit trigger price |
| >tpOrderType | String | LIMIT/MARKET |
| >tpOrderPrice | String | Take profit order price LIMIT/MARKET (source wording) |
| >slStopType | String | MARK_PRICE/LAST_PRICE |
| >slPrice | String | Stop loss trigger price |
| >slOrderType | String | LIMIT/MARKET |
| >slOrderPrice | String | Stop loss order price LIMIT/MARKET (source wording) |
