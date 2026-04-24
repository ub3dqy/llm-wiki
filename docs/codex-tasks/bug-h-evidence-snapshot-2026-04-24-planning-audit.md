# Planning Audit — bug-h-evidence-snapshot-2026-04-24

**Plan**: `bug-h-evidence-snapshot-2026-04-24.md` (this directory)
**Report template**: `bug-h-evidence-snapshot-2026-04-24-report.md` (this directory)
**Background log**: `bug-h-issue-16-tracking-log.md` (this directory) — 2026-04-16 last snapshot; this cycle produces the 2026-04-24 append
**Procedure**: `docs/claude-plan-creation-procedure.md` (11-step sequential)
**Governing contract**: `docs/claude-system-operating-contract.md`
**Created**: 2026-04-24 by Claude

---

## §0 — Meta-procedure reference

Sequential procedure per `docs/claude-plan-creation-procedure.md`; evidence filled inline with each step.

---

## §1 — MCP + Skill selection (Step 3)

Session-available tools: git MCP, ide MCP (per earlier session). Disconnected this session: context7, github, grafana, postgres, redis, sentry, stitch, magic, filesystem. WebFetch available.

| Tool | Purpose | Priority | Notes |
|---|---|---|---|
| `mcp__git__git_log` | Inspect recent commits touching flush.py, hooks, issue #16 references | HIGH | read-only |
| `mcp__git__git_status` | Baseline worktree state at cycle start | MEDIUM | already probed for cycle-1 |
| `WebFetch` | Fetch github issue #16 state + comments (primary) | HIGH | `github` MCP disconnected — WebFetch is the fallback channel |
| `gh` CLI (Bash) | Alternative for issue/PR fetch if WebFetch returns truncated | MEDIUM | secondary fallback; gh-auth must exist |
| `Bash` with `grep/awk/head/tail` | Parse `scripts/flush.log` for "Fatal error in message reader" events, post-bump markers, date ranges | HIGH | the log is plain text; native tools sufficient |
| `Read` | Full reads of `docs/codex-tasks/bug-h-issue-16-tracking-log.md` (schema + prior snapshot format), `scripts/flush.py` (for error-signature context) | HIGH | base tool |
| `plan-audit` skill | Step 10 mandatory | MANDATORY | re-invoke loop until 10/10 |

Notes:
- scope of this plan is **evidence gathering only** — no code changes to `scripts/`, no modification of `bug-h-issue-16-tracking-log.md` structure (only append a new dated snapshot per its own "Update protocol" section)
- Claude Agent SDK NOT invoked (no compile, no LLM query)
- mypy / ruff / pytest NOT relevant — no code touched

---

## §2 — MCP readiness verification (Step 4)

| MCP | Probe | Raw output | Status |
|---|---|---|---|
| `mcp__git__git_log` | `git_log({repo_path: ".", max_count: 5})` | 5 commits returned: `66260af` (cycle-1 fix today), `bd68edc`, `fe4853c`, `167c4e3`, `41cb16e`. All author/date/message parsed cleanly. | ✅ ready |
| `gh` CLI | `gh auth status` | `github.com ✓ Logged in to github.com account ub3dqy (GH_TOKEN) ... Active account: true ... Token: ghp_**** (scopes not listed in summary)` | ✅ ready — repo access authenticated |
| `WebFetch` | deferred (probe happens at first fetch in Step 5) | — | ⚠️ deferred |
| `Bash` | implicit readiness (used repeatedly in cycle 1) | — | ✅ ready |

Probe verdict: sufficient tools ready. `gh` CLI is authenticated and is a first-class channel for issue #16 (removes dependence on WebFetch truncation limits).

---

## §3 — Files read during planning (Step 6)

