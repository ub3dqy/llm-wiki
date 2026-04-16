---
task: Repo Hygiene PR 4a — `ruff format scripts/ hooks/` style-only commit
plan: docs/codex-tasks/repo-hygiene-pr4a-ruff-format-style.md
executor: Codex
status: completed-with-discrepancies
---

# Report — Repo Hygiene PR 4a (ruff format style-only)

## 0. Pre-flight

### 0.1 Environment snapshot

```text
Linux <host> 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64
Python 3.12.3
uv 0.11.6 (x86_64-unknown-linux-gnu)
ruff 0.15.10
```

### 0.2 Git status before changes

```text
 M .github/workflows/wiki-lint.yml
 M hooks/session-start.py
 M hooks/shared_context.py
 M hooks/shared_wiki_search.py
 M hooks/user-prompt-wiki.py
 M pyproject.toml
 M scripts/compile.py
 M scripts/doctor.py
 M scripts/lint.py
 M scripts/query.py
 M scripts/wiki_cli.py
4710d4e
```

Branch:

```text
master
```

### 0.2b Baseline snapshots

**Baseline A — out-of-scope paths SHA256**

Command used:

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', '.github/', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore', 'pyproject.toml']
out = subprocess.check_output(cmd)
print(hashlib.sha256(out).hexdigest())
PY
```

Full stdout:

```text
52098d42bf50cc04e8c430fc4f3419c47869cb7fcb88d44f666acd6feeef89de
```

**Baseline B — current ruff format check**

Command used:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff --version
uv run ruff format --check scripts/ hooks/ 2>&1 | tail -5
```

Full stdout:

```text
ruff 0.15.10
Would reformat: scripts/seed.py
Would reformat: scripts/setup.py
Would reformat: scripts/utils.py
Would reformat: scripts/wiki_cli.py
24 files would be reformatted, 1 file already formatted
```

**Baseline C — current ruff check I state**

Command used:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff check --select I scripts/ hooks/ 2>&1 | tail -3
```

Full stdout:

```text
All checks passed!
```

**Baseline D — current broad ruff check count**

Command used:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff check scripts/ hooks/ --output-format=concise 2>&1 | tail -5
```

Full stdout:

```text
scripts/seed.py:236:11: F541 [*] f-string without any placeholders
scripts/wiki_cli.py:26:20: F401 [*] `config.DAILY_DIR` imported but unused
scripts/wiki_cli.py:26:31: F401 [*] `config.REPORTS_DIR` imported but unused
Found 15 errors.
[*] 12 fixable with the `--fix` option (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

Controls:
- [x] Baseline A SHA256 captured ДО правок
- [x] Baseline B = 24/1
- [x] Baseline C = zero I errors
- [x] Baseline D = 15 errors

### 0.3 Current `pyproject.toml` `[tool.ruff*]` sections (reference, untouched)

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = ["I"]

[tool.ruff.lint.per-file-ignores]
"hooks/hook_utils.py" = ["I"]
"hooks/pre-compact.py" = ["I"]
"hooks/session-end.py" = ["I"]
```

Controls:
- [x] `[tool.ruff.format]` section отсутствует (defaults in effect)
- [x] `pyproject.toml` не модифицируется в этом PR

### 0.4 Preflight file list — 24 expected vs runtime_utils

Observed target set after format matches the plan: 24 `.py` files under `scripts/` and `hooks/` changed, while `scripts/runtime_utils.py` remained untouched.

### 0.5 Ruff version verification

```text
ruff 0.15.10
```

### 0.6 Doc verification

| Source | Verbatim quote | Why it matters |
|---|---|---|
| `https://docs.astral.sh/ruff/formatter/` | `The Ruff formatter is an extremely fast Python code formatter designed as a drop-in replacement for Black, available as part of the ruff CLI via ruff format.` | Confirms formatter purpose and Black-compatibility target. |
| `https://docs.astral.sh/ruff/formatter/#black-compatibility` | `Specifically, the formatter is intended to emit near-identical output when run over existing Black-formatted code.` | Supports style-only / non-disruptive formatting assumption. |
| `https://docs.astral.sh/ruff/formatter/#ruff-format` | `Similar to Black, running ruff format /path/to/file.py will format the given file or directory in-place, while ruff format --check /path/to/file.py will avoid writing any formatted files back, and instead exit with a non-zero status code upon detecting any unformatted files.` | Confirms in-place write vs check mode semantics. |
| `https://docs.astral.sh/ruff/formatter/` | `For example, to configure the formatter ... add the following to your configuration file: [tool.ruff.format] ...` | Confirms formatter-specific config lives under `[tool.ruff.format]`; our repo has no such section, so defaults apply. |
| Local baseline | `24 files would be reformatted, 1 file already formatted` | Confirms actual repo baseline before running formatter. |

