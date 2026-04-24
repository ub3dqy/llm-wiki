# Planning Audit — bug-compile-yaml-list-fix

**Plan**: `bug-compile-yaml-list-fix.md` (this directory)
**Report template**: `bug-compile-yaml-list-fix-report.md` (this directory)
**Tracking memo (background)**: `bug-compile-yaml-list-project-frontmatter.md` (this directory)
**Procedure**: `docs/claude-plan-creation-procedure.md` (11-step sequential)
**Governing contract**: `docs/claude-system-operating-contract.md`
**Created**: 2026-04-23 by Claude

---

## §0 — Meta-procedure reference

This planning-audit was written in parallel with the plan per `feedback_plan_writing_report.md`. Each §N below corresponds to a procedure step whose output is recorded here. No post-hoc entries.

---

## §1 — MCP + Skill selection (Step 3)

Session available tools scanned via deferred-tools system-reminder at conversation start. Disconnection notices (dated 2026-04-23): `context7`, `filesystem`, `github`, `grafana`, `postgres`, `redis`, `sentry`, `stitch`, `magic` — all disconnected this session. `git`, `ide`, `figma`, `claude_ai_Google_Drive` remain.

| Tool | Purpose | Priority | Notes |
|---|---|---|---|
| `mcp__git__git_status` | Read-only repo state before/after plan reads | HIGH | fallback: Bash `git status --short` |
| `mcp__git__git_diff` | Inspect currently-modified frontmatter (`wiki/connections/tool-enforcement-dual-failure.md` manual normalization) | MEDIUM | wiki gitignored, diff may be empty for that specific file — Bash `diff` against a backup alternative |
| `mcp__ide__getDiagnostics` | Type baseline for `scripts/compile.py` after edits | LOW | optional, last step of verification |
| `plan-audit` skill | Step 10 mandatory audit | MANDATORY | per `feedback_use_mcp_and_skills.md`; re-invoke loop until 10/10 |
| `code-review` skill | Optional quality sweep on the fix diff | OPTIONAL | may use at self-audit before delivery |
| `WebFetch` | Fallback for docs (context7 disconnected) | HIGH | primary channel for PyYAML / python-frontmatter / stdlib docs this cycle |
| `Grep` | Pattern scan for `project:` usage across codebase (consumers of that frontmatter field) | HIGH | base tool, used for AST-level call-site inventory |
| `Read` | Full file reads for Step 6 | HIGH | base tool; `mcp__filesystem__*` disconnected so Read is the only path |
| `Bash` (`uv run python -c ...`) | Empirical tests: round-trip YAML parsing on both list vs scalar forms, verify `rebuild_index.py` idempotency with each | HIGH | Step 7 |
| `mcp__git__git_commit` | If user authorizes commit of the fix | CONDITIONAL | only on explicit user command post-Codex-report |

Notes:
- `context7` disconnected — `WebFetch` becomes primary docs channel this cycle. Any doc-verification failure must be flagged as ❌ implementation-knowledge with explicit `[NOT DOCS-VERIFIED]` mark per Source Integrity rule.
- `mcp__github__*` disconnected — no remote PR / issue ops possible this cycle (not needed for this fix scope).
- Skill priority order: `plan-audit` (Step 10 mandatory) → `code-review` (optional pre-delivery) → `simplify` (if fix grows beyond minimal) → `security-audit` (N/A, no security surface).

---

## §2 — MCP readiness verification (Step 4)

| MCP | Probe | Raw output | Status |
|---|---|---|---|
| `mcp__git__git_status` | `git_status({repo_path: "E:\\Project\\memory claude\\memory claude"})` | `On branch master. Your branch is ahead of 'origin/master' by 2 commits. Changes not staged: AGENTS.md, CLAUDE.md, docs/claude-plan-creation-procedure.md. 44 untracked docs/ files.` (verbatim excerpt) | ✅ ready |
| `mcp__ide__getDiagnostics` | `getDiagnostics({})` | `[]` | ✅ ready (no current VSCode diagnostics, which is expected for idle state) |
| `WebFetch` | deferred to first actual Step 5 call | — | ⚠️ deferred: probe happens when fetching first doc. Documented here as non-probed-in-advance. |
| `mcp__context7__*` | N/A — disconnected per session system-reminder | — | ❌ unavailable this session; WebFetch is the fallback |
| `mcp__github__*` | N/A — disconnected per session system-reminder | — | ❌ unavailable (not required for this scope) |
| `plan-audit` skill | listed in user-invocable skills system-reminder; invocation happens Step 10 | — | ✅ available, deferred invocation |

