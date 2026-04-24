# Execution Report — bug-h-evidence-snapshot-2026-04-24

**Plan**: `bug-h-evidence-snapshot-2026-04-24.md` v2 with v2.1 rollback fix and Codex D7 cleanup
**Planning audit**: `bug-h-evidence-snapshot-2026-04-24-planning-audit.md`
**Executor**: Codex
**Started**: `2026-04-24T15:12:10Z` mailbox receipt, execution resumed `2026-04-24T19:10Z`
**Completed**: `2026-04-24T19:22:09Z`
**Status**: `passed`

---

## §1 — Code-authority reads

### `scripts/flush.py` basicConfig lines 42-47

```python
logging.basicConfig(
    filename=str(SCRIPTS_DIR / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [flush] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

### `scripts/compile.py` basicConfig block

```python
logging.basicConfig(
    filename=str(_SCRIPTS_DIR_FOR_LOG / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [compile] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

### Tracking-log update protocol

````markdown
## Update protocol

When revisiting this issue, append only:

- timestamp of check
- post-bump ok/fail counts
- latest fatal timestamp
- `doctor --quick` Bug H line
- short conclusion: `keep open` or `candidate for closure review`
```

---

## §2 — Pre-flight outputs

### §2.1 — Git baseline + untracked-target confirmation

```text
HEAD=66260af0dc0076c1d2e50f5a95dfdf4e9d93c281
git_status_pre_lines=141
git ls-files docs/codex-tasks/bug-h-issue-16-tracking-log.md -> <empty>
pre_sha=9be4af89f0a74481892146d802d5503785a241c49cba8707bbda1a4e1740cffa
pre_lines=136
```

Target-file tracked-status check passed: the tracking log is untracked, so the content-integrity proof path applies.

### §2.2 — `scripts/flush.log` sanity

```text
-rwxrwxrwx 1 dmaka dmaka 1165752 Apr 24 18:28 scripts/flush.log
first_timestamp=2026-04-10 19:56:09
last_timestamp=2026-04-24 18:28:33
line_count=9479
```

### §2.3 — Issue #16 freshness

```json
{"comment_count":4,"last_comment_at":"2026-04-14T21:40:32Z","state":"OPEN","updatedAt":"2026-04-14T21:40:32Z"}
```

State: `OPEN`. New comments after `2026-04-14T21:40:32Z`: no.

### §2.4 — New comment text

No new comments.

### §2.5 — Empirical probe

Probe timestamp: `2026-04-24T19:20:40Z`

```text
POST_FLUSH_OK=969
POST_FLUSH_FAIL=28
POST_COMPILE_FAIL=10
LAST_24H_FATAL=2
LAST_7D_FATAL=31
LAST_FLUSH_FATAL=2026-04-23 19:54:57
LAST_FLUSH_OK=2026-04-24 18:28:33
SUCCESS_RATE=97.19
```

Math check: `969 + 28 = 997`; `969 / 997 * 100 = 97.19%`.

### §2.6 — Doctor line

```text
[PASS] flush_pipeline_correctness: No 'Fatal error in message reader' events in last 24h (historical: 30 in last 7d, most recent 2026-04-23 21:34:32, tracked in issue #16)
```

---

## §3 — Execution

### §3.1 — Decision on planning-time vs execution-time numbers

Chose execution-time numbers for the snapshot body because `scripts/flush.log` is live and the plan requires point-in-time recounting.

Planning-time values from the audit were `POST_FLUSH_OK=962`, `POST_FLUSH_FAIL=28`, `POST_COMPILE_FAIL=10`. Execution-time values were `969`, `28`, and `10`; delta is `+7` successful flushes, `+0` flush failures, `+0` compile failures.

### §3.2 — Appended snapshot content

```markdown
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

Interpretation: both reopen-comment criteria are satisfied and the [flush]-only post-bump success rate is above 90%; residual low-rate failures remain documented.

Doctor line: `[PASS] flush_pipeline_correctness`.

Recommendation: `candidate for closure review`; do not auto-close from this cycle.
````

### §3.3 — Insertion-point confirmation

```text
old_snapshot_line=26
new_snapshot_line=90
assessment_line=167
ordered=true
```

The new block is after the 2026-04-16 snapshot and before `## Assessment`.

---

## §4 — Post-verification

### §4.1 — Append-only diff

```text
pre_sha=9be4af89f0a74481892146d802d5503785a241c49cba8707bbda1a4e1740cffa
post_sha=457e4656f625a551ada67abd11b27cbd168b7d075b6261caec8e48c8c47ac256
pre_vs_post_sha_same=no
tracking_log_diff_lines=86
non_additive_lines=<empty>
```

The unified diff contains only the new `## Snapshot — 2026-04-24 19:20 UTC` block plus diff headers.

### §4.2 — Git-status delta

```text
status_delta=<empty>
delta_paths=<empty>
unexpected_paths=<empty>
```

Pre-baseline was intentionally reset after D7 PDC cleanup and before the final append proof. The tracking log remained `??` before and after append, so status delta is expected to be empty; the content hash/diff is the proof that the target changed.

### §4.3 — PDC detector

```text
pdc_tracked=<empty>
pdc_untracked=<empty>
pdc_merged=<empty>
pdc_delta=<empty>
```

The original plan expected an older allowlist hit. Actual repository state had additional doc-only PDC hits from prior task artifacts and one current handoff plan path literal. Codex removed those path literals before the final pre-baseline and updated this cycle's PDC expectation to an empty clean baseline.

### §4.4 — `gh` call inventory

```text
gh issue view 16 --repo ub3dqy/llm-wiki --json state,updatedAt,comments --jq '{state, updatedAt, comment_count: (.comments | length), last_comment_at: (.comments | last.createdAt // "none")}'
```

No `gh issue close` and no `gh issue comment` calls were made.

### §4.5 — Delta from planning-time numbers

```text
planning:  POST_FLUSH_OK=962 POST_FLUSH_FAIL=28 POST_COMPILE_FAIL=10
execution: POST_FLUSH_OK=969 POST_FLUSH_FAIL=28 POST_COMPILE_FAIL=10
delta: +7 successes, +0 flush failures, +0 compile failures
```

---

## §5 — Discrepancies encountered

- D7 fired on the first post-append PDC run. The failing hits were documentation path literals, not new snapshot content. Codex rolled back the snapshot, removed the path literals from task artifacts, changed the PDC expectation to an empty baseline, reran pre-flight, and re-appended.
- The plan's UTC-cutoff raw probe reported `LAST_24H_FATAL=2`, while `doctor --quick` reported no current 24h events. The snapshot preserves the raw probe value and uses the doctor line as the project-defined correctness signal.
- `doctor --quick` produced its normal ignored lint report side effect because structural lint has existing issues. The report file is not part of git status and no code was changed.

---

## §6 — Acceptance matrix

| Gate | Result | Evidence |
|---|---|---|
| Target file untracked at pre-flight | pass | §2.1 |
| Prior content byte-identical except additive snapshot | pass | §4.1 |
| Post sha differs from pre sha | pass | §4.1 |
| New snapshot section inserted at the right place | pass | §3.3 |
| Snapshot contains required fields | pass | §3.2 |
| Planning-time vs execution-time choice made | pass | §3.1, §4.5 |
| Git-status delta limited | pass | §4.2 |
| PDC detector matches baseline | pass after D7 remediation | §4.3, §5 |
| No `gh issue close` / `gh issue comment` | pass | §4.4 |
| No code files touched by this cycle | pass | §4.2 and git delta by exclusion |

Soft gates:

- doctor `flush_pipeline_correctness`: PASS.
- planning-to-execution delta: `+7` flush successes only.

---

## §7 — Final summary

- File appended: `docs/codex-tasks/bug-h-issue-16-tracking-log.md`
- New section timestamp: `2026-04-24 19:20 UTC`
- Recommendation recorded: `candidate for closure review`
- Post-bump [flush]-only success rate: `97.19%`
- Last [flush] Bug H event: `2026-04-23 19:54:57`
- Compile residual note included: yes
- Cycle closed: passed

---

## §8 — Notification

Reply sent: `to-claude/memory-claude__2026-04-24T19-25-01Z-bug-h-evidence-snapshot-2026-04-24-codex-002.md`

Incoming archived: `archive/bug-h-evidence-snapshot-2026-04-24/memory-claude__2026-04-24T15-12-10Z-bug-h-evidence-snapshot-2026-04-24-claude-002.md`
