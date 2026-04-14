# Task — Wiki backlinks cleanup Phase A (top-10 target articles)

> **Роль**: исполнитель — Codex. Content review task на gitignored wiki files.

> **Иерархия источников правды** (СТРОГО):
> 1. **Официальная документация** — primary source of truth:
>    - GitHub Flavored Markdown lists: `https://github.github.com/gfm/#lists`
>    - Obsidian internal links syntax: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`
> 2. **Реальное состояние repo** — secondary:
>    - `<repo-root>/scripts/lint.py:check_missing_backlinks` (function semantics)
>    - `<repo-root>/scripts/utils.py:extract_wikilinks` (how backlinks are detected)
>    - `<repo-root>/scripts/utils.py:content_has_wikilink_target` (symmetric match check)
>    - `<repo-root>/reports/lint-2026-04-14.md` (current suggestions list)
>    - Every target article before editing it (Read tool)
>    - Every source article before deciding whether to add reverse link (Read tool)
> 3. **Этот план** — derived artifact, написан Claude'ом, может ошибаться.

> **Расхождение план vs дока ИЛИ план vs реальный lint output → побеждает реальность**. Фиксировать в `Discrepancies`.

---

## Source markers used in this plan

Each technical claim tagged:

- `[OFFICIAL-<URL>]` — directly from documentation
- `[EMPIRICAL-<file:line>]` — observed in the repo
- `[PROJECT]` — own architectural decision

Claims without a marker are **forbidden**. Если найдёшь такое — escalate в Discrepancies.

---

## Doc verification (ОБЯЗАТЕЛЬНО до любых правок)

Codex must re-read the following pages **right now**, not from memory. Fill the `Doc verification` section в отчёте с цитатами:

| URL | What to find | Why |
|---|---|---|
| `https://github.github.com/gfm/#lists` | Bullet list syntax (dash + space + content) | Target articles' See Also sections use bullet lists. Need to know exact list item grammar before editing. |
| `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Plain wikilink syntax `[[target]]` | Need to know whether to use plain form or alias form for reverse links. |

If any URL unreachable — document as `BLOCKED: <reason>` and **stop** before proceeding.

---

## Diagnosis (fresh empirical data from 2026-04-14 morning)

[EMPIRICAL-reports/lint-2026-04-14.md] Current lint state:
- **0 errors**
- **1 warning** — `daily/2026-04-14.md` uncompiled daily (не scope этой задачи)
- **283 missing-backlink suggestions**

[EMPIRICAL — grouped analysis of reports/lint-2026-04-14.md]:
- **283 raw suggestions**
- **54 distinct target articles** (the file that needs a reverse link added to its See Also)
- **187 unique source→target pairs** (283/187 = 1.51 duplicates per pair — same source article often mentions same target multiple times via Key Points + Details + See Also)

### Top 10 target articles by inbound backlink deficit

[EMPIRICAL — computed from reports/lint-2026-04-14.md]:

| # | Target article | raw suggestions | unique sources |
|---|---|---|---|
| 1 | `concepts/llm-wiki-architecture` | 54 | 31 |
| 2 | `concepts/claude-code-hooks` | 17 | 13 |
| 3 | `concepts/anthropic-context-anxiety-injection` | 17 | 9 |
| 4 | `sources/a-mem-zettelkasten-memory-hn` | 12 | 7 |
| 5 | `sources/engram-local-first-memory-hn` | 11 | 6 |
| 6 | `entities/pulse-messenger` | 10 | 6 |
| 7 | `concepts/windows-path-issues` | 9 | 5 |
| 8 | `concepts/pion-webrtc-calls` | 8 | 5 |
| 9 | `concepts/codex-stop-hook-reliability` | 8 | 5 |
| 10 | `concepts/bullmq-agent-workers` | 8 | 4 |
| **Top-10 total** | | **154** | **~91** |

[PROJECT] Top-10 targets = ~54% of all suggestions. Fixing just these 10 articles cuts more than half the debt.

[PROJECT] This plan covers **only Phase A** (top-10). Phase B (targets 11-54, ~129 suggestions) and Phase C (re-lint + document intentional asymmetries) are follow-up tasks after user reviews Phase A results.

---

## Contract — how backlink detection actually works

[EMPIRICAL-scripts/lint.py:140-162] `check_missing_backlinks()`:

```python
for article in list_wiki_articles():
    content = article.read_text(...)
    source_link = str(rel).replace(".md", "").replace("\\", "/")
    for link in extract_wikilinks(content):
        if link.startswith("daily/"):
            continue  # daily logs are one-way, never backlinked
        target_path = WIKI_DIR / f"{link}.md"
        if target_path.exists():
            target_content = target_path.read_text(...)
            if not content_has_wikilink_target(target_content, source_link):
                # asymmetric → report as suggestion
