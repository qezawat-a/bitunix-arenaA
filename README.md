# J+rock · Telegram AI agent + Bitunix futures engine

A Python 3.11+ project built as **two independent components**, then composed:

1. `jrock agent`: permissioned Telegram agent; no exchange dependency in its runtime.
2. `jrock trader`: independent scanner, paper ledger and Bitunix execution adapter; no LLM/Telegram dependency in its engine.
3. `jrock run`: combined agent and engine, with authenticated Telegram controls and shared documentation.

**Paper mode by default. No real trades were placed during development. Live trading is not production-certified.**
Strategy confidence is a heuristic score, **not** a probability of profit. Stops do not guarantee an exit.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
chmod 600 .env
# Edit .env locally. NEVER send credentials to a chat or commit them.
jrock doctor
jrock discover      # small paid requests to probe advertised models
jrock run           # Telegram long polling; one process per bot token
```

Configure these locally:

- `TELEGRAM_BOT_TOKEN`: create your bot with Telegram's BotFather.
- `TELEGRAM_ALLOWED_USER_IDS=[123456789]`: your numeric Telegram user ID. **Empty denies everyone.** Only private chats work.
- `AI_BASE_URL`: your **OpenAI-compatible** API prefix (e.g. your gateway's `/v1`).
- `AI_API_KEY`: your provider's API key. Model names are **not** specified in source or default configuration.
- Bitunix credentials are not needed for public scanning or paper trading. Set them only for authenticated reads/live use.

Allowlists are trusted operators of a **shared trading account/workspace**; personal conversations and memories are owner-isolated.
This service controls only the machine/container where you install it, not your Telegram phone automatically.

### Automatic model discovery — no hardcoded model, no runtime fallback

`GET AI_BASE_URL + AI_MODELS_PATH` retrieves advertised IDs. Each ID is probed with **your key** for chat and tool calling.
Only freshly verified compatible IDs can be selected. Selection is deterministic from those IDs; a provider/model failure is
reported, never silently rerouted. A `/models refresh` explicitly re-runs discovery; transient failures require another refresh.

- `/models [refresh]`, `/set models <verified-id>`, `/provider`
- `/compat tools|text`, `/auto-compat`: explicit protocol mode; text mode disables LLM tool execution.
- `/thinking on|off`: opt-in provider reasoning fields in `AI_EXTRA_BODY`; no invented thinking support or hidden chain-of-thought output.
- `/set-api-key reload`: reload local AI `.env` settings. **Never pass a key as a command argument.**

Probing can incur charges. `AI_DISCOVERY_MAX_MODELS` caps advertised IDs to avoid an unbounded bill.
Native Anthropic/Gemini/non-compatible APIs need a compatible gateway or a purpose-built connector; this implementation does not guess their protocol.

## Agent commands

`/help` lists agent commands; `/trade_help` lists trading commands. Hyphenated command aliases and the requested `/set models` syntax are accepted.

| Area | Commands |
| --- | --- |
| Runtime/models | `/harness`, `/thinking`, `/models`, `/set models`, `/provider`, `/compat`, `/auto-compat`, `/set-api-key` |
| Extensions | `/skills`, `/skills add <name> <workspace.md>`, `/skills use <name>`, `/soul`, `/soul add`, `/soul use` |
| Connectors | `/mcp`, `/mcp add <workspace.json>`, `/app_connector add <workspace.json>` |
| Memory | `/memory add|search|forget`, `/learning on|off`, `/feedback <correction>`, `/dream` |
| Workflows | `/deepsearch <query>`, `/bugfixes <task>`, `/code-review <task>`, `/agents build|plan`, `/team <task>` |
| Permissions | `/tools`, `/config`, `/auto_approve_on_edit on|off`, `/approval <id>`, `/approve <id>`, `/deny <id>` |
| Sessions | `/sessions`, `/resume-session <id>`, `/new-session`, `/quit` |
| Generation | `/generator image|tts|video <prompt>`, `/generator files|codes|docs <path> <prompt>` |

`/team` runs a read-only planner then a permissioned builder. Code review is read-only. Terminal, connectors, generation and trading
are never auto-approved by the edit toggle. Exact owner-bound approvals expire after 5 minutes and are single-use.
Use `/approval <id>` to review full arguments, including file contents, before executing an action.

**Terminal warning:** a working directory is not an OS sandbox. All shell execution requires `ALLOW_HOST_TERMINAL=true`
locally **and** human approval of each exact command. Commands run with the service user's OS privileges; inherited API keys/tokens
are stripped. Use a container/VM, not root or an unrestricted personal device. Workspace file tools reject traversal,
symlink escapes and common credential/Git paths. These are application controls, not kernel containment.

### Fable 5.1 soul and learning

`fable-5.1` is a clearly marked placeholder, **not** a guessed reconstruction of your persona or a hardcoded model.
Send your full Fable 5.1 persona for review before replacing it. Style can change; permissions and live-trading gates cannot.

Upload a text file to the bot, then:

```text
/soul add fable-5.1 uploads/fable-5.1.md
/soul use fable-5.1
```

Learning is opt-in, local experience/feedback memory and `/dream` reflection. It does **not** train model weights,
change risk limits, self-modify security rules, or promise automatic performance improvement. Notes can be inspected/deleted.

### MCP, apps, search and generation

MCP supports **streamable HTTP JSON/SSE**, sessions and paginated tool listing; not stdio subprocess servers.
Every remote tool call requires human approval, even if the server claims it is read-only.
See [connectors and generation](docs/CONNECTORS.md) for configurations and honest capability limits.

Image/TTS model IDs must be advertised by your endpoint and explicitly configured; no model/voice names are invented.
Generation is verified only by a successful capability-specific response. Video uses an explicitly configured app connector;
there is no universal video endpoint assumed. Files/code/docs currently generate UTF-8 text formats, not binary DOCX/PDF renderers.

## Trading engine

Strategies: **EMA, RSI, MACD, volume, momentum, ATR breakout, funding rate, Supertrend, Bollinger, Ichimoku**.
Uses complete closed candles, strategy consensus and multi-timeframe thresholds. Missing, stale or gapped data rejects a signal.
Funding alone cannot open a trade. Default `1m,3m,5m,15m`: REST `3m` is constructed from complete, UTC-aligned 1-minute groups.

```text
/engine on
/scan on
/scans interval sec 15
/guard interval sec 15
/mid_management_position sec 15
/report on
/report interval sec 30
/settings_trade
/symbols BTCUSDT,ETHUSDT
/timeframes 1m,3m,5m,15m
/min_agreeing_strategies 2
/min_confidence 80
/tf_min_confidence 60
/autotrade on                 # PAPER unless configured/approved live
/autotrade off
/engine off
```

Natural equivalents such as `Start trading`, `Stop trading`, `Settings trade`, and `Report interval sec 30` work.
All `TradeConfig` settings are exposed as commands; settings changes pause entries. Actual scan duration may exceed the requested
cadence because of symbol count, candle backfill and exchange rate limits; cycles do not overlap.

Other controls: `/breakeven_threshold_pct`, `/trailing_trigger_stop_roi_pct`, `/trailing_stop_pct`, `/trailing_distance_pct`,
`/liq_sl_distance_pct`, `/max_positions`, `/leverage`, `/reversal on|off`, `/positions_history`, `/close_position <id> [qty]`,
`/cancels order|tpsl <symbol> <id>`, `/cancels all [symbol]`, `/reconcile`, `/reset_circuit`.

`/quit` cancels **agent work only**. `/autotrade off` stops new entries. `/engine off` disables scanning/reports/new entries but
keeps already-authorized reducing guards for open positions. `/engine disarm` explicitly disables live local mutations.
Native exchange stops remain when the process stops; **local trailing/account protection does not**.

### Four TP/SL methods and sizing

- `TP_MODE=POSITION`: whole-position native TP/SL.
- `TP_MODE=PARTIAL`: native scale-out ladder plus a full-position protective stop.
- `TP_MODE=TRAILING`: **local** trailing; ATR extension or article's ratio/absolute interval callback.
- `TP_MODE=ACCOUNT`: **local** total unrealized-PnL guard, alongside individual native stops.

`TPSL_METHOD=ADAPTIVE|FIXED_R` is a separate target-calculation axis. ADAPTIVE uses ATR, structure and signal strength;
FIXED_R uses a configured risk multiple. `/partial_tp_ladder 30@1,40@2` leaves a protected runner. Shares must total <=100%.
`ACCOUNT_TP_USDT=0` / `ACCOUNT_SL_USDT=0` disables thresholds. `ACCOUNT_GUARD_SCOPE=MANAGED` is the safe default;
`ALL` includes manual positions and requires explicit live settings approval.

Percent settings are **0..100 percentages**, except `TAKER_FEE_RATE` is a fraction and slippage is basis points.
Break-even/trailing activation thresholds use unrealized-PnL/margin ROI. Stop-distance/callback percentages use price.
`TRAILING_DISTANCE_PCT` caps callback distance from the best price; `TRAILING_STOP_PCT` is an additional entry-price safety cap
once trailing activates. Stops only tighten; never intentionally widen. Exchange `liqPrice` is authoritative; <=0 is not a price.

`/order_units BTCUSDT NOMINAL 1000 10` estimates base-coin quantity, margin and fees. Supports QUANTITY/NOMINAL/COST;
COST includes configured opening fees. Quantity rounds down using current exchange precision/minimum/maximum rules.
The engine additionally checks margin/risk budgets, maximum positions, daily loss, spread, price deviation and tier limits.

### Live activation — explicitly opt-in

1. Use an exchange API key with **no withdrawal permission**, restricted IPs and only required futures permissions.
2. Test on paper first. Do not use this project for funds you cannot afford to lose.
3. Locally set `TRADING_MODE=live`, `LIVE_TRADING_ENABLED=true`, Bitunix key/secret. Restart.
4. `/autotrade on` creates an exact-profile approval showing exposure settings. Review `/approval <id>`, then `/approve <id>`.
5. Live entries also require a healthy authenticated private WebSocket. `/engine authorize` can authorize reducing guards without new entries.

Live authorization is session-only, never restored on restart. Config changes invalidate entry approval. Intents are journaled before
opening POSTs. No mutation is blindly retried; uncertain outcomes trip a circuit and require reconciliation.
Stop/ladder protection is verified; failed protection attempts an emergency reducing close and alerts operators. Emergency closes can fail.
Daily loss is persisted and conservatively includes open-position realized losses/costs; positions spanning midnight can overcount lifetime costs.

`/bitunix <endpoint> <JSON>` exposes the documented SDK. GET is read-only; raw POST is disabled unless
`ALLOW_RAW_EXCHANGE_MUTATIONS=true` locally plus exact human approval. **Expert raw calls bypass scanner strategy checks**,
pause entries, and require manual state reconciliation. Leave this gate off normally.

## Documentation coverage

Packaged [reference catalog](src/jrock/resources/bitunix/manifest.json):

- **35 REST endpoints**, **176 request table rows**, **298 response table rows**.
- **10 public/private WebSocket channels**, preparation/signature docs and **76 error codes**.
- Liquidation, order-unit calculator and four-TP/SL help articles: **52 documents total**.
- Every supplied documentation URL is accounted for; navigation removed, tables retained, repetitive examples normalized.
- Source URLs, retrieval date and content hashes are retained. No unavailable supplied pages remained at the time of retrieval.

Accessible to **both** the standalone SDK/engine and integrated agent (`bitunix_docs` tool):

```text
/bitunix_docs coverage
/bitunix_docs funding
/bitunix_docs four_tpsl_methods
/bitunix get_funding_rate_history {"symbol":"BTCUSDT","starTime":1700000000000,"limit":10}
```

```bash
jrock docs                      # complete index
jrock docs get_pending_positions
python tools/build_catalog.py
python tools/build_ws_catalog.py
python tools/finalize_docs.py    # deterministic rebuild from checked transcriptions; not a live scraper
```

See [known upstream inconsistencies and verification limits](docs/VERIFICATION.md). Future API parity is not guaranteed;
verify with Bitunix before deployment. No native trailing/account REST endpoint was invented from a web UI article.

## Tests and deployment

```bash
ruff check src tests tools
pytest -q
jrock doctor
```

Tests use mocked HTTP and a paper ledger: model permission probes, endpoint/signature correctness, owner-bound approvals,
path boundaries, strategies/indicator references, candle close/aggregation, risk limits, paper scan-to-execution, guards and persistence.
They do not demonstrate actual Telegram delivery, a paid provider's capability, or live exchange fills/latency/liquidation behavior.

A non-root [Docker deployment](compose.yaml) is included. Run **one** service process per state directory/token; don't share SQLite files
among concurrent agent/engine instances. Runtime state/workspace/.env are ignored by Git. Back them up securely and inspect live positions
at the exchange before restarting. No GitHub PAT is needed in chat: use your existing authenticated GitHub connection.
