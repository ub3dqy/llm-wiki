"""Wiki CLI: unified command-line interface for LLM Wiki operations.

Usage:
    uv run python scripts/wiki_cli.py status            # show wiki statistics
    uv run python scripts/wiki_cli.py doctor            # run doctor quick checks
    uv run python scripts/wiki_cli.py doctor --full     # run full doctor gate
    uv run python scripts/wiki_cli.py compile [--all]    # compile daily logs
    uv run python scripts/wiki_cli.py query "question"   # query the wiki
    uv run python scripts/wiki_cli.py query "question" --preview
    uv run python scripts/wiki_cli.py lint               # run structural lint checks
    uv run python scripts/wiki_cli.py lint --full        # run full lint checks
    uv run python scripts/wiki_cli.py rebuild            # rebuild index
    uv run python scripts/wiki_cli.py seed <path>        # seed from project
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Add scripts/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ROOT_DIR, STATE_FILE, WIKI_DIR
from runtime_utils import find_uv
from utils import build_article_metadata_map, list_daily_logs, list_wiki_articles

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


def cmd_status() -> None:
    """Show wiki statistics."""
    articles = list_wiki_articles()
    meta = build_article_metadata_map()
    daily_logs = list_daily_logs()

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

    # Load state
    state: dict = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

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

    print(f"  Daily logs: {len(daily_logs)}", end="")
    if today_entries:
        print(f" (today: {today_entries} entries)")
    else:
        print()

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