Probe verdict: sufficient tools ready for plan creation. `context7` loss is compensated by WebFetch + raw GitHub fallback. No user escalation required.

---

## §3 — Files read during planning (Step 6)

| File | Lines | Tool | Purpose / extracted |
|---|---|---|---|
| `scripts/compile.py` | 1-301 (full, via Grep + Read of lines 1-280) | Read | Compile runs Claude Agent SDK with `allowed_tools=["Read","Write","Edit","Glob","Grep"]` (line 192). Prompt is inline (lines 99-182) and injects `{schema}` from `SCHEMA_FILE` and `{wiki_index}`. Prompt line 132 says "Use YAML frontmatter: title, type (concept), created, updated, sources, confidence, status, project, tags" — **does NOT constrain project to scalar vs list form**. LLM picks format from observing wiki_index examples + instinct. Conclusion: there is no explicit constraint on `project:` format at the prompt level. |
| `scripts/config.py` line 33 | 1 | Grep | `SCHEMA_FILE = ROOT_DIR / "CLAUDE.md"`. Prompt's `{schema}` = Workflow Project CLAUDE.md (this repo's root CLAUDE.md). |
| `CLAUDE.md` (project root) | 1-117 (full) | Read | Does NOT contain wiki-article frontmatter schema at all. Talks about Claude↔Codex workflow. Conclusion: LLM compile receives a `{schema}` block that is unrelated to wiki article shape; it falls back to inferring schema from `{wiki_index}` contents. |
| `scripts/rebuild_index.py` | 1-239 (full) | Read | `enrich_index_line` line 118: `projects = info.get("projects", [])` — expects **list**. Line 123: `suffix += f" [{', '.join(projects)}]"`. `strip_existing_annotations` line 24: `_ANNOTATION_RE = r"(?:\s+\[[a-z0-9_, -]+\])+\s*(?:\(\d+w\))?$"` — non-greedy on single `[...]` only; cannot strip double-nested `[[...]]`. This is the **non-idempotency mechanism**: when `enrich_index_line` receives list with brackets baked into strings, suffix becomes `[[...]]`; next rebuild's strip removes outer `[...]`, inner remains, new suffix is appended → text grows each run. |
| `scripts/utils.py` | 1-305 (full) | Read | **Root cause located at lines 274-283.** `get_article_projects` does naive `raw.split(",")` on the raw frontmatter string. For scalar `project: a, b, c` that works. For list-form `project: [a, b, c]` it produces `["[a", "b", "c]"]` — bracket characters leak into project names. Line 253-261 `parse_frontmatter_list` already handles both forms correctly (strips outer `[...]` before split, also strips quotes) but is not used here. Fix candidate: route `get_article_projects` through `parse_frontmatter_list`. |
| `scripts/lint.py` (planned, not yet read full) | 1017 | deferred — will read before Step 9 | Need to check if there is an existing check that catches list-form `project:` (unlikely — lint check would have flagged the bug at ingest time, but it passed through). |

**Files the plan will touch** (whitelist preview, final in plan):
- `scripts/utils.py` — 1-line fix to `get_article_projects` (routing through `parse_frontmatter_list`).
- Optionally: `scripts/lint.py` — add check warning on list-form `project:` (prevention signal).
- Optionally: `tests/` — regression test asserting `get_article_projects` tolerant to both forms + asserting idempotency of `rebuild_index.py` after ingesting a list-form article.

**Files the plan will NOT touch** (explicit):
- `scripts/compile.py` — prompt-level fix is secondary because the root cause is in parsing utils, not in compile output. Also risk of prompt-drift affecting unrelated compile behavior. If lint check added, LLM will get graceful failure signal instead.
- `scripts/rebuild_index.py` — its logic is correct given a properly-parsed project list. Fixing upstream is cleaner than duct-taping here.
- `wiki/connections/tool-enforcement-dual-failure.md` — Codex already normalized it; no further edit needed and touching gitignored wiki content is out-of-scope for tracked-code-only fix.

---

## §4 — Official docs fetched (Step 5, Source Integrity)

| Topic | Primary source | Result | Fallback | Verbatim quote | Plan section ref |
|---|---|---|---|---|---|
| (none required) | — | — | — | — | — |

