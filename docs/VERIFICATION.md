# Verification scope and upstream discrepancies

Retrieved 2026-10-01. Documentation is a checked table/content transcription, not an untouched website archive;
navigation is omitted and duplicate examples normalized. The SHA-256 manifest verifies local integrity, not ongoing API parity.

All **supplied** endpoints/pages are represented. This is not a claim to implement every future/new Bitunix product endpoint.

Important differences retained:

1. Funding-history parameter is **starTime**, not startTime; source required column has `fasle`. No silently corrected wire key.
2. REST candles list no 3m; WebSocket lists 3min. REST scanner aggregates full closed 1m groups locally.
3. Order examples use MARK/LAST while request tables use MARK_PRICE/LAST_PRICE. Engine follows tables; examples remain documented.
4. modify_order example has symbol, absent from request table. Strict validator does not invent that field.
5. tradeSide table says required, description says only hedge mode. Validator permits omission; engine explicitly supplies OPEN/CLOSE.
6. cancel_orders omits indentation for orderId/clientId; example resolves their location inside orderList.
7. TPSL-history example is a positions array, inconsistent with its orderList/total table. Raw SDK preserves responses, not lossy guessed conversion.
8. sub-account descriptions refer to subAccountUid but rows name subAccountId; engine queries includeSubAccounts=false.
9. WS order/TPSL business times can be ISO-8601 nanoseconds; REST times are milliseconds. Gateway ts is not business event ordering.
10. TPSL `CLOSE+FILLED` means trigger succeeded and child was placed, **not** child filled or position closed.
11. Source types for some public WS data fields disagree with object examples. Preserve incoming data; REST remains authoritative for position details.
12. WS preparation unsubscribe example says channel instead of ch; channel-specific schema says ch.
13. Private WS login signing in preparation/official Python demo differs from generic sign-page WS formulation. Client implements documented private login with seconds;
    REST signing uses milliseconds and sorted key+value query strings with an identical compact request body.
14. The liquidation article contains a contradictory tier-1 reduction paragraph. No simplified cross-account liquidation formula is invented.
15. UI article's four TP/SL types do not specify native trailing/account REST endpoints in the supplied catalog; those two engine features are local.

The official Python demonstration repo/commit was checked for signature behavior; see packaged signature.md for source attribution.
This sandbox could retrieve docs through the page-fetch service; direct shell HTTPS to Bitunix was unavailable.

## Tested here

Mocked model-list/chat/tool probes, authorization and exact one-shot approvals, session ownership, catalog/hash coverage,
REST signatures/wire bodies, no paper financial POSTs, no mutation retry after a timeout, WS event semantics/ordering,
all ten strategy paths, indicator reference values, closed candle/3m aggregation, risk/rounding/tier constraints,
paper scan-to-execution, TP/SL ledger behavior, account guard, funding idempotence and restart persistence.

## Not live-validated

- Telegram delivery/polling and flood-limit behavior against an actual bot token.
- Your real model gateway, native thinking/image/TTS contracts or billing/permissions.
- Live Bitunix signing acceptance, fills, cancel confirmation, partial child-order behavior, fees, latency or liquidation outcomes.
- Native trailing/account endpoints beyond the supplied documents (none assumed).
- Profitability, calibrated signal confidence, financial suitability or legal/regional eligibility.

Read-only reconciliation never blindly resubmits an intent or auto-arms trading. Ambiguous fills can require a human to inspect/close
positions at the exchange before clearing the circuit. Use paper first, then controlled read-only credentials, and review live code/risk
settings independently before considering real funds. Never grant withdrawals or promise that stops prevent losses.
