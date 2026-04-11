"""PostToolUse async hook: capture micro-entries from interesting tool executions.

Runs asynchronously (non-blocking). Captures git commits, test runs,
and other significant Bash commands as micro-entries in the daily log.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
SCRIPTS_DIR = ROOT / "scripts"
DEBOUNCE_FILE = SCRIPTS_DIR / ".last-tool-capture"
DEBOUNCE_SEC = 30

# Patterns that indicate interesting Bash commands
INTERESTING_PATTERNS = [
    ("git commit", "Git commit"),
    ("git merge", "Git merge"),
    ("git rebase", "Git rebase"),
    ("npm test", "Test run (npm)"),
    ("npx jest", "Test run (jest)"),
    ("pytest", "Test run (pytest)"),
    ("npm run build", "Build"),
    ("npm run dev", "Dev server"),
    ("docker compose up", "Docker compose"),
    ("prisma migrate", "DB migration"),
    ("prisma db push", "DB push"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _today_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def check_debounce() -> bool:
    """Return True if enough time has passed since last capture."""
    if not DEBOUNCE_FILE.exists():
        return True
    try:
        last = float(DEBOUNCE_FILE.read_text(encoding="utf-8").strip())
        return (time.time() - last) >= DEBOUNCE_SEC
    except (ValueError, OSError):
        return True


def update_debounce() -> None:
    """Record current time."""
    try:
        DEBOUNCE_FILE.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def classify_command(cmd: str) -> str | None:
    """Check if a Bash command is interesting. Returns label or None."""
    cmd_lower = cmd.lower().strip()
    for pattern, label in INTERESTING_PATTERNS:
        if pattern in cmd_lower:
            return label
    return None


def append_micro_entry(label: str, command: str, project: str) -> None:
    """Append a micro-entry to today's daily log."""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    today = _today_iso()
    log_path = DAILY_DIR / f"{today}.md"

    if not log_path.exists():
        log_path.write_text(
            f"---\ntitle: Daily Log {today}\ntype: daily\ndate: {today}\n---\n\n"
            f"# Daily Log — {today}\n\n",
            encoding="utf-8",
        )

    timestamp = _now_iso()
    entry = (
        f"\n## [{timestamp}] tool-capture\n\n"
        f"- **{label}**: `{command[:200]}`\n"
        f"- Project: {project}\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, ValueError, EOFError):
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return

    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")
    if not command:
        return

    label = classify_command(command)
    if not label:
        return

    if not check_debounce():
        return

    cwd = hook_input.get("cwd", "")
    project = Path(cwd).name if cwd else "unknown"

    append_micro_entry(label, command, project)
    update_debounce()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block tool execution due to hook errors
        pass
