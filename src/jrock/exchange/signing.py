from __future__ import annotations

import hashlib
import json
import secrets
import time


def wire_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def query_signature(params: dict) -> str:
    return "".join(key + wire_value(value) for key, value in sorted(params.items()))


def compact_body(params: dict) -> str:
    # No formatting whitespace; preserve spaces INSIDE values. Sign exactly these bytes.
    return json.dumps(params, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sign(api_key: str, secret: str, nonce: str, timestamp: str, query: str = "", body: str = "") -> str:
    digest = hashlib.sha256((nonce + timestamp + api_key + query + body).encode()).hexdigest()
    return hashlib.sha256((digest + secret).encode()).hexdigest()


def rest_headers(api_key: str, secret: str, params: dict, body: str) -> dict:
    nonce, timestamp = secrets.token_hex(16), str(int(time.time() * 1000))
    return {"api-key": api_key, "nonce": nonce, "timestamp": timestamp,
            "sign": sign(api_key, secret, nonce, timestamp, query_signature(params), body),
            "Content-Type": "application/json", "language": "en-US"}


def websocket_login(api_key: str, secret: str) -> dict:
    timestamp, nonce = int(time.time()), secrets.token_hex(16)
    return {"op": "login", "args": [{"apiKey": api_key, "timestamp": timestamp, "nonce": nonce,
             "sign": sign(api_key, secret, nonce, str(timestamp))}]}
