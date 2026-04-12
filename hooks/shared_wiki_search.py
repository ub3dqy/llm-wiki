"""Shared wiki article search for Claude Code and Codex UserPromptSubmit hooks.

Parses the user's prompt, finds wiki articles matching keywords,
and injects their content as additionalContext so the agent has
just-in-time knowledge for the specific question.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from hook_utils import infer_project_name_from_cwd, parse_frontmatter

ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = ROOT / "wiki"

MAX_ARTICLES = 3
MAX_CONTEXT_CHARS = 4000
MIN_PROMPT_LENGTH = 10
PER_ARTICLE_CHAR_CAP = 1700

# Words to skip during keyword extraction
STOP_WORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "shall",
    "must",
    "need",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "while",
    "for",
    "to",
    "from",
    "in",
    "on",
    "at",
    "by",
    "with",
    "about",
    "into",
    "not",
    "no",
    "yes",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "как",
    "что",
    "где",
    "когда",
    "почему",
    "зачем",
    "какой",
    "какая",
    "какое",
    "какие",
    "мне",
    "мой",
    "нам",
    "наш",
    "все",
    "всё",
    "это",
    "для",
    "при",
    "без",
    "над",
    "под",
    "про",
    "или",
    "так",
    "уже",
    "ещё",
    "еще",
    "тоже",
    "также",
    "очень",
    "можно",
    "нужно",
    "есть",
}

def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3 :].lstrip()


def _normalize_token(text: str) -> str:
    return re.sub(r"[\s_]+", "-", text.lower()).strip("-")


def _extract_aliases(raw_aliases: str) -> list[str]:
    """Parse aliases frontmatter from a loose string form."""
    if not raw_aliases:
        return []
    text = raw_aliases.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    parts = [part.strip().strip("'\"") for part in text.split(",")]
    return [part for part in parts if part]


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_-]{3,}")


def extract_keywords(prompt: str) -> set[str]:
    """Extract meaningful keywords from the user's prompt."""
    words = _WORD_RE.findall(prompt.lower())
    return {w for w in words if w not in STOP_WORDS}


def build_search_phrases(prompt: str) -> set[str]:
    """Build normalized multi-word phrases from the prompt."""
    lowered = prompt.lower()
    phrases: set[str] = set()

    for chunk in re.split(r"[?!.,:;()\[\]\n]+", lowered):
        chunk = chunk.strip()
        if len(chunk) < 5:
            continue
        words = [w for w in _WORD_RE.findall(chunk) if w not in STOP_WORDS]
        if len(words) >= 2:
            phrases.add(" ".join(words[:4]))

    return phrases


# ---------------------------------------------------------------------------
# Article matching
# ---------------------------------------------------------------------------


def score_article(path: Path, keywords: set[str], phrases: set[str], project_name: str | None = None) -> int:
    """Score an article by exact and partial matches in metadata and body."""
    fm = parse_frontmatter(path)
    title = fm.get("title", "").lower()
    tags = fm.get("tags", "").lower()
    project = fm.get("project", "").lower()
    aliases = " ".join(_extract_aliases(fm.get("aliases", ""))).lower()
    slug = path.stem.lower()
    slug_spaced = slug.replace("-", " ").replace("_", " ")
    body = _strip_frontmatter(path.read_text(encoding="utf-8"))
    snippet = body[:900].lower()

    score = 0
    matched_keywords = 0

    normalized_project = _normalize_token(project_name or "")
    article_projects = {_normalize_token(p) for p in project.split(",") if p.strip()}
    if normalized_project and normalized_project in article_projects:
        score += 6

    for kw in keywords:
        normalized_kw = _normalize_token(kw)
        keyword_hit = False

        if kw == title or normalized_kw == _normalize_token(title):
            score += 16
            keyword_hit = True
        elif kw in title:
            score += 10
            keyword_hit = True

        if kw == slug or normalized_kw == _normalize_token(slug):
            score += 14
            keyword_hit = True
        elif kw in slug_spaced or normalized_kw in _normalize_token(slug):
            score += 10
            keyword_hit = True

        if kw in aliases:
            score += 8
            keyword_hit = True

        if kw in tags:
            score += 6
            keyword_hit = True

        if kw in project:
            score += 5
            keyword_hit = True

        if re.search(rf"\b{re.escape(kw)}\b", snippet):
            score += 4
            keyword_hit = True
        elif kw in snippet:
            score += 2
            keyword_hit = True

        if keyword_hit:
            matched_keywords += 1

    normalized_search_space = f"{title} {slug_spaced} {aliases} {tags}"
    for phrase in phrases:
        if phrase in normalized_search_space:
            score += 10
        elif phrase in snippet:
            score += 5

    updated_raw = fm.get("updated", "")
    if updated_raw:
        try:
            updated_date = datetime.strptime(updated_raw, "%Y-%m-%d").date()
            if updated_date >= (datetime.now().date() - timedelta(days=14)):
                score += 1
        except ValueError:
            pass

    return score


def find_relevant_articles(
    prompt: str,
    wiki_dir: Path | None = None,
    project_name: str | None = None,
) -> list[tuple[Path, int]]:
    """Find wiki articles relevant to the prompt, sorted by score descending."""
    search_dir = wiki_dir or WIKI_DIR
    if not search_dir.exists():
        return []

    keywords = extract_keywords(prompt)
    phrases = build_search_phrases(prompt)
    if not keywords:
        return []

    scored: list[tuple[Path, int]] = []
    for article in search_dir.rglob("*.md"):
        score = score_article(article, keywords, phrases, project_name=project_name)
        if score > 0:
            scored.append((article, score))

    scored.sort(key=lambda x: (x[1], str(x[0]).lower()), reverse=True)
    return scored[:MAX_ARTICLES]


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------


def format_matched_articles(
    matches: list[tuple[Path, int]],
    wiki_dir: Path | None = None,
) -> str:
    """Read matched articles and format as additionalContext."""
    base_dir = wiki_dir or WIKI_DIR
    parts: list[str] = []
    total_chars = 0

    for path, score in matches:
        content = path.read_text(encoding="utf-8")
        rel = path.relative_to(base_dir)
        slug = str(rel).replace("\\", "/").replace(".md", "")

        # Cap per-article size
        if len(content) > PER_ARTICLE_CHAR_CAP:
            content = content[:PER_ARTICLE_CHAR_CAP] + "\n\n...(truncated)"

        entry = f"### [[{slug}]] (score: {score})\n\n{content}"

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


def find_and_inject_articles() -> None:
    """Read hook stdin, search matching wiki articles, and print hook JSON."""
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

    cwd = hook_input.get("cwd", "")
    project_name = infer_project_name_from_cwd(cwd, repo_root=ROOT) if isinstance(cwd, str) and cwd else None

    matches = find_relevant_articles(prompt, project_name=project_name)
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