| File | Lines | Tool | Purpose / extracted |
|---|---|---|---|
| `docs/codex-tasks/bug-h-issue-16-tracking-log.md` | 1-137 (full) | Read | Closure contract §, 2026-04-16 snapshot format, update-protocol rules. Tail "Update protocol": append snapshot with timestamp + post-bump ok/fail + latest fatal + doctor line + conclusion. |
| `scripts/flush.py` | 1-80 head + Grep for log signatures | Read + Grep | `logging.basicConfig(filename=...flush.log, format="%(asctime)s %(levelname)s [flush] %(message)s")` line 42-47. Success log line 300 `"Flushed N chars to daily log for session X"`. Error paths: line 281 ProcessError, line 292 generic query failure. `logger.error` from SDK `_internal/query.py:248` inherits root handler → appears as `ERROR [flush]` in log. |
| `scripts/compile.py` | previously read in cycle-1 | (prior) | Same basicConfig but with `[compile]` tag instead of `[flush]`. Compile also uses Agent SDK so it hits the same stalled-streaming failure mode, surfacing as `ERROR [compile] Fatal error in message reader`. Critical for disambiguation in the probe. |
| `scripts/flush.log` | head -3 + tail -3 + date range | Bash | 1.15 MB log; dates span 2026-04-10 19:56:09 → 2026-04-24 17:05:31. File still being written (tail line is tail -1 at probe time). Structure confirmed as `TIMESTAMP LEVEL [source] message`. |

---

## §4 — Official docs / external refs (Step 5, Source Integrity)

| Topic | Source | Result | Fallback | Verbatim quote | Plan section |
|---|---|---|---|---|---|
| Issue #16 body — closure contract | `gh issue view 16 --repo ub3dqy/llm-wiki` | full body fetched | N/A | "Status: OPEN. Title: Bug H — flush.py Agent SDK intermittent exit code 1…" + Symptom, Evidence, Distinguishing features, Hypotheses, Suggested investigation steps, Out-of-scope sections (not repeated verbatim here — tracking log §1 already quotes the closure contract once). | Plan §1, §4 acceptance criteria |
| Issue #16 comment — 2026-04-13T20:00:01Z | `gh issue view 16 --json comments` | fetched | — | Summary of debug_stderr experiment being inconclusive; channel confirmed useless; plan: "Collect real-world samples over ≥1 week before next fix attempt: grep 'Fatal error in message reader' scripts/flush.log to enumerate fails ... Only then design next fix-task with real data, not speculation" | Plan §2 methodology |
| Issue #16 comment — 2026-04-13T21:17:46Z | same channel | fetched | — | Confirms Bug H is path-agnostic (WSL Linux bundled claude AND Windows .exe both affected). Empty stderr on failure. Error signature: "Fatal error in message reader: Command failed with exit code 1" with "Error output: Check stderr output for details" (generic, no stderr content). Root cause unknown, localization blocked on lack of reliable reproducer. | Plan §3 error signature match |
| Issue #16 comment — 2026-04-14T20:54:44Z (root-cause hypothesis + PR#30) | same channel | fetched | — | Mode A (pre-PR#15, 4-7s fast fail) vs Mode B (post-PR#15, 18-51s slow fail, this bug). Observed fail rate 17.4% (8 fails / 38 successes). SDK error-swallowing analysis. PR #30 bumps claude-agent-sdk 0.1.58→0.1.59 (bundled CLI 2.1.97→2.1.105). Mentions Claude Code CHANGELOG fixes in 2.1.98-2.1.105 matching stalled-streaming signature. | Plan §3 hypothesis, §4 pass/fail thresholds |
| Issue #16 comment — 2026-04-14T21:40:32Z (reopen) | same channel | fetched | — | **"Keeping this open until: at least 20 successful post-bump flushes are accumulated in scripts/flush.log, or at least 72 hours have passed since PR #30 merge, whichever comes later"**. PR #30 merge timestamp: 2026-04-14T20:51:59Z. Closure was premature. | Plan §4 acceptance criteria (this cycle's primary reference) |
| Issue #16 state at plan time | `gh issue view 16` | state: OPEN, 4 comments | — | As of 2026-04-24, issue is still open, PR#30 merged 9+ days ago (both reopen criteria long since past). | Plan §1 (readiness to compute closure decision) |

Verbatim extracts above are sufficient for plan authority; full body/comments are preserved via `gh` CLI and can be re-fetched any time. Codex-side pre-flight may re-fetch the issue as freshness check per Plan §4 Step P2.

