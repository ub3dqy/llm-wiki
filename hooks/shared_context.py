"""Shared context assembly for Claude Code and Codex SessionStart hooks.

Reads cwd from stdin to determine the current project, then injects:
1. Wiki-first instructions (MANDATORY)
2. Project-relevant articles (if project recognized)
3. Recent wiki changes (last 48h)
4. Full wiki index
5. Recent daily log

This runs for ALL projects — the wiki is global.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT / "wiki"
DAILY_DIR = ROOT / "daily"
INDEX_FILE = ROOT / "index.md"

MAX_CONTEXT_CHARS = 10_000
MAX_LOG_LINES = 30
MAX_RECENT_CHANGES = 10
RECENT_CHANGES_DAYS = 2


# ---------------------------------------------------------------------------
# Stdin parsing
# ---------------------------------------------------------------------------


def read_stdin_cwd() -> str:
    """Read cwd from SessionStart hook stdin JSON payload.

    Returns empty string if stdin is empty or not valid JSON.
    """
    try:
        raw = sys.stdin.read()
        if raw.strip():
            data = json.loads(raw)
            return data.get("cwd", "")
    except (json.JSONDecodeError, ValueError, EOFError):
        pass
    return ""


# ---------------------------------------------------------------------------
# Frontmatter parsing (local copy — no imports from scripts/)
# ---------------------------------------------------------------------------

_FM_LINE_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$")


def _parse_frontmatter(path: Path) -> dict[str, str]:
    """Minimal frontmatter parser for hook use."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for line in text[3:end].splitlines():
        m = _FM_LINE_RE.match(line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


# ---------------------------------------------------------------------------
# Project detection
# ---------------------------------------------------------------------------


def cwd_to_project_name(cwd: str) -> str | None:
    """Extract project name from cwd. Returns None for wiki dir or empty path."""
    if not cwd:
        return None
    p = Path(cwd)
    # Skip if cwd IS the wiki directory itself
    try:
        if p.resolve() == ROOT.resolve():
            return None
    except OSError:
        pass
    name = p.name.strip()
    return name if name else None


def get_project_articles(project_name: str) -> list[tuple[str, str]]:
    """Return wiki articles tagged with the given project.

    Returns list of (slug, title) tuples, sorted by slug.
    Matching is case-insensitive with space/hyphen normalization.
    """
    if not WIKI_DIR.exists():
        return []

    normalized = project_name.lower().replace(" ", "-").replace("_", "-")
    results: list[tuple[str, str]] = []

    for article in sorted(WIKI_DIR.rglob("*.md")):
        fm = _parse_frontmatter(article)
        raw_project = fm.get("project", "")
        projects = [p.strip().lower().replace(" ", "-").replace("_", "-") for p in raw_project.split(",")]

        if normalized in projects:
            rel = article.relative_to(WIKI_DIR)
            slug = str(rel).replace("\\", "/").replace(".md", "")
            title = fm.get("title", slug)
            results.append((slug, title))

    return results


# ---------------------------------------------------------------------------
# Recent changes
# ---------------------------------------------------------------------------


def get_recent_changes() -> list[dict]:
    """Return wiki articles created or updated in the last RECENT_CHANGES_DAYS days."""
    if not WIKI_DIR.exists():
        return []

    today = datetime.now(timezone.utc).astimezone().date()
    cutoff = today - timedelta(days=RECENT_CHANGES_DAYS)

    results: list[dict] = []
    for article in WIKI_DIR.rglob("*.md"):
        fm = _parse_frontmatter(article)
        created_str = fm.get("created", "")
        updated_str = fm.get("updated", "")

        rel = article.relative_to(WIKI_DIR)
        slug = str(rel).replace("\\", "/").replace(".md", "")

        try:
            updated_date = datetime.strptime(updated_str, "%Y-%m-%d").date() if updated_str else None
            created_date = datetime.strptime(created_str, "%Y-%m-%d").date() if created_str else None
        except ValueError:
            continue

        if updated_date and updated_date >= cutoff:
            status = "NEW" if (created_date and created_date == updated_date) else "UPDATED"
            results.append({"slug": slug, "status": status, "date": updated_str})

    return sorted(results, key=lambda x: x["date"], reverse=True)[:MAX_RECENT_CHANGES]


def format_recent_changes(changes: list[dict]) -> str:
    """Format recent changes as a markdown section. Empty string if no changes."""
    if not changes:
        return ""
    lines = ["## Recent Wiki Changes (last 48h)\n"]
    for ch in changes:
        lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Daily log
# ---------------------------------------------------------------------------


def get_recent_log() -> str:
    """Read the most recent daily log (today or yesterday)."""
    today = datetime.now(timezone.utc).astimezone()

    for offset in range(2):
        date = today - timedelta(days=offset)
        log_path = DAILY_DIR / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()
            recent = lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines
            return "\n".join(recent)

    return "(no recent daily log)"


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

WIKI_ROOT_DISPLAY = str(ROOT).replace("\\", "/")

INSTRUCTIONS = f"""## Knowledge Base Instructions — MANDATORY

You have a global knowledge base (LLM Wiki) at `{WIKI_ROOT_DISPLAY}/`.
The wiki index below lists all articles. To read any article, use the Read tool with the path:
`{WIKI_ROOT_DISPLAY}/wiki/<section>/<slug>.md`

### RULE: Wiki-first (ОБЯЗАТЕЛЬНО)

BEFORE starting any task, you MUST:
1. Scan the wiki index below — are there articles related to the current task?
2. If yes — Read those articles BEFORE writing code or giving recommendations
3. Use wiki knowledge as your foundation, not your training data

DO NOT:
- Ignore the wiki and work "from scratch" when relevant articles exist
- Reinvent solutions already documented in the wiki
- Contradict wiki decisions without explicitly explaining why

### Triggers for mandatory wiki reading:
- User asks about architecture, decisions, or patterns
- Task involves a technology described in the wiki (check index)
- User starts work on a project that has an entity in the wiki
- Before making architectural decisions — check if already decided

You can also **write** new knowledge back to the wiki by following the ingest workflow in `{WIKI_ROOT_DISPLAY}/CLAUDE.md`."""


def build_context(cwd: str = "") -> str:
    """Assemble context. If cwd is provided, prioritize project-relevant articles."""
    parts: list[str] = []

    today = datetime.now(timezone.utc).astimezone()
    parts.append(f"## Knowledge Base\nToday: {today.strftime('%A, %B %d, %Y')}")

    parts.append(INSTRUCTIONS)

    # Project-specific section
    project_name = cwd_to_project_name(cwd)
    if project_name:
        project_articles = get_project_articles(project_name)
        if project_articles:
            article_lines = [f"- [[{slug}]] — {title}" for slug, title in project_articles]
            parts.append(
                f"## Project: {project_name} (relevant wiki articles)\n\n"
                + "\n".join(article_lines)
            )

    # Recent changes
    recent_changes = format_recent_changes(get_recent_changes())
    if recent_changes:
        parts.append(recent_changes)

    # Full index
    if INDEX_FILE.exists():
        index_content = INDEX_FILE.read_text(encoding="utf-8")
        parts.append(f"## Wiki Index\n\n{index_content}")
    else:
        parts.append("## Wiki Index\n\n(empty — no articles yet)")

    # Recent daily log
    recent_log = get_recent_log()
    parts.append(f"## Recent Daily Log\n\n{recent_log}")

    context = "\n\n---\n\n".join(parts)

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

    return context


def build_context_and_output() -> None:
    """Read hook stdin, build SessionStart context, and print hook JSON."""
    cwd = read_stdin_cwd()
    context = build_context(cwd=cwd)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))
