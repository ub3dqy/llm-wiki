# Task — Wiki lint cleanup + provenance discipline + telemetry finding integration

> **Роль**: исполнитель — Codex.
>
> **Иерархия источников правды** (СТРОГО):
> 1. **Официальная документация** — primary source of truth для любого утверждения о behavior внешних tools / API / forматов:
>    - GitHub markdown spec: `https://github.github.com/gfm/`
>    - Obsidian wikilink syntax: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`
>    - Python `re` module: `https://docs.python.org/3/library/re.html`
> 2. **Реальное состояние repo** — secondary, верифицируется через Read/Grep/git ls-files:
>    - `<repo-root>/CLAUDE.md` (schema definitions)
>    - `<repo-root>/scripts/lint.py:check_provenance_completeness` (actual behavior)
>    - `<repo-root>/wiki/concepts/upstream-feedback-queue-coleam00.md` (the file with errors)
>    - `<repo-root>/wiki/sources/anthropic-telemetry-experiment-gates-reddit.md` (Subtask E base)
>    - `<repo-root>/reports/lint-2026-04-13.md` (current lint report)
> 3. **Этот план** — derived artifact, написан Claude'ом, может содержать ошибки.
>
> **Расхождение план vs дока ИЛИ план vs реальный код → побеждает дока/код, не план**. Фиксировать в `Discrepancies` секции отчёта.

---

## Source markers used in this plan

Each technical claim in this plan is tagged:
- `[OFFICIAL-<URL>]` — directly from a documentation page (cite URL)
- `[EMPIRICAL-<file:line>]` — observed in a real file in the repo (cite path)
- `[PROJECT]` — own architectural decision of this project (no external authority)

Claims without a marker are **forbidden** in plans. If you find any in this file before executing, treat the plan as broken и эскалируй в Discrepancies.

---

## Doc verification (ОБЯЗАТЕЛЬНО до любых правок)

Codex must re-read the following pages **right now**, not from memory. Fill `Doc verification` section в отчёте with citations:

| URL | What to find | Why |
|---|---|---|
| `https://github.github.com/gfm/#tables-extension-` | How escaping `\|` works inside table cells in GFM | Subtask B may need to add wikilinks inside table cells; need to know exact escape semantics |
| `https://help.obsidian.md/Linking+notes+and+files/Internal+links` | Aliased wikilink syntax `[[target\|alias]]` | Subtask B needs to know whether to use alias form or plain form when adding inbound links |
| `https://docs.python.org/3/library/re.html#re.sub` | `re.sub` semantics для `re.DOTALL` flag | Subtask D backfill cost script uses regex for `## Provenance` detection — need to know edge cases |

If any of the URLs above are unreachable, document как `BLOCKED: <reason>` in the report **and stop** before proceeding with the dependent subtask.

---

## Diagnosis (cross-checked Claude + Codex, both reports filed in chat 2026-04-14)

`uv run python scripts/lint.py --structural-only` сейчас [EMPIRICAL-reports/lint-2026-04-13.md]:
- **2 errors** — оба в `wiki/concepts/upstream-feedback-queue-coleam00.md` [EMPIRICAL]:
  - Missing `confidence` frontmatter field
  - Missing `## Provenance` section
