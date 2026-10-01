from __future__ import annotations

from jrock.agent.runtime import AgentRuntime
from jrock.agent.tools import Tool, obj
from jrock.config import Settings
from jrock.telegram.app import TelegramApp
from jrock.telegram.controller import AgentController
from jrock.telegram.trading import TRADE_HELP, TradeController
from jrock.trader.engine import TradingEngine


class IntegratedRuntime:
    """Final composition: independent agent + independent engine + explicit control adapter."""

    def __init__(self, settings: Settings):
        self.agent = AgentRuntime(settings)
        self.engine = TradingEngine(settings)
        self.controller = AgentController(self.agent)
        self.trading = TradeController(self.agent, self.engine)
        self.controller.extra = self.trading.handle
        self.controller.approve_extra = self.trading.approve
        # Add an informative skill, not a model fallback or a financial-decision authority.
        async def trade_help(owner: int, args: dict):
            return TRADE_HELP
        self.agent.tools.register(Tool("trade_help", "Read documented command and risk-control usage.", obj({}), trade_help))
        self.app: TelegramApp | None = None

    async def start(self) -> None:
        await self.agent.start()
        await self.engine.start()

    async def run(self, stop) -> None:
        self.app = TelegramApp(self.agent, self.controller)
        async def report(data):
            if self.trading.report_owner:
                from jrock.telegram.controller import pretty
                await self.app.send(self.trading.report_owner, "J+rock report\n" + pretty(data))
        async def notify(text):
            for owner in self.agent.settings.telegram_allowed_user_ids:
                await self.app.send(owner, text)
        self.engine.reporter, self.engine.notifications = report, notify
        await self.start()
        await self.app.run(stop)

    async def close(self) -> None:
        await self.engine.shutdown()
        await self.agent.close()
