"""PreCompact hook: capture transcript before context compaction.

Uses the same content-length threshold as session-end.py so short but meaningful
CLI sessions can still be captured when they carry enough substance.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Recursion guard
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from config import (  # noqa: E402
    WIKI_MAX_CONTEXT_CHARS as MAX_CONTEXT_CHARS,
    WIKI_MAX_TURNS as MAX_TURNS,
    WIKI_MIN_FLUSH_CHARS,
    WIKI_TIMEZONE,
)

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
    format="%(asctime)s %(levelname)s [pre-compact] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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

    content_len = len(context.strip())
    if content_len < WIKI_MIN_FLUSH_CHARS:
        logging.info("SKIP: only %d chars (min %d)", content_len, WIKI_MIN_FLUSH_CHARS)
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

    # Capture child startup errors instead of dropping them to DEVNULL.
    subprocess_log = SCRIPTS_DIR / "flush-subprocess.log"
    try:
        subproc_log_fp = open(subprocess_log, "a", encoding="utf-8", buffering=1)
    except OSError as log_err:
        logging.warning("Could not open subprocess log (%s); falling back to DEVNULL", log_err)
        subproc_log_fp = None

    stdout_target = subproc_log_fp if subproc_log_fp is not None else subprocess.DEVNULL
    stderr_target = subprocess.STDOUT if subproc_log_fp is not None else subprocess.DEVNULL

    try:
        subprocess.Popen(
            cmd,
            stdout=stdout_target,
            stderr=stderr_target,
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
    finally:
        if subproc_log_fp is not None:
            subproc_log_fp.close()

    # NOTE: PreCompact does NOT support additionalContext in hookSpecificOutput.
    # Only UserPromptSubmit and PostToolUse do. Wiki context is re-injected
    # via SessionStart hook which fires after compaction (source: "compact").


if __name__ == "__main__":
    main()