- **6 warnings** — 5 orphan pages + 1 stale daily [EMPIRICAL-reports/lint-2026-04-13.md:lines 16-22]
- **288 suggestions** — missing backlinks (background debt, out of scope, tracked в #21) [EMPIRICAL]

`doctor --quick` падает на `structural_lint` и `wiki_cli_lint_smoke` checks из-за этих 2 errors [EMPIRICAL — Codex's diagnosis report].

### Why the 2 errors happened [EMPIRICAL-scripts/lint.py:181-216]

`scripts/lint.py:check_provenance_completeness` (line 181) фильтрует [EMPIRICAL-scripts/lint.py:190]:
```python
if page_type not in {"concept", "connection"} or not frontmatter_sources_include_prefix(sources, "daily/"):
    continue
```

Концепт `upstream-feedback-queue-coleam00.md` был создан Claude'ом **вручную** (manual synthesis из today's session findings) [PROJECT — Claude session log], но указал в frontmatter [EMPIRICAL — file content]:

```yaml
sources: [docs/codex-tasks/, daily/2026-04-13.md]
```

Префикс `daily/` поставил файл в провенансный фильтр; lint правильно потребовал hygiene fields per [EMPIRICAL-scripts/lint.py:197-214]. Claude не добавил их при создании.

### Systemic gap [PROJECT]

Это **второй такой случай** за сессию (первый — `concepts/upstream-feedback-queue-coleam00.md` сам, написан до этого замечания; см. также chat history). Это указывает на gap:
- `feedback_codex_task_handoff_workflow.md` memory не содержал чёткого правила для manual concept creation (теперь содержит — добавлено в эту же сессию)
- Skill `wiki-save` template не enforce'ит `confidence`/`## Provenance`
- CLAUDE.md schema говорит *"optional for manual ingest"* [EMPIRICAL-CLAUDE.md] — конфликтует с lint behavior [EMPIRICAL-scripts/lint.py:181]

Нужен **prevention layer**, не только одноразовый fix.

---

## Mandatory external tools (ОБЯЗАТЕЛЬНО использовать)

Codex MUST use each of the following at least once during execution. Each must appear in `## Tools used` section отчёта с tick ✅ или explicit `BLOCKED: <reason>` / `not available in environment`. Прочерк недопустим.

| Tool | Purpose | Used in subtask |
|---|---|---|
| **WebFetch** GFM table escape spec | Verify `\|` escape semantics | A, B (if any table edits) |
| **WebFetch** Obsidian wikilink doc | Verify alias syntax | B (when adding inbound links) |
| **WebFetch** Python `re.sub` doc | Verify regex behavior in backfill script | D |
| **Read** `scripts/lint.py:check_provenance_completeness` | Verify actual filter logic before changing it | D |
| **Read** `<repo-root>/CLAUDE.md` schema section про provenance | Verify schema text before proposing change | D |
| **Read** `wiki/concepts/upstream-feedback-queue-coleam00.md` целиком | Before Subtask A edit | A |
| **Read** `wiki/sources/anthropic-telemetry-experiment-gates-reddit.md` целиком | For Subtask E content | E |
| **Read** `wiki/concepts/anthropic-context-anxiety-injection.md` | For Subtask E cross-reference | E |
| **Grep** для location related-articles | Subtask B inbound link target identification | B |
| **Bash** `uv run python scripts/lint.py --structural-only` | Pre/post lint snapshots для каждого subtask | A, B, C, D |
| **Bash** `uv run python scripts/compile.py --file daily/2026-04-13.md` | Subtask C only | C |
| **Wiki articles** для context | `[[concepts/llm-wiki-architecture]]`, `[[concepts/anthropic-context-anxiety-injection]]`, `[[sources/anthropic-telemetry-experiment-gates-reddit]]` | A, B, E |
| **MCP context7** (если доступен) | Альтернативная dependency doc lookup | optional |
| **MCP filesystem** (если доступен) | structured file enumeration | optional |
| **MCP git** (если доступен) | git status / diff via structured API | optional |

Игнорирование любого инструмента из списка above — halтура, не "оптимизация". В отчёт `## Tools used` каждая строка должна быть filled.

---

## Files to modify (whitelist — explicit per subtask)

- **Subtask A**: `wiki/concepts/upstream-feedback-queue-coleam00.md` (gitignored, local only, no commit)
- **Subtask B**: 5 wiki article files (gitignored, no commit) — see Subtask B section
- **Subtask C**: command only (`uv run python scripts/compile.py --file daily/2026-04-13.md`), no file edits expected unless compile creates new wiki articles
- **Subtask D**: `<repo-root>/CLAUDE.md` (tracked, PR-eligible) + `<repo-root>/scripts/lint.py` (tracked, PR-eligible) — **only if user approves** (decision tree below)
- **Subtask E**: `wiki/concepts/upstream-feedback-queue-coleam00.md` (gitignored, can be combined with A in single edit pass)

**Не трогать** (out-of-scope-temptations):
- `scripts/doctor.py` (PR #23 just merged, leave alone)
- `scripts/utils.py` (PR #20 just merged)
- `hooks/codex/stop.py` (PR #18 just merged)
- `pyproject.toml` / dependencies
- `.gitignore`
- Any existing `docs/codex-tasks/*.md` files (except this plan's own report)
- Any `daily/*.md` files (gitignored, but don't touch)

---

## Subtask A — Fix the 2 lint errors (immediate unblock)

### Source markers

- Bug source: [EMPIRICAL-reports/lint-2026-04-13.md:11-12]
- Filter logic: [EMPIRICAL-scripts/lint.py:190]
- Schema authority: [EMPIRICAL-CLAUDE.md] schema section про confidence

### Whitelist

`wiki/concepts/upstream-feedback-queue-coleam00.md` only.

### Action

Edit the article to:

1. **Add `confidence: inferred`** to frontmatter (after `tags:` line). Justification: [PROJECT] the article is manual synthesis across multiple PR findings, не extracted facts из single source; "inferred" — the correct value per [EMPIRICAL-scripts/lint.py:183] which lists `{"extracted", "inferred", "to-verify"}`.
2. **Add `## Provenance` section** at the bottom (before `## See Also`). Use tri-section structure (Extracted facts / Inferred synthesis / To-verify) per [EMPIRICAL-CLAUDE.md] convention used in other concept articles like `wiki/concepts/anthropic-context-anxiety-injection.md`.

Template content for the `## Provenance` section (adapt to actual file structure):

```markdown
## Provenance

- **Confidence: inferred** — manual synthesis Claude'ом of today's wave findings, не compile-generated artifact. Source files в frontmatter — conversation context, не single-source extraction.
- **Extracted facts** (directly observed in repo):
  - Tier 1 #1 (debug_stderr deprecation) — verified via [EMPIRICAL-docs/codex-tasks/remove-dead-debug-stderr-instrumentation-report.md] doc verification section
  - Tier 1 #2 (account-level MCP isolation) — verified via [EMPIRICAL-PR #15 commit f6f162e]
  - Tier 1 #3 (lint wikilink parser bugs) — verified via [EMPIRICAL-PR #20 commit 28002e2]
  - Tier 1 #4 (`<total_tokens>` injection probe) — verified via [EMPIRICAL-PR #23 commit 130c84b]
  - Tier 2 #5 (Codex Stop hook split) — verified via [EMPIRICAL-PR #18 commit 2b75c9a]
- **Inferred synthesis**:
  - Tier breakdown into 1/2/3 — Claude's judgment of "generally applicable" vs "Codex-specific" vs "our ops practice"
  - Suggested form for upstream (PR vs issue vs discussion) — judgment based on bug surface area
- **To-verify** (Pending recon):
  - Active state of upstream `coleam00/claude-memory-compiler` project
  - Whether upstream supports Codex
  - Whether upstream uses `claude_agent_sdk`
  - Whether upstream has a wikilink lint script
- **Not verified**: maintainer responsiveness, time-to-merge for upstream PRs, stylistic preferences
```

### Verification

```bash
# Pre-edit snapshot
uv run python scripts/lint.py --structural-only 2>&1 | grep -E "errors|upstream-feedback" > /tmp/lint-pre-A.txt
cat /tmp/lint-pre-A.txt

# Apply edit (Edit tool, not Bash sed)

# Post-edit snapshot
uv run python scripts/lint.py --structural-only 2>&1 | grep -E "errors|upstream-feedback" > /tmp/lint-post-A.txt
cat /tmp/lint-post-A.txt

# Diff
diff /tmp/lint-pre-A.txt /tmp/lint-post-A.txt
```

**Expected**: pre shows 2 errors mentioning upstream-feedback-queue, post shows 0. The 2 specific provenance errors disappear.

---

## Subtask C — Recompile stale daily

> Выполняется ПЕРЕД Subtask B потому что recompile может создать новые wiki articles which need provenance hygiene check.

### Source markers

- Stale daily: [EMPIRICAL-reports/lint-2026-04-13.md:22]
- Compile semantics: [EMPIRICAL-scripts/compile.py + EMPIRICAL-CLAUDE.md] workflow section

### Action

```bash
uv run python scripts/compile.py --file daily/2026-04-13.md
```

### Verification

```bash
# Did compile create new articles?
ls -lat wiki/concepts/ wiki/connections/ 2>&1 | head -10

# Re-check lint
uv run python scripts/lint.py --structural-only 2>&1 | tail -15
```

**Expected**: stale warning gone. New articles MAY appear; if so, run them through Subtask A logic (verify `confidence` + `## Provenance` present per [EMPIRICAL-scripts/lint.py:181-216]).

**Caveat**: `compile.py` создаёт новые concept articles automatically per [EMPIRICAL-CLAUDE.md] compile workflow. They WILL include `daily/` source reference (because they're compile-generated by definition), so they MUST have provenance hygiene fields. If `compile.py` produces articles without those fields — that's a `compile.py` bug, not your problem to fix in this task. Document it в Discrepancies and move on.

---

## Subtask B — Address 5 orphan page warnings (content linking)

### Source markers

- Orphan list: [EMPIRICAL-reports/lint-2026-04-13.md:16-21]
- Wikilink syntax to use: [OFFICIAL-https://help.obsidian.md/Linking+notes+and+files/Internal+links] — verified в Doc verification phase

### Whitelist

5 wiki article files only (gitignored):
- `wiki/concepts/asyncio-event-loop-patterns.md`
- `wiki/concepts/flutter-dependency-upgrade-waves.md`
- `wiki/sources/flutter-riverpod-vs-bloc-comparison.md`
- `wiki/sources/graperoot-codex-cli-compact-reddit.md`
- `wiki/sources/seo-hacking-side-projects-reddit.md`

Plus the inbound-link target articles, see table below.

### Action — find inbound links from related articles, NOT edit the orphans themselves

For each orphan, identify 1-2 related articles via Grep and add a `[[<orphan-slug>]]` reference в их `See Also` section (или в body text где relevant).

**Suggested mappings** (verify each via Grep on the orphan's actual content + tags before editing the target):

| Orphan | Suggested target | How to verify | Wikilink form |
|---|---|---|---|
| `concepts/asyncio-event-loop-patterns` | `concepts/llm-wiki-architecture` (technological stack section) или `concepts/uv-python-tooling` | `grep -l "asyncio\|async def" wiki/concepts/` | `[[concepts/asyncio-event-loop-patterns]]` |
| `concepts/flutter-dependency-upgrade-waves` | `entities/pulse-messenger` (project context) | `grep -l "flutter" wiki/entities/` | `[[concepts/flutter-dependency-upgrade-waves]]` |
| `sources/flutter-riverpod-vs-bloc-comparison` | `entities/pulse-messenger` или `concepts/agent-memory-production-schema` | `grep -l "flutter\|riverpod" wiki/` | `[[sources/flutter-riverpod-vs-bloc-comparison]]` |
| `sources/graperoot-codex-cli-compact-reddit` | `concepts/claude-code-memory-tooling-landscape` (token reduction tools section) | `grep -l "token reduction\|context management" wiki/concepts/` | `[[sources/graperoot-codex-cli-compact-reddit]]` |
| `sources/seo-hacking-side-projects-reddit` | `concepts/seo-ai-strategy-2026` | `grep -l "seo" wiki/concepts/` | `[[sources/seo-hacking-side-projects-reddit]]` |

**Important**:
1. Do NOT edit the orphans themselves. Edit the **target** article.
2. If a suggested target's content doesn't actually relate to the orphan (verify via Grep на the content), pick a different target or document в отчёт как "no good inbound link target found" and leave the orphan with explicit reasoning.
3. Use plain `[[target]]` form, not aliased form, unless the target name is too long для context.

### Verification

```bash
uv run python scripts/lint.py --structural-only 2>&1 | grep -i orphan
```

**Expected**: orphan warnings drop from 5 to 0 OR a smaller number with explicit reasoning per remaining orphan in the report.

---

## Subtask E — Integrate Boris Cherny telemetry finding into upstream queue

> Combine into single edit pass with Subtask A on the same file (`wiki/concepts/upstream-feedback-queue-coleam00.md`). Apply A first (provenance hygiene), then E (new Tier 1 entry), then save.

### Source markers

- Source article: [EMPIRICAL-wiki/sources/anthropic-telemetry-experiment-gates-reddit.md] (созданный Claude'ом сегодня в этой же сессии)
- Boris Cherny tweet URL: [OFFICIAL-https://x.com/bcherny/status/2043715740080222549?s=20]
- Reddit post: [OFFICIAL-https://www.reddit.com/r/ClaudeAI/comments/1skkc7m/]
- GitHub issue: [OFFICIAL-https://github.com/anthropics/claude-code/issues/47558]
- Concept update: [EMPIRICAL-wiki/concepts/anthropic-context-anxiety-injection.md] (updated Claude'ом сегодня)

### Action — add Tier 1 #5 to the upstream queue

In the `## Tier 1 — generally applicable` section, after item #4 (`<total_tokens>` injection probe), add:

```markdown
### 5. Telemetry-side workaround for Anthropic experiment gates (the gold standard)

**Source**: Boris Cherny tweet `https://x.com/bcherny/status/2043715740080222549?s=20`, ingested today as [[sources/anthropic-telemetry-experiment-gates-reddit]].

Anthropic engineer (Boris Cherny, claude-code lead) confirmed publicly:

> "Separately, when we do this kind of experimentation, we use experiment gates that are cached client-side. When you turn off telemetry we also disable experiment gates -- we do not call home when telemetry is off -- so Claude reads the default value, which is 5m."

**Mechanism**: A/B experiment gates (including `<total_tokens>` injection из #8) кэшируются client-side. Refresh — only via telemetry call-home. Disable telemetry → no call-home → all gates stay at compile-time defaults forever → **permanent immunity** to context anxiety injection и other experimental degradations.

This is **the most generally-applicable finding** of our entire wave. Any project using `claude_agent_sdk` или claude-code in subprocess capture context (which is exactly what coleam00 does) benefits from documenting this workaround. Without it, users at the mercy of unannounced A/B changes.

**Form for upstream**: documentation issue or PR. Не code fix — это configuration / setup recommendation. Suggested: file an issue first to verify they didn't already document this somewhere, then PR a doc snippet if welcomed.

**Reference**: [[sources/anthropic-telemetry-experiment-gates-reddit]] (full provenance), [[concepts/anthropic-context-anxiety-injection]] (updated 2026-04-14 with telemetry workaround section).

**Priority**: ⭐ **highest of Tier 1**. Other Tier 1 items fix individual bugs; this one prevents an entire class of future bugs.
```

Also update the `## Key Points` section count: currently says "9 candidates ... 4 in Tier 1" [EMPIRICAL — verify exact text via Read before edit]. Change to "10 candidates ... 5 in Tier 1".

### Verification

```bash
grep -A2 "Tier 1 #5\|Telemetry-side workaround" wiki/concepts/upstream-feedback-queue-coleam00.md | head -10
```

Should show the new section.

---

## Subtask D — Prevention layer (POLICY DECISION — STOP and ask user)

### Source markers

- Lint filter logic: [EMPIRICAL-scripts/lint.py:181-216]
- CLAUDE.md schema section: [EMPIRICAL-CLAUDE.md] (verify exact text via Read before proposing change)
- Memory file: [EMPIRICAL-<user-home>/.claude/projects/.../memory/feedback_codex_task_handoff_workflow.md]

### The choice (3 options)

#### Option D1 — Stricter lint, simpler schema

**Change**:
- `scripts/lint.py:check_provenance_completeness` line 190 [EMPIRICAL] — remove the `not frontmatter_sources_include_prefix(sources, "daily/")` filter, so all concepts/connections need confidence + Provenance regardless of source prefix
- `CLAUDE.md` schema section [EMPIRICAL — verify exact wording] — change *"optional for manual ingest"* to *"required for all concepts/connections"*

**Pro**: consistent rule, easy to remember, no edge cases
**Con**: stricter, more friction for quick `/wiki-save` on tiny concepts

#### Option D2 — Skill template enforcement

(See plan section earlier.) Skipped because skill file is gitignored per [EMPIRICAL-.gitignore]: `skills/wiki-save/SKILL.md`.

#### Option D3 — Memory feedback rule

**Change**: edit `<user-home>/.claude/projects/.../memory/feedback_codex_task_handoff_workflow.md` to add a "Wiki concept article hygiene" section.

**Pro**: enforces at Claude-behavior level, persists across sessions, no code change
**Con**: relies on Claude reading and following memory (which is unreliable per today's evidence — два залёта за день)

### Recommendation

[PROJECT] **D1 + D3 combined**:
- D1 makes lint rule consistent and catches violations programmatically (defense in depth)
- D3 makes Claude proactively comply at creation time
- Skip D2 because skill file gitignored

**But this is a policy call** — Codex MUST NOT make this decision unilaterally. After presenting и measuring backfill cost, **STOP** before applying.

### Backfill cost measurement (mandatory before deciding)

Run this BEFORE proposing D1:

```bash
uv run python -c "
import sys
sys.path.insert(0, 'scripts')
from utils import list_wiki_articles, parse_frontmatter
from pathlib import Path

count_no_confidence = 0
count_no_provenance = 0
files_to_fix = []
for article in list_wiki_articles():
    fm = parse_frontmatter(article)
    if fm.get('type') not in {'concept', 'connection'}:
        continue
    rel = str(article)
    confidence = fm.get('confidence', '').strip()
    content = article.read_text(encoding='utf-8')
    has_provenance = '\n## Provenance' in content
    if confidence not in {'extracted', 'inferred', 'to-verify'} or not has_provenance:
        files_to_fix.append((rel, confidence, has_provenance))
        if confidence not in {'extracted', 'inferred', 'to-verify'}:
            count_no_confidence += 1
        if not has_provenance:
            count_no_provenance += 1

print(f'Backfill cost if D1 applied:')
print(f'  Concepts/connections missing confidence: {count_no_confidence}')
print(f'  Concepts/connections missing Provenance: {count_no_provenance}')
print(f'  Total files needing edit: {len(files_to_fix)}')
print()
print('Files:')
for f, c, p in files_to_fix[:20]:
    print(f'  {f}: confidence={c!r}, provenance={p}')
"
```

If backfill list > 5 articles — **stop и report** — user may defer policy enforcement.

### **STOP HERE for Subtask D — do not apply, ask user**

- [ ] Backfill cost measured and reported
- [ ] Recommendation written
- [ ] Waiting for user approval before applying any changes to `CLAUDE.md` или `scripts/lint.py`

---

## Acceptance criteria

- ✅ **Doc verification**: 3 URLs above перечитаны, цитаты в отчёте
- ✅ **Mandatory tools**: каждая строка `## Tools used` filled (✅ или explicit BLOCKED)
- ✅ **Subtask A**: lint --structural-only shows 0 errors (was 2). The 2 specific provenance errors gone.
- ✅ **Subtask C**: stale warning resolved OR documented as expected. New compile-created articles checked for provenance hygiene.
- ✅ **Subtask B**: orphan warnings ≤ 5 (was 5). Each remaining orphan documented.
- ✅ **Subtask E**: upstream queue concept has Tier 1 #5 entry, Key Points count updated.
- ✅ **Subtask D**: report contains 3 options + backfill cost, **NOT applied without user approval**.
- ✅ Final `doctor --quick` passes `structural_lint` and `wiki_cli_lint_smoke` (subject to Subtask C).
- ✅ No commits / pushes for any subtask without explicit user approval.

---

## Verification phases (per memory rule)

- **Phase 1 — unit (Codex выполняет sam, в отчёт)**: каждый subtask имеет свой verification block above
- **Phase 2 — integration (`[awaits user]`)**: user sanity-check'аем что Subtask B link choices semantic OK; user approves D1+D3 if presented
- **Phase 3 — statistical (`[awaits 7-day window]`)**: lint rate trends after roll-out (track suggestion count drop after orphan fixes propagate)

---

## Out of scope

- **288 missing-backlink suggestions** — issue #21, separate task
- **Auto-fix script for missing backlinks** — separate enhancement
- **Recompile-everything cleanup** — only the specific stale daily, not full
- **PR #23 enhancement** to make Probe 2 check telemetry state first — separate task
- **Bug H investigation with telemetry off** — separate experimental task (mentioned in [[sources/anthropic-telemetry-experiment-gates-reddit]])
- **Editing the 5 orphan articles themselves** — only edit articles that should link **to** them
- **Rewriting other concept articles to match D1 stricter rule** — only if user approves D1, и then as separate batch operation

---

## Rollback

```bash
# Subtasks A, B, E (wiki edits — gitignored)
# Codex must keep .bak copies before each edit. To rollback: restore .bak.

# Subtask C (compile output — gitignored)
# If compile created bad articles, rm them.

# Subtask D (only if applied — both PR-eligible)
git checkout CLAUDE.md scripts/lint.py
```

---

## Pending user actions

After Codex completes:
1. **Review Subtask D options** and approve/reject D1+D3
2. **Verify** Subtask B orphan link choices (Codex's choices may not match user's mental map)
3. **Decide on PR** for Subtask D if approved
4. **Confirm** Subtask E framing of telemetry workaround

---

## Notes для исполнителя (Codex)

- **THIS PLAN IS ITSELF A REPARATION** for Claude's earlier discipline failure (план был написан без doc verification и source markers, поправлен после user замечания). Apply the structural rules from the new memory section "Plan template — STRUCTURAL CHECKLIST" verbatim.
- **Doc verification is MANDATORY before any edit**. If you skip the WebFetch calls listed above, that's a залёт по дисциплине, не "оптимизация".
- **Source markers** (`[OFFICIAL]` / `[EMPIRICAL]` / `[PROJECT]`) appear throughout this plan. If you find a claim without one, treat it as broken — escalate в Discrepancies, не выполняй blindly.
- **Most subtasks are gitignored wiki edits** — no commit/push, no CI risk. Subtask D is the only one touching tracked files, gated on user approval.
- **Subtask D requires explicit user approval before applying**. STOP after presenting options. Do NOT pick D1 unilaterally.
- **Subtask C may introduce new errors** if `compile.py` creates wiki articles missing provenance hygiene. Watch for this.
- **Don't edit the orphans themselves** — common mistake. Edit articles that SHOULD LINK TO them.
- **Ordering**: A → C → B → E → D (D last, requires user approval).
- **Use placeholders** (`${USER}`, `<repo-root>`, `<user-home>`) per memory rule "Placeholder convention".
- **Создай отчёт** в `docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md` следуя structural checklist из memory rule.
- **Verifier для самопроверки**: после написания каждого раздела отчёта, прогнать checklist из memory rule "Verifier для самопроверки" — для каждого technical claim ask себе: "можно ли удалить и план остаётся consistent?"