```

[EMPIRICAL-scripts/utils.py:92] `content_has_wikilink_target()` returns True iff `link_target in extract_wikilinks(content)`. Что значит:

**To satisfy the lint**, the target article's body (anywhere, not necessarily in See Also) must contain a wikilink `[[<source_slug>]]` either plain or aliased. **The simplest compliant edit is**: add `- [[<source_slug>]]` to the target's `## See Also` section.

[EMPIRICAL-wiki/concepts/llm-wiki-architecture.md + wiki/concepts/claude-code-hooks.md] Existing See Also format (both articles verified):

```markdown
## See Also

- [[concepts/claude-code-hooks]]
- [[concepts/uv-python-tooling]] — optional short description
```

Plain `[[slug]]` bullet, optionally followed by `— description`. No alias form is used.

---

## Mandatory external tools

Every row MUST appear in `## Tools used` of the report with ✅ or explicit `BLOCKED: reason` / `not available in environment`. Прочерк недопустим.

| Tool | Purpose | Phase |
|---|---|---|
| **WebFetch** `https://github.github.com/gfm/#lists` | Verify list syntax | Doc verification |
| **WebFetch** `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Verify wikilink syntax | Doc verification |
| **Read** `scripts/lint.py:140-162` | Understand backlink detection | Pre-flight |
| **Read** `scripts/utils.py:extract_wikilinks + content_has_wikilink_target` | Understand match semantics | Pre-flight |
| **Read** `reports/lint-2026-04-14.md` | Source of authoritative suggestion list | Pre-flight |
| **Read** every target article before editing (10 articles) | Verify current See Also state | Per-target |
| **Read** every unique source article mentioned in that target's suggestions (~91 reads) | Make judgment call per source | Per-target |
| **Bash** `uv run python scripts/lint.py --structural-only` | Pre/post counts | Phase 1 |
| **Bash** `uv run python scripts/wiki_cli.py doctor --quick` | Ensure structural_lint stays PASS | Phase 1 |
| **Bash** Python one-liner to regenerate suggestion list grouped by target | Verify plan's data still current | Pre-flight |
| **Wiki articles** `[[concepts/llm-wiki-architecture]]` + top-10 targets | Required context | Per-target |
| **MCP filesystem** (if available) | Alternative file reads | optional |
| **MCP git** (if available) | git status verification | optional |

Игнорирование любого tool = halтура, не "оптимизация".

---

## Per-target workflow (the "batch by target" pattern)

For each of the 10 target articles, Codex does the following sequence:

### Step 1 — Collect suggestions for this target

Run a short Python script against `reports/lint-2026-04-14.md` to list all unique source articles that link to this target but lack reverse links:

```bash
uv run python -c "
import re
from pathlib import Path
target = 'concepts/llm-wiki-architecture'  # change per target
sources = set()
report = Path('reports/lint-2026-04-14.md').read_text(encoding='utf-8')
for line in report.split('\n'):
    m = re.search(r'\[\[([^\]]+)\]\] links to \[\[([^\]]+)\]\] but not vice versa', line)
    if m and m.group(2) == target:
        sources.add(m.group(1))
for s in sorted(sources):
    print(s)
