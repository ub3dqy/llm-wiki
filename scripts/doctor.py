"""Doctor: verify the local wiki runtime and Codex hook setup.

Usage:
    uv run python scripts/doctor.py [--quick | --full]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

ROOT_DIR = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT_DIR / "hooks" / "codex"
WIKI_DIR = ROOT_DIR / "wiki"
INDEX_FILE = ROOT_DIR / "index.md"
SCRIPTS_DIR = ROOT_DIR / "scripts"
FLUSH_LOG = SCRIPTS_DIR / "flush.log"
CAPTURE_HEALTH_WINDOW_DAYS = 7
from runtime_utils import find_uv, is_wsl


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def has_bootstrap_articles() -> bool:
    if not WIKI_DIR.exists():
        return False
    return any(WIKI_DIR.rglob("*.md"))


def check_wiki_structure() -> CheckResult:
    expected_dirs = [
        WIKI_DIR / "concepts",
        WIKI_DIR / "connections",
        WIKI_DIR / "sources",
        WIKI_DIR / "entities",
        WIKI_DIR / "qa",
        WIKI_DIR / "analyses",
        ROOT_DIR / "daily",
        ROOT_DIR / "raw",
        ROOT_DIR / "reports",
    ]
    missing = [path for path in expected_dirs if not path.exists()]
    if missing or not INDEX_FILE.exists():
        detail = "wiki/ directories or index.md missing. Run: uv run python scripts/setup.py"
        return CheckResult("wiki_structure", False, detail)
    return CheckResult("wiki_structure", True, "Bootstrap files and directories are present")


def check_env_settings() -> CheckResult:
    try:
        from config import WIKI_COMPILE_AFTER_HOUR, WIKI_MAX_TURNS, WIKI_TIMEZONE

        ZoneInfo("UTC")

        raw_timezone = os.environ.get("WIKI_TIMEZONE", "").strip()
        timezone_key = getattr(WIKI_TIMEZONE, "key", str(WIKI_TIMEZONE))

        if not (0 <= WIKI_COMPILE_AFTER_HOUR <= 23):
            return CheckResult(
                "env_settings",
                False,
                f"WIKI_COMPILE_AFTER_HOUR={WIKI_COMPILE_AFTER_HOUR} out of range",
            )
        if WIKI_MAX_TURNS < 1:
            return CheckResult("env_settings", False, f"WIKI_MAX_TURNS={WIKI_MAX_TURNS} invalid")

        detail = f"timezone={timezone_key}, compile_hour={WIKI_COMPILE_AFTER_HOUR}"
        if raw_timezone and raw_timezone != timezone_key:
            detail += f" (warning: invalid WIKI_TIMEZONE={raw_timezone!r}, fell back to {timezone_key})"
        return CheckResult("env_settings", True, detail)
    except Exception as exc:  # noqa: BLE001
        return CheckResult("env_settings", False, f"Failed to load settings: {exc}")


SPAWN_CHARS_RE = re.compile(r"Spawned flush\.py .* \((\d+) turns, (\d+) chars\)")
SKIP_ONLY_CHARS_RE = re.compile(r"SKIP: only (\d+) chars \(min \d+\)")


@lru_cache(maxsize=1)
def _parse_flush_log_events() -> dict[str, object]:
    now = datetime.now()
    cutoff = now - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
    cutoff_24h = now - timedelta(hours=24)
    stats: dict[str, object] = {
        "fired": 0,
        "spawned": 0,
        "spawned_chars": 0,
        "skip_only_chars": 0,
        "fatal_errors": 0,
        "fatal_errors_24h": 0,
        "latest_fatal_ts": None,
    }

    text = FLUSH_LOG.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            ts = datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts < cutoff:
            continue

        tail = parts[3]
        if "[session-end]" in tail or "[pre-compact]" in tail:
            if "SessionEnd fired" in tail or "PreCompact fired" in tail:
                stats["fired"] = int(stats["fired"]) + 1
            elif "Spawned flush.py" in tail:
                stats["spawned"] = int(stats["spawned"]) + 1

            skip_match = SKIP_ONLY_CHARS_RE.search(tail)
            if skip_match:
                stats["skip_only_chars"] = int(stats["skip_only_chars"]) + int(skip_match.group(1))

        spawn_match = SPAWN_CHARS_RE.search(tail)
        if spawn_match:
            stats["spawned_chars"] = int(stats["spawned_chars"]) + int(spawn_match.group(2))

        if "Fatal error in message reader" in tail:
            stats["fatal_errors"] = int(stats["fatal_errors"]) + 1
            if ts >= cutoff_24h:
                stats["fatal_errors_24h"] = int(stats["fatal_errors_24h"]) + 1
            latest = stats["latest_fatal_ts"]
            if latest is None or ts > latest:
                stats["latest_fatal_ts"] = ts

    return stats


def check_flush_throughput() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_throughput",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_throughput", False, f"Could not read flush.log: {exc}")

    fired = int(stats["fired"])
    spawned = int(stats["spawned"])
    if fired == 0:
        return CheckResult(
            "flush_throughput",
            True,
            f"No SessionEnd/PreCompact events in last {CAPTURE_HEALTH_WINDOW_DAYS} days (possibly idle)",
        )

    skip_rate = 1.0 - (spawned / fired)
    detail = (
        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned}/{fired} flushes spawned "
        f"(skip rate {skip_rate:.0%})"
    )
    if spawned == 0:
        return CheckResult(
            "flush_throughput",
            False,
            f"{detail}. Pipeline appears broken: SessionEnds fired but nothing was spawned.",
        )
    if skip_rate > 0.85:
        return CheckResult(
            "flush_throughput",
            True,
            f"{detail} [attention: very high skip rate — possible pipeline issue, investigate flush.py]",
        )
    if skip_rate > 0.70:
        return CheckResult("flush_throughput", True, f"{detail} [info: moderate skip rate — monitor]")
    return CheckResult("flush_throughput", True, detail)


def check_flush_quality_coverage() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_quality_coverage",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_quality_coverage", False, f"Could not read flush.log: {exc}")

    spawned_chars = int(stats["spawned_chars"])
    skip_only_chars = int(stats["skip_only_chars"])
    attempted_chars = spawned_chars + skip_only_chars
    if attempted_chars == 0:
        return CheckResult(
            "flush_quality_coverage",
            True,
            f"No size-qualified capture candidates in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
        )

    quality_ratio = spawned_chars / attempted_chars
    detail = (
        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned_chars}/{attempted_chars} chars reached flush.py "
        f"(coverage {quality_ratio:.1%})"
    )
    if quality_ratio < 0.70:
        return CheckResult(
            "flush_quality_coverage",
            True,
            f"{detail} [attention: significant content filtered before flush.py]",
        )
    if quality_ratio < 0.85:
        return CheckResult(
            "flush_quality_coverage",
            True,
            f"{detail} [info: moderate content filtered before flush.py]",
        )
    return CheckResult("flush_quality_coverage", True, detail)


def check_flush_pipeline_correctness() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_pipeline_correctness", False, f"Could not read flush.log: {exc}")

    fatal_errors_7d = int(stats["fatal_errors"])
    fatal_errors_24h = int(stats["fatal_errors_24h"])
    latest_fatal_ts = stats["latest_fatal_ts"]
    if fatal_errors_7d == 0:
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            f"No 'Fatal error in message reader' events in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
        )

    latest_detail = (
        latest_fatal_ts.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(latest_fatal_ts, datetime)
        else "unknown"
    )
    if fatal_errors_24h == 0:
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            f"No 'Fatal error in message reader' events in last 24h "
            f"(historical: {fatal_errors_7d} in last {CAPTURE_HEALTH_WINDOW_DAYS}d, "
            f"most recent {latest_detail}, tracked in issue #16)",
        )

    return CheckResult(
        "flush_pipeline_correctness",
        False,
        f"Last 24h: {fatal_errors_24h} 'Fatal error in message reader' events "
        f"(7d total: {fatal_errors_7d}, most recent {latest_detail}) "
        f"— active Bug H regression, investigate issue #16",
    )


def check_total_tokens_injection() -> CheckResult:
    """Probe whether Anthropic's <total_tokens> injection is active on this account."""
    try:
        import asyncio
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
    except ImportError:
        return CheckResult("total_tokens_injection", True, "claude_agent_sdk not available, skipping")

    probe = (
        "Diagnostic check. Inspect your current input context and determine whether it contains "
        "a platform-injected <total_tokens> tag or a 'tokens left' counter. "
        "Reply with exactly one token: INJECTION_ACTIVE or INJECTION_NOT_ACTIVE. "
        "Do not include any explanation or extra text."
    )

    async def _run() -> str:
        result = ""
        async for message in query(
            prompt=probe,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                allowed_tools=[],
                max_turns=1,
                extra_args={"strict-mcp-config": None},
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result += block.text
        return result.strip()

    try:
        result_text = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "total_tokens_injection",
            True,
            f"Probe could not run: {type(exc).__name__}: {exc}. Not blocking — re-run when SDK path is healthy.",
        )

    normalized = result_text.strip().upper()
    if normalized == "INJECTION_ACTIVE":
        return CheckResult(
            "total_tokens_injection",
            False,
            "INJECTION DETECTED: model reported platform-level total_tokens/tokens-left marker in context. "
            "Apply workaround preamble to flush.py / compile.py. See issue #8.",
        )
    if normalized == "INJECTION_NOT_ACTIVE":
        return CheckResult(
            "total_tokens_injection",
            True,
            "NOT active — model does not observe <total_tokens> in its input context",
        )

    return CheckResult(
        "total_tokens_injection",
        True,
        f"Probe returned unexpected output: {result_text[:200]!r}. Treating as non-blocking; inspect manually if needed.",
    )

