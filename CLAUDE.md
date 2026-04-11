# LLM Wiki — Schema

This is the schema file for the LLM Wiki. It defines the structure, conventions, and workflows that the LLM follows when maintaining this wiki.

This wiki serves as a **global knowledge base across all projects**. It combines two input channels:

- **Manual ingest** (Karpathy pattern): external sources placed in `raw/`
- **Auto-capture** (Memory Compiler): conversation insights captured via Claude Code hooks

## Directory Structure

```text
.
├── CLAUDE.md          # This file — schema and conventions
├── index.md           # Content index — catalog of all wiki pages
├── log.md             # Chronological log of all operations
├── pyproject.toml     # Python dependencies (uv)
│
├── raw/               # Immutable source documents (manual ingest)
│   └── assets/        # Downloaded images and media
│
├── daily/             # Auto-captured conversation logs (from hooks)
│   └── YYYY-MM-DD.md  # Daily log entries
│
├── wiki/              # LLM-maintained wiki pages
│   ├── overview.md    # High-level overview and synthesis
│   ├── sources/       # Source summaries (one per ingested source from raw/)
│   ├── entities/      # Entity pages (people, organizations, tools)
│   ├── concepts/      # Concept pages (ideas, patterns, architectures)
│   ├── analyses/      # Query results filed as wiki pages
│   ├── connections/   # Cross-concept synthesis (non-obvious relationships)
│   └── qa/            # Filed Q&A answers
│
├── reports/           # Lint health-check reports
│
├── scripts/           # Python scripts (flush, compile, query, lint)
│   ├── config.py      # Paths and constants
│   ├── utils.py       # Shared utilities
│   ├── flush.py       # Extract insights from sessions → daily/
│   ├── compile.py     # Compile daily/ → wiki/ articles
│   ├── query.py       # Search the knowledge base
│   └── lint.py        # 7 health checks
│
└── hooks/             # Claude Code hook scripts
    ├── session-start.py   # Inject wiki context at session start
    ├── session-end.py     # Capture transcript at session end
    └── pre-compact.py     # Capture transcript before compaction
```

## Page Format

Every wiki page uses this structure:

```markdown
---
title: Page Title
type: source | entity | concept | analysis | connection | qa
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [list of source filenames that informed this page]
project: project-name (for auto-captured content)
tags: [relevant tags]
---

# Page Title

Content here. Use [[wikilinks]] for cross-references to other pages.

## See Also

- [[Related Page 1]]
- [[Related Page 2]]
```

## Conventions

- **Language**: Wiki content follows the language of the source material. Meta-files (index, log) are in Russian unless the user specifies otherwise.
- **Wikilinks**: Always use `[[Page Name]]` syntax for internal links (Obsidian-compatible).
- **One concept per page**: Don't merge unrelated topics. Split when a section grows large.
- **Source attribution**: Every claim should be traceable to a source via the `sources` frontmatter field.
- **Contradictions**: When sources disagree, note it explicitly with a `> [!warning] Contradiction` callout.
- **Updates over rewrites**: When new information arrives, update existing pages rather than creating duplicates.
- **Project tags**: Use the `project` frontmatter field to tag content by origin project.

## Workflows

### Ingest (adding a new source from raw/)

1. Read the source document from `raw/`.
2. Discuss key takeaways with the user.
3. Create a summary page in `wiki/sources/` with frontmatter.
4. Update `wiki/overview.md` if the source changes the big picture.
5. Create or update relevant entity pages in `wiki/entities/`.
6. Create or update relevant concept pages in `wiki/concepts/`.
7. Add cross-references (`[[wikilinks]]`) across all touched pages.
8. Update `index.md` with new/changed pages.
9. Append an entry to `log.md`.

### Compile (auto-processing daily logs)

Handled by `scripts/compile.py`. Triggered automatically after 18:00 or manually.

