"""Doctor: verify the local wiki runtime and Codex hook setup.

Usage:
    uv run python scripts/doctor.py [--quick | --full]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

ROOT_DIR = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT_DIR / "hooks" / "codex"
WIKI_DIR = ROOT_DIR / "wiki"
INDEX_FILE = ROOT_DIR / "index.md"
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
    if "results: 0 errors, 0 warnings, 0 suggestions" not in lowered:
        return CheckResult("wiki_cli_lint_smoke", False, "wiki_cli structural lint did not report a clean result")

    return CheckResult("wiki_cli_lint_smoke", True, "wiki_cli structural lint returned a clean report")


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
