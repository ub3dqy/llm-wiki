---
task: Repo Hygiene PR 1 — add `[dependency-groups].dev` (PEP 735) with ruff + pytest
plan: docs/codex-tasks/repo-hygiene-pr1-dev-extras.md
plan_revision: v2.1
executor: Codex
status: completed-with-discrepancies
---

# Report — Repo Hygiene PR 1 (dependency groups)

## 0. Pre-flight

### 0.1 Environment snapshot

```text
Linux <host> 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
Python 3.12.3
uv 0.11.6 (x86_64-unknown-linux-gnu)
```

### 0.2 Git status before changes

```text
 M .github/workflows/wiki-lint.yml
 M .gitignore
 M CLAUDE.md
 M README.md
 M codex-hooks.template.json
 M docs/codex-integration-plan.md
 M docs/codex-tasks/doctor-pipeline-correctness-24h-window-report.md
 M docs/codex-tasks/doctor-pipeline-correctness-24h-window.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe-report.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe.md
 M docs/codex-tasks/fix-codex-stop-hook-report.md
 M docs/codex-tasks/fix-codex-stop-hook.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g.md
 M docs/codex-tasks/investigate-flush-py-bug-h-report.md
 M docs/codex-tasks/investigate-flush-py-bug-h.md
 M docs/codex-tasks/post-review-corrections-and-probe-2-report.md
 M docs/codex-tasks/post-review-corrections-and-probe-2.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation-report.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation-report.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation.md
 M docs/codex-tasks/split-codex-stop-light-worker-report.md
 M docs/codex-tasks/split-codex-stop-light-worker.md
 M docs/codex-tasks/split-doctor-flush-capture-health-report.md
 M docs/codex-tasks/split-doctor-flush-capture-health.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-b.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-c-report.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-c.md
 M docs/codex-tasks/wiki-freshness-claude-feedback-review.md
 M docs/codex-tasks/wiki-freshness-phase1-report.md
 M docs/codex-tasks/wiki-freshness-phase1.md
 M docs/codex-tasks/wiki-freshness-preliminary-plan.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md
 M docs/codex-tasks/wiki-lint-cleanup-d1-continuation.md
 M hooks/codex/stop.py
 M hooks/hook_utils.py
 M hooks/shared_context.py
 M hooks/shared_wiki_search.py
 M index.example.md
 M scripts/compile.py
 M scripts/doctor.py
 M scripts/flush.py
 M scripts/lint.py
 M scripts/query.py
 M scripts/rebuild_index.py
 M scripts/utils.py
?? .codex
?? docs/codex-tasks/bump-claude-agent-sdk-bug-h-report.md
?? docs/codex-tasks/bump-claude-agent-sdk-bug-h.md
?? docs/codex-tasks/codex-vscode-scroll-reality-check.md
?? docs/codex-tasks/coleam00-issue-6-feedback-review.md
?? docs/codex-tasks/local-claude-codex-mailbox-workflow.md
?? docs/codex-tasks/reopen-bug-h-and-clarify-lint-debt-issues-report.md
?? docs/codex-tasks/reopen-bug-h-and-clarify-lint-debt-issues.md
?? docs/codex-tasks/repo-hygiene-opinion-on-claude-proposal.md
?? docs/codex-tasks/repo-hygiene-pr1-dev-extras-report.md
?? docs/codex-tasks/repo-hygiene-pr1-dev-extras.md
?? docs/codex-tasks/repo-hygiene-pr1-discrepancy-optional-deps-vs-dependency-groups.md
?? docs/codex-tasks/repo-hygiene-pr1-v2-blocker-baseline-diff.md
?? docs/codex-tasks/repo-hygiene-response-to-claude-followup.md
7ce58e57eccd3dd06405d34f03a4dece36b9f83a
```

Branch:
```text
master
```

### 0.2b Baseline diff of out-of-scope paths

Note: template command wrote to `/tmp`, but sandbox denied writes there. Used a no-write Python equivalent to capture the same diff and SHA256.

