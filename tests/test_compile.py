from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import compile as compile_module
import pytest


def test_compile_daily_log_uses_noninteractive_agent_options(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "2026-04-27.md"
    log_path.write_text("# Daily Log\n\n## [2026-04-27T00:00:00+00:00]\n\nbody\n", encoding="utf-8")

    captured: dict[str, object] = {}

    class FakeClaudeAgentOptions:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    async def fake_query(prompt: str, options: FakeClaudeAgentOptions):
        captured["prompt"] = prompt
        captured["options"] = options
        yield SimpleNamespace(total_cost_usd=0.12)

    fake_sdk = ModuleType("claude_agent_sdk")
    fake_sdk.ClaudeAgentOptions = FakeClaudeAgentOptions
    fake_sdk.query = fake_query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_sdk)
    monkeypatch.delenv("CLAUDE_INVOKED_BY", raising=False)
    monkeypatch.setattr(compile_module, "WIKI_AGENT_BACKEND", "claude")
    monkeypatch.setattr(compile_module, "SCHEMA_FILE", tmp_path / "CLAUDE.md")
    monkeypatch.setattr(compile_module, "read_wiki_index", lambda: "# Index\n")
    monkeypatch.setattr(compile_module, "save_state", lambda state: None)

    state: dict = {}

    cost = asyncio.run(compile_module.compile_daily_log(log_path, state))

    options = captured["options"]
    assert cost == 0.12
    assert options.kwargs["extra_args"] == {"strict-mcp-config": None}
    assert callable(options.kwargs["stderr"])
    assert options.kwargs["allowed_tools"] == ["Read", "Write", "Edit", "Glob", "Grep"]
    assert state["ingested"][log_path.name]["cost_usd"] == 0.12
    assert "CLAUDE_INVOKED_BY" not in compile_module.os.environ


def test_compile_daily_log_raises_clear_error_on_agent_error_result(
    tmp_path: Path, monkeypatch
) -> None:
    log_path = tmp_path / "2026-04-27.md"
    log_path.write_text("# Daily Log\n\n## [2026-04-27T00:00:00+00:00]\n\nbody\n", encoding="utf-8")

    class FakeClaudeAgentOptions:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class ResultMessage:
        total_cost_usd = 0.0
        is_error = True
        result = "Your organization does not have access to Claude."

    async def fake_query(prompt: str, options: FakeClaudeAgentOptions):
        yield ResultMessage()

    fake_sdk = ModuleType("claude_agent_sdk")
    fake_sdk.ClaudeAgentOptions = FakeClaudeAgentOptions
    fake_sdk.query = fake_query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_sdk)
    monkeypatch.setenv("CLAUDE_INVOKED_BY", "outer")
    monkeypatch.setattr(compile_module, "WIKI_AGENT_BACKEND", "claude")
    monkeypatch.setattr(compile_module, "SCHEMA_FILE", tmp_path / "CLAUDE.md")
    monkeypatch.setattr(compile_module, "read_wiki_index", lambda: "# Index\n")
    monkeypatch.setattr(compile_module, "save_state", lambda state: None)

    state: dict = {}

    with pytest.raises(RuntimeError, match="does not have access to Claude"):
        asyncio.run(compile_module.compile_daily_log(log_path, state))

    assert "ingested" not in state
    assert compile_module.os.environ["CLAUDE_INVOKED_BY"] == "outer"


def test_compile_daily_log_refuses_manual_backend(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "2026-04-27.md"
    log_path.write_text("# Daily Log\n\n## [2026-04-27T00:00:00+00:00]\n\nbody\n", encoding="utf-8")
    monkeypatch.setattr(compile_module, "WIKI_AGENT_BACKEND", "manual")

    with pytest.raises(RuntimeError, match="WIKI_AGENT_BACKEND=claude"):
        asyncio.run(compile_module.compile_daily_log(log_path, {}))


def test_main_mark_manual_updates_state_without_agent(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "2026-05-02.md"
    log_path.write_text("# Daily Log\n\n## [2026-05-02T00:00:00+00:00]\n\nbody\n", encoding="utf-8")

    state: dict = {}
    saved_states: list[dict] = []

    monkeypatch.setattr(compile_module, "load_state", lambda: state)
    monkeypatch.setattr(compile_module, "save_state", lambda saved: saved_states.append(saved))
    monkeypatch.setattr(compile_module, "now_iso", lambda: "2026-05-03T00:00:00+00:00")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compile.py",
            "--file",
            str(log_path),
            "--mark-manual",
            "--manual-note",
            "updated architecture article and log",
        ],
    )

    compile_module.main()

    assert saved_states == [state]
    entry = state["ingested"][log_path.name]
    assert entry["hash"] == compile_module.file_hash(log_path)
    assert entry["compiled_at"] == "2026-05-03T00:00:00+00:00"
    assert entry["cost_usd"] == 0.0
    assert entry["compiled_by"] == "manual"
    assert entry["manual_note"] == "updated architecture article and log"
