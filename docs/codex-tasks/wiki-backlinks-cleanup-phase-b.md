# Task — Wiki backlinks cleanup Phase B (next 15 target articles)

> **Роль**: исполнитель — Codex. Content review task на gitignored wiki files. **Continuation of completed Phase A** (top-10 targets, 88% fix rate, 136 raw suggestions resolved).

> **Иерархия источников правды** (СТРОГО):
> 1. **Официальная документация** — primary source of truth:
>    - GitHub Flavored Markdown lists: `https://github.github.com/gfm/#lists`
>    - Obsidian internal links syntax: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`
> 2. **Реальное состояние repo** — secondary:
>    - `<repo-root>/scripts/lint.py:check_missing_backlinks` (function semantics)
>    - `<repo-root>/scripts/utils.py:extract_wikilinks` + `content_has_wikilink_target` (match logic)
>    - `<repo-root>/reports/lint-2026-04-14.md` (current suggestions list — **regenerate before reading**, lint state may have shifted from Phase A)
>    - `<repo-root>/docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md` — Phase A precedent for similar judgment patterns
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

Claims без marker — escalate в Discrepancies.

---

## Doc verification (ОБЯЗАТЕЛЬНО до любых правок)

Codex must re-read both pages **right now**, not from memory. **Don't reuse Phase A's verification** — re-fetch, even if Phase A's report has the same URLs cited. Doc state may shift.

| URL | What to find | Why |
|---|---|---|
| `https://github.github.com/gfm/#lists` | Bullet list syntax (dash + space + content) | See Also sections use bullet lists |
| `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Plain wikilink syntax `[[target]]` | Need to know whether to use plain form or alias for reverse links |

If unreachable — `BLOCKED: <reason>` and stop.

---

## Diagnosis (fresh empirical data from 2026-04-14 после Phase A)

[EMPIRICAL — current `reports/lint-2026-04-14.md` post Phase A]:

- **0 errors**
- **1 warning** — `daily/2026-04-14.md` uncompiled (out of scope)
- **147 missing-backlink suggestions remaining** (was 283 before Phase A, dropped by 136 = 48%)

[EMPIRICAL — grouped analysis of current report]:
- **129 raw suggestions** in 44 distinct targets (excluding Phase A targets which are now mostly done)
- **187 unique source-target pairs** total (some duplicates from same article mentioning same target multiple times)
- **18 raw suggestions remaining** in Phase A targets (these are intentional NO decisions from Phase A — do NOT re-process)

### Phase B priority — top 15 targets by raw suggestion count

[EMPIRICAL — computed 2026-04-14 после Phase A]:

| # | Target | raw | unique sources |
|---|---|---:|---:|
| 1 | `concepts/claude-cli-autonomous-task-loops` | 7 | 5 |
| 2 | `sources/cognition-rebuilding-devin-sonnet-4-5` | 7 | 5 |
| 3 | `concepts/seo-ai-strategy-2026` | 7 | 4 |
| 4 | `analyses/llm-wiki-improvement-research-2026-04-12` | 6 | 6 |
| 5 | `sources/aris-autonomous-ml-research` | 6 | 5 |
| 6 | `sources/claude-opus-4-6-diagnosis-2026` | 6 | 4 |
| 7 | `sources/seo-ai-strategy-2026-notebooklm` | 5 | 5 |
| 8 | `sources/cowork-vs-claude-code-reddit-apology` | 5 | 4 |
| 9 | `sources/total-recall-write-gated-memory-hn` | 5 | 3 |
| 10 | `concepts/windows-file-locking` | 4 | 3 |
| 11 | `sources/clawmem-gpu-retrieval-memory-hn` | 4 | 3 |
| 12 | `concepts/claude-code-context-limits` | 4 | 2 |
| 13 | `sources/vector-vs-graph-rag-agent-memory` | 4 | 2 |
| 14 | `concepts/claude-code-memory-tooling-landscape` | 4 | 2 |
| 15 | `concepts/flutter-go-messenger-architecture` | 3 | 3 |
| **Top-15 total** | | **81** | **~56 unique** |

[PROJECT] Phase B top-15 = **81 raw / 129 Phase B remaining = 63%** of remaining debt. After Phase B expected: **147 - ~70 = ~77 suggestions remaining** (rough estimate, depends on YES rate). Phase C will deal with long-tail (29 targets, 48 raw).

---

## Contract — how backlink detection actually works

Same as Phase A (verified there). Re-stated for self-containment:

[EMPIRICAL-scripts/lint.py:140-162] `check_missing_backlinks()` checks `content_has_wikilink_target(target_content, source_link)`. Match satisfied iff target's body contains plain `[[<source_slug>]]` or aliased `[[<source_slug>|alias]]`. Simplest compliant edit: add `- [[<source_slug>]]` to target's `## See Also`.

