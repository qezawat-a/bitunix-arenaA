from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from jrock.agent.runtime import AgentRuntime
from jrock.config import Settings
from jrock.telegram.app import TelegramApp


def stop_event() -> asyncio.Event:
    event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, event.set)
    return event


async def run_agent(settings: Settings) -> None:
    runtime = AgentRuntime(settings)
    try:
        await runtime.start()
        await TelegramApp(runtime).run(stop_event())
    finally:
        await runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="J+rock AI agent")
    parser.add_argument("command", choices=["agent", "discover", "trader", "docs", "run", "doctor"], nargs="?", default="agent")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--autotrade", action="store_true", help="Enable standalone PAPER autotrading only")
    args = parser.parse_args()
    # Never enable httpx debug: Telegram URLs contain bot tokens.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
    settings = Settings()
    if args.command == "run":
        from jrock.integration import IntegratedRuntime
        async def integrated():
            runtime = IntegratedRuntime(settings)
            try:
                await runtime.run(stop_event())
            finally:
                await runtime.close()
        asyncio.run(integrated())
        return
    if args.command == "doctor":
        import json

        from jrock.exchange.catalog import Documentation
        from jrock.trader.models import TradeConfig
        docs = Documentation()
        TradeConfig.from_settings(settings)
        print(json.dumps({
            "telegram_ready": bool(settings.telegram_bot_token.get_secret_value() and settings.telegram_allowed_user_ids),
            "ai_configured": bool(settings.ai_base_url and settings.ai_api_key.get_secret_value()),
            "ai_models": "Use jrock discover (costs small probe requests)",
            "exchange_credentials_configured": bool(settings.bitunix_api_key.get_secret_value() and settings.bitunix_api_secret.get_secret_value()),
            "trading_mode": settings.trading_mode, "live_environment_gate": settings.live_trading_enabled,
            "live_runtime_authorization": False, "terminal_environment_gate": settings.allow_host_terminal,
            "documentation_hash_failures": docs.verify(), "rest_endpoints": len(docs.rest),
            "ws_channels": len(docs.ws), "documents": len(docs.manifest["documents"]),
            "no_hardcoded_model": True,
        }, indent=2))
        return
    if args.command == "docs":
        import json

        from jrock.exchange.catalog import Documentation
        docs = Documentation()
        if args.query in {d["id"] for d in docs.manifest["documents"]}:
            print(docs.read(args.query))
        else:
            print(json.dumps(docs.search(args.query), indent=2))
        return
    if args.command == "trader":
        from jrock.trader.engine import TradingEngine
        async def trader():
            import json
            engine = TradingEngine(settings)
            async def report(data):
                print(json.dumps(data, default=str, ensure_ascii=False))
            engine.reporter = report
            try:
                if args.autotrade:
                    engine.enable_paper()
                engine.enabled = engine.scan_on = engine.report_on = True
                await engine.start()
                await stop_event().wait()
            finally:
                await engine.shutdown()
        asyncio.run(trader())
        return
    if args.command == "discover":
        async def discover():
            import json
            runtime = AgentRuntime(settings)
            try:
                print(json.dumps(await runtime.provider.discover(), indent=2))
                print("Selected:", runtime.provider.model)
            finally:
                await runtime.close()
        asyncio.run(discover())
    else:
        asyncio.run(run_agent(settings))


if __name__ == "__main__":
    main()
