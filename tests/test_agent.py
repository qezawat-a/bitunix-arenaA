import json

import httpx
import pytest

from jrock.agent.provider import ModelProvider, ProviderError
from jrock.agent.tools import ToolRegistry
from jrock.config import Settings
from jrock.security import PermissionDenied, Permissions
from jrock.storage import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "state.db")
    yield s
    s.close()


async def test_discovery_probes_permissions_no_hardcoded_fallback(store):
    requested = []

    def handler(r):
        assert r.headers["authorization"] == "Bearer private-key"
        if r.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "user-b"}, {"id": "denied"}, {"id": "user-a"}]})
        body = json.loads(r.content)
        requested.append(body["model"])
        if body["model"] == "denied":
            return httpx.Response(403, json={"error": "not allowed"})
        msg = {"content": "OK"}
        if "tools" in body:
            msg["tool_calls"] = [{"function": {"name": "capability_probe"}}]
        return httpx.Response(200, json={"choices": [{"message": msg}]})

    provider = ModelProvider(Settings(_env_file=None, ai_base_url="https://custom.example/v1", ai_api_key="private-key"),
                            store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    probes = await provider.discover()
    assert provider.model == "user-a"
    assert not next(p for p in probes if p["id"] == "denied")["chat"]
    assert set(requested) == {"user-a", "user-b", "denied"}
    provider.select("user-b")
    assert provider.model == "user-b"
    with pytest.raises(ProviderError):
        provider.select("invented")
    await provider.close()


async def test_failed_discovery_clears_previous_selection(store):
    def handler(r):
        return httpx.Response(401, json={"error": "unauthorized"})
    provider = ModelProvider(Settings(_env_file=None, ai_base_url="https://custom.example", ai_api_key="key"),
                            store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    provider.model = "old-model"
    with pytest.raises(ProviderError):
        await provider.discover()
    assert provider.model is None
    await provider.close()


async def test_chat_only_needs_explicit_compat(store):
    def handler(r):
        if r.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "chat-only"}]})
        if "tools" in json.loads(r.content):
            return httpx.Response(400)
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})
    provider = ModelProvider(Settings(_env_file=None, ai_base_url="https://custom.example", ai_api_key="key"),
                            store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderError):
        await provider.discover()
    provider.compat = "text"
    await provider.discover()
    assert provider.model == "chat-only"
    await provider.close()


async def test_edit_approval_is_exact_owner_bound_and_single_use(tmp_path, store):
    p = Permissions([1, 2], tmp_path)
    tools = ToolRegistry(p, store)
    args = {"path": "test.txt", "content": "hello"}
    pending = await tools.invoke(1, "write_file", args)
    aid = pending["approval_required"]
    assert not (tmp_path / "test.txt").exists()
    with pytest.raises(PermissionDenied):
        p.approve(2, aid)
    a = p.approve(1, aid)
    with pytest.raises(PermissionDenied):
        await tools.invoke(1, "write_file", {**args, "content": "changed"}, aid)
    result = await tools.invoke(1, "write_file", a.payload["args"], aid)
    assert "Wrote" in result["result"]
    assert (tmp_path / "test.txt").read_text() == "hello"
    with pytest.raises(PermissionDenied):
        await tools.invoke(1, "write_file", args, aid)


def test_paths_deny_traversal_symlink_and_secrets(tmp_path):
    p = Permissions([1], tmp_path / "workspace")
    p.workspace.mkdir()
    (p.workspace / "escape").symlink_to(tmp_path, target_is_directory=True)
    for path in ("../outside", "escape/outside", ".env", ".git/config", ".ssh/id_rsa"):
        with pytest.raises(PermissionDenied):
            p.safe_path(path)


async def test_auto_edit_never_auto_approves_terminal(tmp_path, store):
    p = Permissions([1], tmp_path)
    p.edit_auto.add(1)
    tools = ToolRegistry(p, store)
    await tools.invoke(1, "write_file", {"path": "a", "content": "ok"})
    result = await tools.invoke(1, "terminal", {"command": "echo test"})
    assert "approval_required" in result
    with pytest.raises(PermissionDenied):
        await tools.invoke(1, "write_file", {"path": "a", "content": "bad"}, read_only=True)


def test_fail_closed_allowlist():
    with pytest.raises(PermissionDenied):
        Permissions([], __import__("pathlib").Path(".")).authorize(1)
    with pytest.raises(PermissionDenied):
        Permissions([1], __import__("pathlib").Path(".")).authorize(1, False)


def test_resume_ownership(store):
    sid = store.new_session(1)
    store.message(sid, {"role": "user", "content": "test"})
    with pytest.raises(ValueError):
        store.resume(2, sid)
    store.resume(1, sid)
    assert store.messages(sid)[0]["content"] == "test"


def test_config_secrets_and_provider_overrides():
    s = Settings(_env_file=None, ai_api_key="secret", bitunix_api_secret="secret")
    assert "secret" not in json.dumps(s.public_dict())
    with pytest.raises(ValueError):
        Settings(_env_file=None, ai_extra_body={"model": "hardcoded"})
    with pytest.raises(ValueError):
        Settings(_env_file=None, ai_base_url="https://name:secret@example.com")
