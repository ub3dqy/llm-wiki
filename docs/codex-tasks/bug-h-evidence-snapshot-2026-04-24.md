# Bug H evidence snapshot — 2026-04-24

**Version**: v2 (2026-04-24; v1 → v2 Codex-review-round-1 findings applied: **F1+F2** target file `docs/codex-tasks/bug-h-issue-16-tracking-log.md` is actually **untracked** on HEAD `66260af` (same as every handoff file in this cycle — matches cycle-1 model where task-artifact docs stay untracked until the final commit). Append-only proof and git-status delta gate rewritten to use **sha256sum + pre-copy snapshot in /tmp** instead of tracked-file-only git commands. **F3** PDC gate extended to explicitly scan the cycle's known untracked artifacts in addition to `git ls-files` (since git-based scan ignores untracked files). **F4** report §2/§4 sections revised to reflect that all cycle artifacts are untracked at pre-flight. **F5** D4 hardened: if new comments after reopen timestamp **alter the closure contract**, STOP and notify Claude; only pure context/info additions are allowed to continue. v1 rolled out by me on false assumption "tracking log is tracked" — my own Gap-C flag was wrong.)
**Planning audit**: `bug-h-evidence-snapshot-2026-04-24-planning-audit.md` (sibling)
**Report template**: `bug-h-evidence-snapshot-2026-04-24-report.md` (sibling)
**Target tracking file**: `docs/codex-tasks/bug-h-issue-16-tracking-log.md` (append-only snapshot per its §Update protocol)
**GitHub issue**: <https://github.com/ub3dqy/llm-wiki/issues/16>
**Governing contract**: `docs/claude-system-operating-contract.md`
**Executor**: Codex
**Predecessor**: master HEAD (`66260af` after cycle-1)

---

## §1 — Why this plan exists

Last snapshot in `bug-h-issue-16-tracking-log.md` is dated **2026-04-16 10:01**. Both reopen-comment criteria (≥20 successful post-bump flushes AND ≥72 hours since PR#30 merge) were long since satisfied, but no fresh snapshot has been produced since. User asked to continue by priority queue; Bug H is next up.

This cycle produces an **evidence-gathering snapshot** — no code changes. Output is appended to the existing tracking file so the closure-review decision can be made on current data instead of 8-day-old numbers.

Authority: issue body closure contract, reopen comment gating rule, `scripts/flush.log` raw data. See planning-audit §4 for verbatim quotes.

---

## §2 — Hierarchy of truth sources

Per `docs/claude-system-operating-contract.md`:

1. Official docs — N/A this cycle.
2. User's explicit instructions — «вперед по очереди»; go on P3 Bug H after cycle 1.
3. Factual tool / test results — planning-audit §5 (probes) and §6 (empirical counts).
4. Agreed process documents — `bug-h-issue-16-tracking-log.md` defines the snapshot-append protocol.
5. Project memory — contextual only.

---

## §3 — Doc Verification

N/A — no external library / language-feature claims. All claims are local file and log content; verified empirically.

---

## §4 — Pre-flight verification (Codex-executed)

### Step P1 — Git baseline + target-file content snapshot (NEW in v2)

```bash
cd "<repo-root>"
git rev-parse HEAD                               # expected: 66260af (cycle-1 tip) or later
git status --short | sort > /tmp/git_status_pre_bugh.txt
wc -l /tmp/git_status_pre_bugh.txt

# Target-file tracked-status confirmation — this cycle REQUIRES it to be untracked
# (append-only proof path depends on this). STOP if the file is unexpectedly tracked.
git ls-files docs/codex-tasks/bug-h-issue-16-tracking-log.md > /tmp/tracking_log_ls_files.txt
test ! -s /tmp/tracking_log_ls_files.txt || { echo "D-track: tracking log is tracked — content-integrity path differs, STOP and notify Claude"; exit 1; }

# Content-integrity baseline: sha256 + byte-for-byte copy to /tmp
sha256sum docs/codex-tasks/bug-h-issue-16-tracking-log.md > /tmp/tracking_log_pre.sha
cp docs/codex-tasks/bug-h-issue-16-tracking-log.md /tmp/tracking_log_pre.md
wc -l /tmp/tracking_log_pre.md
cat /tmp/tracking_log_pre.sha
```

### Step P2 — Read target files (full reads required)

- `docs/codex-tasks/bug-h-issue-16-tracking-log.md` — full (schema + §Update protocol, so append matches existing style)
- `scripts/flush.py` head + grep for log format (confirm basicConfig tag `[flush]`)
- `scripts/compile.py` grep for basicConfig to re-confirm `[compile]` tag writes to same `scripts/flush.log` — this is what makes tag-disambiguation necessary

### Step P3 — Freshness re-check on issue #16

```bash
gh issue view 16 --repo ub3dqy/llm-wiki --json state,updatedAt,comments \
  --jq '{state, updatedAt, comment_count: (.comments | length), last_comment_at: (.comments | last.createdAt // "none")}' \
  > /tmp/issue_16_state.json
cat /tmp/issue_16_state.json
```

Expected: state == "open", last_comment_at == "2026-04-14T21:40:32Z" (reopen comment), comment_count == 4.

**If state is "closed"** — STOP (D1): the cycle premise is invalidated, nothing to snapshot; notify Claude.

**If there are new comments** after 2026-04-14T21:40:32Z — record their text in report §2.4 before continuing; user may have already changed the closure contract.

### Step P4 — flush.log sanity

```bash
ls -la scripts/flush.log
head -1 scripts/flush.log | cut -d' ' -f1,2                   # first line date
tail -1 scripts/flush.log | cut -d' ' -f1,2                   # last line date
wc -l scripts/flush.log
```

Expected: file exists, first line near `2026-04-10 19:56:09` (earliest known), last line within the current session window.

### Step P5 — Empirical probe (the core of this cycle)

```bash
# 1. Post-PR#30 [flush]-only success count (Bug H scope — acceptance criterion)
POST_FLUSH_OK=$(awk '$1" "$2 > "2026-04-14 20:51:59" && /Flushed .* chars to daily log/ {c++} END{print c+0}' scripts/flush.log)

# 2. Post-PR#30 [flush]-only FAIL count (Bug H scope — acceptance criterion)
POST_FLUSH_FAIL=$(awk '$1" "$2 > "2026-04-14 20:51:59" && /Fatal error in message reader/ && /\[flush\]/ {c++} END{print c+0}' scripts/flush.log)

# 3. Post-PR#30 [compile]-only FAIL count (same-SDK bug, NOT Bug H scope — observational only)
POST_COMPILE_FAIL=$(awk '$1" "$2 > "2026-04-14 20:51:59" && /Fatal error in message reader/ && /\[compile\]/ {c++} END{print c+0}' scripts/flush.log)

# 4. Last 24h Fatal events (all sources)
LAST_24H_FATAL=$(awk -v cutoff="$(date -u -d '24 hours ago' '+%Y-%m-%d %H:%M:%S')" '$1" "$2 > cutoff && /Fatal error in message reader/ {c++} END{print c+0}' scripts/flush.log)

# 5. Last 7d Fatal events (all sources)
LAST_7D_FATAL=$(awk -v cutoff="$(date -u -d '7 days ago' '+%Y-%m-%d %H:%M:%S')" '$1" "$2 > cutoff && /Fatal error in message reader/ {c++} END{print c+0}' scripts/flush.log)

# 6. Most recent [flush] Bug H event timestamp
LAST_FLUSH_FATAL=$(grep 'Fatal error in message reader' scripts/flush.log | grep '\[flush\]' | tail -1 | awk '{print $1" "$2}')

# 7. Most recent successful flush timestamp
LAST_FLUSH_OK=$(grep 'Flushed .* chars to daily log' scripts/flush.log | tail -1 | awk '{print $1" "$2}')

# 8. Success rate arithmetic (two-decimal)
TOTAL=$((POST_FLUSH_OK + POST_FLUSH_FAIL))
SUCCESS_RATE=$(awk -v ok="$POST_FLUSH_OK" -v total="$TOTAL" 'BEGIN {if (total==0) print "N/A"; else printf "%.2f\n", (ok/total)*100}')

# Persist for §3 acceptance cross-check
printf "POST_FLUSH_OK=%s\nPOST_FLUSH_FAIL=%s\nPOST_COMPILE_FAIL=%s\nLAST_24H_FATAL=%s\nLAST_7D_FATAL=%s\nLAST_FLUSH_FATAL=%s\nLAST_FLUSH_OK=%s\nSUCCESS_RATE=%s\n" \
  "$POST_FLUSH_OK" "$POST_FLUSH_FAIL" "$POST_COMPILE_FAIL" "$LAST_24H_FATAL" "$LAST_7D_FATAL" "$LAST_FLUSH_FATAL" "$LAST_FLUSH_OK" "$SUCCESS_RATE" \
  > /tmp/bugh_snapshot.env
cat /tmp/bugh_snapshot.env
```

### Step P6 — `doctor --quick flush_pipeline_correctness` line capture

```bash
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run python scripts/wiki_cli.py doctor --quick > /tmp/doctor_bugh.txt 2>&1
grep 'flush_pipeline_correctness' /tmp/doctor_bugh.txt
# Expected shape: [PASS|FAIL] flush_pipeline_correctness: Last 24h: N 'Fatal error in message reader' events (7d total: M, most recent YYYY-MM-DD HH:MM:SS) — ...
```

Record the verbatim line in report §2.6.

---

## §5 — Whitelist (strict)

### MAY modify

- `docs/codex-tasks/bug-h-issue-16-tracking-log.md` — **append** a new snapshot section at the end of the file, matching the existing 2026-04-16 snapshot shape. Do NOT rewrite existing sections. Do NOT reorder.

### MUST NOT modify

- Any file in `scripts/` — no code changes.
- `docs/codex-tasks/bug-h-issue-16-tracking-log.md` existing content (only append).
- GitHub issue #16 itself (NO `gh issue close`, NO `gh issue comment` except if user explicitly requests).
- `scripts/flush.log` — read-only source of truth.
- `wiki/`, `daily/`, `index.md`, `log.md`, `reports/`, `raw/` — gitignored, unrelated.
- Any other tracked path.

---

## §6 — Change N specs

### Change 1 — Append snapshot to `bug-h-issue-16-tracking-log.md`

Inserted as a new top-level section AFTER the existing `## Snapshot — 2026-04-16 10:01 local` block and BEFORE `## Assessment`. New section template (exact wording — Codex fills `<bracketed>` placeholders from Step P5/P6 values):

```markdown
## Snapshot — 2026-04-24 <HH:MM> local

### GitHub issue state

- issue state: `open`
- latest issue update: `<value from Step P3 last_comment_at>`
- current paper-trail status: `<open — candidate for closure review | open — new comment activity detected (see execution report §2.4) | closed — investigate, cycle premise invalidated>`

### Post-bump evidence from `scripts/flush.log`

Command basis (from Step P5):

\```text
POST_FLUSH_OK=<N>
POST_FLUSH_FAIL=<N>
POST_COMPILE_FAIL=<N>
LAST_24H_FATAL=<N>
LAST_7D_FATAL=<N>
LAST_FLUSH_FATAL=<YYYY-MM-DD HH:MM:SS>
LAST_FLUSH_OK=<YYYY-MM-DD HH:MM:SS>
SUCCESS_RATE=<NN.NN>%
\```

Interpretation:

- post-bump [flush]-only success rate is `<NN.NN>%` vs the 90% acceptance threshold from the issue body → `<above | at | below>`
- `<N>` successful post-bump **flush.py** invocations accumulated (compile.py successes NOT counted) vs the ≥20 reopen criterion → `<satisfied | not satisfied>`
- elapsed since PR#30 merge: `<N>` days vs the 72h reopen criterion → `<satisfied | not satisfied>`
- therefore the issue is `<candidate for closure review | not ready to close — reason>`

### Current active-error signal

From `doctor --quick` (Step P6):

\```text
<verbatim flush_pipeline_correctness line>
\```

Operational meaning: `<Bug H is / is not> still active in the current 24-hour correctness window (<N> events); this <alone supports | alone does not support> a closure decision.`

### Recovery after latest fail (optional — include if there are successful flushes after LAST_FLUSH_FATAL)

- successful flushes after latest [flush]-tagged fatal: `<N>`
- most recent successful flush: `<YYYY-MM-DD HH:MM:SS>`
- recent successful flush examples:

\```text
<5-10 grep'd log lines of "Flushed N chars to daily log ..." from after LAST_FLUSH_FATAL, verbatim>
\```

- recent post-bump fatal events:

\```text
<last 2-3 Fatal lines from log, verbatim, including both [flush] and [compile] tags for completeness>
\```

If no successful flushes after LAST_FLUSH_FATAL (rare edge case), write "no successful flushes since latest fatal — concerning, investigate before closure review" and skip the block.

### Compile.py residual (out of scope, observational only)

- post-bump `[compile]` Fatal events: `<N>`
- most recent `[compile]` Fatal: `<YYYY-MM-DD HH:MM:SS>`
- note: compile.py hits the same SDK stalled-streaming failure mode via the same Agent SDK query path, but it is out of issue #16 scope. If the user decides to track it, open a separate issue.

### Recommendation

`<keep open — reason>` OR `<candidate for closure review — cite which acceptance criteria are met and which residuals remain>`.
```

Exact timestamp (`<HH:MM>`) must be UTC captured at snapshot-append time so the file retains its chronological contract.

---

## §7 — Verification phases

### Phase 1 — Codex pre-flight

Record raw outputs of Steps P1-P6 verbatim in report §2.

### Phase 2 — Post-append verification

```bash
# Append-only proof via content diff (target is UNTRACKED — git diff cannot help).
# Use the byte-for-byte pre-copy captured in Step P1.
diff -u /tmp/tracking_log_pre.md docs/codex-tasks/bug-h-issue-16-tracking-log.md \
  > /tmp/tracking_log_diff.txt || true
cat /tmp/tracking_log_diff.txt

# Expected content in /tmp/tracking_log_diff.txt:
#   - unified-diff header lines (--- /tmp/tracking_log_pre.md ... / +++ docs/... ...) — OK
#   - one hunk header `@@ ... @@` — OK
#   - one or more `+` lines (new snapshot content) — OK
#   - ZERO `-` lines (any `-` line that is NOT a header means prior content was modified)
#   - zero context `' '` mismatches around the insertion point
# Programmatic check:
if grep -En '^-[^-]' /tmp/tracking_log_diff.txt | grep -v '^--- ' ; then
  echo "FAIL: non-additive change detected in tracking log (some prior content was altered/removed)"
  exit 1
fi

# Post-edit sha: must DIFFER from pre-edit (otherwise nothing was appended)
sha256sum docs/codex-tasks/bug-h-issue-16-tracking-log.md > /tmp/tracking_log_post.sha
cat /tmp/tracking_log_post.sha
if diff -q /tmp/tracking_log_pre.sha /tmp/tracking_log_post.sha > /dev/null ; then
  echo "FAIL: tracking log sha unchanged — append did not happen"
  exit 1
fi

# Git-status delta check (tracked files only).
# Since both target (tracking log) and handoff artifacts are UNTRACKED, none of them
# produce tracked deltas. Therefore the delta MUST be empty — any non-empty delta
# means this cycle touched a tracked file beyond scope.
git status --short | sort > /tmp/git_status_post_bugh.txt
diff /tmp/git_status_pre_bugh.txt /tmp/git_status_post_bugh.txt > /tmp/git_status_delta_bugh.txt || true
cat /tmp/git_status_delta_bugh.txt
# Note: a benign delta can still appear if a new untracked file was created
# (prefixed with `??`). Allow only the cycle's own known untracked paths.
awk '/^[<>] /{sub(/^[<>] ...\s*/,"",$0); print}' /tmp/git_status_delta_bugh.txt | sort -u > /tmp/git_delta_paths_bugh.txt
grep -vE '^(docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24.*\.md|docs/codex-tasks/bug-h-issue-16-tracking-log\.md|docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-codex-review\.md)$' \
  /tmp/git_delta_paths_bugh.txt > /tmp/git_delta_unexpected_bugh.txt || true
test ! -s /tmp/git_delta_unexpected_bugh.txt || { echo "FAIL: unexpected paths in git-status delta"; cat /tmp/git_delta_unexpected_bugh.txt; exit 1; }

# Ruff / pytest intentionally NOT re-run (no Python code changed).

# PDC detector — TWO channels (F3 fix):
#   (a) tracked files, same as cycle-1 pattern with CI-matching PCRE `-lP`
git ls-files -z | grep -zv 'personal-data-check.yml' \
  | xargs -0 grep -lP '/mnt/[a-z]/[A-Z]|[A-Z]:/[A-Z]|C:\\\\Users' | sort > /tmp/pdc_tracked_bugh.txt

#   (b) untracked cycle artifacts (the 4 known bug-h task files). git ls-files
#       cannot see them; scan each explicitly.
for f in \
  docs/codex-tasks/bug-h-issue-16-tracking-log.md \
  docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24.md \
  docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-planning-audit.md \
  docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-report.md \
  docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-codex-review.md ; do
  [ -f "$f" ] && grep -lP '/mnt/[a-z]/[A-Z]|[A-Z]:/[A-Z]|C:\\\\Users' "$f"
done | sort > /tmp/pdc_untracked_bugh.txt

# Merged PDC view
cat /tmp/pdc_tracked_bugh.txt /tmp/pdc_untracked_bugh.txt | sort -u > /tmp/pdc_post_bugh.txt

# Expected combined allowlist: empty after the D7 baseline cleanup.
: > /tmp/pdc_expected_bugh.txt
diff /tmp/pdc_post_bugh.txt /tmp/pdc_expected_bugh.txt > /tmp/pdc_delta_bugh.txt || true
test ! -s /tmp/pdc_delta_bugh.txt || { echo "FAIL: PDC set differs from expected baseline"; cat /tmp/pdc_delta_bugh.txt; exit 1; }
```

### Phase 3 — Awaits user

Codex reports back with:
- planning-time vs execution-time probe numbers (both captured)
- new snapshot content (verbatim)
- doctor `flush_pipeline_correctness` line
- any discrepancies

Claude reviews, surfaces to user. User decides whether to close issue #16 separately.

---

## §8 — Acceptance criteria

Hard gates (all must hold):

- [ ] Target file IS untracked at pre-flight (Step P1 `tracking_log_ls_files.txt` empty). If tracked, STOP — proof path differs.
- [ ] Prior tracking-log content byte-identical: `diff -u /tmp/tracking_log_pre.md docs/codex-tasks/bug-h-issue-16-tracking-log.md` shows only `+` additive lines (no `-` lines outside the `--- /tmp/...` header).
- [ ] Tracking-log sha256 DIFFERS pre vs post (proves append happened): `/tmp/tracking_log_pre.sha` ≠ `/tmp/tracking_log_post.sha`.
- [ ] New snapshot section located between existing `## Snapshot — 2026-04-16 10:01 local` and `## Assessment` (verify by grep over post-file: both markers present, new section's start index between them).
- [ ] Snapshot body contains all six fields per §6 Change 1 template (issue state, post-bump evidence block, doctor line, `### Recovery after latest fail` (if applicable), compile residual note, recommendation, UTC timestamp in the header).
- [ ] Planning-time vs execution-time numbers: chose one approach explicitly (see report §3.1), both captured in report §4.5.
- [ ] `git status` tracked-file delta empty OR limited to the 5 allowlisted untracked cycle artifacts (see Phase 2 awk/grep filter). Any other path = scope creep.
- [ ] PDC detector `(tracked ∪ untracked cycle artifacts)` output matches the expected clean baseline (empty).
- [ ] No `gh issue close` / `gh issue comment` calls made. (Verified by report §4.4 `gh` inventory.)
- [ ] No code files (anything under `scripts/`, `tests/`, `hooks/`, `dashboard/`) touched.

Soft gates (document, do not block):

- Doctor `flush_pipeline_correctness` may remain FAIL — that is expected while Bug H exists at any non-zero rate; it is not a closure blocker by itself.
- Planning-time and execution-time probe numbers may differ by a few events — record both, annotate the delta.

---

## §9 — Out of scope

- Closing GitHub issue #16. Agent produces evidence only; user decides closure.
- Commenting on GitHub issue #16. If user wants a summary comment there, that's a separate follow-up.
- Touching `scripts/flush.py` — no code change.
- Cleaning `flush.log` — read-only.
- Investigating compile.py stalled-streaming residual — observational note only; if tracked, separate cycle.
- Any wiki-health work (broken links, provenance, orphan pages) — out of stream.
- Bumping claude-agent-sdk beyond 0.1.59 — separate decision if needed.

---

## §10 — Rollback

Target is untracked, so `git checkout --` does NOT apply (returns `pathspec ... did not match any file(s)`). Restore from the pre-snapshot captured in Step P1:

```bash
cp /tmp/tracking_log_pre.md docs/codex-tasks/bug-h-issue-16-tracking-log.md

# Verify content byte-identical to pre-execution:
diff -q /tmp/tracking_log_pre.md docs/codex-tasks/bug-h-issue-16-tracking-log.md
# Expected: silent success (exit 0, no output).

sha256sum docs/codex-tasks/bug-h-issue-16-tracking-log.md
# Expected: matches /tmp/tracking_log_pre.sha byte-for-byte.
```

If `/tmp/tracking_log_pre.md` was purged by system TMPDIR cleanup between Step P1 and rollback, alternative is to manually edit the file and remove the `## Snapshot — 2026-04-24 <timestamp>` section (with its actual UTC timestamp) up to (but not including) the `## Assessment` header. That block is the entire addition of this cycle.

No tracked files mutated this cycle, so no tracked-tree rollback needed.

---

## §11 — Discrepancy checkpoints (STOP + report)

- **D1**: `gh issue view 16` state is NOT `open` → cycle premise invalid, STOP, notify Claude.
- **D2**: `scripts/flush.log` first-line timestamp is significantly later than `2026-04-10 19:56:09` → log may have been rotated/truncated, numbers may not reflect full post-bump window; STOP, notify Claude.
- **D3**: Step P5 `POST_FLUSH_OK` is 0 → parsing/awk failure; STOP and dump raw `grep` output to report, notify Claude.
- **D4 (hardened in v2 per F5)**: New comments on issue #16 after 2026-04-14T21:40:32Z require a classification step: (a) **pure context/info** (status mention, cross-reference, wiki-page pointer) → continue snapshot with verbatim quote in report §2.4; (b) **criteria-changing** (new numeric bar, new blocking condition, closure-definition edit) → STOP, do NOT append any snapshot, notify Claude for re-alignment. Codex decides classification based on content; if unsure, treat as (b) and STOP.
- **D-track (new in v2)**: `git ls-files docs/codex-tasks/bug-h-issue-16-tracking-log.md` returns non-empty (file is already tracked) → the untracked-target proof path does not apply; STOP, notify Claude to re-choose content-integrity approach.
- **D5**: Computed `SUCCESS_RATE` is below 90% → snapshot records it honestly with "not ready to close" recommendation; do not soften. Proceed (not a blocker for this cycle since this cycle is evidence-only).
- **D6**: `git status --short` post-append shows modifications to any file OTHER than `bug-h-issue-16-tracking-log.md` → STOP, revert, investigate.
- **D7**: PDC detector surfaces any path OTHER than `docs/codex-tasks/wiki-freshness-phase1.md` → STOP, investigate scope creep (must match cycle-1 baseline exactly).
- **D8**: The 72h / 20-flush reopen criteria are unexpectedly NOT satisfied (e.g., PR#30 merge was later than recorded, flush.log is unexpectedly sparse) → STOP, notify Claude to re-derive the contract.

---

## §12 — Self-audit checklist

- [x] All numeric claims backed by planning-audit §5 probes (empirical, not from memory).
- [x] Whitelist strict; MUST NOT list explicit.
- [x] Append-only snapshot protocol respects tracking log §Update protocol.
- [x] 9 discrepancy checkpoints (+1 D-track in v2), ≥5 required.
- [x] No `gh issue close` / `gh issue comment` — evidence-only role enforced.
- [x] PDC gate two-channel: tracked (`git ls-files | -lP`) + untracked cycle artifacts (explicit loop) — F3 applied.
- [x] Content-integrity proof path is sha256 + /tmp byte-copy + `diff -u`, NOT `git diff` (F1+F2 applied; target is untracked).
- [x] Git-status gate is delta-based AND allows the 5 known untracked cycle artifacts; any other path fails.
- [x] D4 hardened to stop on criteria-changing comments (F5 applied).
- [x] Pre-flight adds D-track gate to catch the opposite-direction surprise (tracking log unexpectedly tracked).

---

## §13 — Notes for Codex

- WSL env: `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run ...` for the doctor call. Other probes are plain Bash.
- Claude Agent SDK NOT invoked — no API cost.
- `gh` CLI is authenticated; rate limit at planning time was 4,992 / 5,000 remaining. Keep calls minimal.
- `flush.log` may update mid-run (active session on this machine). Treat probe numbers as point-in-time; record the exact `date -u` alongside them in report §2.5.
- After completion: mailbox reply in new thread `bug-h-evidence-snapshot-2026-04-24` referencing this plan + report.

---

## §14 — Commits strategy

Single commit, only if user explicitly requests after review:

```
docs(bug-h): append 2026-04-24 tracking-log snapshot

Post-PR#30 evidence recount from scripts/flush.log:
- [flush]-only success rate: <NN.NN>% (<ok>/<total>) vs 90% threshold
- most recent [flush] Fatal: <timestamp>
- [compile] same-SDK-bug residuals: <N> post-bump (out of issue #16 scope)
- doctor --quick flush_pipeline_correctness line captured verbatim

Both reopen-comment criteria (≥20 successful post-bump flushes, ≥72h since
PR#30 merge 2026-04-14T20:51:59Z) satisfied ~7 days ago. Issue #16 is
candidate for closure review; the bug persists at low rate as known residual.

No code changes. Append-only update to tracking log per its §Update protocol.
See docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24.md.
```

No split. No push. Commit only on explicit user command after review.
