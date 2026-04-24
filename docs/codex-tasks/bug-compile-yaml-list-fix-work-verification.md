# Work Verification Report — bug-compile-yaml-list-fix

**Plan**: `bug-compile-yaml-list-fix.md` (sibling) v5  
**Planning audit**: `bug-compile-yaml-list-fix-planning-audit.md` (sibling)  
**Execution report**: `bug-compile-yaml-list-fix-report.md` (sibling)  
**Verifier**: Codex  
**Verification date**: `2026-04-24`  
**Verdict**: `pass-with-noted-residuals`

---

## §1 — Scope and authority

This verification covers only the bugfix promised by the agreed plan:

- `scripts/utils.py` routes `get_article_projects()` through `parse_frontmatter_list()`
- regression coverage was added in `tests/test_utils.py`
- idempotency coverage was added in `tests/test_rebuild_index.py`

Out of scope and therefore not grounds for rejection here unless they regressed:

- `scripts/compile.py` output style for future `project:` emission
- `scripts/query.py` direct raw `project:` read
- existing wiki-content lint debt

Authority order used here:

1. code on disk
2. current local test / smoke output
3. existing raw-output evidence in `bug-compile-yaml-list-fix-report.md`
4. plan / planning-audit context
5. wiki as memory/context

Relevant workflow references reviewed before verdict:

- `CLAUDE.md` — requires a separate `-work-verification.md`
- `docs/workflow-instructions-codex.md` — evidence-only approval
- `docs/workflow-role-distribution.md` — Codex is the verification gate
- `wiki/concepts/codex-handoff-review-patterns.md` — verification artifact must state what was checked, how, and what remains unresolved

---

## §2 — Code-state verification

Verified current code diff directly:

- `scripts/utils.py` changes only `get_article_projects()` and its docstring.
- `tests/test_utils.py` adds list/scalar parsing coverage for `get_article_projects()`.
- `tests/test_rebuild_index.py` adds:
  - unit-level idempotency behavior check for `enrich_index_line()`
  - end-to-end list-form frontmatter regression coverage

Observed target paths in current worktree:

```text
 M scripts/utils.py
 M tests/test_rebuild_index.py
 M tests/test_utils.py
?? docs/codex-tasks/bug-compile-yaml-list-fix.md
?? docs/codex-tasks/bug-compile-yaml-list-fix-planning-audit.md
?? docs/codex-tasks/bug-compile-yaml-list-fix-report.md
?? docs/codex-tasks/bug-compile-yaml-list-fix-work-verification.md
```

No additional code files outside the planned fix surface were introduced by this continuation pass.

---

## §3 — Independent re-checks run in the current sandbox

These commands were rerun during this verification pass with the current on-disk state.

### §3.1 — Targeted regression files

Command:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' \
python3 -m pytest tests/test_utils.py tests/test_rebuild_index.py -q
```

Output:

```text
.................................................................        [100%]
65 passed in 0.91s
```

Verdict: pass.

### §3.2 — Full test suite

Command:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' python3 -m pytest tests/ -q
```

Output:

```text
........................................................................ [ 79%]
...................                                                      [100%]
91 passed in 0.83s
```

Verdict: pass.

### §3.3 — Direct reproduction probe

Command:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' python3 -c "from pathlib import Path; from utils import get_article_projects; p=Path('/tmp/bug_compile_yaml_list_fix.md'); p.write_text('---\ntitle: T\ntype: concept\nproject: [a, b, c]\n---\nbody\n', encoding='utf-8'); print(get_article_projects(p))"
```

Output:

```text
['a', 'b', 'c']
```

Verdict: pass. The bug is not reproducible anymore on current code.

### §3.4 — `wiki_cli.py status`

Command:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' python3 scripts/wiki_cli.py status
```

Output:

```text
Wiki Status:
  Articles: 304 (analyses: 6, concepts: 121, connections: 12, entities: 2, sources: 162, top-level: 1)
  Projects: codex-easy-start (22), memory-claude (175), messenger (47), montazhstroy-site (2), office (21), personal (8), site-tiretop (3), skolkovo (2), workflow (30), untagged (3)
  Daily logs: 14 (today: 59 entries)
  Last compile: 2026-04-23T18:41:44+00:00
  Last lint: 2026-04-23T20:24:59+00:00
  Total cost: $46.72
```

Verdict: pass.

### §3.5 — Query preview smokes

Commands:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' \
python3 scripts/query.py 'что wiki знает про llm-wiki-architecture' --preview

PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' \
python3 scripts/wiki_cli.py query 'что wiki знает про llm-wiki-architecture' --preview
```

Observed result in both routes:

- preview header present
- provenance-aware candidate list returned
- `[[concepts/llm-wiki-architecture]]` present in candidate set

Verdict: pass.

### §3.6 — Rebuild freshness smoke

Command:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' python3 scripts/wiki_cli.py rebuild --check
```

