"""Compile: transform daily logs into structured wiki articles.

Reads unprocessed daily/ logs and uses Claude Agent SDK to create/update
articles in wiki/concepts/, wiki/connections/, and wiki/qa/.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

# --- Logging (match flush.py / hooks target file) ---
_SCRIPTS_DIR_FOR_LOG = Path(__file__).resolve().parent
logging.basicConfig(
    filename=str(_SCRIPTS_DIR_FOR_LOG / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [compile] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    INDEX_FILE,
    LOG_FILE,
    SCHEMA_FILE,
    WIKI_AGENT_BACKEND,
    now_iso,
)
from utils import (  # noqa: E402
    daily_log_has_compile_signal,
    file_hash,
    list_daily_logs,
    list_wiki_articles,
    load_state,
    read_wiki_index,
    save_state,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

_API_KEY_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"ghp_[A-Za-z0-9]+"),
    re.compile(r"ghs_[A-Za-z0-9]+"),
]


def _scrub_secrets(text: str) -> str:
    """Redact API-key-shaped tokens before writing diagnostic logs."""
    for pattern in _API_KEY_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _log_cli_stderr(line: str) -> None:
    """Forward bundled Claude CLI stderr into flush.log with secret scrubbing."""
    try:
        for subline in line.splitlines():
            if subline.strip():
                logging.info("[agent-stderr] %s", _scrub_secrets(subline))
    except Exception:
        pass


def _is_agent_result_message(message: object) -> bool:
    """Detect SDK ResultMessage without tying compile.py to one SDK type import."""
    return message.__class__.__name__ == "ResultMessage"


def _format_agent_result_error(message: object) -> str:
    result = getattr(message, "result", None)
    if isinstance(result, str) and result.strip():
        return result.strip()
    errors = getattr(message, "errors", None)
    if errors:
        return str(errors)
    return "Agent SDK returned an error result"


def _restore_invocation_guard(previous_value: str | None) -> None:
    if previous_value is None:
        os.environ.pop("CLAUDE_INVOKED_BY", None)
    else:
        os.environ["CLAUDE_INVOKED_BY"] = previous_value


def count_log_entries(log_path: Path) -> int:
    """Count structured entries in a daily log."""
    content = log_path.read_text(encoding="utf-8")
    return content.count("\n## [")


def build_compile_plan(log_paths: list[Path], state: dict) -> list[dict[str, str | int]]:
    """Build a lightweight staging summary for compile candidates."""
    plan: list[dict[str, str | int]] = []
    ingested = state.get("ingested", {})
    for log_path in log_paths:
        prev = ingested.get(log_path.name, {})
        current_hash = file_hash(log_path)
        prev_hash = prev.get("hash", "")
        status = "new" if not prev else "changed" if prev_hash != current_hash else "unchanged"
        plan.append(
            {
                "file": log_path.name,
                "status": status,
                "entries": count_log_entries(log_path),
                "last_compiled_at": prev.get("compiled_at", "never"),
                "hash_prefix": current_hash[:12],
            }
        )
    return plan


def print_compile_plan(plan: list[dict[str, str | int]]) -> None:
    """Print a staging-style summary for dry-run and operator visibility."""
    print("Compile staging summary:")
    for item in plan:
        print(
            f"  - {item['file']}: status={item['status']}, "
            f"entries={item['entries']}, last_compiled_at={item['last_compiled_at']}, "
            f"hash={item['hash_prefix']}"
        )


def mark_daily_log_manually_compiled(log_path: Path, state: dict, note: str) -> None:
    """Record that a daily log was compiled by a manual/Codex workflow."""
    cleaned_note = note.strip()
    if not cleaned_note:
        raise ValueError("manual note is required")

    state.setdefault("ingested", {})[log_path.name] = {
        "hash": file_hash(log_path),
        "compiled_at": now_iso(),
        "cost_usd": 0.0,
        "compiled_by": "manual",
        "manual_note": cleaned_note,
    }
    save_state(state)


async def compile_daily_log(log_path: Path, state: dict) -> float:
    """Compile a single daily log into wiki articles. Returns API cost."""
    if WIKI_AGENT_BACKEND != "claude":
        raise RuntimeError(
            f"Automated compile requires WIKI_AGENT_BACKEND=claude; current backend is "
            f"{WIKI_AGENT_BACKEND!r}. Use --dry-run, then update wiki/index/log/state via the "
            "manual compile workflow."
        )

    from claude_agent_sdk import ClaudeAgentOptions, query

    log_content = log_path.read_text(encoding="utf-8")
    schema = SCHEMA_FILE.read_text(encoding="utf-8") if SCHEMA_FILE.exists() else "(no schema)"
    wiki_index = read_wiki_index()

    timestamp = now_iso()

    prompt = f"""You are a knowledge compiler. Read the daily conversation log and extract
