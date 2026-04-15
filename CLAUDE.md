# LLM Wiki — Schema

This is the schema file for the LLM Wiki. It defines the structure, conventions, and workflows that the LLM follows when maintaining this wiki.

This wiki serves as a **global knowledge base across all projects**. It combines three input channels:

- **Manual ingest** (Karpathy pattern): external sources placed in `raw/`
- **Auto-capture** (Memory Compiler): conversation insights captured via Claude Code hooks
- **On-demand save**: targeted knowledge captured directly into the wiki via `/wiki-save`

## Directory Structure

```text
.
├── CLAUDE.md          # This file — schema and conventions
├── index.md           # Content index — catalog of all wiki pages
├── log.md             # Chronological log of all operations
├── pyproject.toml     # Python dependencies (uv)
│
├── raw/               # Immutable source documents (manual ingest)
│   ├── <project>/     # One subfolder per project you track in your wiki.
│   │                  # Names should match the canonical project taxonomy
│   │                  # in your local scripts/project_aliases.local.json.
│   ├── external/      # Sources that do not fit any project category
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
│   └── lint.py        # Structural + provenance health checks
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
confidence: extracted | inferred | to-verify
project: project-name (for auto-captured content)
tags: [relevant tags]
---

# Page Title

Content here. Use [[wikilinks]] for cross-references to other pages.

## See Also

- [[Related Page 1]]
- [[Related Page 2]]
```

`confidence` is **required for all concept and connection pages**. Source/entity/analysis/qa
pages may omit it when the field would not add useful signal.

## Agent operating rules (read before any edit in this project)

Non-negotiable rules for any AI agent (Claude Code, Codex, or otherwise) working in this
repository. These exist to compensate for measured behavioral regressions in frontier coding
models (see [[sources/claude-code-67-percent-reasoning-regression-reddit]] — 67% reasoning
depth drop, file reads 6.6→2, ~33% edits without prior read) and to force the habits the
tooling can no longer guarantee by default.

- **Research the codebase before editing. Never change code you haven't read.** If you are
  about to modify a file, open it first — the whole function or block you are touching, plus
  its direct call sites. No guessing at contents based on the filename or the task description.
- **Verify work actually works before claiming done.** Run the relevant smoke check (doctor,
  lint, test, or explicit manual invocation) and include the real output in your report. Do
  not write "should work" — either it does and you can show it, or you say "blocked: <reason>"
  and stop.
- **Non-trivial handoff plans pass through two independent review rounds, not one.** First
  round catches design-level issues (is the approach right, does it cover the real problem).
  Second round catches consistency issues (do all sections of the plan agree with each other
  after revision, do acceptance criteria match verification steps, does arithmetic add up).
  Neither round substitutes for the other — skipping the second round is the exact failure
  mode that leaves stale references in whitelist/verification/acceptance sections after the
  core changes were made. When revising a plan after feedback, always do a **full-document
  walk** reading every section against the new design, not a keyword grep.

These rules apply regardless of task size. "Small task, obviously safe" is the exact failure
mode all three rules are designed to prevent.

## Conventions

- **Language**: Wiki content follows the language of the source material. Meta-files (index, log) are in Russian unless the user specifies otherwise.
- **Wikilinks**: Always use `[[Page Name]]` syntax for internal links (Obsidian-compatible).
- **One concept per page**: Don't merge unrelated topics. Split when a section grows large.
- **Source attribution**: Every claim should be traceable to a source via the `sources` frontmatter field.
- **Confidence labels**: all concept and connection articles should declare whether claims are
  `extracted`, `inferred`, or `to-verify`.
