from __future__ import annotations

from jrock.agent.extensions import TextExtensions
from jrock.agent.harness import Harness
from jrock.agent.provider import ModelProvider
from jrock.agent.tools import Tool, ToolRegistry, obj, string
from jrock.config import Settings
from jrock.connectors.http import ConnectorManager
from jrock.connectors.search import SearchConnector
from jrock.generators.service import Generators
from jrock.security import Permissions
from jrock.storage import Store


class AgentRuntime:
    """The standalone agent. It has no exchange/trading import or dependency."""

    def __init__(self, settings: Settings):
        self.settings = settings
        settings.initialize_directories()
        self.store = Store(settings.data_dir / "agent.db")
        self.permissions = Permissions(settings.telegram_allowed_user_ids, settings.workspace_dir,
                                       settings.allow_host_terminal)
        if settings.auto_approve_on_edit:
            self.permissions.edit_auto.update(settings.telegram_allowed_user_ids)
        self.provider = ModelProvider(settings, self.store)
        self.tools = ToolRegistry(self.permissions, self.store)
        self.extensions = TextExtensions(settings.data_dir, self.permissions)
        self.connectors = ConnectorManager(self.store, self.tools)
        self.search = SearchConnector(settings)
        self.search.register(self.tools)
        self.generators = Generators(settings, self.provider, self.permissions, self.connectors)
        self.generators.register(self.tools)
        self.tools.register(Tool("memory_search", "Read your own stored notes (untrusted reference text).",
                                 obj({"query": string()}, []), self.memory_search))
        self.harness = Harness(self.provider, self.tools, self.extensions, self.permissions, self.store)

    async def memory_search(self, owner: int, args: dict) -> list[dict]:
        return self.store.memories(owner, args.get("query", ""))

    async def start(self) -> None:
        await self.connectors.restore()

    async def close(self) -> None:
        for task in list(self.harness.running.values()):
            task.cancel()
        await self.connectors.close()
        await self.search.close()
        await self.generators.close()
        await self.provider.close()
        self.store.close()
