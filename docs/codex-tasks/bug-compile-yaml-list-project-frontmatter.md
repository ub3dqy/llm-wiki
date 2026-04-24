# Bug: compile generates YAML-list `project:` frontmatter → breaks index idempotency

**Discovered**: 2026-04-22 during P1 wiki-health execution (iter-5 passed) by Codex.
**Tracking doc**: this file (for future task spawn).
**Severity**: moderate — silent index_health FAIL, workaround exists but requires manual per-article normalization.
**Out of P1 scope (wiki-health-2026-04-21)**: Codex normalized the offending article by hand to unblock P1 acceptance. Root cause deferred.

---

## What happened

`scripts/compile.py --file daily/2026-04-21.md` created `wiki/connections/tool-enforcement-dual-failure.md` with frontmatter:

```yaml
project: [codex-easy-start, site-tiretop, workflow]
```

(YAML list of strings.)

But `scripts/rebuild_index.py` + index utilities expect:

```yaml
project: codex-easy-start, site-tiretop, workflow
```

(Single comma-separated scalar string.)

Result: `rebuild_index.py` became **non-idempotent** — repeated runs produced different `index.md` outputs for the same wiki state. `doctor --quick index_health` check flipped to FAIL. Codex manual fix: edit the article, replace list with scalar. `rebuild_index.py --check` then confirmed idempotency.

Observed in report: `docs/codex-tasks/wiki-health-2026-04-21/p1-handoff/report.md` §5 item 3, §6.

---

## Root cause hypotheses (to investigate in follow-up task)

1. **Compile LLM prompt** instructs the model to list projects as YAML array when article spans multiple. Need to read `scripts/compile.py` prompt template to confirm.
2. **Frontmatter validator missing**: no post-compile step asserts `project:` is a scalar. Should be added to `scripts/compile.py` finish-write path, or to `scripts/lint.py` as a check that runs on new concept/connection articles.
3. **Index utils** (`scripts/rebuild_index.py`, `hooks/shared_wiki_search.py`) silently coerce list vs string differently → non-deterministic ordering. Either:
   - Standardize on scalar (cleanest for ad-hoc grep/frontmatter tooling), or
   - Standardize on list (cleanest YAML) and fix index utils.

Repo convention per existing articles: **scalar comma-separated**. So fix direction = prevent compile from emitting lists.

---

## Reproducibility

Every compile that generates a connection article spanning ≥2 projects is likely to hit this. Evidence: 1/1 in this run. Additional data needed from prior compile outputs to confirm frequency.

---

## Suggested follow-up task shape

**Scope**: one of
- A. Fix in `compile.py` prompt (preferred): require model to output `project: a, b, c` scalar.
- B. Add post-compile frontmatter validator that rewrites list → scalar before save.
- C. Add `lint.py` check for this specific pattern and fail fast with clear diff suggestion.

**Acceptance**: new compile with multi-project connection article produces scalar `project:`, `rebuild_index.py` idempotent on first try, `doctor --quick index_health` PASS.

**Evidence to capture**: reference this file; re-run compile against a fresh multi-project daily log; diff output.

---

## Related files

- `scripts/compile.py` — prompt / finish-write path
- `scripts/rebuild_index.py` — non-idempotent behavior
- `scripts/lint.py` — could gain new check
- `wiki/connections/tool-enforcement-dual-failure.md` — manually normalized example of the fix
- `docs/codex-tasks/wiki-health-2026-04-21/p1-handoff/report.md` §5.3, §6 — original incident record