## 1. Change applied

### 1.1 Run `ruff format scripts/ hooks/`

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff format scripts/ hooks/
```

Full stdout:

```text
24 files reformatted, 1 file left unchanged
```

Exit code: `0`

Controls:
- [x] Exit 0
- [x] Count matches baseline (24/1)
- [x] `scripts/runtime_utils.py` not reformatted

### 1.2 Post-format diff stats

Command:

```bash
git diff -w --stat -- scripts/ hooks/
git status --short -- scripts/ hooks/
git status --short -- scripts/runtime_utils.py
```

Full stdout:

```text
 hooks/codex/post-tool-capture.py |   1 +
 hooks/codex/session-start.py     |   1 +
 hooks/codex/stop.py              |  10 ++-
 hooks/codex/user-prompt-wiki.py  |   1 +
 hooks/hook_utils.py              |   1 +
 hooks/post-tool-capture.py       |   1 +
 hooks/pre-compact.py             |   1 +
 hooks/session-end.py             |   1 +
 hooks/session-start.py           |   1 +
 hooks/shared_context.py          |  26 ++++++--
 hooks/shared_wiki_search.py      |  10 ++-
 hooks/stop-wiki-reminder.py      |  31 +++++++--
 hooks/user-prompt-wiki.py        |   1 +
 scripts/compile.py               |   1 +
 scripts/config.py                |   8 +--
 scripts/doctor.py                |  83 ++++++++++++++++++------
 scripts/flush.py                 |  11 +++-
 scripts/lint.py                  | 137 +++++++++++++++++++++++++--------------
 scripts/query.py                 |   5 +-
 scripts/rebuild_index.py         |   5 +-
 scripts/seed.py                  |  10 ++-
 scripts/setup.py                 |  11 +++-
 scripts/utils.py                 |   4 +-
 scripts/wiki_cli.py              |   2 +
 24 files changed, 269 insertions(+), 94 deletions(-)
 M hooks/codex/post-tool-capture.py
 M hooks/codex/session-start.py
 M hooks/codex/stop.py
 M hooks/codex/user-prompt-wiki.py
 M hooks/hook_utils.py
 M hooks/post-tool-capture.py
 M hooks/pre-compact.py
 M hooks/session-end.py
 M hooks/session-start.py
 M hooks/shared_context.py
 M hooks/shared_wiki_search.py
 M hooks/stop-wiki-reminder.py
 M hooks/user-prompt-wiki.py
 M scripts/compile.py
 M scripts/config.py
 M scripts/doctor.py
 M scripts/flush.py
 M scripts/lint.py
 M scripts/query.py
 M scripts/rebuild_index.py
 M scripts/seed.py
 M scripts/setup.py
 M scripts/utils.py
 M scripts/wiki_cli.py
```

`scripts/runtime_utils.py` status:

```text
```

Controls:
- [x] Only `.py` files in diff
- [x] 24 modified files in `scripts/` + `hooks/`
- [x] `runtime_utils.py` not in diff

### 1.3 Path-scoped whitespace-insensitive diff sample

Command:

```bash
git diff -w -- hooks/hook_utils.py hooks/pre-compact.py hooks/session-end.py | sed -n '1,120p'
```

Full stdout:

```diff
diff --git a/hooks/hook_utils.py b/hooks/hook_utils.py
index 76d00e1..f41bb3a 100644
--- a/hooks/hook_utils.py
+++ b/hooks/hook_utils.py
@@ -1,4 +1,5 @@
 """Shared utilities for Claude Code and Codex hooks."""
+
 from __future__ import annotations
 
 import json