def check_python() -> CheckResult:
    version = sys.version_info
    detail = f"Python {version.major}.{version.minor}.{version.micro}"
    if version >= (3, 12):
        return CheckResult("python_version", True, detail)
    if version >= (3, 11):
        detail += " (doctor-compatible; project runtime is usually provided by uv)"
        return CheckResult("python_version", True, detail)
    return CheckResult("python_version", False, detail)


def check_uv() -> CheckResult:
    uv_bin = find_uv()
    if not uv_bin:
        return CheckResult("uv_binary", False, "uv not found in PATH or common install locations")
    return CheckResult("uv_binary", True, uv_bin)


def check_runtime_mode() -> CheckResult:
    if not is_wsl():
        return CheckResult("doctor_runtime", True, "Current shell is not WSL")

    active_venv = os.environ.get("VIRTUAL_ENV", "")
    repo_venv = str(ROOT_DIR / ".venv")
    if active_venv == repo_venv:
        detail = "Doctor is running from repo .venv inside WSL; prefer `python scripts/doctor.py`"
        return CheckResult("doctor_runtime", False, detail)

    return CheckResult("doctor_runtime", True, "Doctor is not using repo .venv in WSL")


def load_codex_config() -> tuple[dict, Path]:
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists() or tomllib is None:
        return {}, config_path
    return tomllib.loads(config_path.read_text(encoding="utf-8")), config_path


