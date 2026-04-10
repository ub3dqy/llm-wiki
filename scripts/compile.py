"""Compile: transform daily logs into structured wiki articles.

Reads unprocessed daily/ logs and uses Claude Agent SDK to create/update
articles in wiki/concepts/, wiki/connections/, and wiki/qa/.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CONCEPTS_DIR, CONNECTIONS_DIR, INDEX_FILE, LOG_FILE, SCHEMA_FILE, WIKI_DIR, now_iso
from utils import file_hash, list_raw_files, list_wiki_articles, load_state, read_wiki_index, save_state

ROOT_DIR = Path(__file__).resolve().parent.parent


async def compile_daily_log(log_path: Path, state: dict) -> float:
    """Compile a single daily log into wiki articles. Returns API cost."""
    from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock, query

    log_content = log_path.read_text(encoding="utf-8")
    schema = SCHEMA_FILE.read_text(encoding="utf-8") if SCHEMA_FILE.exists() else "(no schema)"
    wiki_index = read_wiki_index()

    # Gather existing articles for context
    existing_context = ""
    existing: dict[str, str] = {}
    for article_path in list_wiki_articles():
        rel = article_path.relative_to(ROOT_DIR)
        existing[str(rel)] = article_path.read_text(encoding="utf-8")

    if existing:
        parts = [f"### {rel_path}\n```markdown\n{content}\n```" for rel_path, content in existing.items()]
        existing_context = "\n\n".join(parts)

    timestamp = now_iso()

    prompt = f"""You are a knowledge compiler. Read the daily conversation log and extract
knowledge into structured wiki articles.

## Schema (CLAUDE.md)

{schema}

## Current Wiki Index

{wiki_index}

## Existing Wiki Articles

{existing_context if existing_context else "(No existing articles yet)"}

## Daily Log to Compile

**File:** {log_path.name}

{log_content}

## Your Task

Read the daily log and compile it into wiki articles following the schema.

### Rules:

1. **Extract key concepts** — identify 3-7 distinct concepts worth their own article
2. **Create concept articles** in `wiki/concepts/` — one .md file per concept
   - Use YAML frontmatter: title, type (concept), created, updated, sources, project, tags
   - Use `[[wikilinks]]` for cross-references (e.g. `[[concepts/prisma-migrations]]`)
   - Write in encyclopedia style — neutral, comprehensive
3. **Create connection articles** in `wiki/connections/` if the log reveals non-obvious
   relationships between 2+ existing concepts
4. **Update existing articles** if the log adds new info to concepts already in the wiki
   - Add the new info, add the source to frontmatter
5. **Update index.md** at `{INDEX_FILE}` — add new entries under the appropriate section
6. **Append to log.md** at `{LOG_FILE}`:
   ```
   ## [{timestamp}] compile | {{log_path.name}}
   - Source: daily/{{log_path.name}}
   - Articles created: [[concepts/x]], [[concepts/y]]
   - Articles updated: [[concepts/z]] (if any)
   ```

### File paths:
- Write concept articles to: {CONCEPTS_DIR}
- Write connection articles to: {CONNECTIONS_DIR}
- Update index at: {INDEX_FILE}
- Append log at: {LOG_FILE}

### Quality:
- Every article: complete YAML frontmatter
- Every article: link to at least 2 other articles via [[wikilinks]]
- Key Points: 3-5 bullet points
- Details: 2+ paragraphs
- Related Concepts: 2+ entries
- Sources: cite the daily log with specific claims
"""

    cost = 0.0

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                permission_mode="acceptEdits",
                max_turns=30,
            ),
        ):
            if hasattr(message, "total_cost_usd"):
                cost = message.total_cost_usd or 0.0
                print(f"  Cost: ${cost:.4f}")
    except Exception as e:
        print(f"  Error: {e}")
        return 0.0

    # Track what we compiled
    rel_path = log_path.name
    state.setdefault("ingested", {})[rel_path] = {
        "hash": file_hash(log_path),
        "compiled_at": now_iso(),
        "cost_usd": cost,
    }
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return cost


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile daily logs into wiki articles")
    parser.add_argument("--all", action="store_true", help="Force recompile all logs")
    parser.add_argument("--file", type=str, help="Compile a specific daily log file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    args = parser.parse_args()

    state = load_state()

    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            from config import DAILY_DIR

            target = DAILY_DIR / target.name
        if not target.exists():
            target = ROOT_DIR / args.file
        if not target.exists():
            print(f"Error: {args.file} not found")
            sys.exit(1)
        to_compile = [target]
    else:
        all_logs = list_raw_files()
        if args.all:
            to_compile = all_logs
        else:
            to_compile = []
            for log_path in all_logs:
                rel = log_path.name
                prev = state.get("ingested", {}).get(rel, {})
                if not prev or prev.get("hash") != file_hash(log_path):
                    to_compile.append(log_path)

    if not to_compile:
        print("Nothing to compile — all daily logs are up to date.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Files to compile ({len(to_compile)}):")
    for f in to_compile:
        print(f"  - {f.name}")

    if args.dry_run:
        return

    total_cost = 0.0
    for i, log_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {log_path.name}...")
        cost = asyncio.run(compile_daily_log(log_path, state))
        total_cost += cost
        print("  Done.")

    articles = list_wiki_articles()
    print(f"\nCompilation complete. Total cost: ${total_cost:.2f}")
    print(f"Knowledge base: {len(articles)} articles")


if __name__ == "__main__":
    main()
