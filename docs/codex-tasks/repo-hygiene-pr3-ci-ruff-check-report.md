---
task: Repo Hygiene PR 3 — add `ruff check --select I` step to `.github/workflows/wiki-lint.yml`
plan: docs/codex-tasks/repo-hygiene-pr3-ci-ruff-check.md
executor: Codex
status: completed-with-discrepancies
---

# Report — Repo Hygiene PR 3 (CI Ruff I gate)

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
```

Branch:

```text
master
```

HEAD:

```text
cb85a28
```

### 0.2b Baseline snapshot — out-of-scope paths SHA256

Command used:

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', 'scripts/', 'hooks/', 'pyproject.toml', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore']
out = subprocess.check_output(cmd)
print(hashlib.sha256(out).hexdigest())
print('---HEAD---')
text = out.decode('utf-8', errors='replace').splitlines()
print('\n'.join(text[:20]))
print('---TAIL---')
print('\n'.join(text[-20:]))
PY
```

Full stdout:

```text
3846e5ee524b9af72ab415dc7b0c5109d29f2893c7deb5e4fbcc7f9aa2465362
---HEAD---
diff --git a/.gitignore b/.gitignore
index 101ce0a..70d5dc6 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,47 +1,47 @@
-# Python
-.venv/
-__pycache__/
-*.pyc
-*.pyo
-
-# Local environment overrides
-.env
-
-# State & logs (local, not committed)
-scripts/state.json
-scripts/*.log
-scripts/session-flush-*
-scripts/flush-test-marker.txt
-scripts/locks/
---TAIL---
+        elif "--full" in extra:
+            extra = [x for x in extra if x != "--full"]
+            run_script_with_uv("lint.py", extra)
+            return
+        elif "--fix" in extra:
+            extra = [x for x in extra if x not in {"--fix", "--full"}]
+            extra.append("--structural-only")
+        run_script("lint.py", extra)
+    elif command == "rebuild":
+        run_script("rebuild_index.py", extra)
+    elif command == "seed":
+        run_script("seed.py", extra)
+    else:
+        print(f"Unknown command: {command}")
+        print(__doc__)
+        sys.exit(1)
+
+
+if __name__ == "__main__":
+    main()
```

### 0.3 Current workflow relevant fragment before change

```yaml
      - name: Run structural lint
        run: uv run python scripts/lint.py --structural-only

      - name: Syntax check all Python files
        run: |
          uv run python -c "
```

### 0.4 Current local Ruff state before change

```text
uv 0.11.6 (x86_64-unknown-linux-gnu)
ruff 0.15.10
All checks passed!
```

### 0.5 Current broad Ruff baseline before change

```text
scripts/seed.py:236:11: F541 [*] f-string without any placeholders
scripts/wiki_cli.py:26:20: F401 [*] `config.DAILY_DIR` imported but unused
scripts/wiki_cli.py:26:31: F401 [*] `config.REPORTS_DIR` imported but unused
Found 15 errors.
[*] 12 fixable with the `--fix` option (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

### 0.6 Doc verification

| Source | Verbatim quote | Why it matters |
|---|---|---|
| GitHub Actions workflow syntax | `A workflow is a configurable automated process made up of one or more jobs. You must create a YAML file to define your workflow configuration.` | Confirms workflow file is YAML and job-based. |
| GitHub Actions workflow syntax | `jobs:` / `steps:` example under `jobs.<job_id>.steps` shows `- name:` and `run:` keys in a step | Confirms target structure for the inserted CI step. |
| Ruff linter docs | `Rule selectors like lint.select and lint.ignore accept either a full rule code (e.g., F401) or any valid prefix (e.g., F).` | Confirms narrow rule selection is supported. |
| Ruff linter docs | `Running ruff check --select F401 would result in Ruff enforcing F401, and no other rules.` | Confirms `--select I` is the correct narrow gate. |
| Ruff exit codes docs | `By default, ruff check exits with the following status codes:` | Confirms CI semantics depend on exit code. |
| Ruff exit codes docs | `0 if no violations were found, or if all present violations were fixed automatically.` | Pass case for CI step. |
| Ruff exit codes docs | `1 if violations were found.` | Fail case for CI step. |
| Ruff exit codes docs | `2 if Ruff terminates abnormally due to invalid configuration, invalid CLI options, or an internal error.` | Distinguishes config/tool failure from lint violations. |
| `astral-sh/setup-uv` | `Install a version of uv and add it to PATH` | Confirms the workflow can call `uv` in later steps. |
| `astral-sh/setup-uv` | `The installed version of uv is then added to the runner PATH, enabling later steps to invoke it by name (uv).` | Confirms no extra PATH handling is needed. |

## 1. Change applied

### 1.1 Production file changed

- `.github/workflows/wiki-lint.yml`

### 1.2 Inserted step

```yaml
      - name: Ruff check (I rule)
        run: uv run ruff check --select I scripts/ hooks/
