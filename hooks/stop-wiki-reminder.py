"""Stop hook: remind user to save important decisions to wiki.

Checks the last assistant response for decision/architecture keywords.
If found, outputs a systemMessage hint about /wiki-save.
Non-blocking — only a gentle reminder.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Recursion guard
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DEBOUNCE_FILE = SCRIPTS_DIR / ".last-wiki-reminder"
DEBOUNCE_SEC = 300  # 5 minutes between reminders

DECISION_KEYWORDS = [
    # English
    "decided", "decision", "chose", "chosen", "architecture", "architectural",
    "pattern", "convention", "migration", "schema", "trade-off", "tradeoff",
    "approach", "strategy", "design",
    # Russian
    "решил", "решение", "выбрал", "архитектур", "паттерн", "конвенци",
    "миграци", "схем", "стратеги", "подход",
]


def check_debounce() -> bool:
    if not DEBOUNCE_FILE.exists():
        return True
    try:
        last = float(DEBOUNCE_FILE.read_text(encoding="utf-8").strip())
        return (time.time() - last) >= DEBOUNCE_SEC
    except (ValueError, OSError):
        return True


def update_debounce() -> None:
    try:
        DEBOUNCE_FILE.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def get_last_assistant_response(transcript_path: str) -> str:
    """Read the last assistant response from the JSONL transcript."""
    p = Path(transcript_path)
    if not p.exists():
        return ""

    last_response = ""
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = entry.get("message", {})
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                else:
                    continue

                if role != "assistant":
                    continue

                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    content = " ".join(parts)

                if isinstance(content, str) and content.strip():
                    last_response = content
    except OSError:
        pass

    return last_response


def has_decision_keywords(text: str) -> bool:
    """Check if text contains decision/architecture keywords."""
    text_lower = text.lower()
    matches = sum(1 for kw in DECISION_KEYWORDS if kw in text_lower)
    return matches >= 2  # require at least 2 keyword matches to reduce false positives


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, ValueError, EOFError):
        return

    # Don't re-trigger if already active
    if hook_input.get("stop_hook_active"):
        return

    if not check_debounce():
        return

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path:
        return

    last_response = get_last_assistant_response(transcript_path)
    if not last_response:
        return

    if has_decision_keywords(last_response):
        update_debounce()
        output = {
            "systemMessage": (
                "This response contains architectural decisions or patterns. "
                "Consider using /wiki-save to preserve them in the knowledge base."
            )
        }
        print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block Claude's response due to hook errors
        pass
