# Claude Plan Creation Procedure

**Purpose**: consolidated sequential checklist for creating a Codex handoff plan. Single source of truth, cross-references the underlying memory + wiki rules without duplicating them.

**Scope**: applies every time Claude drafts a development plan intended for Codex execution (format: 3 files in `docs/codex-tasks/`). Not for general conversation, code explanations, or ad-hoc tasks.

**Maintenance**: when any of the source rule files change, this document's numbered steps should be re-verified. Changes here MUST also be reflected in the relevant memory/wiki rule file — this index doesn't replace the rules, it orchestrates them.

---

## Source of truth files

Each step below references the canonical rule file. This document does NOT duplicate rule content — just indexes it.

| File | Location | What it covers |
|---|---|---|
| `feedback_codex_task_handoff_workflow.md` | memory | 3-file handoff format (plan + report + planning-audit) in `docs/codex-tasks/`; anti-fabrication structure |
| `feedback_plan_writing_report.md` | memory | Planning-audit MUST be filled in parallel with plan creation; absence of entry = step not done |
| `feedback_use_mcp_and_skills.md` | memory | MCP+skills scan mandatory; `context7` for library docs; MCP readiness verification via probe; Source Integrity rule (official sources only, deeper search); git MCP availability (no push, no hunk-split) |
| `feedback_verify_before_asserting.md` | memory | Meta-rule: 5-second evidence check for every state claim; "Source integrity bypass" is a named failure mode |
| `feedback_validated_good_patterns.md` | memory | Validated patterns: path-scoped acceptance, baseline-delta for untouched paths, `--force-with-lease`, double-review-loop, git diff `-w` for CRLF, handoff artifacts explicit, reread own instructions |
| `claude-mcp-and-skill-usage-matrix.md` | wiki/concepts | Public-facing matrix of 12 MCP + 30+ skills with when-to-use criteria + readiness + source integrity; same rules as memory but readable by contributors |
| `workflow-instructions-codex.md` | docs (or root, untracked) | Codex-side counterpart: what Codex does on receiving a plan (pre-flight, verify, phases, report fill) |

---

## Sequential procedure (11 steps)

Each step is a discrete action with an observable output. Steps MUST be executed in order. Skipping or reordering violates the rules in the referenced files.

### Step 1 — Create tracked task list

**Tool**: `TaskCreate` (8 tasks, one per subsequent step).

**Why**: progress visible to user + protects against forgotten steps. Particularly important after 3-round pushback cycles observed in session 2026-04-17 where meta-procedure itself was violated.

**Output**: 8 task entries (Steps 2-11 mapped 1-to-1, with Step 11 as delivery).

**Rule source**: general discipline, no specific memory file.

---

### Step 2 — Write planning-audit SKELETON first

**Tool**: `Write`.

**File**: `docs/codex-tasks/<task-slug>-planning-audit.md`.

**Why**: rule from `feedback_plan_writing_report.md` — planning-audit filled in PARALLEL with plan, not post-hoc. Skeleton first, content follows as each subsequent step completes.

**Required sections in skeleton**:
- §0 Meta-procedure (reference this document)
- §1 MCP + Skill selection (filled Step 3)
- §2 MCP readiness verification (filled Step 4)
- §3 Files read during planning (filled Step 6)
- §4 Official docs fetched with Source Integrity chain (filled Step 5)
- §5 AST scans + commands run (filled Step 7)
- §6 Empirical tests (filled Step 7 if applicable)
- §7 Assumptions + verification status (filled throughout)
- §8 plan-audit skill invocation (filled Step 10)
- §9 Delta from prior Tier (filled Step 9)
- §10 Known gaps (honest flags, filled throughout)
- §11 Signature

**Output**: empty-but-structured planning-audit file on disk.

**Rule source**: `feedback_plan_writing_report.md`.

---

### Step 3 — Scan MCP + Skill inventory; identify matches

**Tool**: read session-start system reminder (deferred tools list + skills list).

**Why**: rule from `feedback_use_mcp_and_skills.md` — base tools are fallback, specialized tools preferred.

**Output**: planning-audit §1 table filled with Tool | Purpose | Priority. Identify at minimum:
- `context7` for any library/stdlib/framework docs (MANDATORY if docs needed)
- `git` MCP for local repo state (read-ops preferred over Bash)
- `github` MCP for repo/issue/PR ops (if relevant)
- `ide.getDiagnostics` for type/lint baseline (optional)
- `plan-audit` skill for Step 10 (MANDATORY)

**Rule source**: `feedback_use_mcp_and_skills.md` + `claude-mcp-and-skill-usage-matrix.md`.

---

### Step 4 — MCP readiness probes (MANDATORY before any MCP use)

**Tool**: minimal read-only call of each selected MCP.

