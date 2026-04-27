"""Regression tests for scripts/flush.py retry classification."""

from __future__ import annotations

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
        pytest.param("Command failed with exit code 1", False, id="generic-exit-1"),
        pytest.param("authentication failed", False, id="auth-failure"),
    ],
)
def test_is_retryable_agent_sdk_error_from_message(message: str, expected: bool) -> None:
    assert flush_module._is_retryable_agent_sdk_error(Exception(message)) is expected


def test_is_retryable_agent_sdk_error_reads_stderr_attribute() -> None:
    error = Exception("wrapper error")
    error.stderr = "Fatal error in message reader: Command failed with exit code 1"  # type: ignore[attr-defined]

    assert flush_module._is_retryable_agent_sdk_error(error) is True
