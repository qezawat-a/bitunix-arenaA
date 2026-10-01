import json

import pytest

from jrock.config import Settings
from jrock.integration import IntegratedRuntime
from jrock.security import PermissionDenied
from jrock.trader.models import TradeConfig


@pytest.fixture
async def runtime(tmp_path):
    r = IntegratedRuntime(Settings(_env_file=None, telegram_allowed_user_ids=[123],
            data_dir=tmp_path / "data", workspace_dir=tmp_path / "workspace"))
    yield r
    await r.close()


async def test_integrated_commands_and_natural_control_without_llm(runtime):
    controller = runtime.controller
    assert "PAPER autotrade on" in await controller.handle(123, "Start trading")
    assert runtime.engine.autotrade
    await controller.handle(123, "Stop trading")
    assert not runtime.engine.autotrade
    await controller.handle(123, "/engine on")
    assert runtime.engine.scan_on
    await controller.handle(123, "Report interval sec 31")
    assert runtime.engine.config.report_interval_sec == 31
    await controller.handle(123, "/scans interval sec 16")
    assert runtime.engine.config.scan_interval_sec == 16
    await controller.handle(123, "/mid_management_position sec 17")
    assert runtime.engine.config.management_interval_sec == 17
    await controller.handle(123, "/trailing_trigger_stop_roi_pct 6")
    assert runtime.engine.config.trailing_trigger_roi_pct == 6
    await controller.handle(123, "/settings trade leverage 2")
    assert runtime.engine.config.leverage == 2
    await controller.handle(123, "/symbols BTCUSDT,ETHUSDT")
    assert runtime.engine.config.symbols == ["BTCUSDT", "ETHUSDT"]
    status = json.loads(await controller.handle(123, "/status"))
    assert status["mode"] == "paper" and not status["live_session_authorized"]
    assert json.loads(await controller.handle(123, "/bitunix_docs coverage"))["documents"] == 52


@pytest.mark.parametrize("command", [
    "/help", "/trade_help", "/harness", "/tools", "/skills", "/soul", "/soul(fable-5.1)",
    "/provider", "/config", "/sessions", "/memory", "/tpsl", "/settings_trade",
    "/auto_approve_on_edit off", "/learning off", "/positions_history", "/cancels all",
])
async def test_command_surface_without_credentials(runtime, command):
    assert await runtime.controller.handle(123, command)


async def test_full_approval_payload_and_owner_bound_edit(runtime):
    pending = await runtime.agent.tools.invoke(123, "write_file", {"path": "example.txt", "content": "review me"})
    aid = pending["approval_required"]
    details = json.loads(await runtime.controller.handle(123, "/approval " + aid))
    assert details["exact_payload"]["args"]["content"] == "review me"
    assert not (runtime.agent.permissions.workspace / "example.txt").exists()
    with pytest.raises(PermissionDenied):
        await runtime.controller.handle(999, "/approve " + aid)
    await runtime.controller.handle(123, "/approve " + aid)
    assert (runtime.agent.permissions.workspace / "example.txt").read_text() == "review me"
    with pytest.raises(PermissionDenied):
        await runtime.controller.handle(123, "/approve " + aid)


async def test_text_compat_hallucinated_tool_is_not_executed(runtime):
    runtime.agent.provider.compat = "text"
    runtime.agent.permissions.edit_auto.add(123)
    async def malicious_chat(*args, **kwargs):
        return {"role": "assistant", "tool_calls": [{"id": "fake", "function": {"name": "write_file",
                   "arguments": json.dumps({"path": "should-not-exist", "content": "no"})}}]}
    runtime.agent.provider.chat = malicious_chat
    reply = await runtime.agent.harness.respond(123, "Read-only chat please")
    assert "No tool was executed" in reply
    assert not (runtime.agent.permissions.workspace / "should-not-exist").exists()


async def test_terminal_local_gate_cannot_be_bypassed_by_approval(runtime):
    pending = await runtime.agent.tools.invoke(123, "terminal", {"command": "touch forbidden"})
    with pytest.raises(PermissionDenied, match="Shell access is disabled"):
        await runtime.controller.handle(123, "/approve " + pending["approval_required"])
    assert not (runtime.agent.permissions.workspace / "forbidden").exists()


async def test_raw_mutations_remain_disabled_even_after_approval(runtime):
    pending = await runtime.agent.tools.invoke(123, "bitunix_mutation",
                 {"endpoint": "flash_close_position", "parameters": {"positionId": "1"}})
    with pytest.raises(PermissionDenied, match="Raw financial mutations disabled"):
        await runtime.controller.handle(123, "/approve " + pending["approval_required"])


def test_every_trade_setting_is_also_supported_in_environment():
    assert set(TradeConfig.model_fields).issubset(Settings.model_fields)


async def test_feedback_learning_is_opt_in_and_no_raw_api_key_command(runtime):
    await runtime.controller.handle(123, "/feedback Remember this correction")
    assert runtime.agent.store.memories(123) == []
    await runtime.controller.handle(123, "/learning on")
    await runtime.controller.handle(123, "/feedback Remember this correction")
    assert runtime.agent.store.memories(123)[0]["kind"] == "feedback"
    with pytest.raises(PermissionDenied):
        await runtime.controller.handle(123, "/set-api-key never-store-this-secret")
    assert "never-store-this-secret" not in str(runtime.agent.store.memories(123))
