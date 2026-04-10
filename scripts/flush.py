"""Flush: evaluate a conversation context and save valuable insights to daily log.

Called by hooks/session-end.py and hooks/pre-compact.py as a background process.
Uses Claude Agent SDK to decide what's worth keeping.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard: flush.py uses Agent SDK → Claude Code → hook → flush.py
import os

if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

# --- Paths (inline to avoid import issues when run as background process) ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT_DIR / "daily"
SCRIPTS_DIR = ROOT_DIR / "scripts"
STATE_FILE = SCRIPTS_DIR / "state.json"
COMPILE_TRIGGER_HOUR = 18

# --- Logging ---
logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [flush] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _today_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


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


async def run_flush(context: str, session_id: str) -> None:
    """Use Claude Agent SDK to evaluate and summarize the conversation context."""
    from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, TextBlock, query

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "unknown-project")
    project_name = Path(project_dir).name if project_dir != "unknown-project" else "unknown"

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
    except Exception as e:
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
    now = datetime.now(timezone.utc).astimezone()
    if now.hour < COMPILE_TRIGGER_HOUR:
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

    cmd = ["uv", "run", "--directory", str(ROOT_DIR), "python", str(compile_script)]

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
        state["last_auto_compile_date"] = today
        state["last_auto_compile_hash"] = current_hash
        save_flush_state(state)
        logging.info("Triggered auto-compilation for %s", today)
    except Exception as e:
        logging.error("Failed to spawn compile.py: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: flush.py <context_file> <session_id>")
        sys.exit(1)

    context_file = Path(sys.argv[1])
    session_id = sys.argv[2]

    if not context_file.exists():
        logging.error("Context file not found: %s", context_file)
        sys.exit(1)

    # Deduplication: skip if we already flushed this session
    state = load_flush_state()
    flushed_sessions = state.get("flushed_sessions", {})

    context = context_file.read_text(encoding="utf-8")
    context_hash = hashlib.sha256(context.encode()).hexdigest()

    if session_id in flushed_sessions and flushed_sessions[session_id] == context_hash:
        logging.info("SKIP: session %s already flushed with same content", session_id)
        # Clean up context file
        context_file.unlink(missing_ok=True)
        return

    logging.info("Starting flush for session %s (%d chars)", session_id, len(context))

    try:
        asyncio.run(run_flush(context, session_id))
    except Exception as e:
        logging.error("Flush failed: %s", e)
    finally:
        # Record that we flushed this session
        flushed_sessions[session_id] = context_hash
        state["flushed_sessions"] = flushed_sessions
        save_flush_state(state)

        # Clean up context file
        context_file.unlink(missing_ok=True)

    # Check if we should auto-compile
    maybe_trigger_compilation()


if __name__ == "__main__":
    main()