---

## §5 — Probes + commands run (Step 7)

| Command | Purpose | Key output |
|---|---|---|
| `grep 'Fatal error in message reader' scripts/flush.log \| awk '{print $1" "$2}'` | Enumerate all Bug-H-signature timestamps | 54 events between `2026-04-13 13:20:44` and `2026-04-23 21:34:32`. Distribution confirms post-bump concentration on 04-19 and 04-21. |
| `awk '$1" "$2 > "2026-04-14 20:51:59" && /Flushed .* chars to daily log/ {ok++} … {fail++}'` | Count post-bump successes/failures (any source) | `post_bump_ok=962 post_bump_fail=38` |
| `grep 'Fatal error in message reader' \| awk '{for(i...) if ($i ~ /^\[/) print}' \| sort \| uniq -c` | Disambiguate source tag for every fatal | `10 [compile]` + `44 [flush]` = 54 total |
| `awk '$1" "$2 > "2026-04-14 20:51:59" && /Fatal/ && /\[flush\]/ {c++}'` | [flush]-only post-bump fatals (Bug H scope) | `28` |
| `awk '$1" "$2 > "2026-04-14 20:51:59" && /Fatal/ && /\[compile\]/ {c++}'` | [compile]-only post-bump fatals (same SDK bug, different subsystem) | `10` |
| `awk '$1" "$2 > "2026-04-23 17:05:00" && /Fatal/ {c++}'` | 24h fatals (all sources) | `2` |
| `awk '$1" "$2 > "2026-04-17 17:05:00" && /Fatal/ {c++}'` | 7d fatals (all sources) | `32` |
| `grep 'Fatal' \| grep '\[flush\]' \| tail -3` | Most recent [flush] Bug H events | `2026-04-22 02:42:15`, `2026-04-22 02:54:07`, `2026-04-22 02:54:07` (last [flush] Bug H at **2026-04-22 02:54:07** — roughly 2.5 days ago) |
| `grep 'Fatal' \| grep '\[compile\]' \| tail -3` | Most recent [compile] same-SDK-bug events | `2026-04-21 21:23:57`, `2026-04-22 22:42:59`, `2026-04-23 21:34:32` (yesterday) |
| `git log -5` via MCP | Commit-level context | no flush.py changes since PR#30; most recent commits are cycle-1 utils.py, mypy config, retrieval refactor |

---

## §6 — Empirical tests (Step 7, if applicable)

### Test 1 — Post-bump [flush]-only success rate (Bug H acceptance scope)

`total = 962 OK + 28 FAIL = 990`
`success_rate = 962 / 990 = 97.17%`

**Comparison to acceptance criterion "real Codex 7-day usage window: flush success rate > 90%"**: ✅ **criterion met** (97.17% >> 90%).

### Test 2 — Reopen-criteria compliance

- **≥20 successful post-bump flushes**: observed 962 ≫ 20. ✅
- **≥72 hours since PR#30 merge (2026-04-14T20:51:59Z → 2026-04-24T17:05Z)**: elapsed ≈ 237 hours ≈ **9.9 days**. ✅ both criteria (whichever-comes-later) satisfied for ~7 days already.

### Test 3 — Residual activity check (critical for informed closure decision)