**Justification for N/A**: the fix surface is entirely in-repo Python code and uses only Python stdlib primitives already present in `scripts/utils.py` (`re`, `pathlib`, plain string slicing). No new library dependency. No external API call. No language-feature claim (e.g., walrus-operator semantics) in the plan. The in-repo behaviour claims (current vs fixed `get_article_projects`, `enrich_index_line` idempotency) are **empirically verified** by Test 1 + Test 2 in §6 rather than by documentation lookup — because empirical evidence is strictly stronger than docs for in-repo code behaviour.

No context7 MCP is used this cycle (disconnected). No WebFetch is used this cycle (no doc claim required). If future rounds introduce a new library dep or language-feature claim, this section reopens.

---

## §5 — AST scans + commands run (Step 7)

| Command | Purpose | Key output |
|---|---|---|
| `Grep "project\\s*[:=]" scripts/` | Call-site inventory for `project` field in scripts | 5 files: query.py, utils.py, flush.py, seed.py, rebuild_index.py. utils.py and rebuild_index.py are the consumers; compile.py is the producer (via LLM agent); query/flush/seed are unrelated uses. |
| `Grep "yaml\|frontmatter" scripts/compile.py` | Confirm whether compile.py explicitly handles YAML frontmatter or hand-writes | Only mentions in the prompt template (lines 132, 175). No code-level YAML emission — Claude Agent SDK writes articles directly per prompt instructions. |
| `Grep "SCHEMA_FILE" scripts/config.py` | Find what `{schema}` in compile prompt refers to | Line 33: `SCHEMA_FILE = ROOT_DIR / "CLAUDE.md"`. Prompt `{schema}` = this repo's Workflow-Project CLAUDE.md, which does NOT contain wiki frontmatter schema. |
| `Grep "get_article_projects\|parse_frontmatter" tests/test_utils.py` | Existing test coverage check | `test_parse_frontmatter_list` covers list/scalar/whitespace cases for the shared helper. No existing test for `get_article_projects` specifically. Regression test gap. |
| `Grep "project\|enrich\|idempot" tests/test_rebuild_index.py` | Check idempotency tests | Tests exist for `enrich_index_line` and `build_by_project_section` but all pre-build `meta` with clean string lists — they never exercise the integration path where a list-form frontmatter article drives rebuild. End-to-end gap. |

---

## §6 — Empirical tests (Step 7, if applicable)

### Test 1 — Reproduce bug in `get_article_projects` across frontmatter forms

Command: `uv run python -c '<see planning-audit source>'` with 5 parametrized cases on a tempfile article.

Raw output:
```
Case1 raw frontmatter value: '[codex-easy-start, site-tiretop, workflow]'
Case1 current get_article_projects: ['[codex-easy-start', 'site-tiretop', 'workflow]']
Case1 via parse_frontmatter_list: ['codex-easy-start', 'site-tiretop', 'workflow']
Case2 raw frontmatter value: 'codex-easy-start, site-tiretop, workflow'
Case2 current get_article_projects: ['codex-easy-start', 'site-tiretop', 'workflow']
Case2 via parse_frontmatter_list: ['codex-easy-start', 'site-tiretop', 'workflow']
Case3 raw: 'memory-claude'
Case3 current: ['memory-claude']
Case3 via list: ['memory-claude']
Case4 raw: ''
Case4 current: []
Case4 via list: []
Case5 raw: '["a", "b"]'
Case5 current: ['["a"', '"b"]']
Case5 via list: ['a', 'b']
```

Verdict: **Bug confirmed empirically.** Current `get_article_projects` returns broken strings (bracket chars leak into project names) for list-form frontmatter (Cases 1 and 5). `parse_frontmatter_list` handles all 5 cases cleanly. Fix candidate validated.

### Test 2 — Reproduce non-idempotency of `rebuild_index.py::enrich_index_line` with broken projects

Command: `uv run python -c '<see planning-audit source>'` simulating 3 successive rebuild passes with broken vs fixed projects.

