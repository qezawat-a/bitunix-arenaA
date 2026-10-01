# Signature introduction

Source: https://www.bitunix.com/api-docs/futures/common/sign.html
Retrieved: 2026-10-01 UTC. Transcribed reference; navigation and duplicate Go example removed.
Official demo: https://github.com/BitunixOfficial/open-api/tree/main/Demo/Python
Official commit checked: 0be792c3a98a2706d22e5d1a9742f448f11f3347
User-provided example repository: https://github.com/qezawat-a/open-api/tree/main/Demo
The supplied `/Demo` URL should use `/tree/main/Demo` for GitHub browsing.

## REST public signature parameters (headers)

| Name | Type | Mandatory | Description |
| --- | --- | --- | --- |
| api-key | string | Y | Applied API key |
| nonce | string | Y | Random string, 32 bits (source wording; examples use 32 characters) |
| timestamp | string | Y | Current timestamp in milliseconds |
| sign | string | Y | Signature string |

1. Sort query parameters by key in ascending ASCII order; concatenate **key+value**, NOT URL-encoded `key=value&...`. Example `id1uid200`.
2. Compact body JSON with no formatting whitespace. The request body **must be byte-identical** to the signed body.
3. `digest = SHA256(nonce + timestamp + api-key + queryParams + body)`
4. `sign = SHA256(digest + secretKey)`

```python
import hashlib
nonce = "123456"
timestamp = "20241120123045"
api_key = "yourApiKey"
secret_key = "yourSecretKey"
query_params = "id1uid200"
body = '{"uid":"2899","arr":[{"id":1,"name":"maple"},{"id":2,"name":"lily"}]}'
digest = hashlib.sha256((nonce + timestamp + api_key + query_params + body).encode()).hexdigest()
sign = hashlib.sha256((digest + secret_key).encode()).hexdigest()
```

## General WebSocket signature section (upstream)

| Name | Type | Mandatory | Description |
| --- | --- | --- | --- |
| apiKey | string | Y | API key |
| timestamp | string | Y | Timestamp |
| nonce | string | Y | Random string |
| sign | string | Y | Signature string |

Source text: sort all params except `sign` in ascending ASCII order, removing spaces.
Example: `apiKey9a25209b66004da404d9ddcb48d1e11fnonce123456symbolBTCtimestamp1724285700000`.
`digest=SHA256(nonce+timestamp+apiKey+params)` then `sign=SHA256(digest+secretKey)`.

**Conflict:** private login in websocket/prepare/WebSocket.html and official demo uses **seconds** and
`SHA256(nonce+seconds+apiKey)` then `SHA256(digest+secret)` without appended params. See websocket_prepare.md.
Do not mix REST millisecond timestamps with private login seconds.