Command used:

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', 'scripts/', 'hooks/', '.github/', 'wiki/', 'CLAUDE.md', 'AGENTS.md']
out = subprocess.check_output(cmd)
text = out.decode('utf-8', errors='replace')
print(hashlib.sha256(out).hexdigest())
print('---HEAD---')
lines = text.splitlines()
print('\n'.join(lines[:40]))
print('---TAIL---')
print('\n'.join(lines[-40:]))
PY
```

Full stdout:

```text
aa061db5a743165f51c4bdeb01335e3377d3573a3cf2d58abd5dc438bbad6648
---HEAD---
diff --git a/.github/workflows/wiki-lint.yml b/.github/workflows/wiki-lint.yml
index 400e19b..95bbbcc 100644
--- a/.github/workflows/wiki-lint.yml
+++ b/.github/workflows/wiki-lint.yml
@@ -1,56 +1,56 @@
-name: Wiki Lint
-
-on:
-  push:
-    branches: [master, main]
-    paths:
-      - 'wiki/**'
-      - 'index.md'
-      - 'scripts/**'
-      - 'hooks/**'
-  pull_request:
-    branches: [master, main]
-
-jobs:
-  lint:
-    runs-on: ubuntu-latest
-    steps:
-      - uses: actions/checkout@v4
-
-      - uses: astral-sh/setup-uv@v4
-        with:
-          version: "latest"
-
-      - name: Install dependencies
-        run: uv sync
-
-      - name: Check index is up to date
-        run: uv run python scripts/rebuild_index.py --check
-
-      - name: Run structural lint
-        run: uv run python scripts/lint.py --structural-only
-
-      - name: Syntax check all Python files
-        run: |
-          uv run python -c "
---TAIL---
+def frontmatter_sources_include_prefix(raw_sources: str, prefix: str) -> bool:
+    """Return True if a parsed frontmatter source entry starts with the prefix."""
+    normalized_prefix = prefix.strip()
+    if not normalized_prefix:
+        return False
+    return any(source.startswith(normalized_prefix) for source in parse_frontmatter_list(raw_sources))
+
+
+def get_article_projects(path: Path) -> list[str]:
+    """Return list of project tags from article frontmatter.
+
+    Handles both 'project: foo' and 'project: foo, bar' formats.
+    """
+    fm = parse_frontmatter(path)
+    raw = fm.get("project", "").strip()
+    if not raw:
+        return []
+    return [p.strip() for p in raw.split(",") if p.strip()]
+
+
+def build_article_metadata_map() -> dict[str, dict]:
+    """Build a map of slug → {projects, word_count, updated, title}.
+
+    Slug format matches index.md wikilinks: 'concepts/foo', 'entities/bar'.
+    """
+    meta: dict[str, dict] = {}
+    for article in list_wiki_articles():
+        rel = article.relative_to(WIKI_DIR)
+        slug = str(rel).replace("\\", "/").replace(".md", "")
+        fm = parse_frontmatter(article)
+        meta[slug] = {
+            "projects": get_article_projects(article),
+            "word_count": get_article_word_count(article),
+            "updated": fm.get("updated", ""),
+            "title": fm.get("title", slug),
+            "confidence": fm.get("confidence", ""),
+            "sources": fm.get("sources", ""),
+            "tags": fm.get("tags", ""),
+        }
+    return meta
```

### 0.3 Current `pyproject.toml` content before change

```toml
[project]
name = "llm-personal-kb"
version = "0.1.0"
description = "Personal knowledge base compiled from AI conversations — inspired by Karpathy's LLM Wiki"
requires-python = ">=3.12"
dependencies = [
    "claude-agent-sdk>=0.1.59",
    "python-dotenv>=1.2.2",
    "tzdata>=2026.1",
]