Raw output:
```
original: '- [[concepts/foo]] — Foo'
pass1:    '- [[concepts/foo]] — Foo [[a, b, c]] (100w)'
pass2:    '- [[concepts/foo]] — Foo [[a, b, c]] [[a, b, c]] (100w)'
pass3:    '- [[concepts/foo]] — Foo [[a, b, c]] [[a, b, c]] [[a, b, c]] (100w)'

strip_existing_annotations on pass1: '- [[concepts/foo]] — Foo [[a, b, c]]'

idempotent? False

FIXED pass1: '- [[concepts/foo]] — Foo [a, b, c] (100w)'
FIXED pass2: '- [[concepts/foo]] — Foo [a, b, c] (100w)'
FIXED pass3: '- [[concepts/foo]] — Foo [a, b, c] (100w)'
FIXED idempotent? True
```

Verdict: **Non-idempotency confirmed, and directly caused by broken projects list.** Current behaviour duplicates the `[[…, …]]` annotation on each rebuild. `strip_existing_annotations` only peels one `[...]` layer at end-of-string, leaving the inner `[a, b, c]` as wikilink-looking text the next pass cannot recognise as its own annotation. After the fix (clean projects strings), rebuild is idempotent across unlimited passes. This fully explains the `index_health` FAIL observed by Codex during iter-5 P1 compile.

---

## §7 — Assumptions + verification status (Step 8)

| Claim | Status | Evidence row / flag |
|---|---|---|
| `compile.py` runs Claude Agent SDK and the LLM writes wiki articles (no code-level YAML emission in compile.py) | ✅ verified | §3 row `scripts/compile.py` (prompt inline at lines 99-182; `allowed_tools=["Read","Write","Edit","Glob","Grep"]`). |
| The `{schema}` injected into compile prompt is the Workflow-Project CLAUDE.md, not a dedicated wiki schema | ✅ verified | §3 rows `scripts/config.py` line 33 + full read of `CLAUDE.md`. |
| `get_article_projects` uses naive `str.split(",")` and mis-parses list-form frontmatter | ✅ verified | §3 row `scripts/utils.py` lines 274-283 + §6 Test 1 empirical reproduction (Cases 1, 5). |
| `parse_frontmatter_list` already handles list/scalar/quoted/whitespace-only cases correctly | ✅ verified | §3 row `scripts/utils.py` lines 253-261 + §5 row existing `test_parse_frontmatter_list` parametrized test. |
| `rebuild_index.py::enrich_index_line` becomes non-idempotent under broken projects list, producing doubled `[[…]]` annotations that `strip_existing_annotations` cannot fully remove | ✅ verified | §6 Test 2 empirical reproduction (pass1/pass2/pass3 output). |
| Minimal fix is 1-line change in `get_article_projects` to route through `parse_frontmatter_list` | ✅ verified | §6 Test 1 shows `parse_frontmatter_list` produces correct output for all 5 cases (including the 2 broken-today cases). §6 Test 2 shows cleaned projects make `enrich_index_line` idempotent. |
| No existing regression test asserts `get_article_projects` on list-form frontmatter | ✅ verified | §5 row `tests/test_utils.py` grep — only `test_parse_frontmatter_list` covers the shared helper. |
| No existing end-to-end test asserts `rebuild_index.py` idempotency when a list-form frontmatter article is on disk | ✅ verified | §5 row `tests/test_rebuild_index.py` grep — all existing tests pre-build clean `meta` dicts. |
| Fix does not require `compile.py` prompt changes | ⚠️ assumed-to-verify | If LLM keeps emitting list-form and downstream consumers now handle it, the emitted articles may still look unusual under human review. Mitigation: leave compile.py alone in this fix (out-of-scope); open separate follow-up memo if user finds list-form undesirable for readability. |
| Fix does not require `compile.py` prompt changes to be bug-closed | ⚠️ partial | The bug (rebuild_index non-idempotency + `index_health` FAIL) is fully closed by the parsing fix. Whether list-form `project:` is "wrong style" vs "acceptable style" is a separate convention question not resolved here. |
| No other code path uses raw `project:` frontmatter value without going through `get_article_projects` | ⚠️ partially-refuted — see §10 Gap-A | Post-audit grep with context (Step 8 close-out) found `scripts/query.py:76-83` reads `fm.get("project", "")` directly and concatenates into `meta_text` for keyword search. Bracket chars leak into search text but substring match still functions (e.g., keyword `codex-easy-start` still matches `[codex-easy-start`). Degraded but not broken. `seed.py` and `flush.py` use the string "project" in unrelated contexts (CLI arg + function parameter). |

---

## §8 — plan-audit skill invocations (Step 10)

