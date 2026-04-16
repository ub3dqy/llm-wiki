"""Codex Stop: capture transcript (analog of Claude SessionEnd).

CRITICAL differences from Claude SessionEnd:
- Stop fires after EVERY response, not just at session end -> strict debounce (60s)
- stop_hook_active field must be checked to avoid re-trigger loops
- Matcher is NOT used for Stop events
- Exit 0 always emits valid JSON on stdout; plain text is invalid for this event
- Uses char-based gating to match the main capture pipeline
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Recursion guard: if spawned by flush.py (Agent SDK -> Claude Code -> hook), exit.
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = ROOT / "hooks"
SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from config import WIKI_MIN_FLUSH_CHARS, WIKI_TIMEZONE  # noqa: E402

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

DEBOUNCE_SEC = 60
DEBOUNCE_FILE = SCRIPTS_DIR / ".last-flush-spawn"


def _detach_stdout() -> None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except OSError:
        pass


def _emit_ok(message: str | None = None) -> None:
    """Emit valid Stop hook JSON output, defensive against closed stdout."""
    payload: dict[str, str] = {}
    if message:
        payload["systemMessage"] = message
    try:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    except (BrokenPipeError, OSError):
        _detach_stdout()
        pass


def _spawn_worker(hook_input: dict) -> None:
    subprocess_log = SCRIPTS_DIR / "flush-subprocess.log"
    try:
        subproc_log_fp = open(subprocess_log, "a", encoding="utf-8", buffering=1)
    except OSError as log_err:
        logging.warning("Could not open subprocess log (%s); falling back to DEVNULL", log_err)
        subproc_log_fp = None

    stdout_target = subproc_log_fp if subproc_log_fp is not None else subprocess.DEVNULL
    stderr_target = subprocess.STDOUT if subproc_log_fp is not None else subprocess.DEVNULL

    try:
        worker = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            stdin=subprocess.PIPE,
            stdout=stdout_target,
            stderr=stderr_target,
            start_new_session=True,
        )
    finally:
        if subproc_log_fp is not None:
            subproc_log_fp.close()
    if worker.stdin is None:
        raise RuntimeError("worker stdin pipe not created")
    worker.stdin.write(json.dumps(hook_input, ensure_ascii=False).encode("utf-8"))
    worker.stdin.close()


def main_light() -> None:
    hook_input = parse_hook_stdin()
    if hook_input is None:
        logging.error("Failed to parse stdin")
        _emit_ok()
        return

    session_id = hook_input.get("session_id", "unknown")
    turn_id = hook_input.get("turn_id", "unknown")
    transcript_path_str = get_transcript_path(hook_input)
    last_assistant_message = hook_input.get("last_assistant_message")
    logging.info("Stop fired: session=%s turn=%s", session_id, turn_id)

    if hook_input.get("stop_hook_active"):
        logging.info("SKIP: stop_hook_active already true")
        _emit_ok()
        return

    if not transcript_path_str:
        if isinstance(last_assistant_message, str) and last_assistant_message.strip():
            pass
        else:
            logging.info("SKIP: no transcript path and no last_assistant_message")
            _emit_ok()
            return

    if not check_debounce(DEBOUNCE_FILE, debounce_sec=DEBOUNCE_SEC):
        logging.info("SKIP: debounce - too soon since last spawn")
        _emit_ok()
        return

    try:
        _spawn_worker(hook_input)
        logging.info("Spawned detached worker for session %s", session_id)
    except Exception as exc:
        logging.error("Failed to spawn detached worker: %s", exc)
        _emit_ok()
        return

    _emit_ok()


def main_worker() -> None:
    hook_input = parse_hook_stdin()
    if hook_input is None:
        logging.error("[stop-worker] failed to parse stdin payload")
        return

    session_id = hook_input.get("session_id", "unknown")
    cwd = hook_input.get("cwd", "")
    transcript_path_str = get_transcript_path(hook_input)
    last_assistant_message = hook_input.get("last_assistant_message")
    degraded_mode = False
    degraded_min = max(50, WIKI_MIN_FLUSH_CHARS // 4)

    logging.info("[stop-worker] started session=%s", session_id)

    if not transcript_path_str:
        if isinstance(last_assistant_message, str) and last_assistant_message.strip():
            degraded_mode = True
        else:
            logging.info("[stop-worker] SKIP: no transcript path and no last_assistant_message")
            return

    if degraded_mode:
        context = f"**Assistant (degraded, last-message-only):** {last_assistant_message.strip()}\n"
        turn_count = 1
        logging.info("[stop-worker] DEGRADED: using last_assistant_message fallback")
    else:
        transcript_path = Path(transcript_path_str)
        if not transcript_path.exists():
            logging.info("[stop-worker] SKIP: transcript missing: %s", transcript_path_str)
            return

        try:
            context, turn_count = extract_conversation_context(transcript_path)
        except Exception as exc:
            logging.error("[stop-worker] Context extraction failed: %s", exc)
            return

    content_len = len(context.strip())
    if content_len == 0:
        logging.info("[stop-worker] SKIP: empty context (entries=%d)", turn_count)
        return

    min_chars = degraded_min if degraded_mode else WIKI_MIN_FLUSH_CHARS
    if content_len < min_chars:
        if degraded_mode:
            logging.info(
                "[stop-worker] SKIP: degraded too short (%d chars, min %d)", content_len, min_chars
            )
        else:
            logging.info(
                "[stop-worker] SKIP: only %d chars (min %d)", content_len, WIKI_MIN_FLUSH_CHARS
            )
        return

    project_name = infer_project_name_from_cwd(cwd, repo_root=ROOT) or "unknown"

    timestamp = datetime.now(WIKI_TIMEZONE).strftime("%Y%m%d-%H%M%S")
    if degraded_mode:
        context_file = SCRIPTS_DIR / f"session-flush-DEGRADED-{session_id}-{timestamp}.md"
    else:
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
            creationflags=creation_flags,
        )
        update_debounce(DEBOUNCE_FILE)
        logging.info(
            "[stop-worker] Spawned flush.py for session %s, project=%s (%d turns, %d chars)",
            session_id,
            project_name,
            turn_count,
            len(context),
        )
    except Exception as exc:
        logging.error("[stop-worker] Failed to spawn flush.py: %s", exc)
        return
    finally:
        if subproc_log_fp is not None:
            subproc_log_fp.close()


if __name__ == "__main__":
    try:
        if "--worker" in sys.argv:
            main_worker()
        else:
            main_light()
    except BrokenPipeError:
        _detach_stdout()
        pass
    except Exception as exc:
        logging.exception("Stop hook failed: %s", exc)
        _emit_ok()
