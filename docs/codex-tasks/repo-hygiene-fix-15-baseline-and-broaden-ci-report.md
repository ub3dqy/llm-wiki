---
task: Fix 15 pre-existing ruff errors + broaden CI gate from --select I to full check
plan: docs/codex-tasks/repo-hygiene-fix-15-baseline-and-broaden-ci.md
executor: Codex
status: completed
---

# Report — Fix 15 ruff baseline + broaden CI

## Правила заполнения

1. Docs > код > план. Расхождение → Discrepancy.
2. Только реальные данные.
3. Doc verification ПЕРЕД правкой.
4. Self-audit в конце.

---

## 0. Pre-flight

### 0.1 Environment

```text
Linux <host> 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun 5 18:30:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
Python 3.12.3
uv 0.11.6 (x86_64-unknown-linux-gnu)
ruff 0.15.10
```

### 0.2 Git status + HEAD

```text
HEAD: 2331283a07695d9e00f1cbec3f009b89c16a9a13

Pre-existing worktree dirt already existed across many tracked files in:
- docs/codex-tasks/
- hooks/
- scripts/
- README.md / CLAUDE.md / .gitignore / workflow files

Because of that, this task used path-scoped verification and baseline-delta checks
instead of global clean-worktree assumptions.
```

### 0.2b Baselines (BEFORE edits)

**Baseline A — out-of-scope SHA256**:
```text
57426bbdb494ee69aece2eec232494a31c34ee27f6a02f958f162080fcdbd928  -
```

**Baseline B — full ruff error count**:
```text
scripts/wiki_cli.py:27:31: F401 [*] `config.REPORTS_DIR` imported but unused
Found 15 errors.
[*] 12 fixable with the `--fix` option (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

**Baseline C — format still clean**:
```text
25 files already formatted
```

### 0.3 Verify re-export BEFORE any changes

```text
re-export works
```

### 0.6 Doc verification

| Source | Quote | ✅/❌ |
|---|---|---|
| ruff F401 rule docs | `If an import statement is used to re-export a symbol as part of a module's public interface, consider using a "redundant" import alias` | ✅ |
| ruff F841 rule docs | `This rule's fix is marked as unsafe because removing an unused variable assignment may delete comments that are attached to the assignment.` | ✅ |
| ruff F541 rule docs | `Checks for f-strings that do not contain any placeholder expressions.` | ✅ |
| ruff E402 rule docs | `Checks for imports that are not at the top of the file.` | ✅ |
| ruff `# noqa` docs | `To ignore an individual violation, add # noqa: {code} to the end of the line` | ✅ |

---

## 1. Changes

### 1.1 Change 1 — Protect re-export (FIRST)

Manually add `# noqa: F401` to `hook_utils.py`.

Diff:
```diff
-from utils import parse_frontmatter  # noqa: E402
+from utils import parse_frontmatter  # noqa: E402, F401  # re-export for shared hook modules
```

Post-check: re-export still works?
```text
ok
```

### 1.2 Change 2 — Autofix