```

### 1.3 Path-scoped acceptance

Primary acceptance command:

```bash
git diff -w -- .github/workflows/wiki-lint.yml
```

Full stdout:

```diff
diff --git a/.github/workflows/wiki-lint.yml b/.github/workflows/wiki-lint.yml
index 400e19b..bddd38c 100644
--- a/.github/workflows/wiki-lint.yml
+++ b/.github/workflows/wiki-lint.yml
@@ -30,6 +30,9 @@ jobs:
       - name: Run structural lint
         run: uv run python scripts/lint.py --structural-only
 
+      - name: Ruff check (I rule)
+        run: uv run ruff check --select I scripts/ hooks/
+
       - name: Syntax check all Python files
         run: |
           uv run python -c "
```

Raw diff sanity (advisory only):

```diff
diff --git a/.github/workflows/wiki-lint.yml b/.github/workflows/wiki-lint.yml
index 400e19b..bddd38c 100644
--- a/.github/workflows/wiki-lint.yml
+++ b/.github/workflows/wiki-lint.yml
@@ -1,56 +1,59 @@
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
+name: Wiki Lint
+ 
+on:
+  push:
+    branches: [master, main]
+    paths:
+      - 'wiki/**'
+      - 'index.md'
+      - 'scripts/**'
+      - 'hooks/**'
+  pull_request:
+    branches: [master, main]
+
+jobs:
+  lint:
+    runs-on: ubuntu-latest
+    steps:
+      - uses: actions/checkout@v4
+
+      - uses: astral-sh/setup-uv@v4
+        with:
+          version: "latest"
+
+      - name: Install dependencies
+        run: uv sync
+
+      - name: Check index is up to date
+        run: uv run python scripts/rebuild_index.py --check
+
       - name: Run structural lint
         run: uv run python scripts/lint.py --structural-only
 
+      - name: Ruff check (I rule)
+        run: uv run ruff check --select I scripts/ hooks/
+
       - name: Syntax check all Python files
         run: |
           uv run python -c "
```

### 1.4 Out-of-scope baseline-delta check

Command used:

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', 'scripts/', 'hooks/', 'pyproject.toml', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore']
out = subprocess.check_output(cmd)
print(hashlib.sha256(out).hexdigest())
PY
```

Full stdout:

```text
3846e5ee524b9af72ab415dc7b0c5109d29f2893c7deb5e4fbcc7f9aa2465362
```

Result:

- baseline SHA before change: `3846e5ee524b9af72ab415dc7b0c5109d29f2893c7deb5e4fbcc7f9aa2465362`
- baseline SHA after change: `3846e5ee524b9af72ab415dc7b0c5109d29f2893c7deb5e4fbcc7f9aa2465362`
- out-of-scope paths unchanged: `PASS`

## 2. Verification

### 2.1 YAML parse

Command used:

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/wiki-lint.yml')); print('YAML ok')"
```

Exit code: `0`

Full stdout:

```text
YAML ok
```

### 2.2 Workflow structure preserved

Command used:

```bash
python3 -c "import yaml; wf=yaml.safe_load(open('.github/workflows/wiki-lint.yml')); names=[s.get('name') or s.get('uses') for s in wf['jobs']['lint']['steps']]; print('steps:', names); assert 'Ruff check (I rule)' in names; assert 'Run structural lint' in names; assert 'Syntax check all Python files' in names; print('structure ok')"
```

Exit code: `0`

Full stdout:

```text
steps: ['actions/checkout@v4', 'astral-sh/setup-uv@v4', 'Install dependencies', 'Check index is up to date', 'Run structural lint', 'Ruff check (I rule)', 'Syntax check all Python files']
structure ok
```

### 2.3 Step ordering

Command used:

```bash
python3 -c "import yaml; wf=yaml.safe_load(open('.github/workflows/wiki-lint.yml')); names=[s.get('name') or s.get('uses') for s in wf['jobs']['lint']['steps']]; assert names.index('Run structural lint') < names.index('Ruff check (I rule)') < names.index('Syntax check all Python files'); print('ordering ok')"
```

Exit code: `0`

Full stdout:

```text
ordering ok
```

### 2.4 Local equivalent of new CI step

Command used:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv --version
uv run ruff --version
uv run ruff check --select I scripts/ hooks/
```

Exit code: `0`

Full stdout:

```text
uv 0.11.6 (x86_64-unknown-linux-gnu)
ruff 0.15.10
All checks passed!
```

### 2.5 Broad Ruff baseline still not gated

