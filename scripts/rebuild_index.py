"""Rebuild index.md with enriched link lines (project tags + word counts)
and a By Project section at the end.

Usage:
    uv run python scripts/rebuild_index.py            # rebuild in place
    uv run python scripts/rebuild_index.py --dry-run   # print to stdout
    uv run python scripts/rebuild_index.py --check     # exit 1 if out of date
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INDEX_FILE, now_iso
from utils import build_article_metadata_map

# Regex to strip previously-added annotations: [project] (Nw) at end of line
_ANNOTATION_RE = re.compile(r"\s+\[[a-z0-9_, -]+\]\s*\(\d+w\)$")
_ANNOTATION_WORDCOUNT_ONLY_RE = re.compile(r"\s+\(\d+w\)$")
# Regex to extract wikilink slug from an index line
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)")

_BY_PROJECT_MARKER = "\n## By Project\n"
MAX_PROJECTS_DETAILED = 15  # projects with full article listings



def strip_existing_annotations(line: str) -> str:
    """Remove previously-added [project] (Nw) or (Nw) suffixes for idempotent rebuilds."""
    line = _ANNOTATION_RE.sub("", line)
    line = _ANNOTATION_WORDCOUNT_ONLY_RE.sub("", line)
    return line


def enrich_index_line(line: str, meta: dict[str, dict]) -> str:
    """Enrich one index.md line with [project] (Nw) annotations.

    Lines without [[wikilinks]] or not starting with '- [[' are returned unchanged.
    """
    stripped = line.rstrip()
    if not stripped.startswith("- [["):
        return line

    # Clean any existing annotations first
    clean = strip_existing_annotations(stripped)

    # Extract slug from wikilink
    m = _WIKILINK_RE.search(clean)
    if not m:
        return line

    slug = m.group(1)
    info = meta.get(slug)
    if not info:
        return line

    # Build annotation
    projects = info.get("projects", [])
    word_count = info.get("word_count", 0)

    suffix = ""
    if projects:
        suffix += f" [{', '.join(projects)}]"
    suffix += f" ({word_count}w)"

    return clean + suffix


def build_by_project_section(meta: dict[str, dict], enriched_lines: list[str]) -> str:
    """Build the '## By Project' section grouping articles by project tag."""
    # Collect all projects
    project_articles: dict[str, list[str]] = {}
    untagged: list[str] = []

    # Build a slug → enriched line map for reuse
    slug_to_line: dict[str, str] = {}
    for line in enriched_lines:
        m = _WIKILINK_RE.search(line)
        if m and line.strip().startswith("- [["):
            slug_to_line[m.group(1)] = line.strip()

    for slug, info in sorted(meta.items()):
        projects = info.get("projects", [])
        # Use enriched line if available, else build a basic one
        display = slug_to_line.get(slug, f"- [[{slug}]] — {info.get('title', slug)} ({info['word_count']}w)")

        if not projects:
            untagged.append(display)
        else:
            for proj in projects:
                project_articles.setdefault(proj, []).append(display)

    parts: list[str] = []
    sorted_projects = sorted(project_articles.keys())

    # Detailed listing for top projects, compact for the rest
    for i, proj in enumerate(sorted_projects):
        if i < MAX_PROJECTS_DETAILED:
            parts.append(f"\n### {proj}\n")
            for line in sorted(project_articles[proj]):
                parts.append(line)
        else:
            # Compact: just project name and article count
            count = len(project_articles[proj])
            parts.append(f"\n### {proj} ({count} articles)\n")

    if untagged:
        parts.append("\n### (untagged)\n")
        for line in sorted(untagged):
            parts.append(line)

    return "\n".join(parts) + "\n"


def rebuild_index() -> str:
    """Read index.md, enrich all wikilink lines, add By Project section."""
    meta = build_article_metadata_map()
    original = INDEX_FILE.read_text(encoding="utf-8")

    # Strip existing By Project section
    if _BY_PROJECT_MARKER in original:
        original = original[: original.index(_BY_PROJECT_MARKER)]
    original = original.rstrip() + "\n"

    # Enrich individual lines
    lines = original.splitlines()
    enriched = [enrich_index_line(line, meta) for line in lines]

    # Build By Project section
    by_project = build_by_project_section(meta, enriched)

    result = "\n".join(enriched) + _BY_PROJECT_MARKER + by_project
    return result


def rebuild_and_write_index() -> None:
    """Rebuild index.md in place (atomic write via temp file)."""
    content = rebuild_index()
    # Atomic write: write to temp, then replace
    tmp = Path(str(INDEX_FILE) + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(INDEX_FILE)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild index.md with enriched annotations")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    parser.add_argument("--check", action="store_true", help="Exit 1 if index is out of date")
    args = parser.parse_args()

    if not INDEX_FILE.exists():
        print(f"index.md not found at {INDEX_FILE} — skipping.")
        sys.exit(0)

    content = rebuild_index()

    if args.check:
        current = INDEX_FILE.read_text(encoding="utf-8")
        if current == content:
            print("Index is up to date.")
            sys.exit(0)
        else:
            print("Index is out of date. Run without --check to rebuild.")
            sys.exit(1)

    if args.dry_run:
        print(content)
        return

    rebuild_and_write_index()
    print("Index rebuilt successfully.")


if __name__ == "__main__":
    main()