def check_codex_config() -> CheckResult:
    if not is_wsl():
        return CheckResult("codex_config", True, "Skipped outside WSL")

    config, config_path = load_codex_config()
    if not config_path.exists():
        return CheckResult("codex_config", False, f"Missing {config_path}")

    features = config.get("features", {})
    enabled = bool(features.get("codex_hooks"))
    if not enabled:
        return CheckResult("codex_config", False, f"codex_hooks is not enabled in {config_path}")

    return CheckResult("codex_config", True, f"codex_hooks=true in {config_path}")


def check_codex_hooks_file() -> CheckResult:
    if not is_wsl():
        return CheckResult("codex_hooks_json", True, "Skipped outside WSL")

    hooks_path = Path.home() / ".codex" / "hooks.json"
    if not hooks_path.exists():
        return CheckResult("codex_hooks_json", False, f"Missing {hooks_path}")

    try:
        text = hooks_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        return CheckResult("codex_hooks_json", False, f"Invalid JSON: {exc}")

    if "/root/.cache/llm-wiki/.venv" in text:
        return CheckResult("codex_hooks_json", False, "hooks.json still references /root/.cache/llm-wiki/.venv")

    hook_names = set((data.get("hooks") or {}).keys())
    expected = {"SessionStart", "Stop", "UserPromptSubmit", "PostToolUse"}
    missing = sorted(expected - hook_names)
    if missing:
        return CheckResult("codex_hooks_json", False, f"Missing hooks: {', '.join(missing)}")

    return CheckResult("codex_hooks_json", True, f"Found expected hooks in {hooks_path}")