diff --git a/hooks/pre-compact.py b/hooks/pre-compact.py
index d2210e0..7ce5919 100644
--- a/hooks/pre-compact.py
+++ b/hooks/pre-compact.py
@@ -3,6 +3,7 @@
 Uses the same content-length threshold as session-end.py so short but meaningful
 CLI sessions can still be captured when they carry enough substance.
 """
+
 from __future__ import annotations
 
 import logging
diff --git a/hooks/session-end.py b/hooks/session-end.py
index 092ceed..8ddad33 100644
--- a/hooks/session-end.py
+++ b/hooks/session-end.py
@@ -5,6 +5,7 @@ and launches flush.py as a detached background process.
 
 Includes debounce to prevent cascading spawns when many sessions end at once.
 """
+
 from __future__ import annotations
 
 import logging
```

Controls:
- [x] No destructive multiline import splits
- [x] Cosmetic-only changes in the three previously risky hook files
- [x] `# noqa: E402` comments preserved

### 1.4 Out-of-scope baseline-delta

Command:

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', '.github/', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore', 'pyproject.toml']
out = subprocess.check_output(cmd)
print('after sha256:', hashlib.sha256(out).hexdigest())
PY
```

Full stdout:

```text
after sha256: 52098d42bf50cc04e8c430fc4f3419c47869cb7fcb88d44f666acd6feeef89de
```

Compared to Baseline A:

```text
baseline: 52098d42bf50cc04e8c430fc4f3419c47869cb7fcb88d44f666acd6feeef89de
after:    52098d42bf50cc04e8c430fc4f3419c47869cb7fcb88d44f666acd6feeef89de
IDENTICAL
```

Controls:
- [x] SHA256 identical

## 2. Phase 1 — Unit smoke

### 2.1 Post-format check clean

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff format --check scripts/ hooks/
```

Full stdout:

```text
25 files already formatted
```

Exit code: `0`

### 2.2 Post-format I rule still clean

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff check --select I scripts/ hooks/
```

Full stdout:

```text
All checks passed!
```

Exit code: `0`

Controls:
- [x] Exit 0
- [x] PR 2/3 I invariant preserved

### 2.3 Negative acceptance — non-I baseline unchanged

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff check scripts/ hooks/ --output-format=concise 2>&1 | tail -5
```

Full stdout:

```text
scripts/seed.py:240:11: F541 [*] f-string without any placeholders
scripts/wiki_cli.py:27:20: F401 [*] `config.DAILY_DIR` imported but unused
scripts/wiki_cli.py:27:31: F401 [*] `config.REPORTS_DIR` imported but unused
Found 15 errors.
[*] 12 fixable with the `--fix` option (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

Exit code: `0` (tail pipeline)

Result:
- pre-format non-I baseline: `15`
- post-format non-I baseline: `15`
- new regressions introduced: `0`

### 2.4 AST sanity

Command:

```bash
python3 - <<'PY'
import ast
files = [
    'scripts/compile.py', 'scripts/config.py', 'scripts/doctor.py',
    'scripts/flush.py', 'scripts/lint.py', 'scripts/query.py',
    'scripts/rebuild_index.py', 'scripts/seed.py', 'scripts/setup.py',
    'scripts/utils.py', 'scripts/wiki_cli.py',
    'hooks/hook_utils.py', 'hooks/post-tool-capture.py',
    'hooks/pre-compact.py', 'hooks/session-end.py',
    'hooks/session-start.py', 'hooks/shared_context.py',
    'hooks/shared_wiki_search.py', 'hooks/stop-wiki-reminder.py',
    'hooks/user-prompt-wiki.py',
    'hooks/codex/post-tool-capture.py', 'hooks/codex/session-start.py',
    'hooks/codex/stop.py', 'hooks/codex/user-prompt-wiki.py',
]
for f in files:
    ast.parse(open(f, 'r', encoding='utf-8').read())
print(f'all {len(files)} files parse ok')
PY
```

Full stdout:

```text
all 24 files parse ok
```

Exit code: `0`

### 2.5 Import smoke

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
PYTHONPATH=hooks:scripts uv run python -c "import hook_utils, shared_context, shared_wiki_search; import compile as _c, config, doctor, flush, lint, query, rebuild_index, seed, utils, wiki_cli" && echo all imports ok
```

Full stdout:

```text
all imports ok
```

Exit code: `0`

