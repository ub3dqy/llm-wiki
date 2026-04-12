# LLM Wiki — Persistent Memory for Claude Code & Codex CLI

A global knowledge base that gives Claude Code and Codex CLI **persistent memory across all projects, sessions, and environments** (CLI, VS Code, JetBrains). Knowledge is captured automatically from conversations, compiled into structured wiki articles, and injected back into future sessions — so Claude never starts from zero.

Built on two foundations:
- [**Karpathy's LLM Wiki**](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the three-layer architecture pattern (raw sources → daily logs → wiki articles)
- [**coleam00/claude-memory-compiler**](https://github.com/coleam00/claude-memory-compiler) — auto-capture via Claude Code hooks + Agent SDK compilation

## What makes this different

This project extends both sources with significant improvements:

| Feature | coleam00 original | This project |
|---|---|---|
| Knowledge capture | SessionEnd only | SessionEnd + PreCompact + **PostToolUse async** (real-time) |
| Context injection | Full index dump at session start | **UserPromptSubmit** — per-prompt targeted article injection |
| Project awareness | None | **Project-aware SessionStart** — reads `cwd`, shows relevant articles first |
| Concurrency control | None (caused 400+ node.exe crash) | **File locks + debounce** (max 2 concurrent flush) |
| Index format | Plain list | **Enriched with `[project] (Nw)` + By Project section** |
| Scalability | Loads all articles into prompt | **Index-guided** — agent uses Read/Grep to find articles |
| Wiki save | End-of-session only | **`/wiki-save` skill** — instant save from any project |
| Decision capture | None | **Stop hook** — reminds to save architectural decisions |
| Project seeding | None | **`seed.py`** — bootstrap wiki from existing codebase |
| CLI | Verbose `uv run python scripts/...` | **`wiki_cli.py`** — unified interface |
| Recent changes | None | **Recent Wiki Changes (48h)** section in SessionStart |
| Agent SDK retry | None | **Retry on timeout** with exponential backoff |
| State management | Unbounded growth | **Pruning** (max 50 sessions in state) |
| Provenance | `sources` only | **`confidence` labels + `## Provenance`** for compile-generated articles |
| Query confidence | None | **Query preview + provenance-aware answer guidance** |

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│                    Any Claude Code Session                    │
│                  (CLI, VS Code, JetBrains)                   │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
  SessionStart      UserPromptSubmit     SessionEnd/PreCompact
       │                  │                   │
  Inject wiki        Find relevant       Extract transcript
  index + project    articles by         → flush.py
  context            keywords            → Agent SDK evaluates
       │                  │                   │
       │             Inject article      Worth saving?
       │             content into        → daily/YYYY-MM-DD.md
       │             current prompt           │
       │                                 Auto-compile (18:00)
       │                                 → wiki/concepts/
       │                                 → wiki/connections/
       ▼                                      │
  Claude answers                              ▼
  using wiki knowledge ◄──────────── Knowledge persists
```

### Six hooks power the system

| Hook | When | What it does |
|---|---|---|
| **SessionStart** | Session begins | Injects wiki index + project-relevant articles + recent changes |
| **SessionEnd** | Session ends | Captures transcript → flush.py → daily log |
| **PreCompact** | Before context compression | Same as SessionEnd (safety net) |
| **UserPromptSubmit** | Before each prompt | Finds and injects wiki articles matching prompt keywords |
| **PostToolUse** | After Bash commands (async) | Captures git commits, test runs as micro-entries |
| **Stop** | After each Claude response | Reminds about `/wiki-save` when architectural decisions detected |

## Quick Start

### Prerequisites

- [Claude Code](https://claude.ai/code) (CLI or IDE extension)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/llm-wiki.git
cd llm-wiki

# 2. Install Python dependencies
uv sync

# 3. Bootstrap the wiki structure
uv run python scripts/setup.py

# 4. Verify everything is wired correctly
uv run python scripts/doctor.py --quick

# 5. Follow the next steps printed by setup.py:
#    - Add hooks to ~/.claude/settings.json
#    - Copy skills/wiki-save to ~/.claude/skills/
#    - (optional) Copy codex-hooks.template.json to ~/.codex/hooks.json

# 6. Start a new Claude Code session — wiki context will be injected automatically
```

`setup.py` is idempotent — you can safely re-run it to restore missing bootstrap files
or recreate the local alias template.

### Configuration

After `setup.py`, use the printed repo path when replacing `/path/to/llm-wiki` in your
hook and skill files. You can keep this section as a reference for the manual edits.

All paths in hook commands and skill files must point to your wiki clone location. Search and replace the example path with your actual path:

```
# Example: replace all occurrences
/path/to/llm-wiki  →  /your/actual/path/to/llm-wiki
```

Files to update:
- `~/.claude/settings.json` (hook commands)
- `~/.claude/skills/wiki-save/SKILL.md` (wiki paths)
- `~/.claude/CLAUDE.md` (global instructions)

### Codex CLI Setup

Codex hooks are currently run from WSL in this repo. Keep the hook commands on
Linux-style paths and use an isolated WSL `uv` environment so the repo's
Windows `.venv` is never rewritten by Linux.

1. Enable hooks in `~/.codex/config.toml`:

```toml
[features]
codex_hooks = true
```

2. Keep Codex inside WSL and open the repo from WSL (not native Windows mode).
3. Copy [`codex-hooks.template.json`](codex-hooks.template.json) to `~/.codex/hooks.json`.
4. Replace only the repo path placeholder:

```text
/path/to/llm-wiki -> /your/actual/wsl/path/to/llm-wiki
```

Do **not** replace `$HOME`. The template already resolves the current Linux user home automatically.

5. Keep the hook commands WSL-safe inside WSL:

```bash
bash -lc 'source "$HOME/.local/bin/env" 2>/dev/null; UV_BIN="${UV_BIN:-$(command -v uv)}"; if test -z "$UV_BIN"; then echo "uv not found; install uv in WSL and ensure it is on PATH" >&2; exit 1; fi; UV_PROJECT_ENVIRONMENT="$HOME/.cache/llm-wiki/.venv" UV_LINK_MODE=copy "$UV_BIN" run --directory "/path/to/llm-wiki" python hooks/codex/session-start.py'
```

The template is intentionally fail-loud now: if `uv` is missing in WSL, the hook should error
clearly instead of silently pretending everything is fine.

6. Run the doctor and smoke checks from WSL:

```bash
python scripts/doctor.py --quick
python scripts/doctor.py --full
uv run python scripts/wiki_cli.py doctor
uv run python scripts/wiki_cli.py doctor --quick
uv run python scripts/wiki_cli.py doctor --full
uv run python scripts/wiki_cli.py status
uv run python scripts/rebuild_index.py --check
```

`doctor.py --quick` is for fast daily checks. `doctor.py --full` runs the full gate, including WSL/Codex runtime checks and hook smokes. The same modes are now available through `wiki_cli.py doctor`, and `wiki_cli.py doctor` without flags defaults to the quick mode.

### Gate roles

Keep these three roles separate:

1. **Required gate (CI / pre-commit)**  
   `python scripts/doctor.py --quick` and `python scripts/wiki_cli.py lint`  
   This is the deterministic baseline and should be the only blocking merge gate.

2. **Manual pre-merge check (recommended, not blocker)**  
   `python scripts/doctor.py --full`  
   This extends the quick gate with runtime, WSL/Codex, and hook-smoke coverage.

3. **Advisory knowledge review (non-blocker)**  
   `python scripts/wiki_cli.py lint --full`  
   This includes the expensive contradiction review. Its findings are non-deterministic
   and must not be used as a merge gate.

7. Start Codex from WSL and verify that the SessionStart hook injects wiki context.

### Repo-level instructions for Codex

This repository now ships with [`AGENTS.md`](AGENTS.md). Codex can use it as project-level guidance, while the full wiki schema remains in [`CLAUDE.md`](CLAUDE.md).

## Usage

### Automatic (hooks do everything)

Just use Claude Code normally. The hooks will:
1. Inject wiki context at session start
2. Inject relevant articles when you ask questions
3. Capture knowledge when sessions end
4. Auto-compile daily logs into wiki articles after 18:00
5. Mark compile-generated knowledge with explicit provenance and confidence

### Manual commands

```bash
# Show wiki status
uv run python scripts/wiki_cli.py status

# Run doctor checks
uv run python scripts/wiki_cli.py doctor
uv run python scripts/wiki_cli.py doctor --quick
uv run python scripts/wiki_cli.py doctor --full

# Compile daily logs into wiki articles
uv run python scripts/wiki_cli.py compile

# Query the knowledge base
uv run python scripts/wiki_cli.py query "how does auth work?"

# Preview likely articles without spending an Agent SDK turn
uv run python scripts/wiki_cli.py query "how does auth work?" --preview

# Run health checks
uv run python scripts/wiki_cli.py lint
uv run python scripts/wiki_cli.py lint --full

# Rebuild index with project tags and word counts
uv run python scripts/wiki_cli.py rebuild

# Seed wiki from an existing project
uv run python scripts/wiki_cli.py seed "/path/to/project"
```

### Slash command

```
/wiki-save <topic>
```

Instantly creates or updates a wiki article from the current conversation. Works from any project.

## Project Structure

```
.
├── CLAUDE.md              # Schema — conventions, workflows, page format
├── index.md               # Wiki index with [project] (Nw) annotations
├── log.md                 # Chronological operation log
├── README.md              # This file
│
├── hooks/                 # Claude Code hook scripts
│   ├── session-start.py       # Inject wiki context (project-aware)
│   ├── session-end.py         # Capture transcript → flush.py
│   ├── pre-compact.py         # Safety net before compaction
│   ├── user-prompt-wiki.py    # Per-prompt targeted article injection
│   ├── post-tool-capture.py   # Async capture of git/test events
│   ├── stop-wiki-reminder.py  # Remind about /wiki-save
│   └── hook_utils.py          # Shared utilities (parse stdin, debounce)
│
├── scripts/               # Python scripts
│   ├── config.py              # Path constants
│   ├── utils.py               # Shared utilities (frontmatter, wikilinks)
│   ├── flush.py               # Evaluate + save conversation insights
│   ├── compile.py             # Compile daily/ → wiki/ articles
│   ├── query.py               # Search the knowledge base
│   ├── lint.py                # Structural + provenance health checks
│   ├── rebuild_index.py       # Enrich index with metadata
│   ├── seed.py                # Bootstrap wiki from project files
│   └── wiki_cli.py            # Unified CLI interface
│
├── daily/                 # Auto-captured conversation logs
├── raw/                   # Manual source documents for ingest
│
├── wiki/                  # LLM-maintained wiki articles
│   ├── overview.md            # High-level synthesis
│   ├── concepts/              # Ideas, patterns, technologies
│   ├── entities/              # Projects, tools, organizations
│   ├── sources/               # Summaries of ingested documents
│   ├── connections/           # Cross-concept relationships
│   ├── analyses/              # Filed analysis results
│   └── qa/                    # Filed Q&A answers
│
├── skills/
│   └── wiki-save/
│       └── SKILL.md           # /wiki-save slash command
│
├── reports/               # Lint health-check reports
├── pyproject.toml         # Python dependencies
└── settings.example.json  # Example hook configuration
```

## Key Design Decisions

### Why not RAG/embeddings?

At personal scale (50-500 articles), an LLM reading a structured index outperforms vector similarity search. The wiki index serves as a table of contents — Claude reads it, identifies relevant articles, and reads them directly. No embedding infrastructure needed.

For 2000+ articles, hybrid RAG would be recommended — but that's a problem for later.

### Why separate from projects?

The wiki lives in its own git repo, not inside any project. This allows:
- Cross-project knowledge accumulation
- Global hooks that capture from every project
- Version-controlled knowledge base
- Obsidian-compatible browsing (pure markdown + wikilinks)

### Why Agent SDK for flush/compile?

The `flush.py` script uses Claude Agent SDK to evaluate whether a conversation contains valuable knowledge. This is intentional — only an LLM can judge if "we discussed the weather" is worth saving vs "we decided to use BullMQ for async task processing."

Keep the background chain (`session-end.py` / `pre-compact.py` → `flush.py` → `compile.py`)
on `uv run --directory <repo>` so the Agent SDK and project dependencies always come from the
wiki runtime, not from whichever shell interpreter happened to launch the hook.

Agent SDK uses your existing Claude subscription (Max/Team/Enterprise) — no separate API costs.

### Concurrency control

Without limits, closing multiple sessions simultaneously spawns hundreds of node.exe processes (each flush.py → Agent SDK → bundled claude.exe). File locks limit concurrent flush to 2, debounce prevents rapid-fire spawns.

## Scaling

| Articles | Strategy | Status |
|---|---|---|
| 0-50 | Full index in SessionStart context | Current |
| 50-500 | Index + UserPromptSubmit targeted injection | Current |
| 500-2000 | Category-based sub-indices | Planned |
| 2000+ | Hybrid RAG (embeddings + index) | Future |

## Maintenance Checklist

### After updating Codex CLI

```bash
# 1. Check generated hook schemas in official repo
# Source of truth: openai/codex → codex-rs/hooks/schema/generated/
# NOTE: `codex app-server generate-json-schema` generates app-server
# protocol schemas, NOT hook payload schemas

# 2. Compare payload fields against hook scripts
# Check: hooks/codex/session-start.py, stop.py, user-prompt-wiki.py, post-tool-capture.py

# 3. Run doctor and smoke tests from WSL
python scripts/doctor.py

# 4. Verify feature flag is still active
codex features list
```

Generated schemas are the **source of truth** for your installed version. Wire formats may change between Codex releases — always re-verify after updates.

### After updating Claude Code

```bash
# 1. Verify hooks still pass validation
uv run python scripts/wiki_cli.py status

# 2. Run structural lint
uv run python scripts/wiki_cli.py lint

# 3. Test SessionStart output
echo '{}' | uv run python hooks/session-start.py | python -c "import sys,json; print(len(json.load(sys.stdin)['hookSpecificOutput']['additionalContext']), 'chars')"
```

`wiki_cli.py lint` without flags now defaults to the cheap structural route. Use
`wiki_cli.py lint --full` only when you explicitly want the contradiction review.
That route is advisory, not blocking. The full route uses the project dependency
environment so Agent SDK checks can run even if your current shell Python is
lightweight. In WSL, the contradiction step may delegate to the Windows `uv`
runtime to keep the result consistent with the main project environment.

## Credits

- [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — LLM Wiki concept and three-layer architecture pattern
- [Cole Medin (coleam00)](https://github.com/coleam00/claude-memory-compiler) — Memory Compiler implementation with Claude Code hooks and Agent SDK
- [Claude Code](https://claude.ai/code) — The AI coding tool this system extends
- [claude-agent-sdk](https://pypi.org/project/claude-agent-sdk/) — Python SDK for programmatic Claude Code sessions

## Community

Related projects:
- [alzheimer](https://github.com/j-p-c/alzheimer) — Hierarchical memory management for Claude Code
- [obsidian-mind](https://github.com/breferrari/obsidian-mind) — Obsidian vault as persistent memory
- [claude-code-organizer](https://github.com/mcpware/claude-code-organizer) — Memory dashboard and management

## License

MIT