def run_hook(script_name: str, payload: dict) -> tuple[bool, str]:
    script_path = HOOKS_DIR / script_name
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(ROOT_DIR),
        timeout=20,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or f"exit {proc.returncode}"
        return False, stderr
    return True, proc.stdout.strip()


def run_script_check(script_name: str, args: list[str] | None = None, timeout: int = 30) -> tuple[bool, str]:
    """Run a repo script with the current interpreter and return success plus output."""
    script_path = ROOT_DIR / "scripts" / script_name
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        cwd=str(ROOT_DIR),
        timeout=timeout,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        return False, detail
    return True, proc.stdout.strip()


def check_session_start_smoke() -> CheckResult:
    ok, output = run_hook(
        "session-start.py",
        {
            "hook_event_name": "SessionStart",
            "source": "startup",
            "cwd": str(ROOT_DIR),
        },
    )
    if not ok:
        return CheckResult("session_start_smoke", False, output)

    try:
        data = json.loads(output)
        context = data["hookSpecificOutput"]["additionalContext"]
        if not context.strip():
            return CheckResult("session_start_smoke", False, "Hook returned empty additionalContext")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("session_start_smoke", False, f"Invalid hook output: {exc}")

    return CheckResult("session_start_smoke", True, "SessionStart returned additionalContext")


def check_user_prompt_smoke() -> CheckResult:
    ok, output = run_hook(
        "user-prompt-wiki.py",
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "что wiki знает про llm-wiki-architecture",
            "cwd": str(ROOT_DIR),
        },
    )
    if not ok:
        return CheckResult("user_prompt_smoke", False, output)

    try:
        data = json.loads(output)
        context = data["hookSpecificOutput"]["additionalContext"]
        if "llm-wiki-architecture" not in context.lower():
            return CheckResult("user_prompt_smoke", False, "Relevant article was not injected")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("user_prompt_smoke", False, f"Invalid hook output: {exc}")

    return CheckResult("user_prompt_smoke", True, "UserPromptSubmit returned relevant article context")


def check_stop_smoke() -> CheckResult:
    ok, output = run_hook(
        "stop.py",
        {
            "hook_event_name": "Stop",
            "cwd": str(ROOT_DIR),
            "session_id": "doctor-session",
            "turn_id": "doctor-turn",
        },
    )
    if not ok:
        return CheckResult("stop_smoke", False, output)
    return CheckResult("stop_smoke", True, "Stop hook exited safely")


def check_flush_roundtrip() -> CheckResult:
    test_session_id = f"doctor-roundtrip-{uuid.uuid4().hex[:8]}"
    transcript_path = SCRIPTS_DIR / f"doctor-transcript-{test_session_id}.jsonl"
    marker_path = SCRIPTS_DIR / "flush-test-marker.txt"
    long_body = "This is a doctor roundtrip acceptance test. " * 60
    turns: list[str] = []

    for idx in range(6):
        role = "user" if idx % 2 == 0 else "assistant"
        turns.append(json.dumps({"message": {"role": role, "content": long_body}}))

    transcript_path.write_text("\n".join(turns) + "\n", encoding="utf-8")
    marker_path.unlink(missing_ok=True)

    hook_input = {
        "session_id": test_session_id,
        "source": "doctor-roundtrip",
        "transcript_path": str(transcript_path),
        "cwd": str(ROOT_DIR),
    }

    env = os.environ.copy()
    env["WIKI_FLUSH_TEST_MODE"] = "1"
    env.pop("CLAUDE_INVOKED_BY", None)

    session_end_script = ROOT_DIR / "hooks" / "session-end.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(session_end_script)],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
            env=env,
            cwd=str(ROOT_DIR),
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        transcript_path.unlink(missing_ok=True)
        return CheckResult("flush_roundtrip", False, "session-end.py timed out after 20s")
    except Exception as exc:  # noqa: BLE001
        transcript_path.unlink(missing_ok=True)
        return CheckResult("flush_roundtrip", False, f"Failed to invoke session-end.py: {exc}")
    finally:
        transcript_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        stderr = proc.stderr.strip()[:200]
        return CheckResult(
            "flush_roundtrip",
            False,
            f"session-end.py exited {proc.returncode}: {stderr}",
        )

    deadline = time.time() + 15
    while time.time() < deadline:
        if marker_path.exists():
            try:
                marker_content = marker_path.read_text(encoding="utf-8").strip()
            finally:
                marker_path.unlink(missing_ok=True)
            if test_session_id in marker_content:
                return CheckResult(
                    "flush_roundtrip",
                    True,
                    "session-end -> flush.py chain completed in test mode",
                )
            return CheckResult(
                "flush_roundtrip",
                False,
                f"Marker written for wrong session: {marker_content[:100]}",
            )
        time.sleep(0.3)

    return CheckResult("flush_roundtrip", False, "flush.py did not write test marker within 15s")