| Round | Args | Score | Critical | Important | Optional | Fixes applied |
|---|---|---|---|---|---|---|
| 1 | plan-audit on `bug-compile-yaml-list-fix.md` v1 + this audit | 6/10 🟠 | 3 | 4 | 2 | All critical + important applied in-place (Change 3 rewrite to unit-level; removed sys.path hack; corrected PDC baseline; added ruff + mypy to Phase 2; added wiki_cli.py to blast radius + smoke in Phase 2; corrected conftest.py description). Plan re-saved as v2. |
| 2 | plan-audit on v2 | 10/10 ✅ | 0 | 0 | 2 optional nits (cosmetic only) | Proceeded to Step 11 delivery. Independent pre-baselines: ruff = 0, pytest = 84. (Caveat: mypy 0-errors claim from Round 2 was run on Claude's Windows host where mypy is available separately; not reliable signal for Codex's clean WSL uv env — caught by Codex-review-round-1 F2 below.) |
| Codex-review-round-1 | Codex adversarial review on v2 plan | reject-with-findings (2 critical + 2 important) | 2 | 2 | 0 | **F1** (critical): absolute git-status whitelist gate impossible under current worktree state where many files pre-exist as modified (AGENTS.md, CLAUDE.md, scripts/rebuild_index.py, scripts/wiki_cli.py, docs/...). → v3 rewrites gate as **delta** vs pre-flight snapshot `/tmp/git_status_pre.txt`. **F2** (critical): mypy not installed in dev deps per `pyproject.toml:12-16` (only ruff + pytest) — Codex's WSL env gets "Failed to spawn: mypy, No such file or directory". → v3 drops mypy from all gates; ruff-only lint. **F3** (important): sibling artifacts (`report.md` header, this file's signature) still said v1 while plan was v2 → v3 syncs all three to v3. **F4** (important): Change 3 unit test does not exercise `get_article_projects` at all, so a revert of `scripts/utils.py:274-283` alone would not fail that test. Plan's "fails loudly if someone reverts the fix" claim was overreach. → v3 adds a second test `test_list_form_frontmatter_end_to_end_stays_idempotent` that does the full disk→parse→enrich pipeline, and tightens the unit test's docstring to honestly describe only the enrich_index_line contract. |
| 3 | plan-audit on v3 | 10/10 (self-audit) | 0 | 0 | 1 cosmetic | Self-audit declared clean but missed a pytest-counting error (see Codex-review-round-2 below). Plan-audit skill evaluated math as "`+3` test functions" without cross-checking against pytest's parametrized-case counting. This was an oversight on my part during round 3 validation. |
| Codex-review-round-2 | Codex adversarial review on v3 plan | reject-with-findings (1 critical + 3 important + 1 minor) | 1 | 3 | 1 minor | **F5** (critical): pytest delta arithmetic wrong — plan/report/audit all claim `+3` but pytest counts each parametrized case individually; `test_get_article_projects_handles_list_and_scalar` has 5 params, plus 2 discrete tests = `+7`. Empirical proof from Codex: existing `test_parse_frontmatter_list` has 6 params → `6 passed` in pytest. → v4 corrects all references to `+7`, focused-run comment notes 7 expected nodes. **F6** (important): Phase 2 focused pytest did not include `test_list_form_frontmatter_end_to_end_stays_idempotent` — the integration test is a hard gate but had no dedicated evidence slot. → v4 adds it to focused run command. **F7** (important): report template Change 3 section still singular ("new test", "monkeypatch/fixture choice"). → v4 rewrites for two-test shape. **F8** (important): report lacked dedicated §4.x slot for `wiki_cli.py status` output; acceptance matrix pointed at §4.4 which is doctor diff. → v4 adds §4.4.5 dedicated section. **Minor**: report §5 still referenced D1-D8 while plan §11 has D1-D9. → v4 fixes. |
| 4 | plan-audit on v4 (post Round-2 fixes) | 10/10 ✅ (self-audit miss recorded) | 0 | 0 | 0 | Same pattern as Round 3: self-audit cleared the plan but did not cross-check PDC baseline against the CI workflow regex. The mistake compounded across rounds because my local Windows Git Bash `grep -cE 'C:\\Users' docs/codex-tasks/wiki-freshness-phase1.md` returned `0` (BRE/ERE treat `\\U` differently than PCRE), so I believed "empty baseline" was verifiable. CI uses `grep -lP 'C:\\\\Users'` which does match that file. See Codex-execution-round-1 below. |
| Codex-execution-round-1 | Codex started Phase 1 execution on v4 plan | blocked (1 finding, all code edits succeeded) | 1 | 0 | 0 | **F9** (critical, caught at acceptance gate): plan's `test ! -s /tmp/pdc_post.txt` baseline is factually wrong. `docs/codex-tasks/wiki-freshness-phase1.md:556` contains an illustrative bullet listing `C:\Users` (describing what NOT to store), which the CI workflow's `grep -lP 'C:\\\\Users'` hits. D8 fired correctly; Codex stopped rather than silently suppress. All other acceptance gates passed: fix applied, 91/91 pytest, ruff clean, focused 7/7, git-status delta limited to 3-file whitelist, wiki_cli.py status exited 0, reproduction flipped `['[a', 'b', 'c]']` → `['a', 'b', 'c']`. Only doctor --quick was not run because D8 preceded it. → v5 restores the v1 single-file allowlist baseline AND switches to PCRE `-lP` for CI parity. Code edits stay on disk; Codex only needs to re-verify PDC + finish doctor. |

