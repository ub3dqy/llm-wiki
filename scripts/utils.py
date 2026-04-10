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
    """Load the JSON state file used for dedup & cost tracking."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    """Persist state back to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


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


def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown content."""
    return _WIKILINK_RE.findall(content)


def wiki_article_exists(link: str) -> bool:
    """Check whether a wikilink target resolves to a real file."""
    candidate = WIKI_DIR / f"{link}.md"
    if candidate.exists():
        return True
    # try without wiki/ prefix (link may already include subfolder)
    candidate2 = WIKI_DIR.parent / f"{link}.md"
    return candidate2.exists()


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


def list_raw_files() -> list[Path]:
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
        if f"[[{link_target}]]" in content:
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
