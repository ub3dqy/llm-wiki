# Karpathy Gists Application Plan - 2026-05-07

## Context

User asked to study <https://gist.github.com/karpathy> and apply useful ideas to this
project. The relevant gist is Karpathy's LLM Wiki note:
<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>.

Current project state already implements the core pattern:

- markdown-first global wiki
- local/project agent contracts via `AGENTS.md` and `CLAUDE.md`
- `raw/` staging for source material
- Obsidian-friendly wikilinks
- `wiki/qa/` for filed answers
- hook-based capture and per-prompt retrieval
- `manual` backend for Codex/human maintenance when Agent SDK is unavailable

## Recommended Plan

### Phase 1 - Manual Q&A file-back

Status: implemented in this batch.

Problem: `query.py --file-back` depends on Agent SDK. In `WIKI_AGENT_BACKEND=manual`,
Codex and humans could preview candidates, but there was no first-class command to save an
already-written answer into `wiki/qa/`.

Implementation:

- `scripts/query.py`
  - added `--save-answer-file`
  - writes `wiki/qa/<slug>.md`
  - rebuilds `index.md`
  - appends to `log.md`
  - updates `manual_qa_file_count` in `scripts/state.json`
- `scripts/wiki_cli.py`
  - documented pass-through usage
- tests
  - added manual Q&A article/log/state coverage in `tests/test_query.py`

### Phase 2 - Retrieval benchmark before search replacement

Status: implemented in this batch.

Problem: Karpathy/qmd-style search is attractive, but replacing the current retrieval path
without a baseline risks adding dependency complexity without proving quality improvement.

Implementation:

- `scripts/retrieval_benchmark.py`
  - runs production `shared_wiki_search.find_relevant_articles`
  - ships default cases tied to existing memory-claude pages
  - supports custom JSON cases
  - reports latency, top-1 hit count, any-hit count, and MRR
  - supports machine-readable `--json` output for future qmd/BM25 comparison
- tests
  - added pure metric/normalization coverage in `tests/test_retrieval_benchmark.py`

### Phase 3 - qmd/BM25 decision gate

Status: planned, not implemented.

Decision rule:

- do not add qmd or another search dependency until the benchmark shows a real retrieval
  miss/latency problem that the current Python path cannot address cheaply
- first compare against a Python BM25/IDF improvement or a qmd adapter behind an optional
  command, not the hook hot path

Candidate validation:

```bash
uv run python scripts/retrieval_benchmark.py --json
```

### Phase 4 - Obsidian Dataview metadata

Status: planned.

The repo already has frontmatter fields that Dataview can use. The next useful step is a
small documentation page with example Dataview queries for:

- active/stale/superseded pages
- never-reviewed pages
- Q&A articles by project
- source pages by status

Do not make Dataview a runtime dependency.

### Phase 5 - Raw ingest helper

Status: planned.

The repo already has `raw/`, but source capture would benefit from a helper that stages a raw
file into the right project subfolder and creates a source-page stub. This should stay
markdown-first and avoid network fetches by default.

### Phase 6 - Memory taxonomy

Status: documented in architecture memory after implementation.

Map Karpathy's contemplated memory layers onto existing repo structures:

- episodic: `daily/YYYY-MM-DD.md`
- semantic: `wiki/concepts`, `wiki/sources`, `wiki/entities`, `wiki/connections`
- procedural: `CLAUDE.md`, `AGENTS.md`, hooks, scripts, and project workflow docs

## Non-Goals

- no vector database
- no mandatory qmd dependency
- no always-on service
- no replacement of `shared_wiki_search.py` before benchmark evidence exists

## Verification Plan

Run after implementation:

```bash
uv run python -m pytest -q
uv run ruff check scripts hooks tests
uv run ruff format --check scripts hooks tests
python scripts/retrieval_benchmark.py --json
python scripts/doctor.py --quick
python scripts/lint.py --structural-only
```

## Verification Result

Completed locally after implementation:

- `.venv\Scripts\python.exe -m pytest -q` -> 149 passed
- `.venv\Scripts\ruff.exe check scripts hooks tests` -> all checks passed
- `.venv\Scripts\ruff.exe format --check scripts hooks tests` -> 42 files already formatted
- `.venv\Scripts\python.exe scripts\retrieval_benchmark.py --json` -> default cases top1 5/5, any 5/5, MRR 1.0; average latency ~199ms in the latest run
- `.venv\Scripts\python.exe scripts\doctor.py --quick` -> PASS
- `.venv\Scripts\python.exe scripts\lint.py --structural-only` -> 0 errors, 0 warnings
- `.venv\Scripts\python.exe scripts\personal_data_check.py` -> clear
- `git diff --check` -> no whitespace errors; PowerShell reported LF/CRLF conversion warnings only