- **Freshness metadata** (optional, since 2026-04-15): concept/connection/source pages may declare:
  - `status: active | stale | superseded | archived` (default `active` if omitted)
  - `reviewed: YYYY-MM-DD` — date of most recent **manual human review** of the claim's current relevance.
    This field is **only** set by a human reading the page and explicitly confirming it is still current.
    Automatic processes (`compile.py`, source-drift checks, etc) **must not** write to `reviewed`.
    Pages without `reviewed` are treated as never-reviewed by lint advisory.
  - `superseded_by: [[other-page]]` — wikilink to replacement if status is `superseded`

  Freshness is a **temporal axis** (when was this last checked) and is **orthogonal** to `confidence` which is
  the **epistemic axis** (how confident are we in the claim's accuracy). A page can be `confidence: extracted`
  (high factual confidence) and `status: stale` (world changed, claim no longer current) simultaneously.
  These fields are **advisory-only** at lint time; they affect retrieval ranking but do not block merges.
- **Provenance section**: all concept and connection articles should include a short
  `## Provenance` section that explains what was directly observed in the source material and
  what was inferred.
- **Contradictions**: When sources disagree, note it explicitly with a `> [!warning] Contradiction` callout.
- **Updates over rewrites**: When new information arrives, update existing pages rather than creating duplicates.
- **Project tags**: Use the `project` frontmatter field to tag content by origin project.

## Workflows

### Ingest (adding a new source from raw/)

1. Read the source document from `raw/<project>/` (or `raw/external/` if it does not fit an existing project). Project folders mirror the `project:` taxonomy used across your wiki articles — subfolder names should match the canonical project names in your local `scripts/project_aliases.local.json` configuration.
1b. Before creating the summary page, ensure the raw file is physically located in the correct project subfolder. If a new user dropped a document into `raw/` root, move it into the appropriate subfolder first. This keeps `raw/` immutable at the file-content level but organized at the folder level.
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
3. Create concept articles in `wiki/concepts/` with full frontmatter, including `confidence`.
4. Create connection articles in `wiki/connections/` for cross-cutting insights.
5. Update existing articles if new info relates to known concepts.
6. Add a `## Provenance` section for compile-generated material.
7. Update `index.md` and append to `log.md`.

### Query (answering a question)

Handled by `scripts/query.py` or manually.

1. Read `index.md` to find relevant pages.
2. Read the relevant wiki pages.
3. Use `query.py --preview` when you want a no-cost candidate/provenance check before an Agent SDK turn.
4. Synthesize an answer with `[[wikilink]]` citations.
5. Separate extracted facts, inferred synthesis, and to-verify claims when it matters.
6. If the answer is substantial, offer to file it as a new page in `wiki/qa/`.
7. If filed, update `index.md` and append to `log.md`.

### Lint (health check)

Handled by `scripts/lint.py`. Run periodically.

8 checks:

1. **Broken links** — `[[wikilinks]]` pointing to non-existent pages
2. **Orphan pages** — pages with zero inbound links
3. **Orphan sources** — daily logs not yet compiled
4. **Stale articles** — source changed since compilation
5. **Missing backlinks** — asymmetric links (A→B but no B→A)
6. **Sparse articles** — fewer than 200 words
7. **Provenance completeness** — concept and connection pages
   must have valid `confidence` and `## Provenance`
8. **Contradictions** — LLM-detected conflicting claims (costs API credits)

`scripts/doctor.py` should stay aligned with these cheap quality gates and supports
two modes:

- `--quick` for fast daily checks: index freshness, structural lint cleanliness,
  direct `query.py --preview`, CLI `wiki_cli.py query --preview`,
  `wiki_cli.py status`, `wiki_cli.py lint --structural-only`,
  `wiki_cli.py rebuild --check`, and path normalization
- `--full` for the recommended manual pre-merge check: everything in quick mode
  plus runtime/WSL/Codex checks and hook smokes

### Gate roles

Keep these roles separate:

1. **Required gate (CI / pre-commit)**  
   `doctor --quick` + `lint --structural-only`  
   This is the deterministic merge gate and should be the only blocking quality gate.

2. **Manual pre-merge check (recommended, not blocker)**  
   `doctor --full`  
   This extends the quick gate with runtime, WSL/Codex, and hook-smoke coverage.

3. **Advisory knowledge review (non-blocker)**  
   `lint --full`  
   This adds the expensive contradiction review. Its results are non-deterministic and
   must not be used as a merge gate.

`wiki_cli.py doctor` should default to `--quick` when no mode is passed, so the
main CLI stays convenient for everyday smoke checks.
`wiki_cli.py lint` should default to `--structural-only`, while `wiki_cli.py lint --full`
should remain the explicit expensive advisory route that includes contradiction checks and
uses the project dependency environment.
When `lint --full` runs from WSL, the contradiction check may delegate to the
Windows `uv` runtime to keep results aligned with the primary project setup.

Reports saved to `reports/lint-YYYY-MM-DD.md`.

## Auto-Capture (hooks)

Six Claude Code hooks support the knowledge system overall. Three of them are
the core automatic capture hooks that write new session knowledge into `daily/`,
while the others handle reactive inject, micro-capture, and save reminders:

| Hook                   | When              | What it does                                              |
| ---------------------- | ----------------- | --------------------------------------------------------- |
| `session-start.py`     | Session begins    | Injects wiki index + recent daily log as context          |
| `session-end.py`       | Session ends      | Extracts transcript → spawns flush.py in background       |
| `pre-compact.py`       | Before compaction | Same as session-end but with 5-turn minimum               |
| `user-prompt-wiki.py`  | Before each prompt| Injects top relevant wiki articles for the current prompt |
| `post-tool-capture.py` | After Bash/tool   | Captures git/test micro-events into the daily log         |
| `stop-wiki-reminder.py`| After each answer | Reminds about `/wiki-save` for important decisions        |

`session-end.py`, `pre-compact.py`, and `post-tool-capture.py` are the three
hooks dedicated to automatic knowledge capture. The other hooks keep that
knowledge loop useful during active work.

`flush.py` uses Claude Agent SDK to evaluate whether the conversation contained valuable knowledge. If yes, it appends a structured summary to `daily/YYYY-MM-DD.md`.

When hooks spawn `flush.py` or `compile.py` in the background, keep those subprocesses
on the project `uv run --directory <repo>` path so `claude_agent_sdk` and the project
dependency environment stay consistent across Windows and WSL.

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

# Show staging-style summary for one file without writing
uv run python scripts/compile.py --file daily/2026-04-10.md --dry-run

# Query the knowledge base
uv run python scripts/query.py "your question here"

# Preview likely articles without starting Agent SDK
uv run python scripts/query.py "your question here" --preview

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
uv run python scripts/wiki_cli.py doctor
uv run python scripts/wiki_cli.py doctor --full
uv run python scripts/wiki_cli.py status
uv run python scripts/wiki_cli.py doctor --quick
uv run python scripts/wiki_cli.py doctor --full
uv run python scripts/wiki_cli.py compile
uv run python scripts/wiki_cli.py query "question"
uv run python scripts/wiki_cli.py query "question" --preview
uv run python scripts/wiki_cli.py lint
uv run python scripts/wiki_cli.py lint --full
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
