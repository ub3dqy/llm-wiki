"""Regression tests for scripts/flush.py retry classification."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import claude_agent_sdk
import flush as flush_module
import pytest


@pytest.mark.parametrize(
    "message,expected",
    [
        pytest.param("operation timeout waiting for Agent SDK response", True, id="timeout"),
        pytest.param(
            "Fatal error in message reader: Command failed with exit code 1 (exit code: 1)",
            True,
            id="message-reader-fatal",
        ),
        pytest.param("Command failed with exit code 1", True, id="opaque-exit-1"),
        pytest.param("Command failed with exit code 2", False, id="opaque-exit-2"),
        pytest.param("authentication failed", False, id="auth-failure"),
        pytest.param(
            "authentication failed: Command failed with exit code 1",
            False,
            id="auth-failure-exit-1",
        ),
        pytest.param(
            "MCP config failed: Command failed with exit code 1",
            False,
            id="config-failure-exit-1",
        ),
    ],
)
def test_is_retryable_agent_sdk_error_from_message(message: str, expected: bool) -> None:
    assert flush_module._is_retryable_agent_sdk_error(Exception(message)) is expected


def test_is_retryable_agent_sdk_error_reads_stderr_attribute() -> None:
    error = Exception("wrapper error")
    error.stderr = "Fatal error in message reader: Command failed with exit code 1"  # type: ignore[attr-defined]

    assert flush_module._is_retryable_agent_sdk_error(error) is True


def test_run_flush_uses_streamed_result_when_sdk_fails_after_result(monkeypatch) -> None:
    appended: list[str] = []

    class ResultMessage:
        pass

    class FakeOptions:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    async def fake_query(**kwargs):
        yield SimpleNamespace(content=[SimpleNamespace(text="valuable summary")])
        yield ResultMessage()
        raise Exception("Command failed with exit code 1")

    def fake_append(content: str) -> Path:
        appended.append(content)
        return Path("/tmp/fake-daily.md")

    monkeypatch.setattr(claude_agent_sdk, "ClaudeAgentOptions", FakeOptions)
    monkeypatch.setattr(claude_agent_sdk, "query", fake_query)
    monkeypatch.setattr(flush_module, "append_to_daily_log", fake_append)

    asyncio.run(flush_module.run_flush("context", "session-id", "memory-claude"))

    assert appended == ["valuable summary"]


def test_run_flush_does_not_salvage_without_result_message(monkeypatch) -> None:
    appended: list[str] = []
    call_count = 0

    class FakeOptions:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    async def fake_query(**kwargs):
        nonlocal call_count
        call_count += 1
        yield SimpleNamespace(content=[SimpleNamespace(text="partial summary")])
        raise Exception("Command failed with exit code 1")

    def fake_append(content: str) -> Path:
        appended.append(content)
        return Path("/tmp/fake-daily.md")

    monkeypatch.setattr(claude_agent_sdk, "ClaudeAgentOptions", FakeOptions)
    monkeypatch.setattr(claude_agent_sdk, "query", fake_query)
    monkeypatch.setattr(flush_module, "append_to_daily_log", fake_append)

    asyncio.run(flush_module.run_flush("context", "session-id", "memory-claude"))

    assert call_count == 3
    assert appended == []