- 24h [flush]+[compile] Fatal events: **2** (both [compile]: 2026-04-23 21:34:32 and one earlier yesterday)
- 7d Fatal events (all sources): **32**
- Latest [flush] fatal: **2026-04-22 02:54:07** (just over 2 days old)
- Latest [compile] fatal: **2026-04-23 21:34:32** (yesterday — compile hit the same SDK stalled-streaming mode, outside issue #16 scope but same root cause)

**Interpretation**: the bug is NOT fully eliminated — it still reproduces at low rate (~3% overall). Acceptance criterion is a rate threshold, not a zero-failure bar, so it is satisfied while the bug persists as a known low-rate residual.

### Test 4 — `doctor --quick flush_pipeline_correctness` line for current state

(Not re-run in this planning pass — Codex pre-flight runs doctor and captures this line freshly.)

Verdict summary: all three numeric criteria from the reopen comment + the issue body's >90% rate criterion are **satisfied**. The cycle output is a tracking-log snapshot that records this and recommends a closure-review decision; it does NOT itself close the issue (that is a user gate).

---

## §7 — Assumptions + verification status (Step 8)

| Claim | Status | Evidence row / flag |
|---|---|---|
| Issue #16 is still open on GitHub | ✅ verified | §4 row `gh issue view 16` — state: OPEN, 4 comments |
| Closure contract from issue body = {root cause identified OR environmental evidence, fix applied if fixable, >90% success rate in 7d window} | ✅ verified | §4 row tracking-log `## Current closure contract` + fetched issue body (first Gh call) |
| Reopen comment hardens closure gate to {≥20 successful post-bump flushes OR ≥72h since PR#30 merge, whichever-later} | ✅ verified | §4 row 2026-04-14T21:40:32Z comment — verbatim quoted |
| PR #30 merge timestamp = 2026-04-14T20:51:59Z | ✅ verified | tracking-log line 24 + 2026-04-14T20:54:44Z comment |
| flush.log log format is `TIMESTAMP LEVEL [source] message` with `[flush]` vs `[compile]` tags | ✅ verified | §3 `flush.py:42-47` basicConfig + §5 probe output showing both tags |
| SDK "Fatal error in message reader" surfaces via root logger inheritance into flush.log | ✅ verified | issue comment 2026-04-14T20:54:44Z `_internal/query.py:248` + §5 tag-disambiguation shows it appears with caller's tag ([flush] or [compile]) |
| Post-bump [flush]-only success rate = 97.17% | ✅ verified | §5 counts (962 OK, 28 [flush] FAIL) + §6 Test 1 math |
| Observation window has elapsed (72h criterion long since passed) | ✅ verified | §6 Test 2 — 9.9 days since merge |
| Bug is not fully eliminated but is below the 10% failure threshold | ✅ verified | §5 residual counts + §6 Test 3 |
| Compile.py hits the same SDK stalled-streaming bug but is OUT of issue #16 scope | ⚠️ assumed-to-report | Disambiguated in §5 probe; reported as observation in tracking-log snapshot, not as closure blocker. |
| Log parsing heuristic assumes timestamps sort lexicographically (acceptable given fixed-width `YYYY-MM-DD HH:MM:SS` format) | ⚠️ assumed-to-verify-by-Codex | Codex pre-flight should re-run the same awk expressions against freshly-read `flush.log` to catch new events that landed between planning and execution. |
| flush.log is not rotated or truncated mid-cycle | ⚠️ assumed-to-verify-by-Codex | No log-rotation infrastructure found in repo; Codex pre-flight confirms file still spans pre-PR#30 dates. |

---

## §8 — plan-audit skill invocations (Step 10)

| Round | Args | Score | Critical | Important | Optional | Fixes applied |
|---|---|---|---|---|---|---|
| 1 | plan-audit on v1 plan + this audit | 10/10 (self-audit miss recorded) | 0 | 0 | 3 cosmetic | Applied all three. But self-audit did not check whether `bug-h-issue-16-tracking-log.md` was actually tracked — default-assumed tracked because it lives in `docs/codex-tasks/` alongside already-committed files. That assumption was false (see Codex-review-round-1 below). Same class of baseline mistake as cycle-1 PDC baseline. |
| Codex-review-round-1 | Codex adversarial review on v1 plan | blocked (2 critical + 3 important) | 2 | 3 | 0 | **F1** (critical): tracking log is UNTRACKED at HEAD `66260af`; `git diff` cannot prove append-only integrity. → v2 replaces git-diff path with `sha256sum + cp to /tmp + diff -u` content-integrity proof. **F2** (critical): `git status --short` delta is bypassed when target stays `??`→`??`. → v2 allows delta=empty for tracked files; hardening is now the content-integrity check, not git status. **F3** (important): `git ls-files` PDC scan ignores untracked files — any new PD in the new snapshot passes silently. → v2 adds a second PDC channel: explicit `grep -lP` loop over the 5 known untracked cycle artifacts (plan, planning-audit, report, tracking-log, codex-review). Union is compared against allowlist. **F4** (important): report §4.2 template contradicted the untracked reality. → v2 report §4.2 now explicitly documents "cycle artifacts are untracked; expected delta = empty for tracked files" and §4.1 captures the content-integrity path. **F5** (important): D4 allowed "continue with a note" for any new comment. → v2 D4 is hardened: pure context/info continues; criteria-changing comments STOP the cycle. Added new **D-track** to catch opposite-direction surprise (tracking log being tracked would invalidate content-integrity path). |
| 2 | plan-audit on v2 (post Codex-review-round-1 fixes) | 7/10 🟡 | 1 | 0 | 0 | Critical found: §10 Rollback used `git checkout --` on an untracked target, which doesn't work. Applied inline: replaced with `cp /tmp/tracking_log_pre.md → target` + sha/diff verification; added fallback note for TMPDIR cleanup case. v2 plan updated in place. |
| 3 | plan-audit on v2.1 (post rollback fix) | 10/10 ✅ | 0 | 0 | 1 cosmetic (applied) | Rollback verified: `cp /tmp/tracking_log_pre.md → target` + `diff -q` + `sha256sum` — all syntactically correct, TMPDIR-cleanup fallback provided. Cosmetic nit applied: `<HH:MM>` placeholder in fallback text replaced with `<timestamp>` wording so reader doesn't look for that literal substring. Plan ready to re-send to Codex. |

---

## §9 — Delta from prior cycle

First evidence-snapshot cycle for Bug H since 2026-04-16. Prior tracking log entry exists in `bug-h-issue-16-tracking-log.md`; this cycle appends a new dated snapshot to that same file without rewriting history.

---

## §10 — Known gaps (honest flags)

| Gap | Mitigation |
|---|---|
| **Gap-A**: `scripts/flush.log` keeps growing; probe counts taken at a point in time. By the time Codex runs pre-flight, new successes or failures will have landed. | Codex re-runs the same awk probes immediately in pre-flight Step P2; report records both the planning-time numbers (from this file) and the execution-time numbers (from report §2). Closure decision uses execution-time numbers. |
| **Gap-B**: [compile]-tagged Fatal events are visible in the same log and share root cause. They are NOT part of issue #16 scope (which is flush.py Bug H). | Plan treats them as observational only — records in the snapshot under a separate "compile.py same-SDK-bug residual" bullet, explicitly not a closure blocker. If user wants a separate issue for compile.py, that is a follow-up cycle. |
| **Gap-C**: The snapshot report updates a **tracked** repo file (`bug-h-issue-16-tracking-log.md`), unlike cycle-1 which only touched tests + utils. Git-status delta gate must tolerate this single-file append. | Plan §8 whitelist explicitly lists this file; acceptance gate expected lines count change in tracking log only. |
| **Gap-D**: Closure decision itself is a user gate, not an agent gate. Agent only produces evidence. | Plan §8 explicitly states "produces evidence + recommends review; does NOT close the GitHub issue". Codex must NOT call `gh issue close`. |
| **Gap-E**: Issue #16 has labels `bug, codex, hooks`. Closing may require user to also add a `fixed-by: #30` comment or similar per project conventions. | Out of scope. If user proceeds to close, they handle the GH-side paperwork; plan only supplies local evidence. |
| **Gap-F**: GitHub API rate limit was observed during planning (5,000/hr shared). The tracking plan only uses the issue endpoint + no PR re-reads. Codex's gh activity stays minimal (`gh issue view 16` once at pre-flight). | Plan §4 keeps gh calls to one `gh issue view 16 --json state,updatedAt,comments` at pre-flight; no loop, no list calls. |

---

## §11 — Signature

Author: Claude (Opus 4.7 1M)
Cycle: bug-h-evidence-snapshot-2026-04-24, iteration v2 (Codex-review-round-1 findings applied)
Completed at: 2026-04-24T14:40Z (round-1 self-audit 10/10 on v1; Codex-review-round-1 caught untracked-target blocker → v1→v2)
