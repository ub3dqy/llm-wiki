from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from config import (
    ANALYSES_DIR,
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    ENTITIES_DIR,
    INDEX_FILE,
    QA_DIR,
    SOURCES_DIR,
    STATE_FILE,
    WIKI_DIR,
)

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


def load_state() -> dict:
    """Load the JSON state file used for dedup & cost tracking.

    On corrupt JSON, the existing file is moved aside to
    ``<name>.corrupt-<UTC>`` and an empty state is returned.
    """
    if not STATE_FILE.exists():
        return {}
    raw = STATE_FILE.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        import logging
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = STATE_FILE.with_name(STATE_FILE.name + f".corrupt-{stamp}")
        try:
            STATE_FILE.replace(backup)
            logging.warning("state.json corrupt (%s), backed up to %s", exc, backup.name)
        except OSError as backup_err:
            logging.error("state.json corrupt (%s) AND backup failed (%s)", exc, backup_err)
        return {}


def save_state(state: dict) -> None:
    """Persist state to disk atomically (POSIX-guaranteed, best-effort on Windows)."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    tmp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------


def file_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")[:80]


# ---------------------------------------------------------------------------
# Wikilinks
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_WIKI_ROOT = WIKI_DIR.resolve()
_WIKI_PARENT = WIKI_DIR.parent.resolve()


def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown content.

    Handles Obsidian-style aliases: [[target|display name]] → target
    Also handles markdown table escape: [[target\\|display]] → target
    (when wikilink appears inside a markdown table cell, the alias separator
    must be escaped as \\| so the table parser does not see it as a column
    boundary; this escape must be unescaped before splitting on |).

    Skips wikilinks inside code spans and code blocks — `[[wikilink]]` and
    ```python\n[[wikilink]]\n``` are illustrative references, not real links.
    """
    # Mask out code spans and code blocks first to avoid extracting
    # illustrative wikilinks from them
    cleaned = _CODE_BLOCK_RE.sub("", content)
    cleaned = _INLINE_CODE_RE.sub("", cleaned)
    raw = _WIKILINK_RE.findall(cleaned)
    # Unescape markdown table pipe escape (\| -> |) before splitting on alias separator
    return [link.replace("\\|", "|").split("|")[0] for link in raw]


def content_has_wikilink_target(content: str, link_target: str) -> bool:
    """Return True if markdown content contains a wikilink to the target.

    Handles both plain links and alias links:
    - [[concepts/foo]]
    - [[concepts/foo|Display]]
    """
    return link_target in extract_wikilinks(content)


def wiki_article_exists(link: str) -> bool:
    """Check whether a wikilink target resolves to a real file within the repo tree."""
    candidate = (WIKI_DIR / f"{link}.md").resolve()
    if candidate.is_relative_to(_WIKI_ROOT) and candidate.exists():
        return True

    # Try from repo root for links that already include the wiki/ prefix.
    candidate2 = (WIKI_DIR.parent / f"{link}.md").resolve()
    if candidate2.is_relative_to(_WIKI_PARENT) and candidate2.exists():
        return True

    return False


# ---------------------------------------------------------------------------
# Listing helpers
# ---------------------------------------------------------------------------

_WIKI_SUBDIRS = [CONCEPTS_DIR, CONNECTIONS_DIR, QA_DIR, SOURCES_DIR, ENTITIES_DIR, ANALYSES_DIR]


def list_wiki_articles() -> list[Path]:
    """Return all .md files across wiki/ subdirectories."""
    articles: list[Path] = []
    for subdir in _WIKI_SUBDIRS:
        if subdir.exists():
            articles.extend(sorted(subdir.glob("*.md")))
    # Also include top-level wiki files like overview.md
    for f in sorted(WIKI_DIR.glob("*.md")):
        if f not in articles:
            articles.append(f)
    return articles


def list_daily_logs() -> list[Path]:
    """Return all daily log files sorted by name."""
    from config import DAILY_DIR

    if not DAILY_DIR.exists():
        return []
    return sorted(DAILY_DIR.glob("*.md"))


# ---------------------------------------------------------------------------
# Content aggregation
# ---------------------------------------------------------------------------


def read_wiki_index() -> str:
    """Read the wiki index file."""
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return "(empty index)"


def read_all_wiki_content() -> str:
    """Concatenate index + all wiki articles into a single string for LLM context."""
    parts: list[str] = []

    parts.append(f"## INDEX\n\n{read_wiki_index()}")

    for article in list_wiki_articles():
        rel = article.relative_to(WIKI_DIR.parent)
        content = article.read_text(encoding="utf-8")
        parts.append(f"## {rel}\n\n{content}")

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Link analytics
# ---------------------------------------------------------------------------


def count_inbound_links(link_target: str) -> int:
    """Count how many wiki articles link to the given target via [[wikilink]]."""
    count = 0
    for article in list_wiki_articles():
        content = article.read_text(encoding="utf-8")
        if content_has_wikilink_target(content, link_target):
            count += 1
    return count


def get_article_word_count(path: Path) -> int:
    """Count words in a wiki article, skipping YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    # Strip frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :]
    return len(text.split())


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

_FM_LINE_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$")


def parse_frontmatter_from_text(text: str) -> dict[str, str]:
    """Parse YAML frontmatter from already-loaded article text.

    Returns a dict of key → raw string value.
    Returns empty dict if no frontmatter found.
    """
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


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Parse YAML frontmatter from a wiki article.

    Thin wrapper over `parse_frontmatter_from_text` that reads the file first.
    """
    return parse_frontmatter_from_text(path.read_text(encoding="utf-8"))


def parse_frontmatter_list(raw_value: str) -> list[str]:
    """Parse a loose frontmatter list representation into plain items."""
    text = (raw_value or "").strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    parts = [part.strip().strip("'\"") for part in text.split(",")]
    return [part for part in parts if part]


def frontmatter_sources_include_prefix(raw_sources: str, prefix: str) -> bool:
    """Return True if a parsed frontmatter source entry starts with the prefix."""
    normalized_prefix = prefix.strip()
    if not normalized_prefix:
        return False
    return any(
        source.startswith(normalized_prefix) for source in parse_frontmatter_list(raw_sources)
    )


def get_article_projects(path: Path) -> list[str]:
    """Return list of project tags from article frontmatter.

    Handles both 'project: foo' and 'project: foo, bar' formats.
    """
    fm = parse_frontmatter(path)
    raw = fm.get("project", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def build_article_metadata_map() -> dict[str, dict]:
    """Build a map of slug → {projects, word_count, updated, title}.

    Slug format matches index.md wikilinks: 'concepts/foo', 'entities/bar'.
    """
    meta: dict[str, dict] = {}
    for article in list_wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        slug = str(rel).replace("\\", "/").replace(".md", "")
        fm = parse_frontmatter(article)
        meta[slug] = {
            "projects": get_article_projects(article),
            "word_count": get_article_word_count(article),
            "updated": fm.get("updated", ""),
            "title": fm.get("title", slug),
            "confidence": fm.get("confidence", ""),
            "sources": fm.get("sources", ""),
            "tags": fm.get("tags", ""),
        }
    return meta
