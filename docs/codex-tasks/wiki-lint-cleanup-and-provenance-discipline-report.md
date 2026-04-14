# Report — Wiki lint cleanup + provenance discipline + telemetry finding integration

> Filled during execution. Tracked-file policy changes were **not** applied. This report stops at Subtask D and waits for user approval.

---

## Pre-flight

- [x] Read `docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md` fully
- [x] Read `scripts/lint.py:check_provenance_completeness` before editing
- [x] Read `wiki/concepts/upstream-feedback-queue-coleam00.md` before Subtask A
- [x] Read `wiki/sources/anthropic-telemetry-experiment-gates-reddit.md` before Subtask E
- [x] Read `wiki/concepts/anthropic-context-anxiety-injection.md` before Subtask E
- [x] Read `wiki/concepts/llm-wiki-architecture.md` per mandatory wiki-context row
- [x] Understood that Subtask D requires explicit user approval and must stop before tracked changes
- [x] Understood that Subtasks A/B/C/E operate on gitignored files only

---

## Doc verification

- [x] [OFFICIAL] GFM tables spec re-read now: `https://github.github.com/gfm/`
  - Evidence: Example 200 says a pipe can be included in a table cell by escaping it:
    ```text
    Include a pipe in a cell’s content by escaping it, including inside other inline spans:
    | f\|oo  |
    ...
    <th>f|oo</th>
    ```