knowledge into structured wiki articles.

## Schema (CLAUDE.md)

{schema}

## Current Wiki Index

{wiki_index}

## Daily Log to Compile

**File:** {log_path.name}

{log_content}

## Your Task

Read the daily log and compile it into wiki articles following the schema.

**IMPORTANT**: Use the Read tool to check existing wiki articles before creating or
updating them. Do NOT assume you know their content — read first, then decide whether
to create a new article or update an existing one. Use Grep to find related articles.

### Rules:

0. **Make a staging plan first** — decide which articles will be created vs updated
   before editing files. Keep the set tight and avoid speculative new pages.
1. **Extract key concepts** — identify 3-7 distinct concepts worth their own article
2. **Check existing articles** — Read any related articles from the index before writing.
   Use Grep to search for related terms across wiki/
3. **Create concept articles** in `wiki/concepts/` — one .md file per concept
   - Use YAML frontmatter: title, type (concept), created, updated, sources, confidence, status, project, tags
   - `project` must be a plain scalar string. For multi-project articles, use comma-separated
     scalar form like `project: codex-easy-start, site-tiretop, workflow`
   - Do NOT emit YAML list form for `project` such as `project: [a, b, c]`
   - Use `[[wikilinks]]` for cross-references (e.g. `[[concepts/prisma-migrations]]`)
   - Write in encyclopedia style — neutral, comprehensive
4. **Create connection articles** in `wiki/connections/` if the log reveals non-obvious
   relationships between 2+ existing concepts
5. **Update existing articles** if the log adds new info to concepts already in the wiki
   - Read the existing article first, then use Edit to add info
   - When updating an existing compile-generated article, preserve and revise `confidence`
     if needed instead of silently dropping it
   - If an older compile-generated article is missing `confidence` or `## Provenance`,
     add them during the update
6. **Update index.md** at `{INDEX_FILE}` — add new entries under the appropriate section
7. **Append to log.md** at `{LOG_FILE}`:
   ```
   ## [{timestamp}] compile | {{log_path.name}}
   - Source: daily/{{log_path.name}}
   - Articles created: [[concepts/x]], [[concepts/y]]
   - Articles updated: [[concepts/z]] (if any)
   ```

### Provenance and confidence:

- `sources:` must only list the concrete source files that informed the article
  (for this workflow, usually `daily/{{log_path.name}}`, plus any existing article sources
  if you are merging into an already-sourced page)
- `confidence:` is required for every newly created compile-generated concept/connection:
  - `extracted` — directly supported by the daily log
  - `inferred` — synthesized from multiple statements in the log
  - `to-verify` — plausible but uncertain, ambiguous, or dependent on incomplete context
- `status:` should be set to `active` for every newly created compile-generated concept/connection
- Add a `## Provenance` section to every newly created compile-generated article:
  - `- Source log: daily/{{log_path.name}}`
  - `- Confidence: <value> — short reason`
  - `- Basis: 1-3 bullets explaining what was directly observed vs inferred`
