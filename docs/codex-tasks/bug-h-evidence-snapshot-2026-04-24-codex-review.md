# Codex Review — bug-h-evidence-snapshot-2026-04-24

**Plan reviewed**: `bug-h-evidence-snapshot-2026-04-24.md` v1
**Planning audit reviewed**: `bug-h-evidence-snapshot-2026-04-24-planning-audit.md`
**Report template reviewed**: `bug-h-evidence-snapshot-2026-04-24-report.md`
**Reviewer**: Codex
**Review time**: 2026-04-24
**Verdict**: `blocked`

---

## Summary

The plan is not executable as written. Its hard gates assume
`docs/codex-tasks/bug-h-issue-16-tracking-log.md` is already tracked, but the
current repository state shows it is untracked.

Evidence:

```text
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-planning-audit.md
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-report.md
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24.md
?? docs/codex-tasks/bug-h-issue-16-tracking-log.md
```

```text
error: pathspec 'docs/codex-tasks/bug-h-issue-16-tracking-log.md' did not match any file(s) known to git
Did you forget to 'git add'?
```

Current HEAD:

```text
66260af
```

---

## Findings

### F1 — Critical: append-only proof is invalid for an untracked target

Plan §8 requires the tracking log to show exactly one new snapshot section with
prior content byte-for-byte unchanged, and says the diff should show only `+`
lines. That proof path works for a tracked file. It does not work for an
untracked file because normal `git diff docs/codex-tasks/bug-h-issue-16-tracking-log.md`
does not compare it to any committed baseline.

Impact: Codex cannot prove the append-only claim using the plan's specified
commands. Proceeding would turn a hard gate into a manual assertion.

Required fix: update the plan/report to either:

- make the tracking log part of the tracked artifact set before this cycle, or
- explicitly treat it as a new tracked file and verify append-only against a
  pre-execution copy/hash captured in `/tmp`.

### F2 — Critical: git-status delta gate cannot detect changes to this target

Plan §7 and §8 expect post-append status delta to show:

```text
M docs/codex-tasks/bug-h-issue-16-tracking-log.md
```

But the file is already `??` before execution. After appending, it will still be
`??`, so a pre/post `git status --short` delta can remain empty for the actual
target mutation.

Impact: the primary scope-creep gate cannot prove that the intended file changed
and cannot distinguish "nothing happened" from "untracked file content changed".

Required fix: add a file-content proof for the untracked target, such as
`sha256sum` before/after plus a `diff -u /tmp/pre ...` check, or require staging
the handoff/tracking-log files before execution so `git diff --cached` can prove
the change.

### F3 — Important: PDC gate ignores the untracked target and handoff artifacts

The plan's PDC detector uses `git ls-files`, which only scans tracked files.
Because the target tracking log and new handoff artifacts are currently
untracked, the detector will not scan the new snapshot content or the handoff
files.

Impact: the PDC gate can pass while missing new personal-data-like strings in
the files created or modified by this cycle.

Required fix: either track the task files before running the PDC gate, or add an
explicit supplemental scan for the cycle's untracked files.

### F4 — Important: report template assumes a single tracked-file delta

Report §4.2 says the expected delta is the tracking log only, "plus handoff
artifacts". Since all handoff files and the tracking log are untracked at
pre-flight, the current template cannot accurately represent the actual
baseline/delta relationship without ad hoc explanation.

Impact: the final report would either contradict command output or omit the
reason the hard gate was weakened.

Required fix: revise report §2 and §4 to capture:

- which files were already untracked at pre-flight,
- which untracked files are part of this handoff package,
- how content integrity is proven for the target tracking log.

### F5 — Important: GitHub freshness can change the closure contract

The plan handles new GitHub comments as D4 and says to continue with a note.
That is acceptable only if the new comment does not alter the closure contract.

Impact: if issue #16 has a newer user or maintainer comment changing the closure
bar, proceeding with the old recommendation could be misleading.

Required fix: tighten D4 wording: if new comments after
`2026-04-14T21:40:32Z` change closure criteria, stop and return to Claude/user
instead of continuing with the existing template.

---

## Recommended Revision

Revise the plan to v2 before execution.

Minimum acceptable changes:

1. Decide whether `bug-h-issue-16-tracking-log.md` is meant to become tracked in
   this cycle.
2. Replace tracked-file-only append proof with a proof that works for the actual
   current state.
3. Extend PDC scanning to include the untracked cycle artifacts, or stage them
   before PDC.
4. Update report §4.2 / §4.3 to match the revised proof path.
5. Tighten D4 around new GitHub comments that alter closure criteria.

Until then, Codex should not execute the append step.

---

## Re-review — v2.1 handoff

**Plan reviewed**: `bug-h-evidence-snapshot-2026-04-24.md` v2 text with v2.1 rollback fix recorded in planning audit
**Planning audit reviewed**: `bug-h-evidence-snapshot-2026-04-24-planning-audit.md` through audit round 3
**Report template reviewed**: `bug-h-evidence-snapshot-2026-04-24-report.md` v2
**Reviewer**: Codex
**Review time**: 2026-04-24
**Verdict**: `executable with monitored gates`

### Evidence checked

```text
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-codex-review.md
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-planning-audit.md
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-report.md
?? docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24.md
?? docs/codex-tasks/bug-h-issue-16-tracking-log.md
```

```text
docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24.md 0
docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-planning-audit.md 0
docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-report.md 0
docs/codex-tasks/bug-h-evidence-snapshot-2026-04-24-codex-review.md 0
docs/codex-tasks/bug-h-issue-16-tracking-log.md 0
```

### Adversarial risks re-checked

1. Untracked target append proof: fixed. Step P1 captures pre-edit `sha256sum` and a byte copy in `/tmp`; Phase 2 uses `diff -u` against that pre-copy and rejects non-additive `-` lines.
2. Git-status blind spot for `??` files: mitigated. Status delta is no longer the proof that the target changed; the sha/content diff is.
3. PDC blind spot for untracked artifacts: fixed. Phase 2 scans tracked files and explicitly scans the five known untracked cycle artifacts.
4. GitHub freshness drift: guarded. D4 now stops if a new comment changes closure criteria. Execution must classify any comment after `2026-04-14T21:40:32Z` before appending.
5. Rollback for untracked target: fixed in planning-audit round 3. Rollback restores from `/tmp/tracking_log_pre.md` and verifies byte identity.
6. Version-label mismatch: non-blocking. The plan header still says `v2`, while the planning audit records the rollback-corrected handoff as `v2.1`. This is a documentation mismatch, not a proof-path blocker.

### Execution condition

Proceed only if pre-flight gates P1-P6 pass. In particular, stop without appending if issue #16 is closed, if a new criteria-changing GitHub comment exists, if `scripts/flush.log` appears truncated, if `POST_FLUSH_OK=0`, or if the target file is unexpectedly tracked.

### Post-execution D7 follow-up

The first post-append PDC run failed because the repository baseline contained doc-only path-literal hits from the previous task package and the current handoff plan. This was not caused by the new tracking-log snapshot. Codex rolled back the snapshot, removed those documentation path literals, changed the cycle PDC expectation to an empty baseline, reran pre-flight, and re-appended. Final PDC outputs are empty for tracked files, untracked cycle artifacts, merged set, and delta.
