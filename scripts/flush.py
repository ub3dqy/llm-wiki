"""Flush: evaluate a conversation context and save valuable insights to daily log.

Called by hooks/session-end.py and hooks/pre-compact.py as a background process.
Uses Claude Agent SDK to decide what's worth keeping.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from config import WIKI_COMPILE_AFTER_HOUR, WIKI_TIMEZONE
from runtime_utils import build_uv_python_cmd

# Recursion guard: flush.py uses Agent SDK → Claude Code → hook → flush.py
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

# Propagate guard to any Agent SDK sub-sessions we spawn.
os.environ["CLAUDE_INVOKED_BY"] = "flush"

# --- Paths (inline to avoid import issues when run as background process) ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT_DIR / "daily"
SCRIPTS_DIR = ROOT_DIR / "scripts"
STATE_FILE = SCRIPTS_DIR / "state.json"
LOCK_DIR = SCRIPTS_DIR / "locks"
MAX_CONCURRENT_FLUSH = 2
LOCK_TIMEOUT_SEC = 120  # stale lock cleanup after 2 minutes

# --- Logging ---
logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [flush] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ---------------------------------------------------------------------------
# Concurrency control via lock files
# ---------------------------------------------------------------------------


def _cleanup_stale_locks() -> None:
    """Remove lock files older than LOCK_TIMEOUT_SEC (stale/crashed processes)."""
    if not LOCK_DIR.exists():
        return
    now = time.time()
    for lock_file in LOCK_DIR.glob("flush-*.lock"):
        try:
            age = now - lock_file.stat().st_mtime
            if age > LOCK_TIMEOUT_SEC:
                lock_file.unlink(missing_ok=True)
                logging.info("Cleaned stale lock: %s (age: %.0fs)", lock_file.name, age)
        except OSError:
            pass


def _count_active_locks() -> int:
    """Count current active lock files."""
    if not LOCK_DIR.exists():
        return 0
    return len(list(LOCK_DIR.glob("flush-*.lock")))


def acquire_flush_lock(session_id: str) -> Path | None:
    """Try to acquire a concurrency slot. Returns lock path or None if at capacity."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_stale_locks()

    if _count_active_locks() >= MAX_CONCURRENT_FLUSH:
        return None

    lock_path = LOCK_DIR / f"flush-{session_id}.lock"
    lock_path.write_text(str(os.getpid()), encoding="utf-8")
    return lock_path


def release_flush_lock(lock_path: Path | None) -> None:
    """Release a concurrency slot."""
    if lock_path and lock_path.exists():
        lock_path.unlink(missing_ok=True)


def _now_iso() -> str:
    return datetime.now(WIKI_TIMEZONE).isoformat(timespec="seconds")


def _today_iso() -> str:
    return datetime.now(WIKI_TIMEZONE).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def load_flush_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_flush_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Daily log
# ---------------------------------------------------------------------------


def append_to_daily_log(content: str) -> Path:
    """Append a timestamped entry to today's daily log."""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DAILY_DIR / f"{_today_iso()}.md"

    if not log_path.exists():
        log_path.write_text(
            f"---\ntitle: Daily Log {_today_iso()}\ntype: daily\ndate: {_today_iso()}\n---\n\n"
            f"# Daily Log — {_today_iso()}\n\n",
            encoding="utf-8",
        )

    timestamp = _now_iso()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## [{timestamp}]\n\n{content}\n")

    return log_path


# ---------------------------------------------------------------------------
# Core flush logic
# ---------------------------------------------------------------------------


