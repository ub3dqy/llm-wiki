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
