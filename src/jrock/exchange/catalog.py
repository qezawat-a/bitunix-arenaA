from __future__ import annotations

import hashlib
import json
from importlib.resources import files


class Documentation:
    def __init__(self):
        self.root = files("jrock").joinpath("resources", "bitunix")
        self.rest = json.loads(self.root.joinpath("rest_catalog.json").read_text())
        self.ws = json.loads(self.root.joinpath("ws_catalog.json").read_text())
        self.errors = json.loads(self.root.joinpath("error_codes.json").read_text())
        self.manifest = json.loads(self.root.joinpath("manifest.json").read_text())

    def read(self, name: str) -> str:
        doc = next((d for d in self.manifest["documents"] if d["id"] == name), None)
        if not doc:
            raise ValueError("Documentation not found; use bitunix_docs with an empty query for the index")
        return self.root.joinpath(doc["file"]).read_text()

    def search(self, query: str) -> list[dict]:
        query = query.lower()
        return [{"id": d["id"], "url": d["url"]} for d in self.manifest["documents"]
                if not query or query in d["id"].lower() or query in self.root.joinpath(d["file"]).read_text().lower()]

    def verify(self) -> list[str]:
        return [d["id"] for d in self.manifest["documents"]
                if hashlib.sha256(self.root.joinpath(d["file"]).read_bytes()).hexdigest() != d["sha256"]]

    def endpoint(self, name: str) -> dict:
        if name not in self.rest:
            raise ValueError("Unknown documented Bitunix endpoint")
        return self.rest[name]

    def validate(self, name: str, params: dict) -> None:
        if not isinstance(params, dict):
            raise ValueError("Request parameters must be an object")
        ep = self.endpoint(name)
        top = [p for p in ep["parameters"] if not p["name"].startswith(">")]
        nested = [p for p in ep["parameters"] if p["name"].startswith(">")]
        if name == "cancel_orders":
            # The request example resolves an indentation omission in its table.
            nested = [{**p, "name": ">" + p["name"]} for p in top if p["name"] in {"orderId", "clientId"}]
            top = [p for p in top if p["name"] not in {"orderId", "clientId"}]
        self._validate_fields(params, top)
        if nested:
            values = params.get("orderList")
            if not isinstance(values, list) or not values:
                raise ValueError("orderList must be a non-empty array")
            if name == "batch_order" and len(values) > 5:
                raise ValueError("Batch order maximum length is 5")
            for value in values:
                self._validate_fields(value, [{**p, "name": p["name"][1:]} for p in nested])
                self._conditional(name, value)
        self._conditional(name, params)

    @staticmethod
    def _validate_fields(values: dict, fields: list[dict]) -> None:
        if not isinstance(values, dict):
            raise ValueError("Nested order must be an object")
        allowed = {p["name"] for p in fields}
        if unknown := set(values) - allowed:
            raise ValueError("Undocumented parameters: " + ", ".join(sorted(unknown)))
        for p in fields:
            key = p["name"]
            # Description constrains tradeSide to hedge mode, despite table required=true.
            if p["required"] and key not in values and key != "tradeSide":
                raise ValueError(f"Missing required parameter: {key}")
            if key not in values:
                continue
            v = values[key]
            kind = p["type"].lower()
            if kind in {"string"} and not isinstance(v, str):
                raise ValueError(f"{key} must be a string (including decimal quantities/prices)")
            if kind.startswith("int") or kind == "long":
                if not isinstance(v, int) or isinstance(v, bool):
                    raise ValueError(f"{key} must be an integer")
            if kind in {"bool", "boolean"} and not isinstance(v, bool):
                raise ValueError(f"{key} must be a boolean")
            if kind == "list" and not isinstance(v, list):
                raise ValueError(f"{key} must be a list")
            if isinstance(v, str) and not v:
                raise ValueError(f"{key} cannot be empty")

    @staticmethod
    def _conditional(name: str, p: dict) -> None:
        if name in {"cancel_orders", "get_order_detail", "modify_order"} and "orderList" not in p:
            if not (p.get("orderId") or p.get("clientId")):
                raise ValueError("orderId or clientId required")
        if name == "adjust_position_margin" and not (p.get("side") or p.get("positionId")):
            raise ValueError("side or positionId required")
        if name in {"place_tp_sl_order", "modify_tp_sl_order", "place_position_tp_sl_order", "modify_position_tp_sl_order"}:
            if not (p.get("tpPrice") or p.get("slPrice")):
                raise ValueError("tpPrice or slPrice required")
            if name in {"place_tp_sl_order", "modify_tp_sl_order"}:
                if not (p.get("tpQty") or p.get("slQty")):
                    raise ValueError("tpQty or slQty required")
                if p.get("tpPrice") and not p.get("tpQty"):
                    raise ValueError("tpQty required with tpPrice")
                if p.get("slPrice") and not p.get("slQty"):
                    raise ValueError("slQty required with slPrice")
        for prefix in ("tp", "sl"):
            if p.get(prefix + "OrderType") == "LIMIT" and not p.get(prefix + "OrderPrice"):
                raise ValueError(prefix + "OrderPrice required for LIMIT")
        if p.get("orderType") == "LIMIT" and not p.get("price"):
            raise ValueError("price required for LIMIT")
        if p.get("tradeSide") == "CLOSE" and not p.get("positionId"):
            raise ValueError("positionId required for CLOSE")
        if name == "get_kline" and p.get("interval") not in {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}:
            raise ValueError("Undocumented REST interval; construct 3m from 1m candles")
        if "limit" in p:
            maximum = 200 if name in {"get_kline", "get_funding_rate_history"} else 100
            if name == "get_depth":
                if p["limit"] not in {"1", "5", "15", "50", "max"}:
                    raise ValueError("Depth limit must be 1/5/15/50/max")
            elif not 1 <= p["limit"] <= maximum:
                raise ValueError(f"limit must be 1..{maximum}")
        if p.get("skip", 0) < 0:
            raise ValueError("skip must be nonnegative")
        for field, values in {
            "orderType": {"LIMIT", "MARKET"}, "effect": {"IOC", "FOK", "GTC", "POST_ONLY"},
            "tradeSide": {"OPEN", "CLOSE"}, "tpOrderType": {"LIMIT", "MARKET"}, "slOrderType": {"LIMIT", "MARKET"},
            "tpStopType": {"MARK_PRICE", "LAST_PRICE"}, "slStopType": {"MARK_PRICE", "LAST_PRICE"},
            "marginMode": {"ISOLATION", "CROSS"},
        }.items():
            if field in p and p[field] not in values:
                raise ValueError(f"Invalid {field}; use documented enums")
        if "side" in p and name in {"place_order", "batch_order"} and p["side"] not in {"BUY", "SELL"}:
            raise ValueError("Order side must be BUY/SELL")
        if name == "change_position_mode" and p["positionMode"] not in {"ONE_WAY", "HEDGE"}:
            raise ValueError("Position mode must be ONE_WAY/HEDGE")