**Why**: "advertised in session-start ≠ works right now" — auth tokens expire, credentials rotate, env drifts.

**Probe patterns** (from `claude-mcp-and-skill-usage-matrix.md`):
- `context7` → `mcp__context7__resolve-library-id({libraryName: "Python", query: "readiness probe"})`
- `git` → `mcp__git__git_status({repo_path: "..."})`
- `ide` → `mcp__ide__getDiagnostics({})`
- `github` → `mcp__github__search_repositories` or equivalent light call
- `filesystem` → `mcp__filesystem__list_allowed_directories`

**If any probe fails**: STOP plan execution → diagnose → fix to working state (or ask user if outside my scope) → record fix steps + proof of working state in planning-audit §2.

**Output**: planning-audit §2 filled with Probe command | Raw output | Status (ready / fixed-during-planning / blocked-awaiting-user). Verbatim outputs, no summaries.

**Rule source**: `feedback_use_mcp_and_skills.md` — "MCP Readiness Verification" subsection.

---

### Step 5 — Fetch official docs (Source Integrity rule)

**Tool**: `context7` primary → WebFetch fallback → raw upstream source (GitHub/PEPs/RFCs) final fallback.

**Why**: rule from `feedback_use_mcp_and_skills.md` — no from-memory claims; only official sources; don't bypass gaps with training data.

**Per-topic fetch chain** (each attempt logged):
1. `context7 query-docs` with specific library ID
2. If context7 empty or partial → `WebFetch` the canonical docs URL
3. If WebFetch truncated → `WebFetch` on `raw.githubusercontent.com/<upstream>/<branch>/<path>` raw source
4. If all fail → empirical test in planning environment OR explicit `[NOT DOCS-VERIFIED]` flag in planning-audit §10

**Output**: planning-audit §4 table: Topic | Primary source | Result | Fallback | Verbatim quote | Plan section. Verbatim quotes, URLs real.

**Rule source**: `feedback_use_mcp_and_skills.md` — "Source Integrity" subsection + `feedback_verify_before_asserting.md` "Source integrity bypass" row.

---

### Step 6 — Full file reads for every file the plan will touch

**Tool**: `Read` (or `mcp__filesystem__read_text_file` as alternative).

**Why**: rule from CLAUDE.md `## Agent operating rules` — "Research the codebase before editing. Never change code you haven't read." Full reads, not partial ranges.

**What to read**:
- Every file the plan's `Whitelist` section will touch (full content)
- Every file that imports/consumes symbols from touched files (full content, not just grep)
- Related files for blast-radius verification (e.g., doctor.py if touching log format)

**Output**: planning-audit §3 table: File | Lines | Tool used | Purpose/extracted. Never "I grepped X" as substitute for full read.

**Rule source**: CLAUDE.md operating rules + `feedback_verify_before_asserting.md` (rolling-edit case).

---

### Step 7 — AST scans + grep patterns + empirical tests

**Tool**: Bash `uv run python -c '<ast walker>'` for AST, `Grep` for patterns, Bash `python -c '<test>'` for empirical tests (NOT `mcp__ide__executeCode` which is inline-to-VSCode only).

