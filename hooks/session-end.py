"""SessionEnd hook: capture conversation transcript and spawn flush.py.

Extracts the last N turns from the transcript JSONL, saves to a temp file,
and launches flush.py as a detached background process.

Includes debounce to prevent cascading spawns when many sessions end at once.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Recursion guard: if spawned by flush.py (Agent SDK → Claude Code → hook), exit.
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from config import WIKI_MAX_CONTEXT_CHARS as MAX_CONTEXT_CHARS, WIKI_MAX_TURNS as MAX_TURNS, WIKI_TIMEZONE  # noqa: E402

# Import shared extraction logic
sys.path.insert(0, str(ROOT / "hooks"))
from hook_utils import (  # noqa: E402
    check_debounce,
    extract_conversation_context,
    infer_project_name_from_cwd,
    parse_hook_stdin,
    update_debounce,
)
from runtime_utils import build_uv_python_cmd  # noqa: E402

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [session-end] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MIN_TURNS_TO_FLUSH = 4
DEBOUNCE_FILE = SCRIPTS_DIR / ".last-flush-spawn"


def main() -> None:
    hook_input = parse_hook_stdin()
    if hook_input is None:
        logging.error("Failed to parse stdin")
        return

    session_id = hook_input.get("session_id", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", "")

    logging.info("SessionEnd fired: session=%s", session_id)

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
        context, turn_count = extract_conversation_context(
            transcript_path,
            max_turns=MAX_TURNS,
            max_chars=MAX_CONTEXT_CHARS,
        )
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
    project_name = infer_project_name_from_cwd(cwd, repo_root=ROOT) or "unknown"

    # Save context to temp file for flush.py
    timestamp = datetime.now(WIKI_TIMEZONE).strftime("%Y%m%d-%H%M%S")
    context_file = SCRIPTS_DIR / f"session-flush-{session_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    flush_script = SCRIPTS_DIR / "flush.py"

    try:
        cmd, env = build_uv_python_cmd(
            flush_script,
            [str(context_file), session_id, project_name],
            project_dir=ROOT,
        )
    except FileNotFoundError as e:
        logging.error("Failed to locate uv for flush.py: %s", e)
        context_file.unlink(missing_ok=True)
        return

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
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


if __name__ == "__main__":
    main()