1. Read unprocessed daily logs from `daily/`.
2. Extract 3-7 distinct concepts per log.
3. Create concept articles in `wiki/concepts/` with full frontmatter.
4. Create connection articles in `wiki/connections/` for cross-cutting insights.
5. Update existing articles if new info relates to known concepts.
6. Update `index.md` and append to `log.md`.

### Query (answering a question)

Handled by `scripts/query.py` or manually.

1. Read `index.md` to find relevant pages.
2. Read the relevant wiki pages.
3. Synthesize an answer with `[[wikilink]]` citations.
4. If the answer is substantial, offer to file it as a new page in `wiki/qa/`.
5. If filed, update `index.md` and append to `log.md`.

### Lint (health check)

Handled by `scripts/lint.py`. Run periodically.

7 checks:

1. **Broken links** — `[[wikilinks]]` pointing to non-existent pages
2. **Orphan pages** — pages with zero inbound links
3. **Orphan sources** — daily logs not yet compiled
4. **Stale articles** — source changed since compilation
5. **Missing backlinks** — asymmetric links (A→B but no B→A)
6. **Sparse articles** — fewer than 200 words
7. **Contradictions** — LLM-detected conflicting claims (costs API credits)

Reports saved to `reports/lint-YYYY-MM-DD.md`.

## Auto-Capture (hooks)

Three Claude Code hooks capture knowledge automatically from every session:

| Hook               | When              | What it does                                        |
| ------------------ | ----------------- | --------------------------------------------------- |
| `session-start.py` | Session begins    | Injects wiki index + recent daily log as context    |
| `session-end.py`   | Session ends      | Extracts transcript → spawns flush.py in background |
| `pre-compact.py`   | Before compaction | Same as session-end but with 5-turn minimum         |

`flush.py` uses Claude Agent SDK to evaluate whether the conversation contained valuable knowledge. If yes, it appends a structured summary to `daily/YYYY-MM-DD.md`.

After 18:00, flush.py auto-triggers `compile.py` to process the day's logs into wiki articles.

## CLI Commands

```bash
# Compile daily logs into wiki articles
uv run python scripts/compile.py

# Compile a specific log
uv run python scripts/compile.py --file daily/2026-04-10.md

# Force recompile all
uv run python scripts/compile.py --all

# Preview what would be compiled
uv run python scripts/compile.py --dry-run

# Query the knowledge base
uv run python scripts/query.py "your question here"

# Query and file the answer as a Q&A article
uv run python scripts/query.py "your question" --file-back

# Run all lint checks (includes LLM contradiction check)
uv run python scripts/lint.py

# Run only structural checks (free, no API)
uv run python scripts/lint.py --structural-only

# Rebuild index with enriched annotations [project] (Nw) + By Project section
uv run python scripts/rebuild_index.py

# Preview rebuilt index without writing
uv run python scripts/rebuild_index.py --dry-run

# Check if index is out of date (exit 1 if yes)
uv run python scripts/rebuild_index.py --check

# Seed wiki from an existing project
uv run python scripts/seed.py "path/to/project"
uv run python scripts/seed.py "path/to/project" --dry-run
uv run python scripts/seed.py "path/to/project" --project-name myproject

# Wiki CLI (unified interface)
uv run python scripts/wiki_cli.py status
uv run python scripts/wiki_cli.py compile
uv run python scripts/wiki_cli.py query "question"
uv run python scripts/wiki_cli.py lint
uv run python scripts/wiki_cli.py rebuild
uv run python scripts/wiki_cli.py seed "path/to/project"
```

## Tags Taxonomy

Use lowercase, hyphenated tags. Categories:

- **Project tags**: `#my-project`, `#side-project`, `#personal`, etc.
- **Domain tags**: specific to topic (define as you go)
- **Meta tags**: `#needs-review`, `#contradiction`, `#stub`, `#key-insight`

## Scaling

- **Up to 500 articles**: index-guided search works well (current approach)
- **500-2000 articles**: optimize index.md, consider category-based splitting
- **2000+ articles**: hybrid RAG needed (embeddings + index)
