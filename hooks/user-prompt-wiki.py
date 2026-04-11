"""UserPromptSubmit hook: inject relevant wiki articles based on prompt content.

Parses the user's prompt, finds wiki articles matching keywords,
and injects their content as additionalContext so Claude has
just-in-time knowledge for the specific question.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT / "wiki"

MAX_ARTICLES = 3
MAX_CONTEXT_CHARS = 4000
MIN_PROMPT_LENGTH = 10
# Words to skip during keyword extraction
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "must", "need",
    "and", "or", "but", "if", "then", "else", "when", "while", "for",
    "to", "from", "in", "on", "at", "by", "with", "about", "into",
    "not", "no", "yes", "this", "that", "these", "those", "it", "its",
    "как", "что", "где", "когда", "почему", "зачем", "какой", "какая",
    "какое", "какие", "мне", "мой", "нам", "наш", "все", "всё", "это",
    "для", "при", "без", "над", "под", "про", "или", "так", "уже",
    "ещё", "еще", "тоже", "также", "очень", "можно", "нужно", "есть",
}

# ---------------------------------------------------------------------------
# Frontmatter parsing (local copy)
# ---------------------------------------------------------------------------

_FM_LINE_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$")


def _parse_frontmatter(path: Path) -> dict[str, str]:
    """Minimal frontmatter parser."""
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
# Keyword extraction
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_-]{3,}")


def extract_keywords(prompt: str) -> set[str]:
    """Extract meaningful keywords from the user's prompt."""
    words = _WORD_RE.findall(prompt.lower())
    return {w for w in words if w not in STOP_WORDS}


# ---------------------------------------------------------------------------
# Article matching
# ---------------------------------------------------------------------------


def score_article(path: Path, keywords: set[str]) -> int:
    """Score an article by keyword matches in title, tags, slug, and project."""
    fm = _parse_frontmatter(path)
    title = fm.get("title", "").lower()
    tags = fm.get("tags", "").lower()
    project = fm.get("project", "").lower()
    slug = path.stem.replace("-", " ").lower()

    searchable = f"{title} {tags} {project} {slug}"
    score = 0
    for kw in keywords:
        if kw in searchable:
            score += 2  # title/tag match
        # Check if keyword appears in the first 500 chars of content
        # (cheap heuristic for relevance without reading full article)
    return score


def find_relevant_articles(prompt: str) -> list[tuple[Path, int]]:
    """Find wiki articles relevant to the prompt, sorted by score descending."""
    if not WIKI_DIR.exists():
        return []

    keywords = extract_keywords(prompt)
    if not keywords:
        return []

    scored: list[tuple[Path, int]] = []
    for article in WIKI_DIR.rglob("*.md"):
        score = score_article(article, keywords)
        if score > 0:
            scored.append((article, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:MAX_ARTICLES]


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------


def format_matched_articles(matches: list[tuple[Path, int]]) -> str:
    """Read matched articles and format as additionalContext."""
    parts: list[str] = []
    total_chars = 0

    for path, score in matches:
        content = path.read_text(encoding="utf-8")
        rel = path.relative_to(WIKI_DIR)
        slug = str(rel).replace("\\", "/").replace(".md", "")

        # Cap per-article size
        if len(content) > 1500:
            content = content[:1500] + "\n\n...(truncated)"

        entry = f"### [[{slug}]]\n\n{content}"

        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            break

        parts.append(entry)
        total_chars += len(entry)

    if not parts:
        return ""

    header = "## Relevant wiki articles for your question\n\n"
    return header + "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, ValueError, EOFError):
        return

    prompt = hook_input.get("prompt", "")
    if len(prompt) < MIN_PROMPT_LENGTH:
        return

    matches = find_relevant_articles(prompt)
    if not matches:
        return

    context = format_matched_articles(matches)
    if not context:
        return

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block user prompt due to hook errors
        pass