Output:

```text
Index is up to date.
```

Verdict: pass.

### §3.7 — Structural lint baseline check

Command:

```bash
PYTHONPATH='.venv/Lib/site-packages:scripts:hooks' python3 -u scripts/lint.py --structural-only
```

Observed summary:

```text
Results: 1 errors, 19 warnings, 859 suggestions

Errors found — knowledge base needs attention!
```

The blocking error is pre-existing wiki debt, not part of this patch:

```text
concepts/ntfs-case-fold-wsl-windows.md — Broken link: [[concepts/wsl-environment-divergence-cascade]] — target does not exist
```

Verdict: non-blocking for this bugfix; confirms the same baseline structural-lint debt remains.

### §3.8 — Syntax-only fallback check

Command:

```bash
python3 -m py_compile \
  scripts/utils.py \
  scripts/rebuild_index.py \
  scripts/query.py \
  scripts/wiki_cli.py \
  scripts/doctor.py \
  tests/test_utils.py \
  tests/test_rebuild_index.py
```

Output:

```text
<no output>
```

Verdict: pass.

---

## §4 — Checks inherited from the execution report

These gates already have raw-output evidence in `bug-compile-yaml-list-fix-report.md` and were not invalidated by this verification pass:

- `doctor --quick` retained `index_health PASS` while keeping only pre-existing FAIL classes
- PDC detector matched the corrected expected baseline exactly
- git-status delta stayed inside the planned whitelist
- `ruff check scripts/ tests/` remained clean (`post_ruff_issues = 0`)

Why they are inherited rather than fully rerun here:

1. the current sandbox cannot use the normal WSL `uv run` flow cleanly:
   - default `uv` cache path is read-only in this session
   - redirecting `uv` to `/tmp` still cannot fetch missing wheels because network/DNS access is blocked
2. repo `.venv` is a Windows environment (`.venv/Scripts/*.exe`), so its `ruff.exe` cannot be executed directly from this WSL sandbox

This means:

- I do **not** claim an independent fresh `ruff` rerun in this exact follow-up sandbox
- I **do** accept the existing raw-output evidence from the execution report because:
  - the touched code paths are unchanged since that recorded run
  - independent current reruns of pytest, reproduction, `wiki_cli` consumers, and rebuild freshness all agree with the recorded execution outcome

---

## §5 — Residual risks and non-blocking findings

Codex verification must name explicit residual risks rather than default to “looks fine”. Current residuals:

1. `scripts/query.py` still reads raw `project:` frontmatter text directly, so list-form values may still carry bracket characters into keyword-scoring text. The planning-audit already classifies this as degraded-but-functional, not broken for this fix scope.
2. `scripts/compile.py` is still free to emit list-form `project:`. This patch makes downstream parsing robust, but it does not normalize emitted style. Human-facing style inconsistency may therefore continue.
3. Structural lint debt remains active in the repo baseline. Because `doctor --quick` includes structural lint related checks, unrelated wiki debt can still produce failing smoke summaries around this otherwise-correct code patch.
4. `ruff` was not independently rerun in this exact follow-up sandbox due environment limitations described in §4. Approval therefore relies partly on the earlier raw-output evidence in the execution report, not solely on fresh rerun evidence from this pass.

None of the above residuals invalidate the promised bugfix behavior.

---

## §6 — Acceptance matrix

| Gate | Result | Evidence |
|---|---|---|
| `get_article_projects()` cleans list-form `project:` values | `pass` | §3.3 |
| regression tests for utils + rebuild pass | `pass` | §3.1 |
| full suite stays green | `pass` | §3.2 |
| `wiki_cli.py status` works with current metadata map | `pass` | §3.4 |
| query preview routes still work | `pass` | §3.5 |
| rebuild freshness stays idempotent | `pass` | §3.6 |
| syntax sanity for touched Python files | `pass` | §3.8 |
| PDC baseline remains correct | `pass` | report §4.5 |
| git delta stayed in whitelist | `pass` | report §4.6 |
| ruff stayed clean | `pass`, inherited | report §4.7 |
| `doctor --quick` retained `index_health PASS` | `pass`, inherited | report §4.4 |

---

## §7 — Final verdict

Verdict: `pass-with-noted-residuals`.

Reasoning:

- the underlying bug is fixed on current code
- the new regression coverage passes
- the full suite remains green
- downstream consumers that depend on article project metadata still behave correctly
- no new blocker tied to this patch surfaced during re-verification

The remaining concerns are real but out-of-scope or baseline:

- raw `project:` read in `query.py`
- future `compile.py` style inconsistency
- existing structural-lint debt
- inability to rerun `ruff` from this exact sandbox without relying on the already-recorded execution evidence

This fix is acceptable as the closure of `bug-compile-yaml-list-fix` without broadening scope into unrelated wiki-health cleanup.
