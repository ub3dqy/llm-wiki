"""Shared utilities for Claude Code hooks (session-end, pre-compact)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    PROJECT_ALIASES,
    WIKI_DEBOUNCE_SEC as DEBOUNCE_SEC,
    WIKI_MAX_CONTEXT_CHARS as MAX_CONTEXT_CHARS,
    WIKI_MAX_TURNS as MAX_TURNS,
)
from utils import parse_frontmatter  # noqa: E402

_WINDOWS_DRIVE_RE = re.compile(r"^([a-zA-Z]):(?:/|$)")
_WSL_DRIVE_RE = re.compile(r"^/mnt/([a-zA-Z])(?:/|$)")
_GIT_BASH_DRIVE_RE = re.compile(r"^/([a-zA-Z])(?:/|$)")


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


def normalize_cwd(cwd: str) -> str:
    """Normalize Windows, WSL, and Git Bash paths to a shared form.

    Output format prefers `E:/path/to/project` style for drive-backed paths.
    Unknown Unix paths are returned as normalized POSIX strings.
    """
    if not isinstance(cwd, str):
        return ""

    text = cwd.strip().strip('"').strip("'")
    if not text:
        return ""

    text = text.replace("\\", "/")
    text = re.sub(r"/+", "/", text)

    match = _WSL_DRIVE_RE.match(text)
    if match:
        drive = match.group(1).upper()
        suffix = text[match.end() - 1 :]
        suffix = suffix if suffix.startswith("/") else f"/{suffix}" if suffix else ""
        return f"{drive}:{suffix}".rstrip("/")

    match = _WINDOWS_DRIVE_RE.match(text)
    if match:
        drive = match.group(1).upper()
        suffix = text[2:]
        suffix = suffix if suffix.startswith("/") else f"/{suffix}" if suffix else ""
        return f"{drive}:{suffix}".rstrip("/")

    match = _GIT_BASH_DRIVE_RE.match(text)
    if match and not text.startswith("/mnt/"):
        drive = match.group(1).upper()
        suffix = text[match.end() - 1 :]
        suffix = suffix if suffix.startswith("/") else f"/{suffix}" if suffix else ""
        return f"{drive}:{suffix}".rstrip("/")

    return text.rstrip("/")


def path_tail_parts(cwd: str) -> list[str]:
    """Return normalized path segments without drive prefixes."""
    normalized = normalize_cwd(cwd)
    if not normalized:
        return []

    if len(normalized) >= 2 and normalized[1] == ":":
        normalized = normalized[2:]

    parts = [part for part in normalized.split("/") if part]
    return parts


def canonical_project_key(name: str) -> str:
    """Normalize a project token for matching against aliases and frontmatter."""
    return re.sub(r"[\s_]+", "-", name.strip().lower())


def infer_project_name_from_cwd(cwd: str, repo_root: Path | None = None) -> str | None:
    """Infer canonical project name from Windows/WSL/Git Bash cwd."""
    normalized_cwd = normalize_cwd(cwd)
    if not normalized_cwd:
        return None

    if repo_root is not None:
        normalized_root = normalize_cwd(str(repo_root.resolve()))
        if normalized_root and normalized_cwd == normalized_root:
            return None

    parts = path_tail_parts(cwd)
    if not parts:
        return None

    candidates: list[str] = []
    if len(parts) >= 2:
        candidates.append(" ".join(parts[-2:]))
        candidates.append("-".join(parts[-2:]))
    candidates.append(parts[-1])

    normalized_candidates = {canonical_project_key(candidate) for candidate in candidates}

    for canonical, aliases in PROJECT_ALIASES.items():
        alias_keys = {canonical_project_key(alias) for alias in aliases}
        if normalized_candidates & alias_keys:
            return canonical

    return canonical_project_key(parts[-1]) or None


def get_transcript_path(hook_input: dict) -> str:
    """Extract transcript_path from top-level hook payload."""
    value = hook_input.get("transcript_path", "")
    return value if isinstance(value, str) else ""


def get_prompt(hook_input: dict) -> str:
    """Extract prompt from top-level hook payload."""
    value = hook_input.get("prompt", "")
    return value if isinstance(value, str) else ""


def extract_conversation_context(
    transcript_path: Path,
    max_turns: int = MAX_TURNS,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> tuple[str, int]:
    """Read transcript and extract last ~N conversation turns as markdown.

    Auto-detects JSONL vs JSON array format.

    Returns (context_text, turn_count).
    """
    turns: list[str] = []

    text = transcript_path.read_text(encoding="utf-8")
    stripped = text.strip()

    if stripped.startswith("["):
        try:
            entries = json.loads(stripped)
        except json.JSONDecodeError:
            entries = []
    else:
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    for entry in entries:
        if not isinstance(entry, dict):
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