[tool.ruff]
line-length = 100
```

### 0.4 Current `uv.lock` status

```text
-rwxrwxrwx 1 <user> <user> 99457 Apr 14 23:34 uv.lock
.gitignore:21:uv.lock	uv.lock
21:uv.lock
```

### 0.5 Current `.github/workflows/wiki-lint.yml` ruff presence check

```text
no ruff in CI (expected per plan)
```

### 0.6 Doc verification

| План говорит | Офдока/код говорит сейчас | Совпало? |
|---|---|---|
| `[dependency-groups]` — top-level table per PEP 735, отдельная от `[project]` | PEP 735: `This PEP defines a new section (table) in pyproject.toml files named dependency-groups. The dependency-groups table contains an arbitrary number of user-defined keys...` | ✅ |
| Формат значения — dict of group-name → list of PEP 508 strings, поддерживает `{include-group = "..."}` | PEP 735: `Strings in requirement lists must be valid Dependency Specifiers, as defined in PEP 508.` and example: `typing-test = [{include-group = "typing"}, {include-group = "test"}, "useful-types"]` | ✅ |
| `optional-dependencies` — это extras (published), `dependency-groups` — local-only dev layer | uv docs: `project.optional-dependencies: Published optional dependencies, or "extras".` and `uv reads development dependencies from the [dependency-groups] table (as defined in PEP 735).` | ✅ |
| `uv sync` включает `dev` группу по умолчанию (special-cased) | uv docs: `The dev group is special-cased and synced by default.` | ✅ |
| `uv sync --group <name>` добавляет указанную группу; `--no-dev` отключает dev; `--only-dev` только dev | `uv sync --help` shows `--no-dev`, `--only-dev`, `--group <GROUP>`, `--no-default-groups`, `--only-group <ONLY_GROUP>` | ✅ |
| `uv lock` регенерирует `uv.lock` при изменении dependencies | uv docs: `The uv lockfile is created and modified by project commands such as uv lock, uv sync, and uv add.` | ✅ |
| Local `uv --version` ≥ 0.4.27 (минимум для PEP 735 support) | Local: `uv 0.11.6 (x86_64-unknown-linux-gnu)` and `uv sync --help` includes all required dependency-group flags | ✅ |
| Version constraint `ruff>=<N>` — `N` это актуальный major на pypi | PyPI release history shows current line `0.15.x`; local resolved version is `ruff 0.15.10` | ✅ |
| Version constraint `pytest>=<N>` — `N` это актуальный major на pypi | PyPI page shows `# pytest 9.0.3`; release history current line is `9.0.x`; local resolved version is `pytest 9.0.3` | ✅ |
| `pyproject.toml` текущий содержит ровно то что план ожидает в 0.3 | Pre-change file matched the 14-line baseline exactly | ✅ |

---

## 1. Changes

### 1.1 `pyproject.toml` — add top-level `[dependency-groups]`

Raw diff:

```diff
diff --git a/pyproject.toml b/pyproject.toml
index b1f2ada..e641062 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -9,5 +9,11 @@ dependencies = [
     "tzdata>=2026.1",
 ]
 
+[dependency-groups]
+dev = [
+    "ruff>=0.15",
+    "pytest>=9.0",
+]
+
 [tool.ruff]
 line-length = 100
```

Контрольные точки:

- [x] Top-level секция `[dependency-groups]` добавлена после `[project]` блока и до `[tool.ruff]`
- [x] Секция не nested в `[project]`
- [x] Под ключом `dev` ровно два элемента: `ruff` и `pytest`
- [x] Version constraints совпадают с актуальными major lines
- [x] Отступ 4 пробела внутри массива совпадает с существующим `dependencies` блоком
- [x] Нет новых комментариев
- [x] Никакие другие ключи в `[project]` не тронуты
- [x] `[project.optional-dependencies]` не добавлен
- [x] `[tool.ruff]` не тронут

### 1.2 `uv lock` — resolution sanity check