def check_index_health() -> CheckResult:
    ok, output = run_script_check("rebuild_index.py", ["--check"])
    if not ok:
        return CheckResult("index_health", False, output)
    detail = output or "Index is up to date"
    return CheckResult("index_health", True, detail)


def check_structural_lint() -> CheckResult:
    ok, output = run_script_check("lint.py", ["--structural-only"], timeout=60)
    if not ok:
        return CheckResult("structural_lint", False, output)

    summary = "Results:"
    detail = next((line.strip() for line in output.splitlines() if line.startswith(summary)), "")
    if not detail:
        detail = "Structural lint passed"
    return CheckResult("structural_lint", True, detail)


def check_query_preview_smoke() -> CheckResult:
    if not has_bootstrap_articles():
        return CheckResult("query_preview_smoke", True, "Skipped on bootstrap-only wiki (no articles yet)")

    ok, output = run_script_check(
        "query.py",
        ["что wiki знает про llm-wiki-architecture", "--preview"],
        timeout=30,
    )
    if not ok:
        return CheckResult("query_preview_smoke", False, output)

    lowered = output.lower()
    if "query preview" not in lowered:
        return CheckResult("query_preview_smoke", False, "Preview header missing")
    if "llm-wiki-architecture" not in lowered:
        return CheckResult("query_preview_smoke", False, "Relevant article missing from preview")
    if "confidence:" not in lowered:
        return CheckResult("query_preview_smoke", False, "Preview does not expose confidence metadata")

    return CheckResult("query_preview_smoke", True, "Query preview returned provenance-aware candidates")


def check_wiki_cli_query_preview_smoke() -> CheckResult:
    if not has_bootstrap_articles():
        return CheckResult(
            "wiki_cli_query_preview_smoke",
            True,
            "Skipped on bootstrap-only wiki (no articles yet)",
        )

    ok, output = run_script_check(
        "wiki_cli.py",
        ["query", "что wiki знает про llm-wiki-architecture", "--preview"],
        timeout=30,
    )
    if not ok:
        return CheckResult("wiki_cli_query_preview_smoke", False, output)

    lowered = output.lower()
    if "query preview" not in lowered:
        return CheckResult("wiki_cli_query_preview_smoke", False, "Preview header missing from wiki_cli route")
    if "llm-wiki-architecture" not in lowered:
        return CheckResult("wiki_cli_query_preview_smoke", False, "Relevant article missing from wiki_cli preview")
    if "confidence:" not in lowered:
        return CheckResult("wiki_cli_query_preview_smoke", False, "wiki_cli preview does not expose confidence metadata")

    return CheckResult(
        "wiki_cli_query_preview_smoke",
        True,
        "wiki_cli query preview returned provenance-aware candidates",
    )


def check_wiki_cli_status_smoke() -> CheckResult:
    ok, output = run_script_check("wiki_cli.py", ["status"], timeout=30)
    if not ok:
        return CheckResult("wiki_cli_status_smoke", False, output)

    lowered = output.lower()
    required_markers = ("wiki status:", "articles:", "last compile:", "total cost:")
    missing = [marker for marker in required_markers if marker not in lowered]
    if missing:
        return CheckResult(
            "wiki_cli_status_smoke",
            False,
            f"Missing expected status markers: {', '.join(missing)}",
        )

    return CheckResult("wiki_cli_status_smoke", True, "wiki_cli status returned expected summary fields")


def check_wiki_cli_lint_smoke() -> CheckResult:
    ok, output = run_script_check("wiki_cli.py", ["lint", "--structural-only"], timeout=60)
    if not ok:
        return CheckResult("wiki_cli_lint_smoke", False, output)

    lowered = output.lower()
    if "running knowledge base lint checks" not in lowered:
        return CheckResult("wiki_cli_lint_smoke", False, "Lint header missing from wiki_cli route")
    if "results:" not in lowered:
        return CheckResult("wiki_cli_lint_smoke", False, "wiki_cli structural lint summary missing")
    if "0 errors" not in lowered:
        return CheckResult("wiki_cli_lint_smoke", False, "wiki_cli structural lint reported blocking errors")

    return CheckResult("wiki_cli_lint_smoke", True, "wiki_cli structural lint reported zero blocking errors")


