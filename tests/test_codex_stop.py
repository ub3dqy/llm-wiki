from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def _load_stop_module(monkeypatch) -> ModuleType:
    monkeypatch.delenv("CLAUDE_INVOKED_BY", raising=False)
    module_path = ROOT / "hooks" / "codex" / "stop.py"
    spec = importlib.util.spec_from_file_location("codex_stop_for_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stop_worker_uses_shared_uv_runtime_env(monkeypatch, tmp_path) -> None:
    stop = _load_stop_module(monkeypatch)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_build_uv_python_cmd(script_path, extra_args=None, project_dir=None):
        captured["script_path"] = script_path
        captured["extra_args"] = extra_args
        captured["project_dir"] = project_dir
        return ["uv-test", "run", str(script_path), *(extra_args or [])], {"UV_TEST_ENV": "1"}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs

    monkeypatch.setattr(stop, "WIKI_AGENT_BACKEND", "claude")
    monkeypatch.setattr(stop, "WIKI_MIN_FLUSH_CHARS", 10)
    monkeypatch.setattr(stop, "SCRIPTS_DIR", tmp_path)
    monkeypatch.setattr(stop, "DEBOUNCE_FILE", tmp_path / ".last-flush-spawn")
    monkeypatch.setattr(
        stop,
        "parse_hook_stdin",
        lambda: {
            "session_id": "session-1",
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        },
    )
    monkeypatch.setattr(stop, "get_transcript_path", lambda payload: payload["transcript_path"])
    monkeypatch.setattr(stop, "extract_conversation_context", lambda _path: ("x" * 40, 2))
    monkeypatch.setattr(stop, "infer_project_name_from_cwd", lambda _cwd, repo_root=None: "proj")
    monkeypatch.setattr(stop, "build_uv_python_cmd", fake_build_uv_python_cmd)
    monkeypatch.setattr(stop.subprocess, "Popen", FakePopen)

    stop.main_worker()

    assert captured["script_path"] == tmp_path / "flush.py"
    assert captured["project_dir"] == stop.ROOT
    assert captured["extra_args"][1:] == ["session-1", "proj"]
    assert captured["cmd"][0] == "uv-test"
    assert captured["kwargs"]["env"] == {"UV_TEST_ENV": "1"}
    assert captured["kwargs"]["stderr"] == subprocess.STDOUT
    assert (tmp_path / ".last-flush-spawn").exists()


def test_stop_worker_removes_context_file_when_uv_is_missing(monkeypatch, tmp_path) -> None:
    stop = _load_stop_module(monkeypatch)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}", encoding="utf-8")

    def missing_uv(*_args, **_kwargs):
        raise FileNotFoundError("uv missing")

    def fail_popen(*_args, **_kwargs):  # pragma: no cover - should not be called
        raise AssertionError("Popen should not run when uv is missing")

    monkeypatch.setattr(stop, "WIKI_AGENT_BACKEND", "claude")
    monkeypatch.setattr(stop, "WIKI_MIN_FLUSH_CHARS", 10)
    monkeypatch.setattr(stop, "SCRIPTS_DIR", tmp_path)
    monkeypatch.setattr(stop, "DEBOUNCE_FILE", tmp_path / ".last-flush-spawn")
    monkeypatch.setattr(
        stop,
        "parse_hook_stdin",
        lambda: {
            "session_id": "session-1",
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        },
    )
    monkeypatch.setattr(stop, "get_transcript_path", lambda payload: payload["transcript_path"])
    monkeypatch.setattr(stop, "extract_conversation_context", lambda _path: ("x" * 40, 2))
    monkeypatch.setattr(stop, "infer_project_name_from_cwd", lambda _cwd, repo_root=None: "proj")
    monkeypatch.setattr(stop, "build_uv_python_cmd", missing_uv)
    monkeypatch.setattr(stop.subprocess, "Popen", fail_popen)

    stop.main_worker()

    assert list(tmp_path.glob("session-flush-*.md")) == []
    assert not (tmp_path / ".last-flush-spawn").exists()