[EMPIRICAL — Phase A wiki article spot-checks] See Also format: plain `- [[slug]]`, optional `— description` suffix. No alias form used.

---

## Lessons from Phase A review (judgment guidance)

[EMPIRICAL — Claude review of `wiki-backlinks-cleanup-phase-a-report.md`] Phase A had **15 NO decisions** of which:

- **10 clearly correct** (66%): structural/topical mismatches — e.g., flutter-deps→pion-webrtc, traffic-SEO→wiki-architecture
- **5 borderline-but-defensible** (33%): cases where source mentions target in passing or via meta-references
- **0 wrong**

**Conservative pattern** that Codex applied in Phase A:
- *"meta/queue/process article" → "topical concept"* — typically NO (e.g., `upstream-feedback-queue-coleam00` was NOed 3 times against various concepts, even where queue's Tier entries explicitly referenced those concepts)
- *"dev environment / tooling UX" → "memory architecture concept"* — typically NO
- *"culture/safety source" → "architecture concept"* — typically NO ("indirect at best")

This is **acceptable conservatism**. For Phase B, same pattern is fine. If Codex feels strongly that a borderline should be YES, document the rationale with one extra sentence.

**Specific watchout**: `concepts/claude-code-memory-tooling-landscape` is a **heavy hub** that references almost everything in the wiki ecosystem. When it's a target (Phase B #14), expect many YES decisions and only NO if source is clearly unrelated to memory tooling.

---

## Mandatory external tools

Every row MUST appear in `## Tools used` of the report with ✅ или explicit `BLOCKED: <reason>` / `not available in environment`. Прочерк недопустим.

| Tool | Purpose | Phase |
|---|---|---|
| **WebFetch** `https://github.github.com/gfm/#lists` | Verify list syntax (re-fetch, do not skip) | Doc verification |
| **WebFetch** `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Verify wikilink syntax (re-fetch) | Doc verification |
| **Read** `scripts/lint.py:140-162` | Backlink check semantics (re-confirm) | Pre-flight |
| **Read** `scripts/utils.py:extract_wikilinks + content_has_wikilink_target` | Match logic (re-confirm) | Pre-flight |
| **Read** `reports/lint-2026-04-14.md` (regenerate first via `uv run python scripts/lint.py --structural-only`) | Authoritative current suggestion list | Pre-flight |
| **Read** `docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md` Phase 5 statistics + sample target decisions | Precedent for similar judgment calls | Pre-flight |
| **Read** every target article before editing (15 articles) | Verify current See Also state | Per-target |
| **Read** every unique source article (estimate: ~56 reads) | Make judgment call per source | Per-target |
| **Bash** `uv run python scripts/lint.py --structural-only` | Pre/post snapshots | Phase 1 |
| **Bash** `uv run python scripts/wiki_cli.py doctor --quick` | Ensure structural_lint stays PASS | Phase 3 |
| **Bash** Python one-liner для group-by-target source listing | Per-target source extraction | Phase 1.5 (per target) |
| **Wiki articles** as context for each target's domain | Required reading | Per-target |
| **MCP filesystem** (if available) | Alternative file ops | optional |
| **MCP git** (if available) | git status verification | optional |

Игнорирование любого tool = halтура.

---

## Per-target workflow (same as Phase A)

For each of the 15 target articles, in the order listed:

### Step 1 — Get current sources for this target

```bash
uv run python -c "
import re
from pathlib import Path
target = 'concepts/claude-cli-autonomous-task-loops'  # change per target
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

`Read` tool. Не skip.

### Step 3 — Decide per source

Heuristics [PROJECT] from Phase A precedent:

- **YES**: source is topically relevant, bidirectional value
- **NO**: tangential mention, meta-reference, structurally different domain
- **SKIP**: daily log (filtered automatically), orphan article scheduled for deletion

Patterns from Phase A:

- `sources/<external-doc>` → `concepts/<our-concept>` — usually YES
- `concepts/<A>` → `concepts/<B>` (cross-cutting) — usually YES
- `analyses/<research>` → `concepts/<concept>` — usually YES
- `entities/<project>` → `concepts/<generic>` — NO unless concept is project-specific
- `<meta-process-queue>` → `<topical-concept>` — NO (Phase A pattern)

### Step 4 — Single Edit to target's See Also

Plain `- [[slug]]` bullets, no alias, no description suffix (consistent with Phase A format).

### Step 5 — Record in report

Per-target section должна содержать:
- Source list
- Decision table (Source / Decision / Reason with `[EMPIRICAL]` marker)
- Edit diff
- Summary (Candidates / YES / NO / SKIP / Resolved)

---

## Whitelist (Phase B scope)

**Only these 15 wiki files** may be edited:

1. `wiki/concepts/claude-cli-autonomous-task-loops.md`
2. `wiki/sources/cognition-rebuilding-devin-sonnet-4-5.md`
3. `wiki/concepts/seo-ai-strategy-2026.md`
4. `wiki/analyses/llm-wiki-improvement-research-2026-04-12.md`
5. `wiki/sources/aris-autonomous-ml-research.md`
6. `wiki/sources/claude-opus-4-6-diagnosis-2026.md`
7. `wiki/sources/seo-ai-strategy-2026-notebooklm.md`
8. `wiki/sources/cowork-vs-claude-code-reddit-apology.md`
9. `wiki/sources/total-recall-write-gated-memory-hn.md`
10. `wiki/concepts/windows-file-locking.md`
11. `wiki/sources/clawmem-gpu-retrieval-memory-hn.md`
12. `wiki/concepts/claude-code-context-limits.md`
13. `wiki/sources/vector-vs-graph-rag-agent-memory.md`
14. `wiki/concepts/claude-code-memory-tooling-landscape.md`
15. `wiki/concepts/flutter-go-messenger-architecture.md`

All 15 gitignored, no commit/push, no CI risk.

**Out-of-scope temptations** (do NOT touch):

- Any other wiki/ article (Phase C will cover targets 16-44)
- Phase A targets (already processed — re-processing creates conflict)
- `scripts/`, `CLAUDE.md`, hooks, doctor-tasks files (except this plan's own report)
- `daily/2026-04-14.md` uncompiled warning (separate task)
- Any wiki content rewriting beyond See Also additions

---

## Verification phases

### Phase 1 — pre-edit lint snapshot

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

Record output. **Expected** [EMPIRICAL — based on Phase A end state]: `Results: 0 errors, 1 warnings, 147 suggestions`.

If significantly different — lint state changed since plan written. **Stop and escalate** to Discrepancies.

### Phase 1.5 — per-target sequential processing

Process the 15 targets in the order in Whitelist. For each:
1. Run Step 1 Python one-liner to get current sources
2. Read all source articles
3. Make YES/NO/SKIP decisions with `[EMPIRICAL]` markers in the report
4. Single Edit to target's See Also section
5. Per-target summary in report

### Phase 2 — post-edit lint snapshot

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

**Expected** [PROJECT]: drop from 147 to roughly **75-90 suggestions remaining** (depends on YES rate; Phase A had 88% YES = 81 raw → 71 resolved expected for Phase B if same rate, leaving 147 - 71 = 76).

Record actual drop. If actual drop < 50 — escalate (low YES rate suggests Codex was too conservative). If drop > 90 — escalate (suggests Codex was too aggressive, blind YES).

### Phase 3 — doctor regression

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep -E "(FAIL|PASS).*(lint|provenance)"
```

**Expected**: `[PASS] structural_lint`, `[PASS] wiki_cli_lint_smoke`, `[PASS] query_preview_smoke`. No regressions.

### Phase 4 — spot-check 3 random targets from the 15

For each chosen target, Read final state, verify:
- Original See Also entries preserved
- New reverse links present
- No duplicates
- Valid markdown

### Phase 5 — decision statistics

Aggregate table same format as Phase A:

| Target | Candidates | YES | NO | SKIP | Resolved |
|---|---|---|---|---|---|

Plus derived metrics:
- Total YES rate
- Comparison to Phase A YES rate (88%)
- Если Phase B YES rate сильно отличается — flag for review

---

## Acceptance criteria

- ✅ Doc verification: 2 URLs re-read (do not skip even though Phase A verified them)
- ✅ Mandatory tools table filled with ✅/BLOCKED — no dashes
- ✅ Phase 1 pre-edit snapshot matches `Results: 0 errors, 1 warnings, 147 suggestions` (или escalate)
- ✅ Each of 15 target articles has decision table with `[EMPIRICAL]` markers per source
- ✅ Each of 15 target articles has exactly one Edit to See Also section
- ✅ Post-edit lint suggestions drop is in expected range (50-90)
- ✅ `doctor --quick` lint/provenance/query checks all PASS
- ✅ Spot-check 3 random targets show correct final state
- ✅ Decision statistics table complete (15 rows + TOTAL + comparison to Phase A YES rate)
- ✅ No files touched outside whitelist
- ✅ No commit / push

---

## Out of scope

- **Phase C** (targets 16-44, 48 raw remaining suggestions): separate handoff after Phase B review
- **Phase A re-processing** (the 18 remaining raw in Phase A targets are intentional NO decisions)
- **Auto-fix script** — explicitly excluded per issue #21 body
- **Daily compile** для `daily/2026-04-14.md`
- **Any `scripts/` or `CLAUDE.md` edits**

---

## Rollback

```bash
# Per target — keep .bak before editing
cp wiki/concepts/<target>.md wiki/concepts/<target>.md.bak
# ... edit ...
# To rollback: mv .bak back

# Delete .bak after task succeeds (Codex handles cleanup, как в Phase A)
```

---

## Pending user actions

After Codex completes Phase B:

1. Review decision statistics — YES rate vs Phase A (88%)
2. Spot-check a few target's final See Also
3. Decide whether to proceed with Phase C (long tail) or close #21 as "good enough" с ~77 acceptable asymmetries

---

## Notes для исполнителя (Codex)

- **This is a continuation of Phase A**, not a new task. Phase A's report is precedent — read its judgment patterns before starting Phase B.
- **Doc verification IS mandatory** even though Phase A already verified the same URLs. Re-fetch. Don't shortcut.
- **Source markers** `[OFFICIAL]` / `[EMPIRICAL]` / `[PROJECT]` on every technical claim. If you find a claim without one in this plan, treat as broken — escalate.
- **Same conservative-judgment approach** as Phase A is OK. Don't over-correct toward more YES just because plan says "borderline-but-defensible".
- **15 files strict whitelist**. No "just one more".
- **NO commit / push**.
- **Keep `.bak`** of each target before editing, delete after success (Phase A pattern).
- **Если реальный lint count при Phase 1 значительно отличается от 147** — план stale, stop escalate.
- **Update existing report или create new** — for Phase B create a NEW report file `wiki-backlinks-cleanup-phase-b-report.md` (do NOT overwrite Phase A's).
- **Placeholder convention** in report: `${USER}`, `<repo-root>`, `<user-home>`.
- **Verifier для самопроверки**: после написания каждого раздела отчёта, прогнать: *"можно ли удалить этот claim и отчёт остаётся consistent?"* Если да — claim из головы, escalate.
- **Если task hangs again** — partial progress в gitignored wiki files OK (Phase A precedent), но обязательно finish report fillout до объявления done. Если завис — recover, finish, then announce.