Command used:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run ruff check scripts/ hooks/ --output-format=concise 2>&1 | tail -5
```

Exit code: `0`

Full stdout:

```text
scripts/seed.py:236:11: F541 [*] f-string without any placeholders
scripts/wiki_cli.py:26:20: F401 [*] `config.DAILY_DIR` imported but unused
scripts/wiki_cli.py:26:31: F401 [*] `config.REPORTS_DIR` imported but unused
Found 15 errors.
[*] 12 fixable with the `--fix` option (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

### 2.6 Optional workflow lint

Command used:

```bash
command -v actionlint && actionlint .github/workflows/wiki-lint.yml || echo "actionlint not available, skipped"
```

Exit code: `0`

Full stdout:

```text
actionlint not available, skipped
```

### 2.7 Regression chain

Command used:

```bash
export UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
uv run python scripts/lint.py --structural-only
uv run python scripts/wiki_cli.py doctor --quick
```

Exit code: `0` for `lint.py`, `0` for `doctor --quick`

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

Report saved to: <repo-root>/reports/lint-2026-04-15.md

Results: 0 errors, 21 warnings, 475 suggestions

[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/187 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 2490588/2494161 chars reached flush.py (coverage 99.9%)
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

### 2.8 Phase 2 — real GitHub Actions run

Status: `[awaits user + PR push]`

Expected after push:

- workflow `Wiki Lint / lint` starts
- new step `Ruff check (I rule)` runs after structural lint
- step exits green on `All checks passed!`
- merge gate covers future `I` regressions

## 3. Discrepancies

### D1 — target workflow file had pre-existing CRLF/LF churn

Raw `git diff -- .github/workflows/wiki-lint.yml` was already noisy at baseline because of line-ending churn. Primary acceptance therefore used:

```bash
git diff -w -- .github/workflows/wiki-lint.yml
```

This isolates semantic content changes from whitespace-only churn. Raw diff is retained above for transparency.

### D2 — `PyYAML` unavailable in uv environment

The original plan used:

```bash
uv run python -c "import yaml; ..."
```

But the repo's uv environment does not include `PyYAML`, so YAML validation used system `python3`, which does have a `yaml` module installed. This did not affect the production change or workflow semantics.

### D3 — `actionlint` unavailable locally

`actionlint` was not installed in the current environment. The check was treated as optional per plan and recorded as skipped.

### D4 — `doctor --quick` contains pre-existing Bug H fail

`doctor --quick` still reports the known `flush_pipeline_correctness` failure for Bug H. This is baseline state and unrelated to the workflow change.

## 4. Tools used

- Wiki articles:
  - `wiki/sources/github-actions-docs.md`
  - `wiki/sources/astral-ruff-docs.md`
  - `wiki/sources/yaml-1-2-spec-docs.md`
  - `wiki/analyses/repo-hygiene-findings-2026-04-15.md`
- Local reads:
  - `CLAUDE.md`
  - `docs/codex-tasks/repo-hygiene-pr3-ci-ruff-check.md`
- Git:
  - `git status --short -- .github/workflows/wiki-lint.yml`
  - `git diff -w -- .github/workflows/wiki-lint.yml`
  - `git diff -- .github/workflows/wiki-lint.yml`
  - path-scoped baseline SHA256 snapshot
- Validation:
  - `python3` YAML parse / structure checks
  - `uv run ruff check --select I scripts/ hooks/`
  - `uv run ruff check scripts/ hooks/ --output-format=concise`
  - `uv run python scripts/lint.py --structural-only`
  - `uv run python scripts/wiki_cli.py doctor --quick`

## 5. Out of scope

- broad `ruff check` as CI gate
- `ruff format --check` in CI
- fixing the 15 pre-existing non-I Ruff errors
- adding `actionlint` as a required CI gate
- editing other workflows or triggers
- commit / push / PR creation

## 6. Self-audit

- [x] Doc verification completed before finalizing report
- [x] Only one tracked production file changed
- [x] Step name is exactly `Ruff check (I rule)`
- [x] Command is exactly `uv run ruff check --select I scripts/ hooks/`
- [x] Placement is between structural lint and syntax check
- [x] Primary acceptance uses `git diff -w`
- [x] Raw diff recorded as advisory only
- [x] Out-of-scope baseline SHA unchanged
- [x] Local narrow Ruff check passes
- [x] Broad Ruff baseline recorded, not gated
- [x] YAML parse / structure / ordering checks pass
- [x] Regression chain re-run and recorded
- [x] No commit or push performed

## 7. Final state

Tracked production diff:

- `.github/workflows/wiki-lint.yml`

Handoff artifact:

- `docs/codex-tasks/repo-hygiene-pr3-ci-ruff-check-report.md`

No commit. No push.
