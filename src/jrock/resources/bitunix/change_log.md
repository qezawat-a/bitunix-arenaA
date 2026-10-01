# Change Log
Source: https://www.bitunix.com/api-docs/futures/log/change_log.html
Retrieved: 2026-10-01 UTC. Content transcription; navigation removed.

## 2026-06-15
### WebSocket Connection Limits
Added limits under WebSocket Preparing for Access.
- Maximum **5 messages/second**.
- Includes PING frames, PONG frames, JSON subscribe/unsubscribe.
- Exceeding limits disconnects.
- Repeatedly disconnected IPs may be blocked.
