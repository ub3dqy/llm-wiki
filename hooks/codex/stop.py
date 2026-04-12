"""Codex Stop: capture transcript (analog of Claude SessionEnd).

CRITICAL differences from Claude SessionEnd:
- Stop fires after EVERY response, not just at session end -> strict debounce (60s)
- stop_hook_active field must be checked to avoid re-trigger loops
- Matcher is NOT used for Stop events
- Exit 0 expects JSON or empty stdout; plain text is invalid for this event
- MIN_TURNS higher (6 vs 4) because Stop fires much more frequently
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard: if spawned by flush.py (Agent SDK -> Claude Code -> hook), exit.
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = ROOT / "hooks"
SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(HOOKS_DIR))
from hook_utils import (  # noqa: E402
    check_debounce,
    extract_conversation_context,
    get_transcript_path,
    infer_project_name_from_cwd,
    parse_hook_stdin,
    update_debounce,
)

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [codex-stop] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MIN_TURNS_TO_FLUSH = 6
DEBOUNCE_SEC = 60
DEBOUNCE_FILE = SCRIPTS_DIR / ".last-flush-spawn"


def main() -> None:
    hook_input = parse_hook_stdin()
    if hook_input is None:
        logging.error("Failed to parse stdin")
        return

    session_id = hook_input.get("session_id", "unknown")
    turn_id = hook_input.get("turn_id", "unknown")
    cwd = hook_input.get("cwd", "")
    transcript_path_str = get_transcript_path(hook_input)

    logging.info("Stop fired: session=%s turn=%s", session_id, turn_id)

    if hook_input.get("stop_hook_active"):
        logging.info("SKIP: stop_hook_active already true")
        return

    if not transcript_path_str:
        logging.info("SKIP: no transcript path")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript missing: %s", transcript_path_str)
        return

    if not check_debounce(DEBOUNCE_FILE, debounce_sec=DEBOUNCE_SEC):
        logging.info("SKIP: debounce - too soon since last spawn")
        return

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as exc:
        logging.error("Context extraction failed: %s", exc)
        return

    if not context.strip():
        logging.info("SKIP: empty context")
        return

    if turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_TO_FLUSH)
        return

    project_name = infer_project_name_from_cwd(cwd, repo_root=ROOT) or "unknown"

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = SCRIPTS_DIR / f"session-flush-{session_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    flush_script = SCRIPTS_DIR / "flush.py"
    cmd = [
        "uv",
        "run",
        "--directory",
        str(ROOT),
        "python",
        str(flush_script),
        str(context_file),
        session_id,
        project_name,
    ]

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        update_debounce(DEBOUNCE_FILE)
        logging.info(
            "Spawned flush.py for session %s, project=%s (%d turns, %d chars)",
            session_id,
            project_name,
            turn_count,
            len(context),
        )
    except Exception as exc:
        logging.error("Failed to spawn flush.py: %s", exc)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Stop hook failed: %s", exc)