Command:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv lock && ls -la uv.lock'
```

Full stdout:

```text
Resolved 40 packages in 10ms
-rwxrwxrwx 1 <user> <user> 109112 Apr 15 20:50 uv.lock
```

Exit code: `0`

Контрольные точки:

- [x] `uv lock` successfully completed
- [x] `uv.lock` exists on disk after command
- [x] `uv.lock` was not edited by hand
- [x] No resolution conflict occurred
- [x] `git diff` for `uv.lock` was not used

### 1.3 Path-scoped diff scope

`git diff -- pyproject.toml`:

```text
diff --git a/pyproject.toml b/pyproject.toml
index b1f2ada..e641062 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -9,5 +9,11 @@ dependencies = [
     "tzdata>=2026.1",
 ]
 
+[dependency-groups]
+dev = [
+    "ruff>=0.15",
+    "pytest>=9.0",
+]
+
 [tool.ruff]
 line-length = 100
```

`git status --short -- pyproject.toml`:

```text
 M pyproject.toml
```

Baseline-delta SHA comparison for out-of-scope paths:

```text
baseline sha256: aa061db5a743165f51c4bdeb01335e3377d3573a3cf2d58abd5dc438bbad6648
after    sha256: aa061db5a743165f51c4bdeb01335e3377d3573a3cf2d58abd5dc438bbad6648
```

Контрольные точки:

- [x] `git diff -- pyproject.toml` contains only the new top-level `[dependency-groups]` section
- [x] `git status --short -- pyproject.toml` shows exactly ` M pyproject.toml`
- [x] Out-of-scope paths were unchanged relative to baseline (SHA256 identical)
- [x] Pre-existing worktree dirt stayed baseline-only
- [x] Report file remains handoff artifact outside whitelist

---

## 2. Phase 1 — Unit smoke

### 2.1 TOML valid

Command:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv run python -c "import tomllib; tomllib.load(open(\"pyproject.toml\",\"rb\")); print(\"TOML ok\")"'
```

Full stdout:

```text
Downloading ruff (10.7MiB)
Downloading pygments (1.2MiB)
 Downloaded pygments
 Downloaded ruff
Installed 6 packages in 234ms
TOML ok
```

Exit code: `0`

### 2.2 `[dependency-groups].dev` visible and v1 mistake absent

Command:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv run python -c "import tomllib; d=tomllib.load(open(\"pyproject.toml\",\"rb\")); print(d[\"dependency-groups\"][\"dev\"]); assert \"optional-dependencies\" not in d.get(\"project\", {}), \"v1 mistake: optional-dependencies should not exist\""'
```

Full stdout:

```text
['ruff>=0.15', 'pytest>=9.0']
```

Exit code: `0`

### 2.3 Lockfile resolution sanity

Command:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv lock && ls -la uv.lock'
```

Full stdout:

```text
Resolved 40 packages in 10ms
-rwxrwxrwx 1 <user> <user> 109112 Apr 15 20:50 uv.lock
```

Exit code: `0`

### 2.4 `uv sync` (default dev) + binaries

Commands:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv sync && uv run ruff --version && uv run pytest --version'
```

Full stdout:

```text
Resolved 40 packages in 9ms
Checked 37 packages in 0.69ms
ruff 0.15.10
pytest 9.0.3
```

Exit code: `0`

### 2.4b `uv sync --group dev` explicit

Commands:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv sync --group dev && uv run ruff --version'
```

Full stdout:

```text
Resolved 40 packages in 8ms
Checked 37 packages in 0.76ms
ruff 0.15.10
```

Exit codes: `0`, `0`

### 2.5 Regression — corrected `--no-dev` check

Original plan command was:

```bash
uv sync --no-dev
uv run python -c "import claude_agent_sdk; import dotenv; print('runtime ok')"
uv run ruff --version || echo "ruff unavailable after --no-dev (expected)"
```

That command is not a reliable no-dev assertion, because `uv run ...` re-syncs the environment and reintroduces default groups. I ran it and it reinstalled `ruff` and `pytest`.

