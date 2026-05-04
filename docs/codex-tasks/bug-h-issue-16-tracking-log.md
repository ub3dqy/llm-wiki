# Bug H Issue #16 — Tracking Log

Issue: <https://github.com/ub3dqy/llm-wiki/issues/16>

Purpose: local evidence log for ongoing monitoring of Bug H (`Fatal error in message reader`)
without spamming the GitHub issue with low-signal daily comments.

## Current closure contract

From the issue body:

- root cause identified, or environmental cause documented with evidence
- if fixable in `flush.py`, fix applied
- real Codex 7-day usage window: flush success rate > 90%

From the reopen comment (`2026-04-14T21:40:32Z`):

- do not re-evaluate closure before **72 hours** since PR #30 merge, or
- before **20 successful post-bump flushes**
- whichever comes later

PR #30 merge timestamp used in this log:

- `2026-04-14 20:51:59` local repo time

## Snapshot — 2026-04-16 10:01 local

### GitHub issue state

- issue state: `open`
- latest issue update: `2026-04-14T21:40:32Z`
- current paper-trail status: reopened because closure after PR #30 was premature

### Post-bump evidence from `scripts/flush.log`

Command basis:

```text
post_bump_ok=89
post_bump_fail=2
post_bump_success_rate=97.8%
last_ok=2026-04-16 10:00:35
last_fail=2026-04-16 00:14:33
```

Interpretation:

- the post-bump success rate is currently **above 90%**
- however, there are still **real post-bump failures**
- therefore the issue is **not ready to close**

### Current active-error signal