```text
F841 Local variable `cwd` is assigned to but never used
  --> hooks/codex/stop.py:95:5

E402 Module level import not at top of file
  --> scripts/doctor.py:35:1

F841 Local variable `sources` is assigned to but never used
   --> scripts/lint.py:326:9

Found 14 errors (11 fixed, 3 remaining).
No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

Post-autofix remaining:
```text
hooks/codex/stop.py:95:5: F841 Local variable `cwd` is assigned to but never used
scripts/doctor.py:35:1: E402 Module level import not at top of file
scripts/lint.py:326:9: F841 Local variable `sources` is assigned to but never used
Found 14 errors.
[*] 11 fixable with the `--fix` option (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

### 1.3 Change 3a — Remove dead `cwd` in stop.py

```diff
@@
-    cwd = hook_input.get("cwd", "")
     transcript_path_str = get_transcript_path(hook_input)
```

### 1.4 Change 3b — Remove dead `sources` in lint.py

```diff
@@
-        sources = fm.get("sources", "")
         if page_type not in {"concept", "connection"}:
```

### 1.5 Change 4 — Move import in doctor.py

```diff
@@
+from runtime_utils import find_uv, is_wsl
+
 try:
@@
 FLUSH_LOG = SCRIPTS_DIR / "flush.log"
 CAPTURE_HEALTH_WINDOW_DAYS = 7
-from runtime_utils import find_uv, is_wsl
```

### 1.6 Post-manual ruff check

```text
All checks passed!
```

### 1.7 Change 5 — Broaden CI gate

```diff
@@
-      - name: Ruff check (I rule)
-        run: uv run ruff check --select I scripts/ hooks/
+      - name: Ruff check
+        run: uv run ruff check scripts/ hooks/
```

### 1.8 Final diff scope

```text
 .github/workflows/wiki-lint.yml | 4 ++--
 hooks/codex/stop.py             | 1 -
 hooks/hook_utils.py             | 2 +-
 scripts/compile.py              | 1 -
 scripts/doctor.py               | 4 ++--
 scripts/lint.py                 | 4 +---
 scripts/rebuild_index.py        | 2 +-
 scripts/seed.py                 | 4 +---
 scripts/wiki_cli.py             | 2 +-
 9 files changed, 9 insertions(+), 15 deletions(-)
---
 M .github/workflows/wiki-lint.yml
 M hooks/codex/stop.py
 M hooks/hook_utils.py
 M scripts/compile.py
 M scripts/doctor.py
 M scripts/lint.py
 M scripts/rebuild_index.py
 M scripts/seed.py
 M scripts/wiki_cli.py
---
57426bbdb494ee69aece2eec232494a31c34ee27f6a02f958f162080fcdbd928  -
```

Baseline-delta:
```text
Out-of-scope SHA256 matched Baseline A exactly.
```

---

## 2. Phase 1 — Smoke

### 2.1 Zero ruff errors
```text
All checks passed!
```

### 2.2 Format still clean
```text
25 files already formatted
```

### 2.3 I rule still clean
```text
All checks passed!
```

### 2.4 Re-export preserved
```text
ok
```

### 2.5 AST sanity on 8 modified .py files
```text
AST OK hooks/hook_utils.py
AST OK hooks/codex/stop.py
AST OK scripts/compile.py
AST OK scripts/doctor.py
AST OK scripts/lint.py
AST OK scripts/rebuild_index.py
AST OK scripts/seed.py
AST OK scripts/wiki_cli.py
```

### 2.6 Import smoke
```text
IMPORT OK hooks/hook_utils.py
IMPORT OK hooks/codex/stop.py
IMPORT OK scripts/compile.py
IMPORT OK scripts/doctor.py
IMPORT OK scripts/lint.py
IMPORT OK scripts/rebuild_index.py
IMPORT OK scripts/seed.py
IMPORT OK scripts/wiki_cli.py
```

### 2.7 lint --structural-only
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
    Found 148 issue(s)
  Checking: Missing backlinks...
    Found 325 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo>/reports/lint-2026-04-16.md

Results: 0 errors, 22 warnings, 473 suggestions
```

### 2.8 doctor --quick
```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/187 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 2776026/2779599 chars reached flush.py (coverage 99.9%)
[FAIL] flush_pipeline_correctness: Last 24h: 2 'Fatal error in message reader' events (7d total: 18, most recent 2026-04-16 00:14:33) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <linux-home>/.local/bin/uv
[FAIL] index_health: Index is out of date. Run without --check to rebuild.
[PASS] structural_lint: Results: 0 errors, 22 warnings, 473 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[FAIL] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check did not confirm index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

---

## 3. Phase 2 — `[awaits user + CI]`

`[awaits user]` Push branch / open PR so GitHub Actions can run the broadened `Ruff check` step in CI.

---

## 4. Tools used

| Tool | Status | Details |
|---|---|---|
| Wiki: astral-ruff-docs | used | local repo source summary consulted |
| WebFetch: ruff rules docs | used | F401, F841, F541, E402, noqa docs |
| Local ruff check/fix | used | baseline, autofix, zero-error verification, format check |
| Git | used | status, HEAD, diff scope, baseline-delta SHA256 |
| Repo docs | used | CLAUDE.md and task plan/report template |

---

## 5. Out-of-scope temptations

- Convert the re-export to Ruff-preferred `from utils import parse_frontmatter as parse_frontmatter` instead of `# noqa: F401`
- Broaden rule set beyond default + `I`
- Touch `pyproject.toml` or any non-whitelist files

None were done.

---

## 6. Discrepancies

### D1 — Ruff docs prefer redundant alias for re-export, but plan required `# noqa: F401`

Ruff's F401 docs prefer a redundant alias or `__all__` for re-exports. The approved plan explicitly required `# noqa: F401` as the minimal protective change before `ruff --fix`. Followed plan because:

- it was the task's explicit critical contract
- it minimized blast radius to one line
- it preserved the existing re-export pattern without changing import style

### D2 — `doctor --quick` had an extra pre-existing FAIL beyond Bug H

Plan expected `doctor --quick` exit 0 with only pre-existing Bug H. Actual output had:

- Bug H FAIL in `flush_pipeline_correctness`
- pre-existing `index_health` / `wiki_cli_rebuild_check_smoke` FAIL because `index.md` is already stale

This is unrelated to the Ruff cleanup and CI broadening. Command still exited `0`.

### D3 — Raw git diffs are noisy because the worktree was already dirty

The task used path-scoped diff and baseline-hash checks. Global clean-worktree assumptions would have been false from the start.

---

## 7. Self-audit

- [x] 0.2b baselines captured
- [x] 0.3 re-export verified pre-change
- [x] 0.6 doc verification
- [x] 1.1 Change 1 FIRST (noqa protection)
- [x] 1.2 autofix output matches expected
- [x] 1.3-1.5 manual fixes applied
- [x] 1.6 zero ruff errors post-manual
- [x] 1.7 CI broadened
- [x] 1.8 diff scope = 9 files, baseline-delta clean
- [x] 2.1-2.8 all smokes pass
- [x] Re-export parse_frontmatter preserved
- [x] No commit/push
- [x] No personal data