Corrected command used for verification:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv sync --no-dev && "$HOME/.cache/llm-wiki/.venv/bin/python" -c "import claude_agent_sdk; import dotenv; print(\"runtime ok\")" && (ls -la "$HOME/.cache/llm-wiki/.venv/bin/ruff" "$HOME/.cache/llm-wiki/.venv/bin/pytest" 2>&1 || echo "ruff/pytest absent after --no-dev (expected)")'
```

Full stdout:

```text
Resolved 40 packages in 13ms
Uninstalled 6 packages in 32ms
 - iniconfig==2.3.0
 - packaging==26.1
 - pluggy==1.6.0
 - pygments==2.20.0
 - pytest==9.0.3
 - ruff==0.15.10
runtime ok
ls: cannot access '<linux-home>/.cache/llm-wiki/.venv/bin/ruff': No such file or directory
ls: cannot access '<linux-home>/.cache/llm-wiki/.venv/bin/pytest': No such file or directory
ruff/pytest absent after --no-dev (expected)
```

Exit code: `0`

Then environment restored:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv sync'
```

Stdout:

```text
Resolved 40 packages in 9ms
Checked 37 packages in 1ms
```

Exit code: `0`

### 2.6 `lint.py --structural-only`

Command:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv run python scripts/lint.py --structural-only'
```

Full stdout:

```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 20 issue(s)
  Checking: Orphan sources...
    Found 1 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Freshness review debt...
    Found 137 issue(s)
  Checking: Missing backlinks...
    Found 275 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo-root>/reports/lint-2026-04-15.md

Results: 0 errors, 22 warnings, 412 suggestions
```

Exit code: `0`

### 2.7 `doctor --quick`

Command:

```bash
bash -lc 'export UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy; uv run python scripts/wiki_cli.py doctor --quick'
```

Full stdout:

```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/187 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 2321738/2325311 chars reached flush.py (coverage 99.8%)
[FAIL] flush_pipeline_correctness: Last 24h: 1 'Fatal error in message reader' events (7d total: 17, most recent 2026-04-15 18:51:19) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <linux-home>/.local/bin/uv
[PASS] index_health: Index is up to date.
[PASS] structural_lint: Results: 0 errors, 22 warnings, 412 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

Exit code: `0`

---

## 3. Phase 2 — Integration `[awaits user]`

### 3.1 User diff review

`[awaits user]`

### 3.2 Clean-clone install from scratch (optional)

`[awaits user]`

### 3.3 Merge decision

`[awaits user]`

---

## 4. Phase 3 — Statistical

Not applicable for this PR. Effect is immediate after merge.

---

## 5. Tools used

| Tool | Status | Details |
|---|---|---|
| Wiki: `wiki/sources/python-pyproject-toml-docs.md` | ✅ | Read for PEP 621 context; explicit note at line 278 says it does not cover PEP 735, so it was not treated as primary for dependency groups |
| Wiki: `wiki/sources/astral-uv-docs.md` | ✅ | Read for uv sync behavior, `UV_PROJECT_ENVIRONMENT`, and lock/sync semantics |
| Wiki: `wiki/sources/uv-lockfile-format-docs.md` | ✅ | Read for `uv.lock` lifecycle and confirmation that `uv lock`/`uv sync` create or modify lockfile |
| Wiki: `wiki/analyses/repo-hygiene-findings-2026-04-15.md` | ✅ | Confirmed this task is PR 1 in the agreed repo-hygiene sequence |
| WebFetch: PEP 735 | ✅ | Used as primary for top-level `[dependency-groups]`, unpublished nature, and include syntax |
| WebFetch: uv dependency groups docs | ✅ | Used as primary for extras vs dependency-groups distinction |
| WebFetch: uv CLI `uv sync` | ✅ | Used to confirm `--group`, `--no-dev`, `--only-dev` and default `dev` behavior |
| WebFetch: PEP 621 | ✅ | Used as context only: why `[project.optional-dependencies]` is extras and not the right dev-only layer here |
| WebFetch: PyPI ruff | ✅ | Used to confirm current release line is `0.15.x`; local resolved version was `0.15.10` |
| WebFetch: PyPI pytest | ✅ | Used to confirm current release line is `9.0.x`; local resolved version was `9.0.3` |
| Local: `uv --version` + `uv sync --help` | ✅ | Confirmed local uv is `0.11.6` and supports dependency-group flags |
| Git snapshots | ✅ | Used `git status --short`, `git rev-parse HEAD`, `git diff -- pyproject.toml`, and SHA256 of baseline diff |
| Repo-local doc: `CLAUDE.md` | ✅ | Read earlier in-session; confirms gate roles and verification discipline |
| Repo-local doc: `AGENTS.md` | ✅ | Read; WSL uv discipline acknowledged, but `/root/...` path was not used because current WSL user is non-root and prior repo task established `<linux-home>/.cache/llm-wiki/.venv` session override |
| Subagent delegation | not used | Not required |
| Linters | ✅ | See sections 2.6 and 2.7 |