"
```

### Step 2 — Read each unique source article

Use the `Read` tool on every distinct source. Understand what the source is about and how it references the target. Do not skip this step.

### Step 3 — Decide per source (YES / NO / SKIP-WITH-REASON)

Decision heuristics [PROJECT]:

- **YES — add reverse link**: source is topically relevant to the target's subject matter, the connection is bidirectionally meaningful (reader of target would benefit from knowing about the source, not just vice versa)
- **NO — intentional asymmetry, document in report**: source is a tangential mention, e.g., a sources/ article quotes the target as background context but the target article itself doesn't gain anything from listing the source
- **SKIP with reason in report**: source is a daily log (shouldn't happen per lint filter, but double-check), orphan article scheduled for deletion, or source is itself a See Also-only mention of the target without substantive discussion

Typical patterns to watch:

- `sources/<external-doc>` → `concepts/<our-concept>` — usually YES (concept "enriches its bibliography")
- `concepts/<our-concept-A>` → `concepts/<our-concept-B>` — usually YES (cross-cutting, reciprocal)
- `analyses/<research-memo>` → `concepts/<our-concept>` — usually YES (research references concept)
- `entities/<project>` → `concepts/<our-concept>` — YES if concept is specific to project, NO if concept is generic

### Step 4 — Edit target article's See Also section

Single Edit operation adding all "YES" reverse links as plain bullets:

```markdown
## See Also

- [[concepts/claude-code-hooks]]        <- existing
- [[concepts/uv-python-tooling]]        <- existing
- [[sources/new-source-1]]              <- NEW reverse link
- [[sources/new-source-2]]              <- NEW reverse link
- [[concepts/new-concept-3]]            <- NEW reverse link
```

Use plain wikilink form, no alias, no description suffix (keep consistent with [EMPIRICAL — observed format in existing articles]).

### Step 5 — Record decisions in report

For this target, the report should include:

- Total candidates (unique source count)
- YES count (links added)
- NO count (intentional asymmetry, with one-line reason per skip)
- Final bullet list added to the target's See Also

---

## Whitelist (Phase A scope)

**Only these 10 files** may be edited in Phase A:

1. `wiki/concepts/llm-wiki-architecture.md`
2. `wiki/concepts/claude-code-hooks.md`
3. `wiki/concepts/anthropic-context-anxiety-injection.md`
4. `wiki/sources/a-mem-zettelkasten-memory-hn.md`
5. `wiki/sources/engram-local-first-memory-hn.md`
6. `wiki/entities/pulse-messenger.md`
7. `wiki/concepts/windows-path-issues.md`
8. `wiki/concepts/pion-webrtc-calls.md`
9. `wiki/concepts/codex-stop-hook-reliability.md`
10. `wiki/concepts/bullmq-agent-workers.md`

All 10 are **gitignored** (under `wiki/`), no commit/push, no CI risk.

**Out-of-scope temptations** (do NOT touch):

- Any other wiki/ article (Phase B covers 44 more targets)
- `scripts/lint.py` or any script — this is content edit, not code
- `CLAUDE.md` or any policy doc
- Any `docs/codex-tasks/` file (except this plan's own report file)
- Orphan `daily/2026-04-14.md` uncompiled warning — separate task
- Any source article that currently references the target but doesn't appear in the 10 — scope is bounded to top-10 only

---

## Verification phases

### Phase 1 — pre-edit lint snapshot (Codex runs before any edit)

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

Record the exact output in the report. Expected [EMPIRICAL-reports/lint-2026-04-14.md]: `Results: 0 errors, 1 warnings, 283 suggestions`.

If numbers differ significantly — the lint state changed since this plan was written. **Stop и escalate в Discrepancies**, do not proceed with assumptions from the plan.

### Phase 1.5 — per-target analysis & edits (Codex runs sequentially)

For each of the 10 targets, in the order listed in Whitelist:

1. Run the Python one-liner from Step 1 to get current source list for this target
2. Read every source article
3. Make YES/NO decisions with one-line reason per decision in the report
4. Edit the target article's See Also section once
5. Record the per-target summary in the report

### Phase 2 — post-edit lint snapshot (Codex runs after all 10 targets done)

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

**Expected** [PROJECT]: suggestion count drops from 283 to roughly 283 - (cumulative YES count across 10 targets). Since duplicates per unique pair = 1.51, adding 1 reverse link resolves ~1.51 raw suggestions on average. If all 154 raw suggestions from top-10 were resolved, count would drop to ~129.

Record actual drop in the report. Do not pre-commit to a specific number — the "actual vs expected" comparison itself is the signal.

### Phase 3 — doctor regression

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep -E "(FAIL|PASS).*(lint|provenance)"
```