---

## §9 — Delta from prior cycle

This is the first plan-creation cycle for this bug. No prior Tier. Background memo `bug-compile-yaml-list-project-frontmatter.md` was written as a tracking record during P1 wiki-health report review on 2026-04-23 — it is bug-description only, not a prior plan iteration.

---

## §10 — Known gaps (honest flags)

| Gap | Mitigation |
|---|---|
| **Gap-A**: `scripts/query.py:76-83` reads `project:` directly without `get_article_projects`. For list-form frontmatter the bracket chars leak into keyword-match text. Degraded (not broken) — substring match still works for keywords that happen to be inside the bracketed list. | Out-of-scope for this fix (minimum-viable bug closure = rebuild_index idempotency + clean project names in index). Separate follow-up optional: route query.py through `parse_frontmatter_list` too for consistency. Flag surfaced in §7 and plan §Out-of-scope. |
| **Gap-B**: This fix stops the rebuild_index symptom. It does NOT stop compile LLM from emitting list-form `project:` in the future. Every subsequent multi-project connection article will still be written in list-form. That is visually inconsistent with scalar-style articles even if parsing is robust. | Deliberate out-of-scope decision: touching the compile prompt risks prompt-drift affecting unrelated compile behaviour; parsing-side fix is less risky. If user/Codex later decides convention should enforce scalar form, a lint check + prompt update would be the separate cycle. |
| **Gap-C**: No verification against real wiki article on disk. Both Test 1 and Test 2 used tempfile + simulated meta dict. The current `wiki/connections/tool-enforcement-dual-failure.md` was manually normalized by Codex in iter-5 P1 to scalar form, so it cannot serve as a natural test subject without re-injecting the broken form. | Codex pre-flight (plan §Phase 1) to (a) grep `wiki/` for any `project:\s*\[` patterns; (b) if zero found, construct a temporary test article locally to validate fix; (c) if ≥1 found, verify fix resolves all observed broken patterns. Empirical, not docs. |
| **Gap-D**: Known test infrastructure is only pytest. No YAML-load-based schema validator exists; `lint.py` does not currently check `project:` field shape. Adding a lint check is optional scope. | Plan-level decision: include a small regression test in `tests/test_utils.py` (targeted at `get_article_projects`) as part of the fix. Lint check is explicitly out-of-scope for this cycle (kept for future prevention work). |
| **Gap-E**: The `_FM_LINE_RE` regex (`scripts/utils.py:223`) treats frontmatter as key:value per line and is silent on multi-line YAML constructs (block-style lists, folded strings). Non-issue for `project:` since compile historically emits inline form, but other frontmatter fields could hide similar bugs. | Out-of-scope flag — logged for separate audit if ever needed. No action in this cycle. |

---

## §11 — Signature

Author: Claude (Opus 4.7 1M)
Cycle: bug-compile-yaml-list-fix, iteration v5 (Codex execution-round-1 F9 PDC baseline correction applied)
Completed at: 2026-04-23T20:30Z (audit-round-1 v1→v2; Codex-review-round-1 v2→v3; Codex-review-round-2 v3→v4; Codex-execution-round-1 v4→v5 — edits survived on disk, plan metadata corrected)
