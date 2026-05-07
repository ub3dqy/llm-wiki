"""Wiki CLI: unified command-line interface for LLM Wiki operations.

Usage:
    uv run python scripts/wiki_cli.py status            # show wiki statistics
    uv run python scripts/wiki_cli.py doctor            # run doctor quick checks
    uv run python scripts/wiki_cli.py doctor --full     # run full doctor gate
    uv run python scripts/wiki_cli.py compile [--all]    # compile daily logs
    uv run python scripts/wiki_cli.py compile --file daily/2026-04-10.md --mark-manual --manual-note "updated concepts/x"
    uv run python scripts/wiki_cli.py query "question"   # query the wiki
    uv run python scripts/wiki_cli.py query "question" --preview
    uv run python scripts/wiki_cli.py query "question" --save-answer-file answer.md --consulted concepts/foo
    uv run python scripts/wiki_cli.py lint               # run structural lint checks
    uv run python scripts/wiki_cli.py lint --full        # run full lint checks
    uv run python scripts/wiki_cli.py rebuild            # rebuild index
    uv run python scripts/wiki_cli.py seed <path>        # seed from project
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Add scripts/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ROOT_DIR, WIKI_DIR
from runtime_utils import find_uv
from utils import (
    build_article_metadata_map,
    daily_log_has_compile_signal,
    file_hash,
    list_daily_logs,
    list_wiki_articles,
    load_state,
)

SCRIPTS_DIR = Path(__file__).resolve().parent


def get_last_compile_marker(state: dict) -> str:
    """Return the most recent real compile timestamp from state."""
    ingested = state.get("ingested", {})
    compiled_at_values = [
        info.get("compiled_at", "")
        for info in ingested.values()
        if isinstance(info, dict) and info.get("compiled_at")
    ]
    if compiled_at_values:
        return max(compiled_at_values)
    return state.get("last_auto_compile_date", "never")


def build_daily_log_status(logs: list[Path], state: dict) -> dict[str, object]:
    """Summarize daily logs using the same signal rules as compile/lint."""
    ingested = state.get("ingested", {})
    compile_worthy = 0
    low_signal = 0
    pending: list[str] = []

    for log_path in logs:
        if not daily_log_has_compile_signal(log_path):
            low_signal += 1
            continue

        compile_worthy += 1
        prev = ingested.get(log_path.name, {})
        current_hash = file_hash(log_path)
        if not prev:
            pending.append(f"{log_path.name} (new)")
        elif prev.get("hash") != current_hash:
            pending.append(f"{log_path.name} (changed)")

    return {
        "total": len(logs),
        "compile_worthy": compile_worthy,
        "low_signal": low_signal,
        "pending": pending,
    }


def cmd_status() -> None:
    """Show wiki statistics."""
    articles = list_wiki_articles()
    meta = build_article_metadata_map()
    daily_logs = list_daily_logs()
    state: dict = load_state()
    daily_status = build_daily_log_status(daily_logs, state)

    # Count by type
    type_counts: dict[str, int] = {}
    for art in articles:
        rel = art.relative_to(WIKI_DIR)
        parts = str(rel).replace("\\", "/").split("/")
        section = parts[0] if len(parts) > 1 else "top-level"
        type_counts[section] = type_counts.get(section, 0) + 1

    # Count by project
    project_counts: dict[str, int] = {}
    untagged = 0
    for info in meta.values():
        projects = info.get("projects", [])
        if projects:
            for p in projects:
                project_counts[p] = project_counts.get(p, 0) + 1
        else:
            untagged += 1

    # Today's daily log entries
    today_entries = 0
    if daily_logs:
        latest = daily_logs[-1]
        content = latest.read_text(encoding="utf-8")
        today_entries = content.count("\n## [")

    print("Wiki Status:")
    print(f"  Articles: {len(articles)}", end="")
    if type_counts:
        parts = [f"{k}: {v}" for k, v in sorted(type_counts.items())]
        print(f" ({', '.join(parts)})")
    else:
        print()

    if project_counts:
        parts = [f"{k} ({v})" for k, v in sorted(project_counts.items())]
        if untagged:
            parts.append(f"untagged ({untagged})")
        print(f"  Projects: {', '.join(parts)}")

    daily_parts = [
        f"compile-worthy: {daily_status['compile_worthy']}",
        f"pending: {len(daily_status['pending'])}",
        f"low-signal: {daily_status['low_signal']}",
    ]
    if today_entries:
        daily_parts.insert(0, f"today: {today_entries} entries")
    print(f"  Daily logs: {len(daily_logs)} ({', '.join(daily_parts)})")

    pending_logs = daily_status["pending"]
    if pending_logs:
        print(f"  Pending compile: {', '.join(pending_logs)}")

    last_compile = get_last_compile_marker(state)
    last_lint = state.get("last_lint", "never")
    total_cost = state.get("total_cost", 0.0)

    print(f"  Last compile: {last_compile}")
    print(f"  Last lint: {last_lint}")
    print(f"  Total cost: ${total_cost:.2f}")


def run_script(script_name: str, extra_args: list[str] | None = None) -> int:
    """Run a wiki script via the current Python interpreter."""
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.call(cmd, cwd=str(ROOT_DIR))


def run_script_with_uv(script_name: str, extra_args: list[str] | None = None) -> int:
    """Run a wiki script via uv when project-only dependencies are required."""
    uv_bin = find_uv()
    if not uv_bin:
        print("uv not found; cannot run this command in full mode.", file=sys.stderr)
        return 1

    script_path = SCRIPTS_DIR / script_name
    cmd = [uv_bin, "run", "--directory", str(ROOT_DIR), "python", str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    if env.get("WSL_DISTRO_NAME"):
        env.setdefault("UV_PROJECT_ENVIRONMENT", str(Path.home() / ".cache" / "llm-wiki" / ".venv"))
        env.setdefault("UV_LINK_MODE", "copy")

    return subprocess.call(cmd, cwd=str(ROOT_DIR), env=env)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    extra = sys.argv[2:]

    if command == "status":
        cmd_status()
    elif command == "doctor":
        if not extra:
            extra = ["--quick"]
        run_script("doctor.py", extra)
    elif command == "compile":
        run_script("compile.py", extra)
    elif command == "query":
        run_script("query.py", extra)
    elif command == "lint":
        if not extra:
            extra = ["--structural-only"]
        elif "--full" in extra:
            extra = [x for x in extra if x != "--full"]
            run_script_with_uv("lint.py", extra)
            return
        elif "--fix" in extra:
            extra = [x for x in extra if x not in {"--fix", "--full"}]
            extra.append("--structural-only")
        run_script("lint.py", extra)
    elif command == "rebuild":
        run_script("rebuild_index.py", extra)
    elif command == "seed":
        run_script("seed.py", extra)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
