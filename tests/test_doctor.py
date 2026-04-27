"""Regression tests for doctor flush pipeline classification."""

from __future__ import annotations

from datetime import datetime

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


def test_flush_pipeline_correctness_counts_unsalvaged_query_failure(
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
