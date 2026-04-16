"""Bootstrap a fresh clone into a usable local wiki workspace.

Usage:
    uv run python scripts/setup.py [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT_DIR / "wiki"
INDEX_EXAMPLE = ROOT_DIR / "index.example.md"
INDEX_FILE = ROOT_DIR / "index.md"
LOG_FILE = ROOT_DIR / "log.md"
ALIASES_EXAMPLE = ROOT_DIR / "scripts" / "project_aliases.example.json"
ALIASES_LOCAL = ROOT_DIR / "scripts" / "project_aliases.local.json"
ENV_EXAMPLE = ROOT_DIR / ".env.example"
ENV_LOCAL = ROOT_DIR / ".env"

DIRECTORIES = [
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

MINIMAL_LOG = "# Wiki Operations Log\n\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the wiki structure for a fresh clone")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be created without writing files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate index.md and project_aliases.local.json from examples",
    )
    return parser.parse_args()


def announce(action: str, path: Path, extra: str = "") -> None:
    message = f"[{action}] {path}"
    if extra:
        message = f"{message} {extra}"
    print(message)


def ensure_directory(path: Path, dry_run: bool) -> None:
    if path.exists():
        announce("skip", path, "already exists")
        return
    announce("create", path)
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)


def ensure_copy(src: Path, dst: Path, dry_run: bool, force: bool) -> bool:
    if dst.exists() and not force:
        announce("skip", dst, "already exists")
        return False
    if not src.exists():
        announce("warn", src, "missing example file; cannot copy")
        return False
    action = "overwrite" if dst.exists() and force else "create"
    announce(action, dst, f"from {src.name}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return True


def ensure_log(path: Path, dry_run: bool) -> None:
    if path.exists():
        announce("skip", path, "already exists")
        return
    announce("create", path)
    if not dry_run:
        path.write_text(MINIMAL_LOG, encoding="utf-8")


def sync_index(dry_run: bool) -> bool:
    if dry_run:
        announce("sync", INDEX_FILE, "(dry-run via rebuild_index.py)")
        return True

    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "rebuild_index.py")]
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        cwd=str(ROOT_DIR),
        timeout=30,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "rebuild_index.py failed"
        announce("warn", INDEX_FILE, detail)
        return False

    detail = proc.stdout.strip() or "index synced"
    announce("sync", INDEX_FILE, detail)
    return True


def check_claude_agent_sdk() -> bool:
    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError:
        return False
    return True


def print_next_steps(repo_root: Path) -> None:
    repo_path = str(repo_root.resolve())
    print()
    print(f"[ok] Wiki structure ready at {repo_path}")
    print()
    print("Next steps:")
    print("0. Review your .env file (created from .env.example):")
    print("   cat .env")
    print("   Adjust WIKI_TIMEZONE, WIKI_COMPILE_AFTER_HOUR etc. to your preferences.")
    print("1. Add hooks to your ~/.claude/settings.json:")
    print("   See settings.example.json - replace /path/to/llm-wiki with:")
    print(f"   {repo_path}")
    print("2. Copy the /wiki-save skill:")
    print("   cp -r skills/wiki-save ~/.claude/skills/wiki-save")
    print("   Then edit ~/.claude/skills/wiki-save/SKILL.md and replace")
    print(f"   /path/to/llm-wiki with: {repo_path}")
    print("3. (Optional, for Codex users) Copy codex-hooks.template.json to")
    print("   ~/.codex/hooks.json and replace /path/to/llm-wiki with:")
    print(f"   {repo_path}")
    print("4. Verify the install:")
    print("   uv run python scripts/doctor.py --quick")


def main() -> int:
    args = parse_args()
    ok = True

    for directory in DIRECTORIES:
        ensure_directory(directory, dry_run=args.dry_run)

    index_changed = ensure_copy(INDEX_EXAMPLE, INDEX_FILE, dry_run=args.dry_run, force=args.force)
    ensure_log(LOG_FILE, dry_run=args.dry_run)
    ensure_copy(ALIASES_EXAMPLE, ALIASES_LOCAL, dry_run=args.dry_run, force=args.force)
    ensure_copy(ENV_EXAMPLE, ENV_LOCAL, dry_run=args.dry_run, force=args.force)

    if index_changed:
        ok = sync_index(dry_run=args.dry_run) and ok

    sdk_available = check_claude_agent_sdk()
    if not sdk_available:
        print("[warn] claude_agent_sdk not available. Run: uv sync")
        ok = False

    print_next_steps(ROOT_DIR)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
