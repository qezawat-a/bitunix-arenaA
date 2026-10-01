from __future__ import annotations

import base64
import uuid

import httpx

from jrock.agent.provider import ModelProvider
from jrock.agent.tools import Tool, ToolRegistry, obj, string
from jrock.config import Settings
from jrock.connectors.http import ConnectorManager
from jrock.security import Permissions


class Generators:
    """Honest capability-specific generators. No invented image/audio/video model IDs."""

    def __init__(self, settings: Settings, provider: ModelProvider, permissions: Permissions,
                 connectors: ConnectorManager):
        self.settings, self.provider, self.permissions, self.connectors = settings, provider, permissions, connectors
        self.client = httpx.AsyncClient(timeout=120, follow_redirects=False)

    def register(self, registry: ToolRegistry) -> None:
        registry.register(Tool("generate_image", "Generate an image using the explicitly configured IMAGE_MODEL. Costs provider credits.",
                               obj({"prompt": string()}), self.image, "generation"))
        registry.register(Tool("generate_tts", "Generate spoken audio using explicitly configured TTS_MODEL and TTS_VOICE.",
                               obj({"text": string()}), self.tts, "generation"))
        registry.register(Tool("generate_video", "Submit a video job to the configured video app connector (provider-specific contract).",
                               obj({"prompt": string()}), self.video, "generation"))
        registry.register(Tool("generate_document", "Generate UTF-8 code/docs/files at a workspace path. Requires approval before generation and write.",
                               obj({"path": string(), "prompt": string()}), self.document, "generation"))

    async def _verified_id(self, model: str) -> None:
        if not model:
            raise ValueError("Configure the capability's model locally or with /generator <kind> model <advertised-id>; no guessed model")
        ids = await self.provider.advertised()
        if model not in ids:
            raise ValueError("Configured capability model is not advertised by this endpoint for this key")

    def artifact(self, content: bytes, extension: str) -> str:
        if not content or len(content) > 30_000_000:
            raise ValueError("Generated file is empty or exceeds 30 MB")
        name = f"generated/{uuid.uuid4().hex[:12]}{extension}"
        p = self.permissions.safe_path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        p.chmod(0o600)
        return name

    async def image(self, owner: int, args: dict) -> dict:
        await self._verified_id(self.settings.image_model)
        r = await self.client.post(self.provider.url("/images/generations"), headers=self.provider.headers(),
                    json={"model": self.settings.image_model, "prompt": args["prompt"], "n": 1,
                          "response_format": "b64_json"})
        if r.is_error:
            raise RuntimeError(f"Image generation HTTP {r.status_code}; no fallback used")
        rows = r.json().get("data", [])
        if not rows or not rows[0].get("b64_json"):
            raise ValueError("Provider did not return b64_json; use a configured app connector for its native image format")
        return {"artifact": self.artifact(base64.b64decode(rows[0]["b64_json"], validate=True), ".png")}

    async def tts(self, owner: int, args: dict) -> dict:
        await self._verified_id(self.settings.tts_model)
        if not self.settings.tts_voice:
            raise ValueError("Set TTS_VOICE to a voice supported by your provider")
        r = await self.client.post(self.provider.url("/audio/speech"), headers=self.provider.headers(),
                    json={"model": self.settings.tts_model, "voice": self.settings.tts_voice,
                          "input": args["text"], "response_format": "mp3"})
        if r.is_error:
            raise RuntimeError(f"TTS HTTP {r.status_code}; no fallback used")
        return {"artifact": self.artifact(r.content, ".mp3")}

    async def video(self, owner: int, args: dict) -> dict:
        connector = self.connectors.connectors.get(self.settings.video_connector)
        if not connector or connector.spec.protocol != "http":
            raise ValueError("Configure an HTTP video app connector, then set VIDEO_CONNECTOR to its name; no universal video API assumed")
        return await connector.call({"operation": "generate_video", "prompt": args["prompt"]})

    async def document(self, owner: int, args: dict) -> dict:
        p = self.permissions.safe_path(args["path"])
        if p.suffix not in {".md", ".txt", ".py", ".js", ".ts", ".json", ".html", ".css", ".csv", ".yaml", ".yml"}:
            raise ValueError("Choose a UTF-8 text/code format (.md/.txt/.py/.json/etc). Binary docs need an app connector")
        message = await self.provider.chat([{"role": "system", "content": "Generate the requested file as plain text only, without markdown fences. Do not claim to execute code."},
                                            {"role": "user", "content": args["prompt"]}])
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("No file content returned")
        if len(text.encode()) > 1_000_000:
            raise ValueError("Generated file exceeds 1 MB")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        p.chmod(0o600)
        return {"artifact": str(p.relative_to(self.permissions.workspace))}

    async def close(self) -> None:
        await self.client.aclose()
