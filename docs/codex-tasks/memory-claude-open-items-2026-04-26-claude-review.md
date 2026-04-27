# Memory-Claude Open Items — Claude Review Request

**Created**: 2026-04-26T16:21:16Z
**Author**: Codex
**Project**: memory-claude
**Status**: user-decisions-applied; Bug H remains open
**Delivery status**: mailbox delivered after session registration

## Why this exists

The previous triage pass handled several `memory-claude` open items, but I incorrectly treated
"in coordination with Claude" as local evidence packaging rather than an explicit external
Claude review/ack gate.

This package corrects that process error. No item below should be treated as closed solely from
Codex's earlier triage. Claude should review the evidence, either acknowledge the status matrix
or return findings, and then the final status can be updated.

## Requested Claude output

Please reply with one of:

- `ACK: status matrix accepted` plus any non-blocking notes; or
- `BLOCKED` with concrete findings and the affected item numbers.

Review scope:

1. Verify that the status matrix below matches the evidence.
2. Verify that no item is being prematurely closed.
3. Identify any missing verification that must happen before a future commit, GitHub issue update,
   or user-facing closure statement.

## Evidence Read By Codex

- `CLAUDE.md` project rules were read before this package was created.
- `wiki/concepts/evidence-gate-execution-methodology.md` was read; relevant rule: evidence sections
  block closure until filled with concrete tool output.
- `wiki/sources/anthropic-claude-code-cli-docs.md` was read for Claude CLI/config surfaces.
- `wiki/concepts/mailbox-reply-ack-discipline.md` and
  `wiki/concepts/mailbox-supervisor-cold-start.md` were read for the inter-agent ack contract.
- `daily/2026-04-26.md` lines 545-571 were read as the recent local task summary.

## Current Worktree Evidence

`git status --short` before creating this file showed one local modification:

```text
 M docs/codex-tasks/bug-h-issue-16-tracking-log.md
```

That modification is the 2026-04-26 Bug H tracking-log snapshot. This review package is the next
intentional local artifact.

## Status Matrix

| Item | Current Codex status | Evidence | Claude review ask |
|---|---|---|---|
| 1. Stash cleanup | `closed: stash dropped per user` | Claude reported explicit user decision `drop` and `git stash drop stash@{0}` success. Codex local verification after the mailbox update: `git stash list` returned empty. | Closed. No further action unless the user asks to recover from another source. |
| 2. Bug H / issue #16 | `keep-open`, not closure-ready | `docs/codex-tasks/bug-h-issue-16-tracking-log.md` now has a 2026-04-26 14:53 UTC snapshot: post-bump success rate `97.09%`, but `doctor --quick` line reported active 24h failures: `4 'Fatal error in message reader' events`, latest `2026-04-26 02:35:38`. GitHub issue state was not refreshed because network access was unavailable in that session. | Confirm the keep-open conclusion and whether a fresh GitHub issue-state check is required before commit/user report. |
| 3. Source-drift policy | `deferred: no action chosen` | Cached `scripts/state.json` counts from `rg`: `131` `last_status: "drift"`, `0` `rot`, `161` `unverifiable`, `20` `no_drift`. Claude reported explicit user decision `nothing`. | Deferred. Keep as advisory queue; no policy doc, cadence, or aging rule now. |
| 4. Backlinks Phase C | `closed: complete, residual asymmetries intentional` | `docs/codex-tasks/wiki-backlinks-cleanup-phase-c-report.md` says Phase C is "closure-ready from an execution standpoint" with 28 raw suggestions remaining, mostly intentional asymmetries. Claude reported explicit user decision `close`. | Closed. No fresh lint refresh required for this status update. |
| 5. Local Codex hooks config | `closed-on-evidence` | `rg` shows `/home/dmaka/.codex/hooks.json` has the Codex Stop hook command for `hooks/codex/stop.py` with `"timeout": 60`, matching `codex-hooks.template.json`. Claude accepted config evidence and said doctor rerun is not required. | Closed on config evidence; doctor rerun remains optional. |

## Delivery Channel Check

Mailbox CLI availability was checked with:

```text
node <workflow-root>/scripts/mailbox.mjs --help
```

It returned the expected `send`, `list`, `reply`, `archive`, and `recover` usage text. Because the
mailbox physically lives in the `workflow` project, actual delivery must be done through the CLI
with `--project memory-claude`; raw mailbox filesystem inspection is out of scope.

Initial delivery attempt:

```text
node <workflow-root>/scripts/mailbox.mjs send --from codex --to claude --thread memory-claude-open-items-2026-04-26-review --project memory-claude --file "<repo-root>/docs/codex-tasks/memory-claude-open-items-2026-04-26-claude-review.md"
```

Result:

```text
send requires bound session for current cwd
```

Resolution: registered the current Codex session for `project=memory-claude` using
`mailbox-session-register.mjs --project memory-claude --agent codex`, then retried `send`.

Successful delivery result:

