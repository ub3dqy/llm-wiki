"""Regression tests for doctor flush pipeline classification."""

from __future__ import annotations

import sys
from datetime import datetime
from types import ModuleType, SimpleNamespace

import config as config_module
import doctor


def _current_log_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _use_flush_log(monkeypatch, tmp_path, content: str) -> None:
    flush_log = tmp_path / "flush.log"
    flush_log.write_text(content, encoding="utf-8")
    monkeypatch.setattr(doctor, "FLUSH_LOG", flush_log)
    doctor._parse_flush_log_events.cache_clear()


def test_flush_pipeline_correctness_ignores_salvaged_post_result_exit(
    monkeypatch, tmp_path
) -> None:
    ts = _current_log_timestamp()
    _use_flush_log(
        monkeypatch,
        tmp_path,
        "\n".join(
            [
                f"{ts} ERROR [flush] Fatal error in message reader: Command failed with exit code 1",
                "Error output: Check stderr output for details",
                f"{ts} WARNING [flush] Agent SDK exited non-zero after emitting result; "
                "using streamed result: Command failed with exit code 1",
                f"{ts} INFO [flush] Flushed 99 chars to daily log for session test-session",
            ]
        ),
    )

    result = doctor.check_flush_pipeline_correctness()

    assert result.ok is True
    assert "No failed flush Agent SDK exits" in result.detail
    assert "reader fatal raw: 1 in last 24h" in result.detail
    assert "salvaged post-result: 1 in last 24h" in result.detail


def test_flush_pipeline_correctness_counts_unsalvaged_query_failure(monkeypatch, tmp_path) -> None:
    ts = _current_log_timestamp()
    _use_flush_log(
        monkeypatch,
        tmp_path,
        "\n".join(
            [
                f"{ts} ERROR [flush] Fatal error in message reader: Command failed with exit code 1",
                "Error output: Check stderr output for details",
                f"{ts} ERROR [flush] Agent SDK query failed: Command failed with exit code 1",
                "Error output: Check stderr output for details",
            ]
        ),
    )

    result = doctor.check_flush_pipeline_correctness()

    assert result.ok is False
    assert "Last 24h: 1 failed flush Agent SDK exits" in result.detail
    assert "reader fatal raw: 1 in last 24h" in result.detail
    assert "salvaged post-result: 0 in last 24h" in result.detail


def test_wiki_cli_status_smoke_requires_daily_queue_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        doctor,
        "run_script_check",
        lambda script_name, args=None, timeout=30: (
            True,
            "\n".join(
                [
                    "Wiki Status:",
                    "  Articles: 325",
                    "  Daily logs: 23 (compile-worthy: 18, pending: 2, low-signal: 5)",
                    "  Last compile: 2026-04-26T18:29:21+00:00",
                    "  Total cost: $63.83",
                ]
            ),
        ),
    )

    result = doctor.check_wiki_cli_status_smoke()

    assert result.ok is True


def test_wiki_cli_status_smoke_flags_missing_daily_queue_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        doctor,
        "run_script_check",
        lambda script_name, args=None, timeout=30: (
            True,
            "\n".join(
                [
                    "Wiki Status:",
                    "  Articles: 325",
                    "  Daily logs: 23",
                    "  Last compile: 2026-04-26T18:29:21+00:00",
                    "  Total cost: $63.83",
                ]
            ),
        ),
    )

    result = doctor.check_wiki_cli_status_smoke()

    assert result.ok is False
    assert "compile-worthy:" in result.detail
    assert "low-signal:" in result.detail


def test_agent_sdk_account_access_passes_on_ok(monkeypatch) -> None:
    class FakeClaudeAgentOptions:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    async def fake_query(prompt: str, options: FakeClaudeAgentOptions):
        yield SimpleNamespace(content=[SimpleNamespace(text="OK")])

    fake_sdk = ModuleType("claude_agent_sdk")
    fake_sdk.ClaudeAgentOptions = FakeClaudeAgentOptions
    fake_sdk.query = fake_query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_sdk)
    monkeypatch.setattr(config_module, "WIKI_AGENT_BACKEND", "claude")

    result = doctor.check_agent_sdk_account_access()

    assert result.ok is True
    assert "returned OK" in result.detail


def test_agent_sdk_account_access_flags_auth_result(monkeypatch) -> None:
    class FakeClaudeAgentOptions:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class ResultMessage:
        is_error = True
        result = "Your organization does not have access to Claude."

    async def fake_query(prompt: str, options: FakeClaudeAgentOptions):
        yield ResultMessage()
        raise Exception("Command failed with exit code 1")

    fake_sdk = ModuleType("claude_agent_sdk")
    fake_sdk.ClaudeAgentOptions = FakeClaudeAgentOptions
    fake_sdk.query = fake_query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_sdk)
    monkeypatch.setattr(config_module, "WIKI_AGENT_BACKEND", "claude")

    result = doctor.check_agent_sdk_account_access()

    assert result.ok is False
    assert "does not have access to Claude" in result.detail


def test_total_tokens_injection_skips_when_account_access_unavailable(monkeypatch) -> None:
    class FakeClaudeAgentOptions:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class TextBlock:
        def __init__(self, text: str) -> None:
            self.text = text

    class AssistantMessage:
        def __init__(self, text: str) -> None:
            self.content = [TextBlock(text)]

    async def fake_query(prompt: str, options: FakeClaudeAgentOptions):
        yield AssistantMessage("Your organization does not have access to Claude.")
        raise Exception("Command failed with exit code 1")

    fake_sdk = ModuleType("claude_agent_sdk")
    fake_sdk.AssistantMessage = AssistantMessage
    fake_sdk.ClaudeAgentOptions = FakeClaudeAgentOptions
    fake_sdk.TextBlock = TextBlock
    fake_sdk.query = fake_query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_sdk)
    monkeypatch.setattr(config_module, "WIKI_AGENT_BACKEND", "claude")

    result = doctor.check_total_tokens_injection()

    assert result.ok is True
    assert "Skipped" in result.detail
    assert "agent_sdk_account_access" in result.detail


def test_agent_sdk_account_access_skips_manual_backend(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "WIKI_AGENT_BACKEND", "manual")

    result = doctor.check_agent_sdk_account_access()

    assert result.ok is True
    assert "WIKI_AGENT_BACKEND=manual" in result.detail


def test_total_tokens_injection_skips_manual_backend(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "WIKI_AGENT_BACKEND", "manual")

    result = doctor.check_total_tokens_injection()

    assert result.ok is True
    assert "WIKI_AGENT_BACKEND=manual" in result.detail


def test_flush_roundtrip_skips_manual_backend(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "WIKI_AGENT_BACKEND", "manual")

    result = doctor.check_flush_roundtrip()

    assert result.ok is True
    assert "WIKI_AGENT_BACKEND=manual" in result.detail