---

## 6. Out-of-scope temptations

- Add Ruff CI checks now: refused, this is PR 3
- Add `.pre-commit-config.yaml`: refused, this is later in the sequence
- Update `CLAUDE.md` or repo docs to mention dependency groups: refused, out of whitelist
- Touch `.github/workflows/wiki-lint.yml`: refused, out of whitelist and already dirty baseline

---

## 7. Discrepancies

- **D1**: Report template `0.2b` wrote baseline diff to `/tmp/baseline-out-of-scope.diff`, but sandbox denied writes there. Resolved by using a no-write Python equivalent to compute SHA256 and print head/tail directly from `git diff`.
- **D2**: Plan `2.5` command was semantically wrong for proving `--no-dev`, because `uv run ...` re-syncs the environment and can reintroduce default dev packages. I observed exactly that: `uv sync --no-dev` followed by `uv run python ...` and `uv run ruff --version` brought `ruff` and `pytest` back. Resolved by switching verification to direct venv inspection: `"<linux-home>/.cache/llm-wiki/.venv/bin/python"` for runtime imports and `ls` on `bin/ruff` / `bin/pytest`.
- **D3**: PyPI web crawl lagged behind local resolution for exact patch versions (`ruff 0.15.10`, `pytest 9.0.3`). No major-version mismatch; constraints `ruff>=0.15` and `pytest>=9.0` remain correct.

---

## 8. Self-audit checklist

- [x] 0.1 Environment snapshot filled with sanitized hostname
- [x] 0.2 Git status before filled verbatim, HEAD SHA recorded
- [x] 0.2b Baseline out-of-scope diff snapshot captured and SHA256 recorded
- [x] 0.3 Current `pyproject.toml` pre-change content recorded
- [x] 0.4 `uv.lock` presence and gitignored status recorded
- [x] 0.5 CI Ruff absence confirmed
- [x] 0.6 Doc verification filled from official docs and local commands
- [x] 0.6 Version lookup for Ruff and pytest completed
- [x] 1.1 `pyproject.toml` diff recorded, controls checked
- [x] 1.2 `uv lock` resolution sanity passed
- [x] 1.3 Path-scoped diff check completed via baseline-delta SHA equality
- [x] 2.1 TOML valid smoke run with full stdout
- [x] 2.2 Dependency-group access smoke run with full stdout
- [x] 2.3 Lockfile regen smoke run with full stdout
- [x] 2.4 `uv sync` default-dev + versions run
- [x] 2.4b `uv sync --group dev` explicit run
- [x] 2.5 `uv sync --no-dev` regression verified with corrected direct-venv method
- [x] 2.6 lint structural smoke run
- [x] 2.7 doctor --quick smoke run
- [x] 3.x Phase 2 marked `[awaits user]`
- [x] 4 Phase 3 marked non-applicable
- [x] 5 Tools used table filled without blanks
- [x] 6 Out-of-scope temptations filled
- [x] 7 Discrepancies filled
- [x] No git commit done
- [x] No git push done
- [x] No personal data paths or hostname in final report
- [x] No tracked files edited outside whitelist (`pyproject.toml` only; `uv.lock` local side effect; this report as handoff artifact)
- [x] Pre-existing worktree dirt remained baseline-only and was not mutated by this task
