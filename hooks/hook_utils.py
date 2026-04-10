"""Shared utilities for Claude Code hooks (session-end, pre-compact)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

MAX_TURNS = 30
MAX_CONTEXT_CHARS = 15_000
DEBOUNCE_SEC = 10


# ---------------------------------------------------------------------------
# Debounce
# ---------------------------------------------------------------------------


def check_debounce(debounce_file: Path, debounce_sec: int = DEBOUNCE_SEC) -> bool:
    """Return True if enough time has passed since last spawn."""
    if not debounce_file.exists():
        return True
    try:
        last_spawn = float(debounce_file.read_text(encoding="utf-8").strip())
        return (time.time() - last_spawn) >= debounce_sec
    except (ValueError, OSError):
        return True


def update_debounce(debounce_file: Path) -> None:
    """Record current time as last spawn time."""
    try:
        debounce_file.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def parse_hook_stdin() -> dict | None:
    """Parse JSON from stdin, handling Windows path escaping issues."""
    try:
        raw = sys.stdin.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            fixed = re.sub(r'(?<!\\)\\(?!["\\])', r"\\\\", raw)
            return json.loads(fixed)
    except (json.JSONDecodeError, ValueError, EOFError):
        return None


def extract_conversation_context(
    transcript_path: Path,
    max_turns: int = MAX_TURNS,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> tuple[str, int]:
    """Read JSONL transcript and extract last ~N conversation turns as markdown.

    Returns (context_text, turn_count).
    """
    turns: list[str] = []

    with open(transcript_path, encoding="utf-8") as f:
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
                role = entry.get("role", "")
                content = entry.get("content", "")

            if role not in ("user", "assistant"):
                continue

            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)

            if isinstance(content, str) and content.strip():
                label = "User" if role == "user" else "Assistant"
                turns.append(f"**{label}:** {content.strip()}\n")

    recent = turns[-max_turns:]
    context = "\n".join(recent)

    if len(context) > max_chars:
        context = context[-max_chars:]
        boundary = context.find("\n**")
        if boundary > 0:
            context = context[boundary + 1:]

    return context, len(recent)