**Expected**:
- `[PASS] structural_lint: ...` (still PASS — adding reverse links doesn't introduce errors)
- `[PASS] wiki_cli_lint_smoke: ...`

If either fails — **stop и escalate в Discrepancies**.

### Phase 4 — spot-check 3 random target articles (Codex runs)

For 3 randomly-chosen targets (out of 10), Read the final state of each and confirm:
- Original See Also entries preserved
- New reverse links present
- No duplicates (same link listed twice)
- File is valid markdown (no broken frontmatter, etc.)

### Phase 5 — decision statistics

In the report, total:
- YES count across all 10 targets
- NO count across all 10 targets
- Per-target split: target | YES | NO | net suggestions resolved

---

## Acceptance criteria

- ✅ Doc verification: 2 URLs re-read, цитаты in report
- ✅ Mandatory tools table filled with ✅/BLOCKED — no dashes
- ✅ Phase 1 pre-edit snapshot matches plan's expected state OR stop-escalate
- ✅ Each of the 10 target articles has per-target decision analysis in the report
- ✅ Each of the 10 target articles has exactly one Edit operation applied to its See Also section
- ✅ Post-edit lint suggestion count dropped by a meaningful amount (plan's expected: ~154 raw, rough because of duplicates)
- ✅ `doctor --quick` structural_lint + wiki_cli_lint_smoke still PASS
- ✅ Spot-check 3 random targets show correct final state
- ✅ Decision statistics summary в report
- ✅ No files touched outside whitelist
- ✅ No commit / push

---

## Out of scope

- **Phase B** (targets 11-54, ~129 raw suggestions): separate follow-up handoff after user reviews Phase A
- **Phase C** (accept ≤10 remaining as intentional asymmetries, close #21): follow-up after Phase B
- **Auto-fix script** — issue #21 body [EMPIRICAL-gh issue 21] explicitly says *"Auto-fix tooling (separate enhancement if desired)"*. Not this task.
- **Rewriting any source article** to be linked from the target side — only target article edits
- **Creating new wiki articles** to satisfy orphan linking needs — current content is sufficient
- **Daily log compile** for `daily/2026-04-14.md` — separate task
- **Any `scripts/` or `CLAUDE.md` edits** — content-only task

---

## Rollback

Wiki files are gitignored, so no `git checkout` recovery. Codex must keep `.bak` of each target file before editing:

```bash
cp wiki/concepts/llm-wiki-architecture.md wiki/concepts/llm-wiki-architecture.md.bak
# ... edit ...
# to rollback: mv wiki/concepts/llm-wiki-architecture.md.bak wiki/concepts/llm-wiki-architecture.md
```

Delete `.bak` files after task completes successfully.

---

## Pending user actions

After Codex completes Phase A:

1. Review decision statistics (did Codex skip reasonable sources?)
2. Review 3-5 target articles' final See Also sections to confirm quality
3. Decide whether to proceed with Phase B (targets 11-54) as a follow-up handoff
4. Decide when to close #21 (after all Phase A+B+C, или earlier acceptance of remaining debt)

---

## Notes для исполнителя (Codex)

- **This plan follows the new structural checklist** from memory rule `feedback_codex_task_handoff_workflow.md:32` "Plan template — STRUCTURAL CHECKLIST". Every section required by that checklist is present.
- **Doc verification is mandatory before any edit**. Two URLs must be re-read. If you skip, that's a дисциплинарный залёт.
- **Source markers** `[OFFICIAL]` / `[EMPIRICAL-path]` / `[PROJECT]` appear throughout this plan. If any technical claim lacks one, treat the plan as broken — escalate.
- **This is content review, not code**. But issue #21 body explicitly said *"auto-fix creates noise"* — use judgment per source article, don't blindly add every reverse link. "NO" decisions with one-line reason are valid outcomes.
- **Batch by target, not by suggestion**. 283 suggestions → 54 targets → top-10 = 10 decisions per target max. Read all sources for one target, then edit once.
- **Whitelist is 10 files strict**. Phase B follows after user review. Do not "just fix a couple more while I'm here".
- **NO commit / push** — wiki/ is gitignored anyway, but explicit rule.
- **Placeholder convention** applies to the report file — use `${USER}`, `<repo-root>`, `<user-home>` for any path citations.
- **Если реальный lint count значительно отличается от 283** при Phase 1 snapshot — план устарел, stop и escalate.
- **Создай отчёт** в `docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md` следуя structural checklist из memory rule.
- **Self-audit verifier**: после написания каждой секции отчёта, прогнать: *"можно ли удалить этот claim и отчёт остаётся consistent?"* Если да — claim из головы, escalate.
