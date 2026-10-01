from __future__ import annotations

import asyncio
import contextlib
import io
import logging

from pydantic import SecretStr, ValidationError
from telegram import BotCommand, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from jrock.agent.runtime import AgentRuntime
from jrock.security import PermissionDenied
from jrock.telegram.controller import AgentController

logger = logging.getLogger(__name__)


class TelegramApp:
    def __init__(self, runtime: AgentRuntime, controller: AgentController | None = None):
        self.r, self.controller = runtime, controller or AgentController(runtime)
        token = runtime.settings.telegram_bot_token.get_secret_value()
        if not token or not runtime.settings.telegram_allowed_user_ids:
            raise ValueError("Configure TELEGRAM_BOT_TOKEN and non-empty TELEGRAM_ALLOWED_USER_IDS locally")
        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(filters.TEXT, self.on_message))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.on_document))
        self.application.add_error_handler(self.on_error)
        self.tasks: set[asyncio.Task] = set()

    def owner(self, update: Update) -> int:
        if not update.effective_user or not update.effective_chat:
            raise PermissionDenied("Unsupported update")
        owner = update.effective_user.id
        self.r.permissions.authorize(owner, update.effective_chat.type == "private")
        return owner

    async def send(self, owner: int, text: str) -> None:
        for name in self.r.settings.model_fields:
            value = getattr(self.r.settings, name)
            if isinstance(value, SecretStr) and value.get_secret_value():
                text = text.replace(value.get_secret_value(), "[REDACTED]")
        if len(text) > 12_000:
            await self.application.bot.send_message(owner, "Full response attached as a text file to avoid Telegram message limits.")
            await self.application.bot.send_document(owner, document=io.BytesIO(text.encode()), filename="jrock-response.txt")
            return
        for i in range(0, len(text), 3900):
            await self.application.bot.send_message(owner, text[i:i + 3900])

    async def execute(self, owner: int, text: str) -> None:
        try:
            response = await self.controller.handle(owner, text)
            await self.send(owner, response)
            # Generated artifacts are sent only after the approved operation has actually completed.
            import json
            try:
                data = json.loads(response)
                result = data.get("result", data)
                artifact = result.get("artifact") if isinstance(result, dict) else None
            except (ValueError, AttributeError):
                artifact = None
            if artifact:
                p = self.r.permissions.safe_path(artifact)
                with p.open("rb") as file:
                    await self.application.bot.send_document(owner, document=file, filename=p.name)
        except asyncio.CancelledError:
            await self.send(owner, "Task cancelled. Trading state is unchanged.")
        except (ValueError, RuntimeError, OSError) as exc:
            # Controlled internal errors should not include secrets; transport errors are generic.
            import httpx
            message = type(exc).__name__ if isinstance(exc, (httpx.HTTPError, ValidationError)) else str(exc)
            await self.send(owner, message[:3900])
        except Exception as exc:
            logger.error("Telegram task failed: %s", type(exc).__name__)
            await self.send(owner, "Task failed. Check the server's sanitized event log; no fallback action was taken.")

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            owner = self.owner(update)
        except PermissionDenied:
            return  # Fail closed, silently: don't reveal bot setup to arbitrary Telegram users/groups.
        assert update.effective_message and update.effective_message.text
        # Short-lived handler launches the task so /quit and approvals work during a long agent run.
        task = asyncio.create_task(self.execute(owner, update.effective_message.text))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def on_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            owner = self.owner(update)
        except PermissionDenied:
            return
        doc = update.effective_message.document
        name = doc.file_name or "upload.txt"
        if (doc.file_size or 0) > 1_000_000 or name.startswith(".env"):
            await self.send(owner, "Upload text/config files under 1 MB only, never credentials.")
            return
        from pathlib import Path
        p = self.r.permissions.safe_path("uploads/" + Path(name).name)
        p.parent.mkdir(parents=True, exist_ok=True)
        await (await doc.get_file()).download_to_drive(p)
        p.chmod(0o600)
        await self.send(owner, f"Saved workspace uploads/{p.name}. To install a persona: /soul add fable-5.1 uploads/{p.name}")

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Telegram transport error: %s", type(context.error).__name__)

    async def run(self, stop: asyncio.Event) -> None:
        async with self.application:
            await self.application.start()
            await self.application.bot.set_my_commands([
                BotCommand("help", "All commands"), BotCommand("models", "Discover verified models"),
                BotCommand("harness", "Agent status"), BotCommand("tools", "Available tools"),
                BotCommand("soul", "Persona"), BotCommand("sessions", "Saved conversations"),
                BotCommand("status", "Trading engine status"), BotCommand("trade_help", "Trading commands"),
                BotCommand("quit", "Cancel agent task (not trading)"),
            ])
            assert self.application.updater is not None
            await self.application.updater.start_polling(drop_pending_updates=True,
                                                        allowed_updates=["message"])
            try:
                await stop.wait()
            finally:
                await self.application.updater.stop()
                for task in list(self.tasks):
                    task.cancel()
                for task in list(self.tasks):
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                await self.application.stop()