- When a claim is uncertain, prefer `confidence: to-verify` and say so explicitly.

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
- Compile-generated articles: include `## Provenance`
- Related Concepts: 2+ entries
- Sources: cite the daily log with specific claims
"""

    cost = 0.0
    previous_invoked_by = os.environ.get("CLAUDE_INVOKED_BY")
    os.environ["CLAUDE_INVOKED_BY"] = "compile"

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                permission_mode="acceptEdits",
                max_turns=30,
                stderr=_log_cli_stderr,
                # Keep compile.py non-interactive. Without this, the bundled
                # Claude CLI may discover account-level MCP servers and fail on
                # their auth/config flow after the SDK has already streamed
                # partial output.
                extra_args={"strict-mcp-config": None},
            ),
        ):
            if _is_agent_result_message(message) and getattr(message, "is_error", False):
                raise RuntimeError(_format_agent_result_error(message))
            if hasattr(message, "total_cost_usd"):
                cost = message.total_cost_usd or 0.0
                print(f"  Cost: ${cost:.4f}")
                logging.info("Compile cost for %s: $%.4f", log_path.name, cost)
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        logging.error("Agent SDK failure compiling %s: %s", log_path.name, e)
        raise
    finally:
        _restore_invocation_guard(previous_invoked_by)

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
    parser.add_argument(
        "--mark-manual",
        action="store_true",
        help="Mark --file as manually compiled after wiki/index/log updates are complete",
    )
    parser.add_argument(
        "--manual-note",
        type=str,
        default="",
        help="Required note describing the manual wiki/index/log updates",
    )
    args = parser.parse_args()

    if args.mark_manual:
        if not args.file:
            parser.error("--mark-manual requires --file")
        if args.all:
            parser.error("--mark-manual cannot be combined with --all")
        if not args.manual_note.strip():
            parser.error("--mark-manual requires --manual-note")

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
        all_logs = list_daily_logs()
        low_signal_logs: list[Path] = []
        if args.all:
            to_compile = all_logs
        else:
            to_compile = []
            for log_path in all_logs:
                if not daily_log_has_compile_signal(log_path):
                    low_signal_logs.append(log_path)
                    continue
                rel = log_path.name
                prev = state.get("ingested", {}).get(rel, {})
                if not prev or prev.get("hash") != file_hash(log_path):
                    to_compile.append(log_path)
        if low_signal_logs:
            print(
                "Skipped low-signal daily logs: "
                + ", ".join(log_path.name for log_path in low_signal_logs)
            )

    if not to_compile:
        print("Nothing to compile — all daily logs are up to date.")
        return

    plan = build_compile_plan(to_compile, state)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Files to compile ({len(to_compile)}):")
    for f in to_compile:
        print(f"  - {f.name}")
    print()
    print_compile_plan(plan)

    if args.dry_run:
        print("\nDry run only: no Agent SDK session started, no wiki files changed.")
        return

    if args.mark_manual:
        mark_daily_log_manually_compiled(to_compile[0], state, args.manual_note)
        print(
            "\nManual compile mark written: "
            f"{to_compile[0].name} (cost $0.00, backend manual/Codex)."
        )
        print("No wiki, index, or log files were changed by this command.")
        return

    total_cost = 0.0
    failed_logs: list[str] = []
    compiled_logs: list[str] = []
    for i, log_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {log_path.name}...")
        try:
            cost = asyncio.run(compile_daily_log(log_path, state))
        except Exception as e:
            failed_logs.append(log_path.name)
            print(f"  Failed: {e}", file=sys.stderr)
            continue
        total_cost += cost
        compiled_logs.append(log_path.name)
        print("  Done.")

    if compiled_logs:
        # Rebuild index with enriched annotations and By Project section
        from rebuild_index import rebuild_and_write_index

        rebuild_and_write_index()
        print("Index enriched with project tags and word counts.")
    else:
        print("No logs compiled successfully; skipping index rebuild.")

    articles = list_wiki_articles()
    if failed_logs and not compiled_logs:
        completion_label = "Compilation failed"
    elif failed_logs:
        completion_label = "Compilation partially complete"
    else:
        completion_label = "Compilation complete"
    print(f"\n{completion_label}. Total cost: ${total_cost:.2f}")
    print(f"Knowledge base: {len(articles)} articles")

    if failed_logs:
        print(
            f"\n{len(failed_logs)} log(s) failed to compile: {', '.join(failed_logs)}",
            file=sys.stderr,
        )
        logging.error("compile.py exit 1 — %d failed log(s): %s", len(failed_logs), failed_logs)
        sys.exit(1)


if __name__ == "__main__":
    main()
