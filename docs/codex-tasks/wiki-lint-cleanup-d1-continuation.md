# Continuation — Subtask D1 approved (2026-04-14)

> User approved **D1 + D3** after reviewing backfill cost = 0. D3 (memory rule) already applied by Claude directly. **This continuation covers D1 only** — tracked file changes to `scripts/lint.py` and `CLAUDE.md`.

## Context

- Main plan: `docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md` Subtask D section
- Main report: `docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md` (Subtasks A/B/C/E already filled, D section marked as awaiting approval)
- Backfill cost: **0 files** (Codex's own measurement in the report). Applying D1 will not introduce cascading errors on existing wiki content.
- D3 memory rule already added by Claude to `<user-home>/.claude/projects/.../memory/feedback_codex_task_handoff_workflow.md` under section "Wiki concept/connection article hygiene (since 2026-04-14)".

## Iерархия источников правды (same as parent plan)

1. **Официальная документация** — primary source of truth:
   - `https://docs.python.org/3/library/re.html` (regex semantics)
2. **Реальное состояние repo** — secondary:
   - `<repo-root>/scripts/lint.py` (the actual function to modify)
   - `<repo-root>/CLAUDE.md` (the schema text to update)
3. **Этот continuation + parent plan** — derived.

## Files to modify (whitelist)

1. `<repo-root>/scripts/lint.py` — one-line change in `check_provenance_completeness`
2. `<repo-root>/CLAUDE.md` — schema text change про `confidence` / `## Provenance` requirement

**Nothing else**. Do not touch any other file. `<repo-root>/wiki/` already in correct state per Subtasks A-E. Memory file under user-home already handled.

## Mandatory external tools

| Tool | Purpose |
|---|---|
| **Read** `<repo-root>/scripts/lint.py` lines 181-216 | Verify exact current filter logic before editing |
| **Read** `<repo-root>/CLAUDE.md` entire file | Find exact text location describing `confidence` optionality |
| **Grep** `<repo-root>/CLAUDE.md` for "confidence" | Find all mentions to update consistently |
| **Bash** `uv run python scripts/lint.py --structural-only` | Pre/post snapshots |
| **Bash** `uv run python scripts/wiki_cli.py doctor --quick` | Confirm `structural_lint` and `wiki_cli_lint_smoke` stay PASS |

Each must appear in `## Tools used` of the updated report with ✅ or explicit `BLOCKED: reason`.

## Change 1 — scripts/lint.py

### Source marker

[EMPIRICAL-`<repo-root>/scripts/lint.py:190`] Current filter:

```python
if page_type not in {"concept", "connection"} or not frontmatter_sources_include_prefix(sources, "daily/"):
    continue
```

### Action

Remove the `daily/` prefix filter clause so the check applies to **all** concepts and connections regardless of source prefix. The resulting line should be:

```python
if page_type not in {"concept", "connection"}:
    continue
```

### Justification

[PROJECT] Current filter was a carveout allowing manual `wiki-save`-created concepts to skip provenance hygiene. This carveout caused two Claude discipline failures today (documented in report Subtasks A/B of this same task). Removing the carveout makes the rule consistent and filesystem-enforced.

[EMPIRICAL] Backfill cost measured as 0 in Subtask D-prep. No existing articles will newly fail the lint check after this change.

### Verification

```bash
# Pre snapshot
uv run python scripts/lint.py --structural-only 2>&1 | tail -5

# Apply edit via Edit tool (not sed)

# Post snapshot
uv run python scripts/lint.py --structural-only 2>&1 | tail -5
```

**Expected**: both snapshots show `0 errors` (because backfill = 0). The change is latent — it catches **future** violations, not existing ones. If any errors appear post-change, that indicates a backfill miss and must be reported in Discrepancies.

## Change 2 — CLAUDE.md schema text

### Source marker

[EMPIRICAL-`<repo-root>/CLAUDE.md`] — need to Grep for current text mentioning `confidence` optionality. Expected phrase pattern: *"optional for manual ingest"* or *"required for compile-generated concepts/connections"*.

### Action

Find the section describing `confidence` and `## Provenance` requirements for wiki articles. Update the text to explicitly state that **all concepts and connections** require both fields, not just compile-generated ones.

Suggested new wording (adapt to actual CLAUDE.md structure):

```markdown
- **Confidence labels**: required for **all** concept and connection articles (not just compile-generated). Valid values: `extracted`, `inferred`, or `to-verify`. Manual ingest pages created via `/wiki-save` or Write tool must include `confidence` in frontmatter.
- **Provenance section**: concepts and connections must include a `## Provenance` section explaining what was directly observed in the source vs. what was inferred synthesis. See `wiki/concepts/anthropic-context-anxiety-injection.md` for a canonical example.
```

The exact text and location depend on the current CLAUDE.md structure — Read the file first, find the paragraph about `confidence`, and replace the "optional for manual ingest" part with the new requirement.

### Justification

[PROJECT] Schema doc must agree with lint behavior. Having the doc say "optional" while lint enforces "required" causes confusion (exactly what happened today).

### Verification

```bash
# Re-read the changed section to ensure no other text contradicts it
grep -A3 -B1 "confidence" CLAUDE.md
```

**Expected**: text clearly states concepts/connections require `confidence` + `## Provenance`. No contradictory leftover "optional" language.

## Final combined verification (after both changes)

```bash
# Lint remains clean
uv run python scripts/lint.py --structural-only 2>&1 | tail -5

# Doctor remains green on lint-specific checks
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep -E "structural_lint|wiki_cli_lint_smoke"
```

**Expected**:
- `Results: 0 errors, 0 warnings, <N> suggestions` (warnings stay 0 per Subtask B fix)
- `[PASS] structural_lint: ...`
- `[PASS] wiki_cli_lint_smoke: ...`

If any regression — stop, revert via `git checkout scripts/lint.py CLAUDE.md`, report in Discrepancies.

## Acceptance criteria

- ✅ `scripts/lint.py:190` has the `daily/` filter removed
- ✅ `CLAUDE.md` schema text reflects the new requirement consistently
- ✅ Backfill=0 still holds (no new errors)
- ✅ `doctor --quick` passes `structural_lint` and `wiki_cli_lint_smoke`
- ✅ `## Tools used` in the updated report shows all 5 mandatory tools ticked
- ✅ Source markers present on all technical claims in the updated D section of the report
- ✅ **NO commit / push** — leave diff for user review

## Out of scope

- Rollback of any earlier subtask (A/B/C/E stay as they are)
- Modifying the wiki/ content (already in correct state)
- Updating `feedback_codex_task_handoff_workflow.md` memory (Claude handled D3 directly)
- Creating additional issue comments or PRs
- Improving the lint check beyond the specific carveout removal

## Rollback

```bash
git checkout scripts/lint.py CLAUDE.md
```

## Pending user actions after Codex completes

1. Review the two-file diff
2. Decide whether to merge as a separate PR or bundle with the wiki-lint-cleanup task closure
3. Confirm `doctor --full` still acts as expected (not just `--quick`)

## Notes для исполнителя (Codex)

- **This is a minimal continuation**. One code line change + one schema text update. Do NOT expand scope.
- **Update the existing report file** `wiki-lint-cleanup-and-provenance-discipline-report.md` Subtask D section with:
  - "D1 applied per continuation plan" note
  - Full diff of both files
  - Post-change lint + doctor output
  - Tools used checklist for this continuation
- **Source markers** expected on any new content in the updated report section
- **Doc verification** — Python `re` doc already verified in the parent task's Doc verification section. No need to re-verify unless you're making regex changes (which you aren't — this is just filter logic).
- **No new report file** — extend the existing one. Put the continuation section after the existing Subtask D "STOP" marker.
