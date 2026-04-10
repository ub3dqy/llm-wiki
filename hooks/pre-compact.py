"""PreCompact hook: capture transcript before context compaction.

Same logic as session-end.py but with a higher turn threshold (5 vs 4),
since compaction happens mid-session and short conversations aren't worth capturing.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"

# Import shared extraction logic
sys.path.insert(0, str(ROOT / "hooks"))
from hook_utils import check_debounce, extract_conversation_context, parse_hook_stdin, update_debounce

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [pre-compact] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MIN_TURNS_TO_FLUSH = 5
DEBOUNCE_FILE = SCRIPTS_DIR / ".last-flush-spawn"


def main() -> None:
    hook_input = parse_hook_stdin()
    if hook_input is None:
        logging.error("Failed to parse stdin")
        return

    session_id = hook_input.get("session_id", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", "")

    logging.info("PreCompact fired: session=%s", session_id)

    if not transcript_path_str or not isinstance(transcript_path_str, str):
        logging.info("SKIP: no transcript path")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript missing: %s", transcript_path_str)
        return

    # Debounce: prevent cascading spawns
    if not check_debounce(DEBOUNCE_FILE):
        logging.info("SKIP: debounce — too soon since last spawn")
        return

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip():
        logging.info("SKIP: empty context")
        return

    if turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_TO_FLUSH)
        return

    # Derive project name from cwd
    project_name = Path(cwd).name if cwd else "unknown"

    # Save context to temp file for flush.py
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
    except Exception as e:
        logging.error("Failed to spawn flush.py: %s", e)

    # NOTE: PreCompact does NOT support additionalContext in hookSpecificOutput.
    # Only UserPromptSubmit and PostToolUse do. Wiki context is re-injected
    # via SessionStart hook which fires after compaction (source: "compact").


if __name__ == "__main__":
    main()