def check_wiki_cli_rebuild_check_smoke() -> CheckResult:
    ok, output = run_script_check("wiki_cli.py", ["rebuild", "--check"], timeout=30)
    if not ok:
        return CheckResult("wiki_cli_rebuild_check_smoke", False, output)

    lowered = output.lower()
    if "index is up to date" not in lowered:
        return CheckResult(
            "wiki_cli_rebuild_check_smoke",
            False,
            "wiki_cli rebuild --check did not confirm index freshness",
        )

    return CheckResult(
        "wiki_cli_rebuild_check_smoke",
        True,
        "wiki_cli rebuild --check confirmed index freshness",
    )


def check_path_normalization() -> CheckResult:
    hooks_dir = ROOT_DIR / "hooks"
    sys.path.insert(0, str(hooks_dir))
    from hook_utils import infer_project_name_from_cwd  # noqa: WPS433

    cases = {
        r"D:\workspace\example\example-project": "example-project",
        "/mnt/d/workspace/example/example-project": "example-project",
        "/d/workspace/example/example-project": "example-project",
        r"D:\workspace\example\example-other": "example-other",
    }

    failures: list[str] = []
    for raw_path, expected in cases.items():
        actual = infer_project_name_from_cwd(raw_path, repo_root=ROOT_DIR)
        if actual != expected:
            failures.append(f"{raw_path} -> {actual!r} (expected {expected!r})")

    repo_cases = [
        str(ROOT_DIR),
        str(ROOT_DIR).replace("\\", "/"),
    ]
    for raw_path in repo_cases:
        actual = infer_project_name_from_cwd(raw_path, repo_root=ROOT_DIR)
        if actual is not None:
            failures.append(f"{raw_path} -> {actual!r} (expected None)")

    if failures:
        return CheckResult("path_normalization", False, "; ".join(failures))

    return CheckResult("path_normalization", True, "Windows, WSL, Git Bash, and repo-root cwd cases passed")


def print_result(result: CheckResult) -> None:
    prefix = "PASS" if result.ok else "FAIL"
    print(f"[{prefix}] {result.name}: {result.detail}")


def get_quick_checks() -> list[CheckResult]:
    return [
        check_wiki_structure(),
        check_env_settings(),
        check_flush_throughput(),
        check_flush_quality_coverage(),
        check_flush_pipeline_correctness(),
        check_python(),
        check_uv(),
        check_index_health(),
        check_structural_lint(),
        check_query_preview_smoke(),
        check_wiki_cli_query_preview_smoke(),
        check_wiki_cli_status_smoke(),
        check_wiki_cli_lint_smoke(),
        check_wiki_cli_rebuild_check_smoke(),
        check_path_normalization(),
    ]


def get_full_checks() -> list[CheckResult]:
    return [
        check_wiki_structure(),
        check_env_settings(),
        check_flush_throughput(),
        check_flush_quality_coverage(),
        check_flush_pipeline_correctness(),
        check_python(),
        check_uv(),
        check_runtime_mode(),
        check_codex_config(),
        check_codex_hooks_file(),
        check_index_health(),
        check_structural_lint(),
        check_query_preview_smoke(),
        check_wiki_cli_query_preview_smoke(),
        check_wiki_cli_status_smoke(),
        check_wiki_cli_lint_smoke(),
        check_wiki_cli_rebuild_check_smoke(),
        check_path_normalization(),
        check_session_start_smoke(),
        check_user_prompt_smoke(),
        check_stop_smoke(),
        check_flush_roundtrip(),
        check_total_tokens_injection(),
    ]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the local wiki runtime and Codex hook setup")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run only the fast daily checks")
    mode.add_argument("--full", action="store_true", help="Run the full gate, including hook and WSL-specific checks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checks = get_quick_checks() if args.quick else get_full_checks()

    failed = False
    for result in checks:
        print_result(result)
        failed = failed or not result.ok
        if result.name == "wiki_structure" and not result.ok:
            sys.exit(1)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
