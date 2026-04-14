# Task — Wiki backlinks cleanup Phase C (final 29 target articles)

> **Роль**: исполнитель — Codex. Content review task на gitignored wiki files. **Final phase** of #21 wave (Phase A=10 targets done, Phase B=15 targets done, this Phase C closes the remaining 29).

> **Иерархия источников правды** (СТРОГО):
> 1. **Официальная документация** — primary source of truth:
>    - GitHub Flavored Markdown lists: `https://github.github.com/gfm/#lists`
>    - Obsidian internal links syntax: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`
> 2. **Реальное состояние repo** — secondary:
>    - `<repo-root>/scripts/lint.py:check_missing_backlinks` (function semantics)
>    - `<repo-root>/scripts/utils.py:extract_wikilinks` + `content_has_wikilink_target`
>    - `<repo-root>/reports/lint-2026-04-14.md` (regenerate before reading — lint state may have shifted)
>    - `<repo-root>/docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md` — Phase A precedent
>    - `<repo-root>/docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md` — Phase B precedent
>    - Every target article before editing (Read tool)
>    - Every source article before deciding YES/NO (Read tool)
> 3. **Этот план** — derived artifact, написан Claude'ом, может ошибаться.

> **Расхождение план vs дока ИЛИ план vs реальный lint output → побеждает реальность**. Фиксировать в `Discrepancies`.

---

## Source markers used in this plan

Каждое техническое утверждение помечено: `[OFFICIAL-<URL>]` / `[EMPIRICAL-<file:line>]` / `[PROJECT]`. Без marker — escalate в Discrepancies.

---

## Doc verification (ОБЯЗАТЕЛЬНО до любых правок)

Re-read both pages **right now**, не из памяти. **Don't reuse Phase A/B verification** — re-fetch.

| URL | What to find | Why |
|---|---|---|
| `https://github.github.com/gfm/#lists` | Bullet list syntax | See Also sections |
| `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Plain wikilink syntax | Reverse link format |

Если URL unreachable → `BLOCKED: <reason>` в отчёте, stop dependent subtask.

---

## Diagnosis (fresh empirical data 2026-04-14 после Phase B)

[EMPIRICAL — current `reports/lint-2026-04-14.md` post Phase B]:

- **0 errors**
- **1 warning** — `daily/2026-04-14.md` uncompiled (out of scope)
- **79 missing-backlink suggestions remaining** (was 283 at Phase A start, dropped 72% across Phases A+B)

[EMPIRICAL — grouped analysis post-Phase-B]:
- **52 raw suggestions** в 29 distinct **new targets** (excluding Phases A+B targets)
- **40 unique source→target pairs** (52/40 = 1.3 duplication factor — lower than earlier phases because of long-tail dominance)
- **27 raw remaining в Phase A+B targets** = intentional NOs from previous reviews — **DO NOT re-process**

### Phase C — full target list (29 targets, sorted by raw count desc)

[EMPIRICAL — computed 2026-04-14 после Phase B completion]:

#### Sub-batch C1: targets с raw ≥ 2 (19 targets, 42 raw)

| # | Target | raw | unique sources |
|---|---|---:|---:|
| 1 | `concepts/claude-desktop-cowork-architecture` | 3 | 3 |
| 2 | `sources/great-claude-code-leak-2026` | 3 | 2 |
| 3 | `concepts/fastify-api-framework` | 3 | 2 |
| 4 | `concepts/messenger-docker-infrastructure` | 3 | 2 |
| 5 | `sources/spec-driven-verification-overnight-agents` | 2 | 2 |
| 6 | `entities/agentcorp` | 2 | 2 |
| 7 | `sources/anthropic-scaling-managed-agents` | 2 | 2 |
| 8 | `sources/total-tokens-injection-bug-reddit` | 2 | 2 |
| 9 | `sources/claude-codepro-dev-env-hn` | 2 | 2 |
| 10 | `concepts/pgvector-agent-memory` | 2 | 2 |
| 11 | `concepts/agent-notification-system` | 2 | 1 |
| 12 | `sources/claude-code-vscode-mcp-crash-bug` | 2 | 1 |
| 13 | `concepts/pulse-e2ee-issues` | 2 | 1 |
| 14 | `concepts/pulse-durable-mutations` | 2 | 1 |
| 15 | `sources/calx-corrections-tracking-hn` | 2 | 1 |
| 16 | `sources/ai-seo-statistics-100-plus-2026` | 2 | 1 |
| 17 | `sources/answer-engine-optimization-frase-guide` | 2 | 1 |
| 18 | `sources/geo-aeo-faq-emarketer-2026` | 2 | 1 |
| 19 | `sources/llm-referred-traffic-converts-venturebeat` | 2 | 1 |
| **C1 subtotal** | | **42** | **30** |

#### Sub-batch C2: targets с raw = 1 (10 targets, 10 raw — true long tail)

| # | Target | raw | unique sources |
|---|---|---:|---:|
| 20 | `concepts/uv-python-tooling` | 1 | 1 |
| 21 | `analyses/reddit-hn-research-2026-04-13` | 1 | 1 |
| 22 | `concepts/pulse-testing-methodology` | 1 | 1 |
| 23 | `concepts/jwt-auth-pattern` | 1 | 1 |
| 24 | `sources/claude-code-subagent-orphan-bug` | 1 | 1 |
| 25 | `concepts/agentcorp-domain-model` | 1 | 1 |
| 26 | `sources/mason-context-builder-github` | 1 | 1 |
| 27 | `sources/cloud-coder-overnight-agent-reddit` | 1 | 1 |
| 28 | `sources/recall-mcp-hooks-memory-hn` | 1 | 1 |
| 29 | `sources/alive-five-markdown-files-memory-hn` | 1 | 1 |
| **C2 subtotal** | | **10** | **10** |

[PROJECT] **Realistic outcome** at ~85% YES rate (matching Phase A/B):
- C1: ~36 raw resolved, ~6 raw remaining (NO decisions)
- C2: ~9 raw resolved, ~1 raw remaining
- **Phase C total resolved**: ~45 raw → final lint state **~7 + 27 (intentional from A+B) = ~34 raw**

[PROJECT] Acceptance criteria for #21 was *"≤10 suggestions remaining"* — this was **aspirational** based on earlier estimate. Realistic floor is ~25-35 remaining (intentional asymmetries from A+B+C). #21 should close с note explaining the acceptance criteria was revised based on actual judgment patterns.

---

## Internal sub-batching strategy [PROJECT]

29 targets is large для single Codex pass. Split into two **inner batches** sequentially:

### C1 first (19 targets, raw ≥ 2)

Higher value per target, more decision rationale needed. Process sequentially as listed in C1 table above.

### C2 second (10 targets, raw = 1)

True long tail. Each target has только 1 candidate source. Decision is binary YES/NO с minimal context. Should go faster than C1 — maybe 2-3 min per target vs 5-10 min in C1.

### Recovery point

Если Codex hangs или должен resume — recovery is by target ID. Phase C report's per-target sections are independent. If you complete targets 1-12 then crash, restart from target 13.

---

## Contract — how backlink detection works

[EMPIRICAL-scripts/lint.py:140-162] — same as Phase A/B. Match satisfied iff target's body contains `[[<source_slug>]]` или aliased `[[<source_slug>|alias]]`. Simplest compliant edit: add `- [[<source_slug>]]` to target's `## See Also`.