### 2.6 `lint.py --structural-only` regression check

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run python scripts/lint.py --structural-only
```

Full stdout:

```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 20 issue(s)
  Checking: Orphan sources...
    Found 0 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Freshness review debt...
    Found 148 issue(s)
  Checking: Missing backlinks...
    Found 327 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo-root>/reports/lint-2026-04-16.md

Results: 0 errors, 21 warnings, 475 suggestions
```

Exit code: `0`

### 2.7 `doctor --quick` regression check

Command:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run python scripts/wiki_cli.py doctor --quick
```

Full stdout:

```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/187 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 2544646/2548219 chars reached flush.py (coverage 99.9%)
[FAIL] flush_pipeline_correctness: Last 24h: 2 'Fatal error in message reader' events (7d total: 18, most recent 2026-04-16 00:14:33) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <linux-home>/.local/bin/uv
[PASS] index_health: Index is up to date.
[PASS] structural_lint: Results: 0 errors, 21 warnings, 475 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

Exit code: `0`

## 3. Phase 2 — Integration `[awaits user + PR push]`

Expected after push:
- PR 3 workflow `Wiki Lint / lint` runs
- narrow step `Ruff check (I rule)` still passes
- style-only format does not change CI semantics

## 4. Discrepancies

### D1 — target paths were already dirty before PR 4a

`hooks/session-start.py`, `hooks/shared_context.py`, `hooks/shared_wiki_search.py`, `hooks/user-prompt-wiki.py`, `scripts/compile.py`, `scripts/doctor.py`, `scripts/lint.py`, `scripts/query.py`, and `scripts/wiki_cli.py` were already modified in the worktree before this task started. Because of that, this PR is style-only **relative to the current worktree content**, not relative to `HEAD`.

Mitigation:
- baseline captured before format
- negative acceptance preserved exact `15` non-I baseline
- AST parse, import smoke, lint, and doctor all passed after format

No rollback was needed.

### D2 — uv-based checks required execution outside read-only sandbox

`uv run ...` commands attempted to write temporary files under the uv cache and failed inside the read-only sandbox. All formatter and Ruff checks were re-run outside the sandbox with the approved user-level uv environment:

```text
UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv
```

This affected execution method only, not repo contents.

## 5. Tools used

- Wiki:
  - `wiki/sources/astral-ruff-docs.md`
  - `wiki/analyses/repo-hygiene-findings-2026-04-15.md`
- Docs:
  - Ruff formatter docs
  - Ruff formatter `ruff format` section
  - Ruff settings docs
- Local commands:
  - `uv run ruff format --check scripts/ hooks/`
  - `uv run ruff format scripts/ hooks/`
  - `uv run ruff check --select I scripts/ hooks/`
  - `uv run ruff check scripts/ hooks/ --output-format=concise`
  - `uv run python scripts/lint.py --structural-only`
  - `uv run python scripts/wiki_cli.py doctor --quick`
  - Python AST and import smokes
  - `git diff -w --stat -- scripts/ hooks/`
  - `git status --short -- scripts/ hooks/`
  - path-scoped out-of-scope SHA256 snapshots

## 6. Out of scope

- `.git-blame-ignore-revs` (PR 4b)
- `ruff format --check` in CI (PR 5)
- fixing the 15 pre-existing non-I Ruff errors
- changing `pyproject.toml`
- any workflow / docs / wiki changes
- commit / push / PR creation

## 7. Self-audit

- [x] Doc verification completed before recording the final change summary
- [x] Formatter run used exactly `ruff format scripts/ hooks/`
- [x] Post-format check reports all files already formatted
- [x] I-rule invariant preserved
- [x] Non-I baseline stayed exactly `15`
- [x] All 24 formatted files parse as valid AST
- [x] Import smoke passes
- [x] `lint --structural-only` passes
- [x] `doctor --quick` passes with only pre-existing Bug H fail
- [x] `scripts/runtime_utils.py` is not in diff
- [x] Out-of-scope SHA256 unchanged
- [x] No out-of-scope tracked files modified
- [x] No commit or push performed

## 8. Final state

Tracked production paths modified by this task:

- `scripts/` and `hooks/` — 24 `.py` files formatted

Handoff artifact:

- `docs/codex-tasks/repo-hygiene-pr4a-ruff-format-style-report.md`

Commit not created. Push not performed.