From `doctor --quick`:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 2 'Fatal error in message reader' events (7d total: 18, most recent 2026-04-16 00:14:33) — active Bug H regression, investigate issue #16
```

Operational meaning:

- Bug H is still active in the current 24-hour correctness window
- this alone is enough to keep the issue open

### Recovery after latest fail

Evidence from `scripts/flush.log` after the latest fatal event at `2026-04-16 00:14:33`:

- successful flushes after latest fail: `19`
- most recent successful flush: `2026-04-16 10:00:35`

Recent successful flush examples:

```text
2026-04-16 09:50:43 INFO [flush] Flushed 3331 chars to daily log for session 019d7d26-fd6b-7712-b49a-2db94684e0dc
2026-04-16 09:50:49 INFO [flush] Flushed 3101 chars to daily log for session 019d9330-7a1a-78d1-82a4-01c134c00d88
2026-04-16 09:52:00 INFO [flush] Flushed 3114 chars to daily log for session 019d7d26-fd6b-7712-b49a-2db94684e0dc
2026-04-16 09:53:00 INFO [flush] Flushed 2822 chars to daily log for session 019d7d26-fd6b-7712-b49a-2db94684e0dc
2026-04-16 09:54:42 INFO [flush] Flushed 2805 chars to daily log for session 019d7d26-fd6b-7712-b49a-2db94684e0dc
2026-04-16 10:00:35 INFO [flush] Flushed 2715 chars to daily log for session 019d7d26-fd6b-7712-b49a-2db94684e0dc
```

Recent post-bump fatal events:

```text
2026-04-15 18:51:19 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-16 00:14:33 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
```

## Snapshot — 2026-04-24 19:20 UTC

### GitHub issue state

- issue state: `open`
- latest issue update: `2026-04-14T21:40:32Z`
- current paper-trail status: open — candidate for closure review

### Post-bump evidence from `scripts/flush.log`

Command basis (from the 2026-04-24T19:20:40Z execution probe):

```text
POST_FLUSH_OK=969
POST_FLUSH_FAIL=28
POST_COMPILE_FAIL=10
LAST_24H_FATAL=2
LAST_7D_FATAL=31
LAST_FLUSH_FATAL=2026-04-23 19:54:57
LAST_FLUSH_OK=2026-04-24 18:28:33
SUCCESS_RATE=97.19%
```

Interpretation:

- post-bump [flush]-only success rate is `97.19%` vs the 90% acceptance threshold from the issue body -> above
- `969` successful post-bump **flush.py** invocations accumulated (compile.py successes NOT counted) vs the >=20 reopen criterion -> satisfied
- elapsed since PR #30 merge: about `9.9` days vs the 72h reopen criterion -> satisfied
- therefore the issue is a candidate for closure review, with low-rate residual failures still documented

### Current active-error signal

From `doctor --quick`:

```text
[PASS] flush_pipeline_correctness: No 'Fatal error in message reader' events in last 24h (historical: 30 in last 7d, most recent 2026-04-23 21:34:32, tracked in issue #16)
```

Operational meaning: Bug H is not active in the project-defined current 24-hour correctness window; this alone does not close the issue, but it supports a closure-review decision when combined with the aggregate post-bump success rate.

### Recovery after latest fail

- successful flushes after latest [flush]-tagged fatal: `71`
- most recent successful flush: `2026-04-24 18:28:33`
- recent successful flush examples:

```text
2026-04-24 13:29:31 INFO [flush] Flushed 3121 chars to daily log for session 019dbbb5-dd19-7193-bf2f-4163d388b44a
2026-04-24 13:39:06 INFO [flush] Flushed 2778 chars to daily log for session 019dbbb5-dd19-7193-bf2f-4163d388b44a
2026-04-24 17:05:31 INFO [flush] Flushed 2639 chars to daily log for session 019dbc2e-00f5-7071-802c-0768dfd927df
2026-04-24 17:12:41 INFO [flush] Flushed 2154 chars to daily log for session 019dbc2e-00f5-7071-802c-0768dfd927df
2026-04-24 17:18:28 INFO [flush] Flushed 2777 chars to daily log for session 019dbbb5-dd19-7193-bf2f-4163d388b44a
2026-04-24 17:33:37 INFO [flush] Flushed 3359 chars to daily log for session 019dbc2e-00f5-7071-802c-0768dfd927df
2026-04-24 17:33:37 INFO [flush] Flushed 2779 chars to daily log for session 019dbc30-e8b1-73f0-91b9-55bf1a9eb784
2026-04-24 17:50:33 INFO [flush] Flushed 2821 chars to daily log for session 019dbbb5-dd19-7193-bf2f-4163d388b44a
2026-04-24 18:25:10 INFO [flush] Flushed 3141 chars to daily log for session 019dbbb5-dd19-7193-bf2f-4163d388b44a
2026-04-24 18:28:33 INFO [flush] Flushed 2833 chars to daily log for session 019dbc30-e8b1-73f0-91b9-55bf1a9eb784
```

- recent post-bump fatal events:

```text
2026-04-22 22:42:59 ERROR [compile] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-23 19:54:57 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-23 21:34:32 ERROR [compile] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
```

### Compile.py residual (out of scope, observational only)

- post-bump `[compile]` Fatal events: `10`
- most recent `[compile]` Fatal: `2026-04-23 21:34:32`
- note: compile.py hits the same SDK stalled-streaming failure mode via the same Agent SDK query path, but it is out of issue #16 scope. If the user decides to track it, open a separate issue.

### Recommendation

`candidate for closure review` — both reopen-comment criteria are satisfied, the post-bump [flush]-only success rate is above the 90% threshold, and `doctor --quick` reports no current 24-hour active Bug H event. Do not auto-close: the paper trail should still acknowledge the residual low-rate [flush] failures and the separate [compile] same-SDK residual.

## Snapshot — 2026-04-26 14:53 UTC

### GitHub issue state

- issue state: not refreshed in this run
- reason: GitHub CLI network access was unavailable in the current sandbox session
- local paper-trail status: keep open

### Post-bump evidence from `scripts/flush.log`

Command basis:

```text
POST_FLUSH_OK=1034
POST_FLUSH_FAIL=31
LAST_FLUSH_FATAL=2026-04-26 02:35:38
LAST_FLUSH_OK=2026-04-26 14:53:21
SUCCESS_RATE=97.09%
```

Interpretation:

- post-bump [flush]-only success rate remains above the 90% threshold
- the reopen-comment criteria remain satisfied
- however, the failure is still active in the current correctness window

### Current active-error signal

From `doctor --quick`:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 4 'Fatal error in message reader' events (7d total: 28, most recent 2026-04-26 02:35:38) — active Bug H regression, investigate issue #16
```

Operational meaning:

- Bug H is active again in the current 24-hour correctness window
- issue #16 is not closure-ready despite the aggregate success rate

### Recommendation

`keep open` — the aggregate post-bump success rate is healthy, but the latest `doctor --quick`
run reports active 24-hour failures. Re-evaluate only after the active window is clean again.

## Snapshot — 2026-04-26 19:37 UTC

### GitHub issue state

- issue state: `OPEN`
- latest issue update: `2026-04-14T21:40:32Z`
- remote paper-trail status: unchanged since reopen comment

### Post-bump evidence from `scripts/flush.log`

Command basis:

```text
POST_FLUSH_OK=1056
POST_FLUSH_FAIL=31
LAST_FLUSH_FATAL=2026-04-26 02:35:38
LAST_FLUSH_OK=2026-04-26 22:36:34
SUCCESS_RATE=97.15%
```

### Current active-error signal

From `doctor --quick`:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 4 'Fatal error in message reader' events (7d total: 21, most recent 2026-04-26 02:35:38) — active Bug H regression, investigate issue #16
```

Interpretation:

- `doctor --quick` counts all `Fatal error in message reader` lines in `scripts/flush.log`, not
  only `[flush]`
- in this 24-hour window that means `1` `[compile]` fatal at `2026-04-25 23:24:18` plus `3`
  `[flush]` fatals at `2026-04-26 00:39:01`, `01:39:40`, and `02:35:38`
- historical note: this snapshot reflects the pre-2026-04-27 local `doctor.py` behavior before
  `flush_pipeline_correctness` was narrowed to report `[flush]` counts directly

### Recommendation

`keep open` — no new `[flush]` fatal was observed after `2026-04-26 02:35:38`, but the active
24-hour correctness window has not cleared yet. Earliest meaningful re-check is after
`2026-04-27 02:35:38` local log time if no new fatal events appear.

## Snapshot — 2026-04-26 21:26 UTC

### Post-bump evidence from `scripts/flush.log`

Command basis:

```text
POST_FLUSH_OK=1063
POST_FLUSH_FAIL=31
LAST_FLUSH_FATAL=2026-04-26 02:35:38
LAST_FLUSH_OK=2026-04-27 00:21:23
SUCCESS_RATE=97.17%
```

### Current active-error signal

From `doctor --quick` after the local `doctor.py` tag-scope fix:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 3 '[flush] Fatal error in message reader' events (7d flush total: 15, most recent 2026-04-26 02:35:38) — active Bug H regression, investigate issue #16 [note: compile residual 6 in last 7d, latest 2026-04-25 23:24:18]
```

### Recommendation

`keep open` — the doctor signal is now aligned with issue #16 scope (`[flush]` only), but the
24-hour flush window still has not cleared. Re-check after `2026-04-27 02:35:38` local log time.

## Assessment

### Terminology correction

In this repository's paper trail, these are separate bugs:

- **BrokenPipe in `hooks/codex/stop.py`** — fixed by the defensive `_emit_ok()` handling and top-level `except BrokenPipeError`
- **Issue #16 / Bug H** — intermittent `Fatal error in message reader` from `flush.py` / Agent SDK

So the current state is:

- the **BrokenPipe hook bug** appears fixed in shipped code
- **issue #16** is still open because its error signature still appears in the log

Current state is mixed:

- good signal: post-bump aggregate rate looks much better than the original issue estimate
- bad signal: the bug still reproduces in the live 24-hour window

That means:

1. PR #30 may have reduced the failure rate.
2. PR #30 has **not** yet met the issue closure bar.
3. The issue should remain open until there is both:
   - a clean enough observation window, and
   - a closure argument that matches the issue's written acceptance criteria

## Next check

Earliest meaningful re-evaluation point from the reopen comment:

- `2026-04-17 20:51:59` local time (`72h` after PR #30 merge)

But even after that timestamp, closure still requires checking the stricter issue-level contract:

- active failures in the current window
- whether the 7-day usage criterion is actually satisfied

## Update protocol

When revisiting this issue, append only:

- timestamp of check
- post-bump ok/fail counts
- latest fatal timestamp
- `doctor --quick` Bug H line
- short conclusion: `keep open` or `candidate for closure review`

## Snapshot — 2026-04-27 10:09 UTC

### Post-bump evidence from `scripts/flush.log`

Command basis:

```text
POST_FLUSH_OK=1196
POST_FLUSH_FAIL=32
LAST_FLUSH_FATAL=2026-04-27 11:10:36
LAST_FLUSH_OK=2026-04-27 13:08:08
SUCCESS_RATE=97.39%
```

Recent post-bump `[flush]` fatal events:

```text
2026-04-23 19:54:57
2026-04-26 00:39:01
2026-04-26 01:39:40
2026-04-26 02:35:38
2026-04-27 11:10:36
```

### Current active-error signal

From `doctor --quick`:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 1 '[flush] Fatal error in message reader' events (7d flush total: 16, most recent 2026-04-27 11:10:36) — active Bug H regression, investigate issue #16 [note: compile residual 6 in last 7d, latest 2026-04-25 23:24:18]
```

### Recommendation

`keep open` — the prior 24-hour window did not clear cleanly. A new `[flush]` fatal appeared at
`2026-04-27 11:10:36`, so issue #16 is not a closure candidate. Earliest meaningful re-check is
after `2026-04-28 11:10:36` local log time if no newer `[flush]` fatal appears.

## Mitigation attempt — 2026-04-27 11:24 UTC

### Change

`scripts/flush.py` now treats the known Agent SDK reader failure signature as retryable:

```text
Fatal error in message reader
```

The existing retry loop already retried timeout-like failures. This mitigation narrows the new
retry surface to two textual markers only:

- `timeout`
- `fatal error in message reader`

Generic `Command failed with exit code 1` remains non-retryable so auth/config failures are not
silently hidden.

### Verification

```text
uv run pytest tests/test_flush.py -q
5 passed

uv run pytest tests/ -q
98 passed

uv run ruff check scripts/flush.py tests/test_flush.py
All checks passed!

uv run python scripts/wiki_cli.py doctor --quick
13/14 PASS; existing flush_pipeline_correctness FAIL remains from 2026-04-27 11:10:36
```

### Observation requirement

This is a mitigation, not closure evidence. Issue #16 stays `keep open` until post-change live
flush traffic shows the 24-hour window clearing. Next meaningful local re-check remains after
`2026-04-28 11:10:36` local log time unless a newer `[flush]` fatal appears.

GitHub issue update:

- <https://github.com/ub3dqy/llm-wiki/issues/16#issuecomment-4326568455>

## Mitigation follow-up — 2026-04-27 12:26 UTC

### First mitigation result

The `90f0ecd` retry change was insufficient. Live traffic produced three newer `[flush]` fatals:

```text
2026-04-27 14:28:12
2026-04-27 14:45:41
2026-04-27 15:06:26
```

Current post-bump evidence:

```text
POST_FLUSH_OK=1204
POST_FLUSH_FAIL=35
LAST_FLUSH_FATAL=2026-04-27 15:06:26
LAST_FLUSH_OK=2026-04-27 14:20:44
SUCCESS_RATE=97.18%
```

From `doctor --quick`:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 4 '[flush] Fatal error in message reader' events (7d flush total: 19, most recent 2026-04-27 15:06:26) — active Bug H regression, investigate issue #16 [note: compile residual 6 in last 7d, latest 2026-04-25 23:24:18]
```

### Root-cause update for the mitigation

The exact `Fatal error in message reader` marker is visible in `scripts/flush.log`, but not in the
exception text that reaches the retry classifier. The exception path only logged:

```text
Agent SDK query failed: Command failed with exit code 1 (exit code: 1)
```

Therefore the first mitigation never entered its retry branch. The follow-up change broadens the
retry classifier to include opaque `Command failed with exit code 1`, while deny-listing obvious
auth/config/permission failures so persistent setup errors are not silently hidden.

### Verification

```text
uv run pytest tests/test_flush.py -q
8 passed

uv run pytest tests/ -q
101 passed

uv run ruff check scripts/flush.py tests/test_flush.py
All checks passed!

uv run python scripts/wiki_cli.py doctor --quick
13/14 PASS; existing flush_pipeline_correctness FAIL remains from live pre-follow-up events
```

### Observation requirement

Issue #16 remains `keep open`. The latest observed `[flush]` fatal is now
`2026-04-27 15:06:26`; the next meaningful local re-check moves to after
`2026-04-28 15:06:26` local log time unless a newer `[flush]` fatal appears.

GitHub issue update:

- <https://github.com/ub3dqy/llm-wiki/issues/16#issuecomment-4326985287>

## Mitigation follow-up — 2026-04-27 12:55 UTC

### Second mitigation result

The `d850343` opaque-exit retry change was still insufficient under live traffic. It entered the
retry branch, but several flush runs failed all three attempts in a row. The latest unsalvaged
failed flush exit before this follow-up was:

```text
2026-04-27 15:45:53
```

### Change

`scripts/flush.py` now distinguishes two Agent SDK exit-1 cases:

- **no result emitted**: keep retrying and eventually report a failed flush exit
- **`ResultMessage` plus assistant text already emitted**: treat the non-zero process exit as a
  post-result cleanup failure, keep the streamed result, and write it to the daily log

`scripts/doctor.py` was updated to measure the same operational boundary. It now reports failed
flush Agent SDK exits as pipeline failures while keeping raw reader fatal and salvaged post-result
counts as context. This prevents a successfully salvaged `Fatal error in message reader` from
resetting the data-loss observation window.

### Live post-change evidence

The first live flush after the change hit the same SDK reader fatal, but no data was lost:

```text
2026-04-27 15:50:01 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-27 15:50:01 WARNING [flush] Agent SDK exited non-zero after emitting result; using streamed result: Command failed with exit code 1 (exit code: 1)
2026-04-27 15:50:01 INFO [flush] Flushed 99 chars to daily log for session 019dcbcc-4e30-7fa1-8584-19f13f0e88b3
```

From `doctor --quick` after the doctor classification update:

```text
[FAIL] flush_pipeline_correctness: Last 24h: 15 failed flush Agent SDK exits (7d failed flush total: 30, most recent 2026-04-27 15:45:53) — active Bug H regression, investigate issue #16 [reader fatal raw: 38 in last 24h / 53 in last 7d; salvaged post-result: 1 in last 24h / 1 in last 7d] [note: compile residual 6 in last 7d, latest 2026-04-25 23:24:18]
```

### Verification

```text
uv run pytest tests/test_flush.py tests/test_doctor.py -q
12 passed

uv run pytest tests/ -q
105 passed

uv run ruff check scripts/flush.py scripts/doctor.py tests/test_flush.py tests/test_doctor.py
All checks passed!

git diff --check
<no output>

uv run python scripts/wiki_cli.py doctor --quick
14/15 PASS; expected flush_pipeline_correctness FAIL remains from unsalvaged pre-follow-up exits
```

### Observation requirement

Issue #16 remains `keep open`. For data-loss pipeline correctness, the latest unsalvaged failed
flush exit is now `2026-04-27 15:45:53`; the next meaningful local re-check moves to after
`2026-04-28 15:45:53` local log time unless a newer failed flush exit appears.

Raw SDK reader fatals may still appear. They should only reset the project pipeline observation
window if they end in `Agent SDK query failed` / `Agent SDK ProcessError` rather than the new
`Agent SDK exited non-zero after emitting result; using streamed result` salvage path.

### Live follow-up — 2026-04-27 13:15 UTC

Additional live traffic after the salvage change produced five more `[flush] Fatal error in message
reader` events, all salvaged without data loss:

```text
2026-04-27 15:50:01 salvaged + Flushed 99 chars
2026-04-27 15:54:05 salvaged + Flushed 99 chars
2026-04-27 15:57:37 salvaged + Flushed 99 chars
2026-04-27 16:13:29 salvaged + Flushed 99 chars
2026-04-27 16:15:28 salvaged + Flushed 99 chars
```

No newer `Agent SDK query failed` or `Agent SDK ProcessError` line was observed after the latest
unsalvaged failure at `2026-04-27 15:45:53`.

GitHub issue update:

- <https://github.com/ub3dqy/llm-wiki/issues/16#issuecomment-4327294308>

## Snapshot — 2026-04-30 20:00 UTC

### GitHub issue state

- issue state: `OPEN`
- latest issue update: `2026-04-27T13:20:08Z`
- remote paper-trail status: still open after the mitigation updates

### Post-bump evidence from `scripts/flush.log`

Command basis: PowerShell count over log lines after `2026-04-14 20:51:59`, the PR #30 merge
timestamp used by this tracking log.

```text
POST_FLUSH_OK=1122
POST_FLUSH_FAILED_EXIT=46
POST_FLUSH_FATAL_RAW=84
POST_FLUSH_SALVAGED_POST_RESULT=16
POST_COMPILE_FATAL=14
LAST_FLUSH_OK=2026-04-29 01:47:12
LAST_FAILED_FLUSH_EXIT=2026-04-27 15:45:53
LAST_FLUSH_FATAL_RAW=2026-04-29 01:47:12
LAST_FLUSH_SALVAGED=2026-04-29 01:47:12
LAST_COMPILE_FATAL=2026-04-29 01:23:54
LOSS_BOUNDARY_SUCCESS_RATE=96.06%
```

Interpretation:

- the post-bump loss-boundary success rate remains above the 90% issue threshold
- the latest unsalvaged failed flush Agent SDK exit is `2026-04-27 15:45:53`
- later raw `[flush] Fatal error in message reader` events were salvaged after a streamed result,
  so they did not reset the data-loss observation window
- compile.py still has same-SDK residuals, latest `2026-04-29 01:23:54`, but they remain outside
  issue #16 scope

### Current active-error signal

From `doctor --quick`:

```text
[PASS] flush_pipeline_correctness: No failed flush Agent SDK exits in last 24h (historical failed flushes: 18 in last 7d, most recent 2026-04-27 15:45:53, tracked in issue #16) [reader fatal raw: 0 in last 24h / 56 in last 7d; salvaged post-result: 0 in last 24h / 16 in last 7d] [note: compile residual 4 in last 7d, latest 2026-04-29 01:23:54]
```

Operational meaning:

- Bug H is no longer active in the current 24-hour project-defined data-loss window.
- Historical failed exits remain in the 7-day context, so the issue should not be auto-closed
  without an explicit closure decision and a GitHub paper-trail update.

### Recommendation

`candidate for closure review` — the active 24-hour failed-exit window is clean and the aggregate
post-bump success rate is above threshold. Do not close or comment on issue #16 automatically; user
authorization is still required for any remote GitHub action.

## Snapshot — 2026-05-03 18:30 UTC

### Compile.py residual classification

`daily/2026-04-27.md` was retried with `compile.py --file daily/2026-04-27.md` while clearing the
pending compile queue. The live Agent SDK probe showed the root cause for the current compile
blocker:

```text
Your organization does not have access to Claude. Please login again or contact your administrator.
```

Implementation changes made in response:

- `compile.py` now passes `extra_args={"strict-mcp-config": None}` like `flush.py`, keeping the
  subprocess non-interactive.
- `compile.py` detects Agent SDK `ResultMessage.is_error` and reports the concrete access error
  instead of the opaque `Command failed with exit code 1`.
- if no logs compile successfully, `compile.py` skips index rebuild and prints
  `Compilation failed`, not `Compilation complete`.
- `doctor.py --full` now includes `agent_sdk_account_access`, a live account-access probe for the
  Agent SDK path used by flush/compile. `total_tokens_injection` skips cleanly when that access
  probe is unavailable.

Current status:

- issue #16 remains about the flush data-loss boundary, not compile account access.
- pending compile logs remain `2026-04-26.md (changed)` and `2026-04-27.md (new)`.
- do not manually mark these logs ingested; fix Claude account access and rerun compile.

## Snapshot — 2026-05-03 19:35 UTC

### Codex-only/manual backend transition

Claude Code / Claude Agent SDK is currently unavailable for this workspace, so the local runtime
has moved to `WIKI_AGENT_BACKEND=manual`.

Implementation changes made in response:

- `.env` can set `WIKI_AGENT_BACKEND=manual`, while `.env.example` documents the default
  `claude` backend.
- SDK-dependent hook paths (`session-end.py`, `pre-compact.py`, `hooks/codex/stop.py`),
  `flush.py`, `compile.py`, `query.py`, and `seed.py` now skip or return explicit manual-mode
  messages instead of trying to start Claude Agent SDK.
- `doctor.py --full` skips Agent SDK account, token-injection, and flush-roundtrip probes in
  manual backend mode.
- `compile.py --mark-manual --manual-note ...` records a daily log as manually compiled only
  after Codex/human wiki, index, and log updates have been performed.

Current status:

- issue #16 remains historical flush data-loss tracking, not a blocker for Codex-only wiki work.
- pending compile logs remain `2026-04-26.md (changed)` and `2026-04-27.md (new)` until they are
  manually reviewed and then marked with the new manual compile command.

## Snapshot — 2026-05-03 20:05 UTC

### Manual compile queue cleared

Codex manually reviewed and compiled the two remaining compile-worthy daily logs:

- `daily/2026-04-26.md` — changed tail after prior automated compile.
- `daily/2026-04-27.md` — new high-signal log.

Manual compile output was captured in local wiki/index/log/state:

- created `[[concepts/claude-code-channels-mailbox-wakeup]]`
- created `[[concepts/clauder-portable-launcher]]`
- updated related mailbox, launcher, LLM Wiki, and Skolkovo grading pages
- recorded both hashes through `compile.py --mark-manual --manual-note ...`

Current status:

- `wiki_cli.py status` reports `pending: 0`.
- structural lint reports `0 errors, 0 warnings`; remaining items are advisory suggestions.
- issue #16 remains historical flush data-loss tracking only.

## Snapshot — 2026-05-04 07:35 UTC

### GitHub issue state before closure

- issue state: `OPEN`
- latest issue update: `2026-04-27T13:20:08Z`
- remote paper-trail status: still open after the `2375ebe` salvage mitigation

### Current evidence from `scripts/flush.log`

Command basis: PowerShell count over log lines after `2026-04-14 20:51:59`, the PR #30 merge
timestamp used by this tracking log.

```text
POST_FLUSH_OK=1122
POST_FLUSH_FAILED_EXIT=46
POST_FLUSH_FATAL_RAW=84
POST_FLUSH_SALVAGED_POST_RESULT=16
POST_COMPILE_FATAL=16
LAST_FLUSH_OK=2026-04-29 01:47:12
LAST_FAILED_FLUSH_EXIT=2026-04-27 15:45:53
LAST_FLUSH_FATAL_RAW=2026-04-29 01:47:12
LAST_FLUSH_SALVAGED=2026-04-29 01:47:12
LAST_COMPILE_FATAL=2026-05-03 21:13:14
POST_SALVAGE_FLUSH_OK=16
POST_SALVAGE_FAILED_EXIT=0
LOSS_BOUNDARY_SUCCESS_RATE=96.06%
POST_SALVAGE_LOSS_BOUNDARY_SUCCESS_RATE=100%
```

### Gate evidence

From `doctor --quick`:

```text
[PASS] flush_pipeline_correctness: No failed flush Agent SDK exits in last 24h (historical failed flushes: 15 in last 7d, most recent 2026-04-27 15:45:53, tracked in issue #16) [reader fatal raw: 0 in last 24h / 53 in last 7d; salvaged post-result: 0 in last 24h / 16 in last 7d] [note: compile residual 2 in last 24h / 5 in last 7d, latest 2026-05-03 21:13:14]
```

From `doctor --full`: all checks passed. Agent SDK live probes are skipped because the workspace is
currently in `WIKI_AGENT_BACKEND=manual`.

GitHub CI on `c53dd35`:

- Personal Data Check: success
- Wiki Lint / lint: success
- Wiki Lint / pytest-windows: success

### Closure decision

`close as completed` for issue #16. The issue's project-defined data-loss boundary is clean:

- the post-bump loss-boundary success rate is above the 90% acceptance threshold
- there is no failed flush Agent SDK exit in the current 24-hour window
- no unsalvaged failed flush Agent SDK exit appears after `2026-04-27 15:45:53`
- post-result reader failures after `2375ebe` were salvaged and ended in `Flushed 99 chars`

Scope note: compile.py residual Agent SDK failures and current Claude account/manual-backend state are
tracked separately from issue #16. They do not reset the flush.py data-loss observation window.