[EMPIRICAL — Phase A+B observed See Also format] Plain `- [[slug]]` bullets, optional `— description` suffix. No alias form used.

---

## Lessons from Phase A+B reviews [PROJECT]

[EMPIRICAL — Claude review of both phase reports] Combined judgment patterns observed in 23 NO decisions across A+B:

**Conservative-but-mostly-positive pattern** (84% Phase A YES, 85.7% Phase B YES):

- **"meta/queue/process article" → "topical concept"** = NO (Phase A and Phase B both NOed `upstream-feedback-queue-coleam00` against various concepts)
- **"dev environment / tooling UX" → "memory architecture"** = NO
- **"safety/culture source" → "architecture concept"** = NO ("indirect at best")
- **"too narrow scope source" → "broad scope target"** = NO
- **"implementation-specific detail" → "high-level abstraction"** = NO

**Common YES pattern**:
- `sources/<external-doc>` → `concepts/<our-concept>` — usually YES (concept enriches its bibliography)
- `concepts/<A>` → `concepts/<B>` (cross-cutting) — usually YES
- `analyses/<research>` → any topical target — usually YES
- `entities/<project>` → `concepts/<project-specific>` — YES if relevant

**Phase C-specific watchouts**:
- Many Phase C targets are `sources/seo-*` and `concepts/pulse-*` — these are **project-scoped** (personal SEO domain, messenger project domain). Sources should reverse-link only if topically aligned, не just because they're in same project.
- Several SEO sources cross-link to multiple SEO concepts → likely all YES (consistent SEO knowledge cluster)
- Several Pulse messenger concepts cross-link to other messenger concepts → likely all YES
- `concepts/agent-notification-system` and `concepts/jwt-auth-pattern` are very specific implementation patterns — sources linking to them usually have YES asymmetry (source mentions feature, target is the feature's spec)

---

## Mandatory external tools

Каждая строка MUST appear в `## Tools used` отчёта с ✅ или explicit `BLOCKED: <reason>` / `not available in environment`. Прочерк недопустим.

| Tool | Purpose | Phase |
|---|---|---|
| **WebFetch** `https://github.github.com/gfm/#lists` | Verify list syntax (re-fetch) | Doc verification |
| **WebFetch** `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Verify wikilink syntax (re-fetch) | Doc verification |
| **Read** `scripts/lint.py:140-162` | Re-confirm backlink check semantics | Pre-flight |
| **Read** `scripts/utils.py:extract_wikilinks + content_has_wikilink_target` | Re-confirm match logic | Pre-flight |
| **Read** `reports/lint-2026-04-14.md` (regenerate first via lint.py) | Authoritative current suggestion list | Pre-flight |
| **Read** `docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md` | Phase A precedent для judgment patterns | Pre-flight |
| **Read** `docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md` | Phase B precedent | Pre-flight |
| **Read** every target article before editing (29 articles) | Verify current See Also state | Per-target |
| **Read** every unique source article (estimate ~40 reads) | Make judgment call | Per-target |
| **Bash** `uv run python scripts/lint.py --structural-only` | Pre/post snapshots | Phase 1 |
| **Bash** `uv run python scripts/wiki_cli.py doctor --quick` | Ensure structural_lint stays PASS | Phase 3 |
| **Bash** Python one-liners для per-target source listing | Per-target source extraction | Per-target |
| **Wiki articles** as context for each target's domain | Required reading | Per-target |
| **MCP filesystem** (if available) | Alternative file ops | optional |
| **MCP git** (if available) | git status verification | optional |

Игнорирование любого tool = halтура.

---

## Per-target workflow (same as Phase A/B)

For each of 29 targets, in order C1 → C2:

1. Run Python one-liner для current sources of this target
2. Read each unique source article
3. Decide per source с `[EMPIRICAL]` reason marker
4. Single Edit to target's See Also
5. Per-target summary в report

### Step 1 template

```bash
uv run python -c "
import re
from pathlib import Path
target = 'concepts/claude-desktop-cowork-architecture'  # change per target
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

### Step 4 template

Single Edit to target's See Also section, plain `- [[slug]]` bullets, no alias, no description suffix.

### Step 5 template

Per-target section в report:
- Source list (one per line in code block)
- Decision table (Source / Decision / Reason с `[EMPIRICAL]` marker)
- Edit diff
- Summary line: `Candidates N | YES N | NO N | SKIP N | Resolved N`

For C2 targets с raw=1 единственный candidate, simpler form OK:
```markdown
### N. `target-slug`
Source: `source-slug`
Decision: YES (or NO)
Reason: `[EMPIRICAL]` one-line reason
Edit: `+ [[source-slug]]` to See Also
```

---

## Whitelist (Phase C scope — full 29 files)

**Only these 29 wiki files** may be edited:

### C1 (raw≥2):
1. `wiki/concepts/claude-desktop-cowork-architecture.md`
2. `wiki/sources/great-claude-code-leak-2026.md`
3. `wiki/concepts/fastify-api-framework.md`
4. `wiki/concepts/messenger-docker-infrastructure.md`
5. `wiki/sources/spec-driven-verification-overnight-agents.md`
6. `wiki/entities/agentcorp.md`
7. `wiki/sources/anthropic-scaling-managed-agents.md`
8. `wiki/sources/total-tokens-injection-bug-reddit.md`
9. `wiki/sources/claude-codepro-dev-env-hn.md`
10. `wiki/concepts/pgvector-agent-memory.md`
11. `wiki/concepts/agent-notification-system.md`
12. `wiki/sources/claude-code-vscode-mcp-crash-bug.md`
13. `wiki/concepts/pulse-e2ee-issues.md`
14. `wiki/concepts/pulse-durable-mutations.md`
15. `wiki/sources/calx-corrections-tracking-hn.md`
16. `wiki/sources/ai-seo-statistics-100-plus-2026.md`
17. `wiki/sources/answer-engine-optimization-frase-guide.md`
18. `wiki/sources/geo-aeo-faq-emarketer-2026.md`
19. `wiki/sources/llm-referred-traffic-converts-venturebeat.md`

### C2 (raw=1):
20. `wiki/concepts/uv-python-tooling.md`
21. `wiki/analyses/reddit-hn-research-2026-04-13.md`
22. `wiki/concepts/pulse-testing-methodology.md`
23. `wiki/concepts/jwt-auth-pattern.md`
24. `wiki/sources/claude-code-subagent-orphan-bug.md`
25. `wiki/concepts/agentcorp-domain-model.md`
26. `wiki/sources/mason-context-builder-github.md`
27. `wiki/sources/cloud-coder-overnight-agent-reddit.md`
28. `wiki/sources/recall-mcp-hooks-memory-hn.md`
29. `wiki/sources/alive-five-markdown-files-memory-hn.md`

All 29 gitignored, no commit/push, no CI risk.

**Out-of-scope temptations** (do NOT touch):
- Phase A targets (10) — already processed, intentional NOs preserved
- Phase B targets (15) — already processed, intentional NOs preserved
- Any other wiki/ article not in 29 list above
- `scripts/`, `CLAUDE.md`, hooks, doctor — code/config out of scope
- `daily/2026-04-14.md` uncompiled warning — separate task
- Any wiki content rewriting beyond See Also additions
- New source articles I created for Anthropic docs ingest wave (`sources/anthropic-*-engineering.md`, `sources/anthropic-*-news.md`, `sources/anthropic-*-docs.md`, `concepts/anthropic-documentation-index.md`) — these are **NEW** in current session, may have appeared after lint snapshot, и не в Phase C target list anyway

---

## Verification phases

### Phase 1 — pre-edit lint snapshot

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

**Expected** [EMPIRICAL — based on Phase B end state]: `Results: 0 errors, 1 warnings, 79 suggestions`.

If significantly different — lint state shifted. Stop, escalate в Discrepancies.

### Phase 1.5 — per-target sequential processing (29 targets)

Process в order: C1 (1-19) → C2 (20-29). Per-target workflow as above.

### Phase 2 — post-edit lint snapshot

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

**Expected** [PROJECT]: drop from 79 to **~30-35 suggestions remaining** (depends on YES rate; Phase A+B averaged 84-86% YES = ~45 raw resolved expected, leaving ~34).

If actual drop < 30 — too conservative, escalate. If actual drop > 50 — too aggressive (likely missed NO decisions), escalate.

### Phase 3 — doctor regression

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep -E "(FAIL|PASS).*(lint|provenance|query)"
```

**Expected**: `[PASS] structural_lint`, `[PASS] wiki_cli_lint_smoke`, `[PASS] query_preview_smoke`. No regressions.

### Phase 4 — spot-check 5 random targets (more than Phase A/B due to larger scope)

For 5 randomly-chosen targets (mix from C1 + C2), Read final state, verify:
- Original See Also entries preserved
- New reverse links present (or zero new links if all NO — note этот case)
- No duplicates
- Valid markdown

### Phase 5 — decision statistics

Aggregate table same format as Phase A/B:

| Target | Candidates | YES | NO | SKIP | Resolved |
|---|---|---|---|---|---|

Plus derived metrics:
- C1 subtotal vs C2 subtotal
- Total YES rate
- Comparison to Phase A (84%) и Phase B (85.7%)
- Если Phase C YES rate сильно отличается — flag for review в notes

### Phase 6 — closure summary

В отчёт add секцию "## Closure summary for issue #21":

- Phase A processed 10 targets (88% fix rate, 136 raw resolved)
- Phase B processed 15 targets (Phase B YES rate, 68 raw resolved)
- Phase C processed 29 targets (this phase's stats)
- **Cumulative**: <total> raw suggestions resolved из original 283 (X% reduction)
- **Final state**: <N> suggestions remaining as **intentional asymmetries** (sum of all NO decisions across A+B+C)
- **Acceptance criteria revision**: original "≤10 remaining" was aspirational. Realistic floor based on actual judgment patterns is the cumulative NO count = ~30. Issue #21 should close с this revised criteria explained.

---

## Acceptance criteria

- ✅ Doc verification: 2 URLs re-read with citations
- ✅ Mandatory tools table filled with ✅/BLOCKED — no dashes
- ✅ Phase 1 pre-edit snapshot matches `0 errors, 1 warning, 79 suggestions` (или escalate)
- ✅ Each of 29 target articles has decision documentation в report (table for C1, simplified for C2)
- ✅ Each of 29 target articles has exactly one Edit to See Also (or explicit "all NO, no edit" note)
- ✅ Post-edit lint suggestions drop в expected range (30-50 raw resolved)
- ✅ `doctor --quick` lint/provenance/query all PASS
- ✅ Spot-check 5 random targets show correct final state
- ✅ Decision statistics complete (29 rows + C1 subtotal + C2 subtotal + grand TOTAL + Phase comparison)
- ✅ Closure summary section drafted for #21
- ✅ No files touched outside whitelist
- ✅ No commit / push

---

## Out of scope

- **Phase A or B target re-processing** — those intentional NOs стay as-is
- **Auto-fix script** — issue #21 explicitly excluded
- **Daily compile** для `daily/2026-04-14.md` (separate task)
- **Any `scripts/` or `CLAUDE.md` edits**
- **New wiki articles** of any type — only edits к existing 29 targets in whitelist
- **Closing issue #21 на GitHub** — that's user's call после reviewing Phase C report

---

## Rollback

```bash
# Per target — keep .bak before editing
cp wiki/concepts/<target>.md wiki/concepts/<target>.md.bak
# ... edit ...
# To rollback: mv .bak back

# Delete all .bak after task succeeds
```

---

## Pending user actions

After Codex completes Phase C:

1. Review decision statistics — YES rate vs Phase A (84%) и Phase B (85.7%)
2. Spot-check 5-10 target's final See Also
3. Decide whether to **close #21** with revised acceptance criteria, or push for tighter fit
4. (Optional) Comment on #21 with cumulative summary across all 3 phases

---

## Notes для исполнителя (Codex)

- **This is the final phase of #21 wave**. Goal is closure-ready state, не perfection.
- **Doc verification IS mandatory** even though Phase A+B already verified the same URLs. Re-fetch.
- **Source markers** `[OFFICIAL]` / `[EMPIRICAL]` / `[PROJECT]` on every claim. Если find a claim без one — escalate.
- **Same conservative-judgment approach as Phase A+B** is OK and expected. Don't over-correct.
- **29 files strict whitelist**. Process в order C1 → C2.
- **C2 simpler format OK** — single source per target, simpler decision documentation.
- **NO commit / push**.
- **Keep `.bak`** of each target before editing, delete после success.
- **Если реальный lint count при Phase 1 != 79** — план stale, stop escalate.
- **Create NEW report** `wiki-backlinks-cleanup-phase-c-report.md` (do NOT overwrite Phase A или Phase B reports).
- **Placeholder convention** в report: `${USER}`, `<repo-root>`, `<user-home>`.
- **Verifier для самопроверки**: после написания каждого раздела отчёта, ask: *"можно ли удалить этот claim и отчёт остаётся consistent?"* Если да — claim из головы, escalate.
- **Recovery point** if hang: each target section is independent. Resume from next un-processed target ID.
- **Closure summary section** в Phase 6 — это deliverable для user's review of full #21 wave.