async def run_flush(context: str, session_id: str, project_name: str = "unknown") -> None:
    """Use Claude Agent SDK to evaluate and summarize the conversation context."""
    from claude_agent_sdk import ClaudeAgentOptions, query

    prompt = f"""You are a knowledge extraction agent. Read the conversation context below and
decide if it contains anything worth preserving in a personal knowledge base.

## Conversation Context (from project: {project_name})

{context}

## Your Task

If the conversation contains valuable knowledge, output a structured summary with these sections:

### Context
One-line: what project/task was being worked on.

### Key Exchanges
Bullet points of the most important Q&A pairs or decisions.

### Decisions Made
Bullet points of architectural or implementation decisions and their rationale.

### Lessons Learned
Bullet points of insights, gotchas, debugging tricks, or patterns discovered.

### Action Items
Bullet points of follow-up tasks mentioned but not completed.

If the conversation was trivial (simple file reads, minor edits, no insights), output exactly:
SKIP: No significant knowledge to extract.

Keep the summary concise — aim for 200-500 words. Include project tag: `project: {project_name}`
"""

    max_retries = 2
    for attempt in range(max_retries + 1):
        result_text = ""
        try:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    allowed_tools=[],
                    max_turns=2,
                ),
            ):
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            result_text += block.text
            break  # success
        except Exception as e:
            if attempt < max_retries and "timeout" in str(e).lower():
                logging.warning("Agent SDK timeout (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
                await asyncio.sleep(2)
                continue
            logging.error("Agent SDK query failed: %s", e)
            return

    if result_text.strip().startswith("SKIP:"):
        logging.info("Flush decided to skip: %s", result_text.strip()[:100])
        return

    append_to_daily_log(result_text)
    logging.info("Flushed %d chars to daily log for session %s", len(result_text), session_id)


# ---------------------------------------------------------------------------
# Auto-compile trigger
# ---------------------------------------------------------------------------


def maybe_trigger_compilation() -> None:
    """Spawn compile.py if it's past the trigger hour and today hasn't been compiled."""
    now = datetime.now(WIKI_TIMEZONE)
    if now.hour < WIKI_COMPILE_AFTER_HOUR:
        return

    state = load_flush_state()
    last_compile_date = state.get("last_auto_compile_date", "")
    today = _today_iso()

    if last_compile_date == today:
        return

    # Check if today's daily log exists and has content
    today_log = DAILY_DIR / f"{today}.md"
    if not today_log.exists():
        return

    current_hash = hashlib.sha256(today_log.read_bytes()).hexdigest()
    if state.get("last_auto_compile_hash") == current_hash:
        return

    compile_script = SCRIPTS_DIR / "compile.py"
    if not compile_script.exists():
        return

    try:
        cmd, env = build_uv_python_cmd(compile_script, project_dir=ROOT_DIR)
    except FileNotFoundError as e:
        logging.error("Failed to locate uv for compile.py: %s", e)
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
        state["last_auto_compile_date"] = today
        state["last_auto_compile_hash"] = current_hash
        save_flush_state(state)
        logging.info("Triggered auto-compilation for %s", today)
    except Exception as e:
        logging.error("Failed to spawn compile.py: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def prune_flushed_sessions(state: dict) -> None:
    """Remove flushed_sessions entries older than 7 days to prevent unbounded growth."""
    flushed = state.get("flushed_sessions", {})
    if len(flushed) <= 50:
        return
    # Keep only the last 50 entries (dict preserves insertion order in Python 3.7+)
    state["flushed_sessions"] = dict(list(flushed.items())[-50:])


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: flush.py <context_file> <session_id> [project_name]")
        sys.exit(1)

    context_file = Path(sys.argv[1])
    session_id = sys.argv[2]
    project_name = sys.argv[3] if len(sys.argv) > 3 else "unknown"

    if not context_file.exists():
        logging.error("Context file not found: %s", context_file)
        sys.exit(1)

    # Concurrency control: max MAX_CONCURRENT_FLUSH parallel flush processes
    lock_path = acquire_flush_lock(session_id)
    if lock_path is None:
        logging.info("SKIP: concurrency limit reached (%d), dropping session %s", MAX_CONCURRENT_FLUSH, session_id)
        context_file.unlink(missing_ok=True)
        return

    try:
        # Deduplication: skip if we already flushed this session
        state = load_flush_state()
        flushed_sessions = state.get("flushed_sessions", {})

        context = context_file.read_text(encoding="utf-8")
        context_hash = hashlib.sha256(context.encode()).hexdigest()

        if session_id in flushed_sessions and flushed_sessions[session_id] == context_hash:
            logging.info("SKIP: session %s already flushed with same content", session_id)
            context_file.unlink(missing_ok=True)
            return

        logging.info("Starting flush for session %s (%d chars)", session_id, len(context))

        try:
            asyncio.run(run_flush(context, session_id, project_name))
        except Exception as e:
            logging.error("Flush failed: %s", e)
        finally:
            # Record that we flushed this session
            flushed_sessions[session_id] = context_hash
            state["flushed_sessions"] = flushed_sessions
            prune_flushed_sessions(state)
            save_flush_state(state)

            # Clean up context file
            context_file.unlink(missing_ok=True)

        # Check if we should auto-compile
        maybe_trigger_compilation()
    finally:
        release_flush_lock(lock_path)


if __name__ == "__main__":
    main()