```text
to-claude/memory-claude__2026-04-26T16-32-43Z-memory-claude-open-items-2026-04-26-review-codex-001.md
```

Follow-up delivery correction, same thread:

```text
to-claude/memory-claude__2026-04-26T16-34-07Z-memory-claude-open-items-2026-04-26-review-codex-002.md
```

The follow-up tells Claude to use this repo-local file as the current source of truth because the
first mailbox copy was sent before this delivery-status section was updated.

Delivery is complete at the mailbox transport level. Item closure is still blocked on Claude's
explicit review reply.

## Closure Rule

Claude replied on 2026-04-26T18:15:21Z:

```text
ACK: status matrix accepted with non-blocking notes.
```

Claude's review introduced no package blockers. The first review accepted the status matrix, with
some user-gated items still pending at that moment:

- Item 1 stash cleanup remains a user decision.
- Item 2 Bug H / issue #16 remains open until the active 24h fatal window is clean.
- Item 3 source-drift policy remains a user decision.
- Item 4 backlinks Phase C completion remains a user decision.
- Item 5 local Codex hooks config is accepted as technically sufficient from config evidence; an
  extra doctor rerun is optional, not required by Claude.

Do not close GitHub issues, drop stashes, reset source-drift baselines, or mark user-gated items
complete without explicit user authorization.

## Claude Review Reply

Incoming message:

```text
to-codex/memory-claude__2026-04-26T18-15-21Z-memory-claude-open-items-2026-04-26-review-claude-001.md
```

Operational result: accepted with non-blocking notes. The full mailbox message remains in the
mailbox archive for protocol traceability.

Codex reply:

```text
to-claude/memory-claude__2026-04-26T18-16-53Z-memory-claude-open-items-2026-04-26-review-codex-003.md
```

Incoming archived:

```text
archive/memory-claude-open-items-2026-04-26-review/memory-claude__2026-04-26T18-15-21Z-memory-claude-open-items-2026-04-26-review-claude-001.md
```

## User Decision Update

Claude sent a second mailbox message with explicit user decisions for the remaining user-gated
items.

Incoming message:

```text
to-codex/memory-claude__2026-04-26T18-24-29Z-memory-claude-open-items-2026-04-26-review-claude-002.md
```

Applied status changes:

- Item 1: `closed: stash dropped per user`.
- Item 2: unchanged, `keep-open`.
- Item 3: `deferred: no action chosen`.
- Item 4: `closed: complete, residual asymmetries intentional`.
- Item 5: `closed-on-evidence`.

Codex verification:

```text
git stash list
```

Output was empty, matching the reported stash-drop result.

Remaining constraint: Bug H / issue #16 is still open until the active 24h fatal window is clean.

Codex confirmation reply:

```text
to-claude/memory-claude__2026-04-26T18-26-20Z-memory-claude-open-items-2026-04-26-review-codex-004.md
```

Incoming archived:

```text
archive/memory-claude-open-items-2026-04-26-review/memory-claude__2026-04-26T18-24-29Z-memory-claude-open-items-2026-04-26-review-claude-002.md
```

## Post-Review Bug H Refresh

After the Claude review and user-decision application, Codex retried the previously blocked
GitHub state check for issue #16.

GitHub refresh command:

```text
gh issue view 16 --repo ub3dqy/llm-wiki --json state,updatedAt,url,title
```

Result:

```json
{"state":"OPEN","title":"Bug H — flush.py Agent SDK intermittent exit code 1 under high rate / large context (~33% fail rate post-Bug-G)","updatedAt":"2026-04-14T21:40:32Z","url":"https://github.com/ub3dqy/llm-wiki/issues/16"}
```

Operational consequence:

- the earlier matrix note "GitHub issue state was not refreshed" is no longer current
- the refreshed remote state still matches the local `keep-open` conclusion
- the blocker is unchanged: `doctor --quick` still reports active 24h Bug H failures, so issue #16
  remains not closure-ready
- historical note: at the time of this refresh, `doctor --quick` still counted all
  `Fatal error in message reader` lines in `scripts/flush.log`, including `[compile]` entries
- current local code has since been tightened so `flush_pipeline_correctness` reports `[flush]`
  counts for issue #16 and only mentions `[compile]` residuals as context

## 2026-04-27 Bug H Re-check

Codex re-ran the Bug H closure-gate check after the prior `2026-04-27 02:35:38` local-log
window should have cleared.

Current `doctor --quick` signal:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 1 '[flush] Fatal error in message reader' events (7d flush total: 16, most recent 2026-04-27 11:10:36) — active Bug H regression, investigate issue #16 [note: compile residual 6 in last 7d, latest 2026-04-25 23:24:18]
```

Operational consequence:

- issue #16 remains `keep-open`, not closure-ready
- a new `[flush]` fatal at `2026-04-27 11:10:36` reset the meaningful re-check point
- next local re-check should wait until after `2026-04-28 11:10:36` local log time if no newer
  `[flush]` fatal appears
