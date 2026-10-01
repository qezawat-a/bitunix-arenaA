# WebSocket Preparing for Access

Source: https://www.bitunix.com/api-docs/futures/websocket/prepare/WebSocket.html
Retrieved: 2026-10-01 UTC. Content transcription, navigation removed.

WebSocket is a full-duplex protocol: server/client can initiate data transmission; no repeated TCP connections.
Official demos: https://github.com/BitunixOfficial/open-api
WebSockets are strongly recommended for market information and depth.

| Domain | Usage |
| --- | --- |
| wss://fapi.bitunix.com/public/ | Public channels |
| wss://fapi.bitunix.com/private/ | Private channels |

## Limits

Maximum **5 messages/sec**, including PING frames, PONG frames, JSON subscribe/unsubscribe.
Exceeding limits disconnects; repeatedly disconnected IPs can be blocked.
Maximum **300 subscriptions/connection**. J+rock sends application messages <= 3/sec,
disables library-initiated automatic pings, and uses JSON heartbeat as documented.
Unsolicited control-frame responses are managed by the WebSocket library.

## Ping

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | ping |
| ping | int64 | Yes | Unix timestamp in seconds |

Request: `{"op":"ping","ping":1732519687}`
Response: `{"op":"ping","pong":1732519687,"ping":1732519690}`

## Subscribe / unsubscribe

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | subscribe / unsubscribe |
| args | Array | Yes | Channel list |
| >ch | String | Yes | Channel name |
| >symbol | String | No | Instrument ID |

Subscribe example:
```json
{"op":"subscribe","args":[{"symbol":"BTCUSDT","ch":"market_kline_1min"},{"symbol":"BTCUSDT","ch":"depth_books"}]}
```
The preparation page unsubscribe example uses `channel` instead of `ch`; channel-specific request
tables say `ch`. J+rock uses `ch` and preserves this conflict here.

## Login

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| op | String | Yes | login |
| args | Array | Yes | Login arguments |
| >apiKey | String | Yes | API key |
| >timestamp | Int | Yes | Unix timestamp in seconds |
| >nonce | String | Yes | Random string |
| >sign | String | Yes | Signature string |

```json
{"op":"login","args":[{"apiKey":"your-api-key","timestamp":1747402389,"nonce":"your-random-nonce","sign":"your-signature"}]}
```

Create keys at https://www.bitunix.com/account/apiManagement . Public data needs no key.
Private operations require signatures. API key/secret leakage can cause asset loss; delete compromised keys.

Login signature, as demonstrated on this page and official Python WebSocket demo:
```python
import hashlib
first = hashlib.sha256((nonce + str(timestamp_seconds) + api_key).encode()).hexdigest()
sign = hashlib.sha256((first + secret_key).encode()).hexdigest()
```
The separate common/sign page describes a different WebSocket request-signing formulation.
This client implements **private login**, matching this preparation page and pinned official Python demo;
it does not guess an additional WebSocket trading RPC.
