#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src/jrock/resources/bitunix"
extras = {
 "websocket_prepare": "https://www.bitunix.com/api-docs/futures/websocket/prepare/WebSocket.html",
 "signature": "https://www.bitunix.com/api-docs/futures/common/sign.html",
 "change_log": "https://www.bitunix.com/api-docs/futures/log/change_log.html",
 "error_code": "https://www.bitunix.com/api-docs/futures/ErrorCode/error_code.html",
 "liquidation": "https://support.bitunix.com/hc/en-us/articles/32152530856601-Bitunix-Futures-Liquidation-Mechanism-and-Tiered-Risk-Limit",
 "four_tpsl_methods": "https://www.bitunix.com/uk-ua/hub/helpcenter/article/bitunix-futures-position-a-guide-to-four-take-profit-and-stop-loss-methods-web?id=290",
 "order_units": "https://www.bitunix.com/hub/helpcenter/article/explanation-of-the-order-units-in-futures-trading?id=170",
}
p = OUT / "manifest.json"
m = json.loads(p.read_text())
m["documents"] = [d for d in m["documents"] if d["id"] not in extras]
for name, url in extras.items():
    content = (OUT / (name + ".md")).read_bytes()
    m["documents"].append({"id": name, "url": url, "file": name + ".md", "sha256": hashlib.sha256(content).hexdigest(), "status": "content-transcription"})
m["unavailable_supplied_pages"] = []
m["example_repositories"] = ["https://github.com/qezawat-a/open-api/tree/main/Demo", "https://github.com/BitunixOfficial/open-api/tree/main/Demo"]
m["transcription_note"] = "Endpoint/channel tables retained. Navigation omitted; descriptions transcribed; repetitive examples normalized. URLs and hashes retained. Not a guarantee of future documentation/API parity."
p.write_text(json.dumps(m, indent=2) + "\n")
errors = {}
for line in (OUT / "error_code.md").read_text().splitlines():
    cols = [c.strip() for c in line.strip("|").split("|")]
    if len(cols) == 3 and cols[0].isdigit():
        errors[cols[0]] = {"description": cols[1], "http_status": int(cols[2])}
(OUT / "error_codes.json").write_text(json.dumps(errors, indent=2) + "\n")
print(len(m["documents"]), "documents,", len(errors), "error codes")