**Why**:
- AST scan = authoritative call-site inventory (not grep of text)
- Empirical test substitutes when docs gap (e.g., Tier 1 `O_EXCL` test for semantic docs don't cover)
- Commands run must be recorded as evidence, not "I looked at it"

**Output**:
- planning-audit §5 table: Command | Purpose | Key output
- planning-audit §6 table (if applicable): Test | Purpose | Raw output | Verdict

**Rule source**: `feedback_plan_writing_report.md` (audit must document commands run) + `feedback_verify_before_asserting.md`.

---

### Step 8 — Fill assumptions + honest-gap flags

**Tool**: `Edit` on planning-audit sections §7 + §10.

**Why**: every claim in the plan needs an evidence row (§3/§4/§5/§6 backing) OR an explicit flag in §7 as "assumed" OR §10 as "known gap, empirical test / ask user". Rule from `feedback_verify_before_asserting.md` — no state claim without 5-second evidence.

**Categories**:
- ✅ verified (cite evidence row)
- ⚠️ assumed-to-verify-by-codex (flagged for pre-flight)
- ❌ flagged as implementation-knowledge (honest about non-docs-backed claims)

**Output**: planning-audit §7 table complete. §10 lists ALL known gaps honestly with mitigation.

**Rule source**: `feedback_verify_before_asserting.md` + `feedback_plan_writing_report.md`.

---

### Step 9 — Draft plan + report template

**Tool**: `Write` (two files).

**Files**:
- `docs/codex-tasks/<task-slug>.md` (plan)
- `docs/codex-tasks/<task-slug>-report.md` (report template)

**Plan structure** (canonical from `feedback_codex_task_handoff_workflow.md`):
1. Version + Planning-audit reference
2. Why this plan exists (derived from which audit/source)
3. Иерархия источников правды (numbered list: docs → code → plan → discrepancy)
4. Doc Verification §V1-§V_n with verbatim quotes + URLs
5. Pre-flight verification (Steps for Codex: file reads, AST, baseline, empirical tests)
6. Whitelist (strict — explicit "НЕ трогать" list)
7. Change N sections (Current quote → Target code → Rationale with §V_n refs)
8. Verification phases (Phase 1 Codex-only pre-flight, Phase 2 post-change smokes, Phase 3 awaits-user)
9. Acceptance criteria
10. Out of scope (explicit — prevent scope creep)
11. Rollback
12. Discrepancy-first checkpoints (STOP conditions)
13. Self-audit checklist
14. Notes для Codex (WSL uv discipline, no commit/push without approval)
15. Commits strategy (one vs split, with hunk map if split)

**Report template structure**: `<fill: ...>` placeholders for every section Codex must populate. Anti-fabrication — raw outputs verbatim, no summarize.

**Output**: plan + report files on disk. Every claim in plan cites planning-audit row or §V_n.

**Rule source**: `feedback_codex_task_handoff_workflow.md`.

---

### Step 10 — plan-audit skill invocation

**Tool**: `Skill({skill: "plan-audit", args: "..."})`.

**Why**: rule from `feedback_use_mcp_and_skills.md` — skill description matches task literally ("Аудит планов разработки — проверяет план на соответствие реальному состоянию проекта"). MANDATORY invocation.

**Process**:
1. Invoke skill with plan path + planning-audit path as context
2. Receive scored report (0-10 + findings by severity)
3. Apply ALL critical + important fixes inline to plan
4. Optional fixes apply or defer with rationale
5. Record invocation + result + fixes in planning-audit §8

**If skill returns <7/10**: substantial fixes needed, may warrant re-audit after fixes. If 7-8/10: minor fixes, no re-audit. If 9-10/10: ready, proceed.

**Output**: planning-audit §8 filled; plan fixes applied.

**Rule source**: `feedback_use_mcp_and_skills.md` + `claude-mcp-and-skill-usage-matrix.md`.

---

### Step 11 — Deliver handoff

**Tool**: text response in chat + verification of 3 files on disk.

**Deliverables**:
1. **3 files on disk** (verified via `ls -la docs/codex-tasks/<slug>*`):
   - `<slug>.md` — plan
   - `<slug>-report.md` — report template
   - `<slug>-planning-audit.md` — evidence trail
2. **Short inline prompt in chat** (NOT a 4th file) — copy-pasteable text for Codex chat. Includes: file paths, scope summary, pre-flight steps, whitelist, commit strategy, push policy, reference to planning-audit for evidence backing.

**Anti-pattern observed 2026-04-17**: creating a 4th `-prompt.md` file was WRONG. Prompt lives in chat, not as artifact.

**Output**: chat response with the prompt block + file list confirmation.

**Rule source**: `workflow-instructions-codex.md` (Codex-side expects text-in-chat prompt, not file).

---

## What NOT to do (session 2026-04-17 anti-patterns)

1. **Write plan before reading files**. Every file the plan touches must be read in full BEFORE drafting the plan. Observed: pre-Tier-1 plan had wrong line numbers because flush.py was only partially read.

2. **Skip MCP readiness probe**. Observed: assumed context7 worked, wasted WebFetch attempts on truncated docs.python.org, fallback to CPython GitHub worked but took 3 rounds.

3. **Use memory/training data for docs claims**. Observed: "os.replace uses MoveFileExW on Windows" — was implementation knowledge not docs-verified. Plan's honest flag after Source Integrity rule saved it.

4. **Skip planning-audit**. Observed: pre-Tier-1 planning-audit missing entirely, then v1 shipped with known gaps section. Post-hoc audit = not audit, it's after-action justification.

5. **Create 4-file handoff**. Observed: v1 Tier 1 had `<slug>-prompt.md` file. Wrong — prompt lives in chat.

6. **Skip plan-audit skill**. Observed: pre-Tier-1 draft never invoked skill; issues caught by user pushback instead.

7. **Default to base tools when specialized exists**. Observed: Bash `git commit` used when `mcp__git__git_commit` available. Rule violation even when result identical.

8. **Scope creep**. Observed: early plan drafts included "optional cleanup" changes. Whitelist strict = ONLY what plan explicitly targets. Other findings go to "Out of scope" + next-Tier candidates.

9. **Run git commands without explicit user command** (ANY git operation — status, diff, log, show, add, commit, push, branch, checkout — READ or WRITE). Observed 2026-04-17 post-meta-procedure: after finishing the asked task (meta-procedure file creation), ran `git status`, `git diff --stat` (twice), `mcp__git__git_status`, attempted `mcp__git__git_log` and `mcp__git__git_show` — all without user command. User rightfully interrupted.

   **Rule**: every git invocation (Bash or MCP) requires an explicit user command that either (a) directly names the git operation, or (b) is part of a current workflow step where git is documented as needed (e.g., "pre-flight Step 2 baseline"). Absent either → do NOT invoke.

   **Why the misconception is easy**: read-only git commands feel "safe" because they don't modify state. But each is a tool call = an action on a tool budget + an interruption of the user's mental model of what I'm doing. "Let me just check the state" is the gateway to "let me just recommend a commit" to "let me just recommend a push".

   **Corollary — racing the executor**: when Codex is running a handoff, I do NOT check progress by running git queries, reading report files, or tailing logs. Codex reports back; I wait. A system-reminder flagging a modified file ≠ "Codex is done" — it's just a filesystem event notification.

10. **Interpret filesystem events as completion signals**. Observed 2026-04-17: a `system-reminder` about a report file being modified triggered interpretation "Codex finished". The modification notice only says the file changed — NOT that the executor finished its workflow. Completion is signalled by user message, not by filesystem telemetry.

11. **Echo executor's report as own verification**. Observed 2026-04-17 Tier 3.1 post-Codex: summarized Codex's report in chat including "Personal data scan: clean" — but that was Codex's claim, not my own verification. I had NOT run my own scan. User: "проверил или из головы написал?" Distinction: (a) Codex report = his claims; (b) my verification = my own tool call with my own output. For mandatory pre-push steps (personal data scan per `feedback_commit_push_workflow`), scan is MY responsibility. Never copy executor's "clean" claim without running scan myself.

12. **Ask permission for mandatory documented steps**. Observed 2026-04-17 Tier 3.1: user said "push?" → I replied "запустить personal data scan сейчас?" instead of just running it. But memory documents scan as MANDATORY pre-push — not requiring per-invocation permission. User's "push" command = permission to execute full pre-push checklist. Asking "should I?" for documented mandatory steps = lazy deferral. Just execute, then report result.

13. **Meta-talk instead of action**. Observed 2026-04-17: user asked "что должен сделать?" → I replied with text listing what I should do, instead of doing it. User repeated question 2-3 times. Pattern wastes token budget on descriptions of actions rather than action outputs. When user asks "что должен?" or "почему не сделал?", response = action + result report, NOT action plan. User's "what should you do?" = implicit permission to execute currently-pending authorized actions. Reply in chat AFTER the actions, with their output.

14. **Options without recommendation**. Observed 2026-04-17 cleanup question: presented 3 options ("cleanup / commit handoffs / status quo — выбирай") without own recommendation and without trade-off justification. User: "ты должен дать рекомендацию с обоснованием". Deferral of judgment to user = laziness disguised as neutrality. **Rule**: every options list MUST end with (a) explicit "Рекомендую Option X" + (b) concrete justification with trade-offs. User can override, but default is my analysis-backed recommendation. "Do nothing / status quo" is a valid option but must be evaluated explicitly with its own pros/cons — not hidden under passive voice.

---

## Delivery signal — what "done" looks like

Plan is ready for Codex when ALL of:

- [ ] 3 files on disk (plan + report + planning-audit)
- [ ] Planning-audit §1-§11 all filled (no `<fill>` placeholders in non-Step 11 sections)
- [ ] Every plan claim either cites §V_n verbatim quote OR has ⚠️/❌ flag in §7/§10
- [ ] plan-audit skill invoked, score ≥7/10, all critical+important fixes applied
- [ ] Whitelist has explicit "НЕ трогать" list
- [ ] Out-of-scope section exists
- [ ] Discrepancy checkpoints ≥5 items
- [ ] Short inline prompt posted in chat (NOT as file)
- [ ] User hasn't pushed back on meta-procedure during creation (if yes — fix before delivery)

Only then deliver.

---

## Maintenance notes

- When a new rule file is added to memory, add row to §Source of truth table here
- When a step changes in any referenced rule file, audit this document's step's wording
- When plan-audit skill is updated, re-verify Step 10 invocation pattern still correct
- Keep this document ≤300 lines. If it grows, split cluster of related steps into a sub-document.

## Cross-reference

Same content in compressed form for memory cross-session retrieval:
- Memory pointer: `feedback_meta_plan_procedure_index.md` (one-line + link to this file)
- Wiki concept: not created — this file lives in project docs/, not wiki/concepts/, because it's a procedural checklist tied to this specific repo's workflow, not a universal concept.
