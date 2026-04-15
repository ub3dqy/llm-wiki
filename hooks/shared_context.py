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
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from config import WIKI_TIMEZONE  # noqa: E402
from hook_utils import infer_project_name_from_cwd, parse_frontmatter

ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT / "wiki"
DAILY_DIR = ROOT / "daily"
INDEX_FILE = ROOT / "index.md"

MAX_CONTEXT_CHARS = 10_000
MAX_LOG_LINES = 30
MAX_RECENT_CHANGES = 10
RECENT_CHANGES_DAYS = 2
SECTION_SEPARATOR = "\n\n---\n\n"

SECTION_BUDGETS = {
    "header": 160,
    "instructions": 3400,
    "project": 1400,
    "recent_changes": 900,
    "index": 3200,
    "recent_log": 1200,
}


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
# Project detection
# ---------------------------------------------------------------------------


def cwd_to_project_name(cwd: str) -> str | None:
    """Extract project name from cwd. Returns None for wiki dir or empty path."""
    return infer_project_name_from_cwd(cwd, repo_root=ROOT)


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
        fm = parse_frontmatter(article)
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

    today = datetime.now(WIKI_TIMEZONE).date()
    cutoff = today - timedelta(days=RECENT_CHANGES_DAYS)

    results: list[dict] = []
    for article in WIKI_DIR.rglob("*.md"):
        fm = parse_frontmatter(article)
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
            freshness_status = (fm.get("status", "active") or "active").lower()
            if freshness_status != "active":
                results[-1]["freshness"] = freshness_status

    return sorted(results, key=lambda x: x["date"], reverse=True)[:MAX_RECENT_CHANGES]


def format_recent_changes(changes: list[dict]) -> str:
    """Format recent changes as a markdown section. Empty string if no changes."""
    if not changes:
        return ""
    lines = ["## Recent Wiki Changes (last 48h)\n"]
    for ch in changes:
        suffix = f" ⚠ {ch['freshness']}" if "freshness" in ch else ""
        lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']}){suffix}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Daily log
# ---------------------------------------------------------------------------


def get_recent_log() -> str:
    """Read the most recent daily log (today or yesterday)."""
    today = datetime.now(WIKI_TIMEZONE)

    for offset in range(2):
        date = today - timedelta(days=offset)
        log_path = DAILY_DIR / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()
            recent = lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines
            return "\n".join(recent)

    return "(no recent daily log)"


def trim_text(text: str, max_chars: int, suffix: str = "\n\n...(truncated)") -> str:
    """Trim text without cutting directly through the middle of a line when possible."""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    budget = max_chars - len(suffix)
    if budget <= 0:
        return suffix[:max_chars]

    trimmed = text[:budget]
    boundary = max(trimmed.rfind("\n"), trimmed.rfind(". "))
    if boundary > max_chars // 3:
        trimmed = trimmed[:boundary].rstrip()
    else:
        trimmed = trimmed.rstrip()

    return trimmed + suffix


def trim_lines(lines: list[str], max_chars: int) -> str:
    """Join as many whole lines as fit in the given budget."""
    if max_chars <= 0 or not lines:
        return ""

    selected: list[str] = []
    total = 0
    for line in lines:
        extra = len(line) + (1 if selected else 0)
        if total + extra > max_chars:
            break
        selected.append(line)
        total += extra

    text = "\n".join(selected)
    if len(selected) < len(lines):
        text += "\n...(truncated)"
    return text


def build_project_section(project_name: str, max_chars: int) -> str:
    """Build a capped project section."""
    project_articles = get_project_articles(project_name)
    if not project_articles:
        return ""

    intro = f"## Project: {project_name} (relevant wiki articles)\n\n"
    lines = [f"- [[{slug}]] — {title}" for slug, title in project_articles]
    body = trim_lines(lines, max_chars=max(0, max_chars - len(intro)))
    return intro + body if body else ""


def build_index_section(project_name: str | None, max_chars: int) -> str:
    """Build a capped wiki index section, prioritizing project-relevant lines when possible."""
    if not INDEX_FILE.exists():
        return "## Wiki Index\n\n(empty — no articles yet)"

    index_content = INDEX_FILE.read_text(encoding="utf-8")
    prefix = "## Wiki Index\n\n"
    body_budget = max(0, max_chars - len(prefix))
    if len(index_content) <= body_budget:
        return prefix + index_content

    lines = index_content.splitlines()
    selected: list[str] = []
    used = 0
    normalized_project = ""
    if project_name:
        normalized_project = project_name.lower().replace("_", "-").replace(" ", "-")

    def add_line(line: str) -> bool:
        nonlocal used
        extra = len(line) + (1 if selected else 0)
        if used + extra > body_budget:
            return False
        selected.append(line)
        used += extra
        return True

    # Always keep the top of the index.
    for line in lines[:22]:
        if not add_line(line):
            break

    # Then prioritize lines mentioning the current project or its articles.
    if normalized_project:
        for line in lines[22:]:
            normalized_line = line.lower().replace("_", "-").replace(" ", "-")
            if normalized_project in normalized_line and line not in selected:
                if not add_line(line):
                    break

    text = "\n".join(selected)
    if len(selected) < len(lines):
        text += "\n...(truncated; use Read on index.md for full catalog)"

    return prefix + text


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

    today = datetime.now(WIKI_TIMEZONE)
    project_name = cwd_to_project_name(cwd)

    header = trim_text(
        f"## Knowledge Base\nToday: {today.strftime('%A, %B %d, %Y')}",
        SECTION_BUDGETS["header"],
    )
    instructions = trim_text(INSTRUCTIONS, SECTION_BUDGETS["instructions"])
    project_section = build_project_section(project_name, SECTION_BUDGETS["project"]) if project_name else ""
    recent_changes = trim_text(
        format_recent_changes(get_recent_changes()),
        SECTION_BUDGETS["recent_changes"],
    )
    index_section = build_index_section(project_name, SECTION_BUDGETS["index"])
    recent_log = trim_text(
        f"## Recent Daily Log\n\n{get_recent_log()}",
        SECTION_BUDGETS["recent_log"],
    )

    for section in (header, instructions, project_section, recent_changes, index_section, recent_log):
        if section.strip():
            parts.append(section)

    context = SECTION_SEPARATOR.join(parts)

    if len(context) > MAX_CONTEXT_CHARS:
        overflow = len(context) - MAX_CONTEXT_CHARS
        # Trim the least important sections first.
        if recent_log:
            recent_log = trim_text(recent_log, max(240, len(recent_log) - overflow))
        parts = [header, instructions, project_section, recent_changes, index_section, recent_log]
        parts = [part for part in parts if part.strip()]
        context = SECTION_SEPARATOR.join(parts)

    if len(context) > MAX_CONTEXT_CHARS:
        context = trim_text(context, MAX_CONTEXT_CHARS)

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