- [x] [OFFICIAL] Obsidian internal links doc re-read now: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`
  - Evidence from the official published markdown:
    ```text
    Wikilink format:
    Use a vertical bar (`|`) to change the display text.
    - [[Example|Custom name]]
    - [[Example#Details|Section name]]
    ```
- [x] [OFFICIAL] Python `re` doc re-read now: `https://docs.python.org/3/library/re.html#re.sub`
  - Evidence:
    ```text
    (Dot.) In the default mode, this matches any character except a newline.
    If the DOTALL flag has been specified, this matches any character including a newline.
    ```
  - [OFFICIAL] This was sufficient to validate the DOTALL/newline semantics relevant to the plan’s regex note.

---

## Initial state

### Lint output before any changes

Command run before edits:

```bash
uv run python scripts/lint.py --structural-only
```

Output:

```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 5 issue(s)
  Checking: Orphan sources...
    Found 0 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Missing backlinks...
    Found 288 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 2 issue(s)
Results: 2 errors, 6 warnings, 288 suggestions
```

### `doctor --quick` before

Blocked from capturing a clean pre-edit snapshot after the required Bash phase, because [EMPIRICAL] the WSL Bash run recreated `<repo-root>/.venv` as a Linux env and broke subsequent Windows `uv run` with:

```text
error: failed to remove file `<repo-root>/.venv/lib64`: Отказано в доступе. (os error 5)
```

[EMPIRICAL] The environment was repaired later by rebuilding `<repo-root>/.venv` as a Windows env before final verification.

---

## Subtask A — Fix the 2 lint errors in upstream-feedback-queue-coleam00.md

### Pre-edit state of the file's frontmatter

From the `.bak` copy kept before editing:

```yaml
---
title: Upstream Feedback Queue — coleam00/claude-memory-compiler
type: concept
created: 2026-04-14
updated: 2026-04-14
sources: [docs/codex-tasks/, daily/2026-04-13.md]
project: memory-claude
tags: [upstream, feedback, coleam00, claude-memory-compiler, deferred, queue]
---
```

### Diff applied

```diff
diff --git a/wiki/concepts/upstream-feedback-queue-coleam00.md.bak b/wiki/concepts/upstream-feedback-queue-coleam00.md
@@ -6,6 +6,7 @@ updated: 2026-04-14
 sources: [docs/codex-tasks/, daily/2026-04-13.md]
 project: memory-claude
 tags: [upstream, feedback, coleam00, claude-memory-compiler, deferred, queue]
+confidence: inferred
@@ -149,6 +168,29 @@
+## Provenance
+
+- **Confidence: inferred** — это не compile-generated article, а ручная сводка из сегодняшней reliability wave на основе execution reports, wiki updates и session findings.
+- **Extracted facts**:
+  - `debug_stderr` в Agent SDK deprecated и замещается `stderr=` callback path.
+  - `strict-mcp-config` устраняет subprocess exposure к account-level MCP discovery в нашем Agent SDK path.
+  - lint false positives вокруг wikilinks были исправлены через `extract_wikilinks` и shared parser reuse.
+  - `total_tokens` injection probe добавлен как отдельная doctor-проверка и обсуждается как generally applicable finding.
+  - split light/worker pattern для Codex Stop hook уже реализован у нас и подтверждён живыми логами.
+- **Inferred synthesis**:
+  - tier breakdown into 1 / 2 / 3 is a judgment call about upstream applicability, not a fact extracted from a single source.
+  - suggested upstream form (PR vs issue vs discussion) is based on expected maintainer effort and surface area.
+  - prioritization reflects our view of what is most portable upstream, not maintainer-confirmed demand.
+- **To-verify**:
+  - current activity level of `coleam00/claude-memory-compiler`
+  - whether upstream supports Codex at all
+  - whether upstream uses `claude_agent_sdk` in the same subprocess pattern
+  - whether upstream has a comparable wikilink lint pipeline that would benefit from the parser fixes
```

### Post-edit lint check

```text
Results: 0 errors, 6 warnings, 288 suggestions
```

### Verdict

- [x] `confidence: inferred` added to frontmatter
- [x] `## Provenance` section added before `## See Also`
- [x] Provenance section has Extracted / Inferred / To-verify structure
- [x] Lint errors dropped by 2 (from 2 to 0)

---

## Subtask C — Recompile stale daily

### Command

```bash
uv run python scripts/compile.py --file daily/2026-04-13.md
```

### Output

```text
Compiled 1 file(s)
Cost: $1.0212
Compilation complete. Total cost: $1.02
Knowledge base: 86 articles
```

### New articles created / updated

Recent concept files after compile:

```text
.\wiki\concepts\pulse-testing-methodology.md
.\wiki\concepts\codex-stop-hook-reliability.md
.\wiki\concepts\mcp-infrastructure-security.md
```

[EMPIRICAL] These compile-created/updated concept files were checked and already contained both `confidence` frontmatter and `## Provenance`.

### Post-compile lint check

```text
Results: 0 errors, 5 warnings, 292 suggestions
```

### Verdict

- [x] `compile.py` ran successfully
- [x] Stale daily warning was resolved
- [x] Compile-created / compile-updated concept files passed provenance hygiene checks

---

## Subtask B — Address 5 orphan page warnings

### Plan-vs-actual mapping

| Orphan | Plan suggested link from | Actual link from | Reasoning if changed |
|---|---|---|---|
| `concepts/asyncio-event-loop-patterns` | `concepts/llm-wiki-architecture` or `concepts/uv-python-tooling` | `concepts/uv-python-tooling` | [EMPIRICAL] direct tooling/runtime adjacency |
| `concepts/flutter-dependency-upgrade-waves` | `entities/pulse-messenger` | `entities/pulse-messenger` | matched plan |
| `sources/flutter-riverpod-vs-bloc-comparison` | `entities/pulse-messenger` | `entities/pulse-messenger` | matched plan |
| `sources/graperoot-codex-cli-compact-reddit` | `concepts/claude-code-memory-tooling-landscape` | `concepts/claude-code-memory-tooling-landscape` | matched plan |
| `sources/seo-hacking-side-projects-reddit` | `concepts/seo-ai-strategy-2026` | `concepts/seo-ai-strategy-2026` | matched plan |

### Grep / target identification evidence

[EMPIRICAL] Target choices were based on real file content review plus targeted search among related articles. No orphan file was edited directly.

### Diffs applied

`wiki/concepts/uv-python-tooling.md`

```diff
@@ -49,5 +49,6 @@
 - [[concepts/llm-wiki-architecture]]
 - [[concepts/claude-code-hooks]]
+- [[concepts/asyncio-event-loop-patterns]]
 - [[concepts/windows-path-issues]]
 - [[analyses/llm-wiki-improvement-research-2026-04-12]]
```

`wiki/entities/pulse-messenger.md`

```diff
@@ -34,6 +34,8 @@
+Отдельно для Flutter-слоя накопились практические заметки не только по runtime, но и по evolution decisions: [[concepts/flutter-dependency-upgrade-waves]] фиксирует безопасный паттерн dependency-upgrade волн, а [[sources/flutter-riverpod-vs-bloc-comparison]] полезен как reference по state-management trade-offs.
@@ -57,6 +59,8 @@
+- [[concepts/flutter-dependency-upgrade-waves]]
+- [[sources/flutter-riverpod-vs-bloc-comparison]]
```

`wiki/concepts/claude-code-memory-tooling-landscape.md`

```diff
@@ -147,6 +147,7 @@
 - [[concepts/llm-wiki-architecture]] — наш инстанс этого класса систем
 - [[concepts/claude-code-hooks]] — hook infrastructure which all tools use
+- [[sources/graperoot-codex-cli-compact-reddit]] — live action-graph angle on retrieval vs memory
 - [[concepts/claude-cli-autonomous-task-loops]] — adjacent pattern "Claude processes Claude" (coding context)
```

`wiki/concepts/seo-ai-strategy-2026.md`

```diff
@@ -95,4 +95,5 @@
 - [[sources/seo-ai-strategy-2026-notebooklm]]
+- [[sources/seo-hacking-side-projects-reddit]]
 - [[overview]] — обзор всех крупных веток знаний в текущей wiki
```

### Post-edit lint check

```text
Checking: Orphan pages...
  Found 0 issue(s)
Results: 0 errors, 0 warnings, 283 suggestions
```

### Verdict

- [x] Each orphan got a new inbound link from a related target article
- [x] Orphan warnings were reduced from 5 to 0

---

## Subtask E — Add Tier 1 #5 (telemetry workaround) to upstream queue

### Pre-edit state of Tier 1 section

From the `.bak` copy:

```text
## Tier 1 — generally applicable

### 1. `debug_stderr` deprecation + `stderr=` callback pattern
...
### 4. `<total_tokens>` injection probe
...
## Tier 2 — architectural, applicable если supports Codex
```

### Diff applied

```diff
@@ -14,8 +15,8 @@
- - 9 candidates разбиты на 3 tier'а по applicability к upstream
- - 4 в Tier 1 (generally applicable, low upstream-knowledge requirement)
+ - 10 candidates разбиты на 3 tier'а по applicability к upstream
+ - 5 в Tier 1 (generally applicable, low upstream-knowledge requirement)
@@ -74,6 +75,24 @@
+### 5. Telemetry-side workaround for Anthropic experiment gates (the gold standard)
+
+**Source**: Boris Cherny tweet `https://x.com/bcherny/status/2043715740080222549?s=20`, ingested today as [[sources/anthropic-telemetry-experiment-gates-reddit]].
+...
+**Reference**: [[sources/anthropic-telemetry-experiment-gates-reddit]] (full provenance), [[concepts/anthropic-context-anxiety-injection]] (updated with telemetry-side workaround).
+**Priority**: highest of Tier 1.
```

### Post-edit verification

```text
- 10 candidates разбиты на 3 tier'а по applicability к upstream
- 5 в Tier 1 (generally applicable, low upstream-knowledge requirement)
### 5. Telemetry-side workaround for Anthropic experiment gates (the gold standard)
**Source**: Boris Cherny tweet `https://x.com/bcherny/status/2043715740080222549?s=20`, ingested today as [[sources/anthropic-telemetry-experiment-gates-reddit]].
**Reference**: [[sources/anthropic-telemetry-experiment-gates-reddit]] (full provenance), [[concepts/anthropic-context-anxiety-injection]] (updated with telemetry-side workaround).
```

### Verdict

- [x] Tier 1 #5 added with Boris Cherny telemetry finding
- [x] Key Points count updated from 4 to 5 in Tier 1
- [x] Cross-references to `[[sources/anthropic-telemetry-experiment-gates-reddit]]` and `[[concepts/anthropic-context-anxiety-injection]]` are present

---

## Subtask D — Prevention layer (POLICY DECISION)

> **STOP POINT**: no tracked-file changes were applied. This section only measures cost and presents options.

### Three options analysis

#### Option D1 — Stricter lint, simpler schema

[PROJECT] Change the rule so *all* concept/connection pages require valid `confidence` + `## Provenance`, then align `CLAUDE.md` wording with that rule.

Tracked files that would change if approved:
- `scripts/lint.py`
- `CLAUDE.md`

Backfill cost measurement:

```text
Backfill cost if D1 applied:
  Concepts/connections missing confidence: 0
  Concepts/connections missing Provenance: 0
  Total files needing edit: 0

Files:
```

[EMPIRICAL] Current backfill cost is zero.

#### Option D2 — Skill template enforcement

[PROJECT] Not applied here. The plan itself marks this as effectively skipped because the relevant skill template path is not part of the allowed tracked-file change set for this task.

#### Option D3 — Memory feedback rule

[PROJECT] Add / tighten the concept-article hygiene reminder in `<user-home>/.claude/projects/.../memory/feedback_codex_task_handoff_workflow.md`.

Tracked repo files affected:
- none

Local user-memory files affected:
- one memory file under `<user-home>`

### Recommendation

[PROJECT] Because the measured backfill cost is **0**, D1 is now much less risky than it looked when the plan was written. My recommendation is:

1. **D1 now** — it makes the rule consistent between `CLAUDE.md` and `scripts/lint.py`, with zero backfill burden.
2. **D3 optionally after that** — useful as a behavioral reminder, but weaker than D1 because it still depends on the model obeying memory.

### **STOP HERE — waiting for user approval**

- [x] Backfill cost measured
- [x] Recommendation written
- [x] No tracked-file changes applied
- [x] Waiting for user approval before touching `CLAUDE.md` or `scripts/lint.py`

### Continuation — D1 applied after approval

[PROJECT] User later approved **D1 + D3**. D3 was handled outside the repo. This continuation applied **D1 only** in the tracked files allowed by the continuation plan.

`scripts/lint.py`

```diff
@@
-def check_provenance_completeness() -> list[dict]:
-    """Check compile-generated articles for confidence and Provenance metadata."""
+def check_provenance_completeness() -> list[dict]:
+    """Check concept/connection articles for confidence and Provenance metadata."""
@@
-        if page_type not in {"concept", "connection"} or not frontmatter_sources_include_prefix(sources, "daily/"):
+        if page_type not in {"concept", "connection"}:
             continue
@@
-                    "Compile-generated article must have confidence: "
+                    "Concept/connection article must have confidence: "
                     "extracted | inferred | to-verify"
@@
-                "detail": "Compile-generated article must include a ## Provenance section",
+                "detail": "Concept/connection article must include a ## Provenance section",
```

`CLAUDE.md`

```diff
@@
-`confidence` is optional for manual ingest pages, but **required for compile-generated
-concepts/connections** from `daily/`.
+`confidence` is **required for all concept and connection pages**. Source/entity/analysis/qa
+pages may omit it when the field would not add useful signal.
@@
-- **Confidence labels**: compile-generated articles should declare whether claims are
+- **Confidence labels**: all concept and connection articles should declare whether claims are
   `extracted`, `inferred`, or `to-verify`.
-- **Provenance section**: compile-generated articles should include a short `## Provenance`
-  section that explains what was directly observed in the source log and what was inferred.
+- **Provenance section**: all concept and connection articles should include a short
+  `## Provenance` section that explains what was directly observed in the source material and
+  what was inferred.
@@
-7. **Provenance completeness** — compile-generated concepts/connections from `daily/`
+7. **Provenance completeness** — concept and connection pages
   must have valid `confidence` and `## Provenance`
```

[EMPIRICAL] The continuation plan asked for Bash pre/post lint snapshots. Pre-snapshot Bash succeeded, but post-snapshot Bash was **BLOCKED** because WSL tried to resolve the repo through the Windows-only `.venv` and failed with:

```text
FileNotFoundError: [Errno 2] No such file or directory: '<repo-root>/.venv/lib/python3.14/site-packages/dotenv/parser.py'
```

[EMPIRICAL] I restored `<repo-root>/.venv` to a Windows env after that probe. Final verification below therefore uses Windows `uv run`, while keeping the blocked Bash evidence in the report.

---

## Final state

### Lint output after A + B + C + E + approved D1

```text
Results: 0 errors, 1 warnings, 283 suggestions
```

### `doctor --quick` after (lint-related checks)

```text
[PASS] structural_lint: Results: 0 errors, 1 warnings, 283 suggestions
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
```

### Why warning count became 1 again

[EMPIRICAL] After D1, the warning was not caused by the policy change. The current lint report shows:

```text
- **[!]** `daily/2026-04-14.md` — Uncompiled daily log: 2026-04-14.md has not been ingested
```

[PROJECT] This is a fresh daily-log warning that appeared because the date rolled forward during the task. It is unrelated to provenance enforcement and does not indicate a D1 regression.

### `doctor --quick` note

[EMPIRICAL] The full `wiki_cli doctor --quick` command still reports index freshness failures unrelated to this task:

```text
[FAIL] index_health: Index is out of date. Run without --check to rebuild.
[FAIL] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check did not confirm index freshness
```

[PROJECT] I am not fixing that here because this task is explicitly about lint cleanup + provenance discipline, and the plan did not authorize extra tracked-file or workflow changes.

### `git status`

```text
 M CLAUDE.md
 M scripts/lint.py
?? Untitled.md
?? docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md
?? docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md
?? docs/codex-tasks/wiki-lint-cleanup-d1-continuation.md
```

[EMPIRICAL] Wiki edits do not appear in `git status` because `wiki/` is gitignored in this repo.

### Files touched (gitignored)

| File | Subtask | Action |
|---|---|---|
| `wiki/concepts/upstream-feedback-queue-coleam00.md` | A + E | edit |
| `wiki/concepts/uv-python-tooling.md` | B | edit |
| `wiki/entities/pulse-messenger.md` | B | edit |
| `wiki/concepts/claude-code-memory-tooling-landscape.md` | B | edit |
| `wiki/concepts/seo-ai-strategy-2026.md` | B | edit |
| `scripts/lint.py` | D1 continuation | edit |
| `CLAUDE.md` | D1 continuation | edit |

---

## Tools used

| Tool from plan | Status | Evidence / note |
|---|---|---|
| WebFetch — GFM table escape spec | ✅ | Re-read official GFM spec; Example 200 confirms escaped `\|` becomes literal `|` in a table cell |
| WebFetch — Obsidian wikilink doc | ✅ | Re-read official Obsidian internal links doc; `[[Example|Custom name]]` confirmed |
| WebFetch — Python `re.sub` doc | ✅ | Re-read official Python `re` doc; DOTALL/newline semantics confirmed |
| Read `scripts/lint.py:check_provenance_completeness` | ✅ | Done before edits |
| Read `<repo-root>/CLAUDE.md` provenance schema | ✅ | Done before D recommendation |
| Read `wiki/concepts/upstream-feedback-queue-coleam00.md` | ✅ | Done before A/E |
| Read `wiki/sources/anthropic-telemetry-experiment-gates-reddit.md` | ✅ | Done before E |
| Read `wiki/concepts/anthropic-context-anxiety-injection.md` | ✅ | Done before E |
| Grep for related articles / orphan targets | ✅ | Used to select inbound-link targets for B |
| Bash `uv run python scripts/lint.py --structural-only` | ✅ | Used for pre/post lint snapshots |
| Bash `uv run python scripts/compile.py --file daily/2026-04-13.md` | ✅ | Used in C |
| Wiki article context: `[[concepts/llm-wiki-architecture]]` | ✅ | Read during execution |
| Wiki article context: `[[concepts/anthropic-context-anxiety-injection]]` | ✅ | Read during execution |
| Wiki article context: `[[sources/anthropic-telemetry-experiment-gates-reddit]]` | ✅ | Read during execution |
| MCP context7 | BLOCKED | Available in environment, but not needed because primary-source requirement was already satisfied by direct official docs |
| MCP filesystem | BLOCKED | No filesystem MCP server listed in current environment |
| MCP git | BLOCKED | No git MCP server listed in current environment |
| Read continuation `scripts/lint.py` lines 181-216 | ✅ | Re-read before D1 edit |
| Read `CLAUDE.md` entire file for D1 | ✅ | Re-read before D1 edit |
| Grep `CLAUDE.md` for `confidence` mentions | ✅ | Used to find all contradictory schema text |
| Bash `uv run python scripts/lint.py --structural-only` (continuation) | BLOCKED | Pre-snapshot succeeded; post-snapshot blocked by WSL trying to use the Windows-only `.venv` |
| Bash `uv run python scripts/wiki_cli.py doctor --quick` (continuation) | BLOCKED | Same runtime boundary issue; final lint-specific verification captured with Windows `uv run` instead |

---

## Discrepancies

- [EMPIRICAL] The required WSL Bash phase recreated `<repo-root>/.venv` as a Linux env and reintroduced the historical `.venv/lib64` problem. I repaired the environment by rebuilding `.venv` with Windows `uv sync` before continuing.
- [EMPIRICAL] The plan’s D1 backfill section assumed there might be a non-trivial cleanup wave. Actual measured backfill cost is **0 files**.
- [EMPIRICAL] `doctor --quick` is now green on the lint-specific checks the plan cared about, but still red overall on index freshness. I left that alone because it is outside the approved scope of this task.
- [EMPIRICAL] The continuation plan expected post-D1 lint to stay at `0 warnings`, but a fresh `daily/2026-04-14.md` warning appeared during the task. This is a new uncompiled-daily warning, not a D1 provenance regression.

---

## Self-audit

- [x] Subtask A removed the 2 provenance errors
- [x] Subtask C cleared the stale daily warning
- [x] Subtask B reduced orphan warnings from 5 to 0
- [x] Subtask E added Tier 1 #5 with the required cross-references
- [x] Subtask D measured backfill cost
- [x] D1 was applied later only after explicit approval
- [x] `CLAUDE.md` was edited only in the approved D1 continuation scope
- [x] `scripts/lint.py` was edited only in the approved D1 continuation scope
- [x] No commit / push happened
- [x] Final lint state has no errors and no provenance warnings introduced by D1
- [x] Report uses real command output or explicitly marked discrepancies / blocked sections

---

## Notes / observations

- [PROJECT] The repo is in a much cleaner state than when this task started: lint errors are gone, orphan/stale/provenance warning debt from the original task is gone, and the remaining 283 items are suggestion-level backlink debt. The only warning now is a fresh `daily/2026-04-14.md` uncompiled-log warning that appeared later in the day.
- [PROJECT] The D1 policy decision turned out to be mostly a product preference question, not a migration-cost question.
