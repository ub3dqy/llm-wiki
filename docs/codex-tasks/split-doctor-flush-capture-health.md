# Task — Split doctor flush_capture_health into three independent checks

> **Роль**: исполнитель — Codex. Code refactor task в one file.

> **Иерархия источников правды** (СТРОГО):
> 1. **Официальная документация** — primary source of truth:
>    - Python `re` module: `https://docs.python.org/3/library/re.html`
>    - Python `datetime` module: `https://docs.python.org/3/library/datetime.html`
> 2. **Реальное состояние repo** — secondary:
>    - `<repo-root>/scripts/doctor.py:94-168` — текущая `check_flush_capture_health` function
>    - `<repo-root>/scripts/doctor.py:652-680` — `get_quick_checks` и `get_full_checks` registration
>    - `<repo-root>/scripts/doctor.py:32` — `CAPTURE_HEALTH_WINDOW_DAYS = 7`
>    - `<repo-root>/scripts/flush.log` — real sample data для testing (272 real log entries как of 2026-04-14)
>    - `<repo-root>/hooks/session-end.py` + `<repo-root>/hooks/pre-compact.py` — authoritative SKIP message formats
>    - `<repo-root>/scripts/flush.py` — authoritative "Spawned flush.py" и "Flushed N chars" message formats
>    - GitHub issue #22 (parent #9) — acceptance criteria
> 3. **Этот план** — derived artifact, написан Claude'ом, может ошибаться.

> **Расхождение план vs дока ИЛИ план vs реальный код → побеждает реальность**. Фиксировать в `Discrepancies`.

---

## Source markers used in this plan

Каждое техническое утверждение помечено: `[OFFICIAL-<URL>]` / `[EMPIRICAL-<file:line>]` / `[PROJECT]`. Без marker — escalate в Discrepancies.

---

## Doc verification (ОБЯЗАТЕЛЬНО до правок)

Re-read both pages **right now**, не из памяти.

| URL | What to find | Why |
|---|---|---|
| `https://docs.python.org/3/library/re.html` | `re.search` / `re.findall` semantics, group extraction | New check functions use regex to parse log lines — need exact group capture behavior |
| `https://docs.python.org/3/library/datetime.html#datetime.timedelta` | `timedelta(days=N)` semantics | Three new checks use 7-day window (same as existing) |

If URL unreachable → `BLOCKED: <reason>` в отчёте, stop dependent work.

---

## Problem recap

[EMPIRICAL-scripts/doctor.py:94-168] Current `check_flush_capture_health` returns **one** metric: `spawned / fired` ratio. Warns at `>50%` with suggestion to lower `WIKI_MIN_FLUSH_CHARS`.

[PROJECT] This single metric is **operationally noisy** because it mixes two independent things:
1. **Legitimate filtering** of tiny test sessions (50-100 chars) below `WIKI_MIN_FLUSH_CHARS=500` threshold — this is correct behavior
2. **Actual pipeline failures** — transcript missing, Agent SDK errors, etc.

[PROJECT] At steady-state the ratio hovers near 50-60% even when pipeline is healthy (per investigation in closed #9 и ее follow-up). The warning fires intermittently forever without actionable signal.

## Goal — replace with three independent checks

[PROJECT] Per issue #22 acceptance criteria, replace single check with three:

1. **`flush_throughput`** — `spawned / fired` ratio (same as current metric), но с более мягкими thresholds (warn at >70% skip, info at >85% skip). Renamed to signal that this is **just** throughput, не health.
2. **`flush_quality_coverage`** — `captured_chars / attempted_chars`: of all substantive content seen by hooks, what fraction made it to daily log. More stable metric — short test sessions don't dominate.
3. **`flush_pipeline_correctness`** — count of `Fatal error in message reader` occurrences в last 7 days. Zero = PASS. Non-zero = FAIL with count. **Catches Bug H regressions automatically**.

---

## Contract — parse rules для new metrics

### Existing log line formats [EMPIRICAL]

Все из `scripts/flush.log` observed patterns:

```
2026-04-14 HH:MM:SS INFO [session-end] SessionEnd fired: session=<id>
2026-04-14 HH:MM:SS INFO [session-end] Spawned flush.py for session <id>, project=<name> (<N> turns, <M> chars)
2026-04-14 HH:MM:SS INFO [session-end] SKIP: only <M> chars (min 500)
2026-04-14 HH:MM:SS INFO [session-end] SKIP: no transcript path
2026-04-14 HH:MM:SS INFO [session-end] SKIP: empty context
2026-04-14 HH:MM:SS INFO [session-end] SKIP: debounce — too soon since last spawn
2026-04-14 HH:MM:SS INFO [pre-compact] PreCompact fired: session=<id>
2026-04-14 HH:MM:SS INFO [flush] Starting flush for session <id> (<M> chars)
2026-04-14 HH:MM:SS INFO [flush] Flushed <N> chars to daily log for session <id>
2026-04-14 HH:MM:SS INFO [flush] Flush decided to skip: SKIP: <reason>
2026-04-14 HH:MM:SS ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
```

### flush_throughput parse rules

[PROJECT] Same parsing as existing check, renamed:
- **fired**: lines with `[session-end]` or `[pre-compact]` containing `SessionEnd fired` or `PreCompact fired`
- **spawned**: lines with `[session-end]` or `[pre-compact]` containing `Spawned flush.py`
- `throughput_ratio = spawned / fired`
- Exit code `skip_rate = 1 - throughput_ratio`

**Thresholds** [PROJECT]:
- `skip_rate > 0.85` → warn "very high, possible pipeline issue, investigate flush.py" (was previously 0.5)
- `skip_rate > 0.70` → info "moderate skip rate, monitor"
- Otherwise → PASS
- `spawned == 0 && fired > 0` → FAIL "pipeline broken" (unchanged from existing)

### flush_quality_coverage parse rules

[PROJECT] New metric. Parse `(<M> chars)` from Spawned lines и `SKIP: only <M> chars` from session-end/pre-compact SKIPs.

- **attempted_chars**: sum of all `<M>` values extracted from:
  - `Spawned flush.py for session ... (<N> turns, <M> chars)` lines — those that reached flush.py spawn
  - `SKIP: only <M> chars (min 500)` lines — those filtered by char threshold before spawn
- **captured_chars**: sum of `<M>` values from Spawned lines **where the corresponding session also produced `Flushed <N> chars to daily log`** within the same 7-day window. Note that `N` (summary output) ≠ `M` (input), so we use input `M` as the "captured" numerator (input was captured by pipeline)
- `quality_ratio = captured_chars / attempted_chars`

Simpler approximation [PROJECT] that avoids cross-line session correlation:
- **attempted_chars_simple**: all `Spawned` lines chars + all `SKIP: only N chars` lines chars
- **captured_chars_simple**: all `Spawned` lines chars where **the session did NOT later have** `Fatal error in message reader` OR `Flush decided to skip`

If correlation is too complex, **even simpler** [PROJECT]:
- **attempted**: sum of all `(N chars)` from Spawned lines + sum of all `SKIP: only N chars` chars
- **captured**: sum of all `(N chars)` from Spawned lines
- Ratio = captured / attempted

**The third (simplest) approach is acceptable** per #22 intent — Codex should pick whichever is cleanest to implement robustly. Document the choice in report.

**Thresholds** [PROJECT]:
- `quality_ratio < 0.70` → warn "significant content lost"
- `quality_ratio < 0.85` → info "moderate content filtered"
- Otherwise → PASS

### flush_pipeline_correctness parse rules

[PROJECT] Simplest new check:
- Count lines matching `Fatal error in message reader` within last 7-day window
- `errors == 0` → PASS
- `errors > 0` → FAIL with count + timestamp of most recent occurrence + note "likely Bug H regression, investigate issue #16"

---

## Mandatory external tools

Every row MUST appear в `## Tools used` с ✅ или `BLOCKED`. No dashes.

| Tool | Purpose |
|---|---|
| **WebFetch** `https://docs.python.org/3/library/re.html` | Regex semantics verification |
| **WebFetch** `https://docs.python.org/3/library/datetime.html#datetime.timedelta` | timedelta semantics |
| **Read** `scripts/doctor.py:94-168` | Existing check function |
| **Read** `scripts/doctor.py:32` | Window constant |
| **Read** `scripts/doctor.py:650-680` | Check registration in quick/full |
| **Read** `hooks/session-end.py` | SKIP message formats |
| **Read** `hooks/pre-compact.py` | SKIP message formats |
| **Read** `scripts/flush.py` | Starting/Flushed/Fatal error message formats |
| **Bash** `uv run python scripts/doctor.py --quick` | Pre/post snapshots |
| **Bash** `uv run python scripts/lint.py --structural-only` | Regression guard |
| **Bash** Inline Python for testing parse functions on real `flush.log` | Unit-test equivalent |
| **MCP filesystem** if available | Optional structured file ops |
| **MCP git** if available | Optional git status |

---

## Files to modify (whitelist)

**Only**: `scripts/doctor.py`

Не трогать:
- `hooks/` any file
- `scripts/flush.py`
- `scripts/lint.py`
- Any config
- Any wiki content
- Any existing `docs/codex-tasks/` file (except this task's own report)

---

## Implementation plan

### Step 1 — Remove old `check_flush_capture_health`

Delete the function at `scripts/doctor.py:94-168`. Also remove its registration from `get_quick_checks` (around line 656) и `get_full_checks` (around line 674).

Document removal in report с exact pre-state line ranges.

### Step 2 — Add three new check functions

Добавить **в тот же module-level scope** (после existing env_settings check, before `check_python`):

```python
def check_flush_throughput() -> CheckResult:
    """Measure spawned/fired ratio for capture hooks (throughput only, not health)."""
    # 1. Read FLUSH_LOG if exists, else return PASS "no log yet"
    # 2. Compute cutoff = now - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
    # 3. Parse lines, count fired and spawned events within window
    # 4. If fired == 0 → PASS "no activity"
    # 5. If spawned == 0 && fired > 0 → FAIL "pipeline broken: nothing spawned"
    # 6. Compute skip_rate = 1 - spawned/fired
    # 7. Thresholds: >85% warn, >70% info, else PASS
    # 8. Return CheckResult with detail including raw N/M ratio

def check_flush_quality_coverage() -> CheckResult:
    """Measure what fraction of session content actually reaches daily log."""
    # 1. Same file-load / cutoff pattern
    # 2. Parse chars from Spawned lines via regex
    # 3. Parse chars from SKIP lines via regex
    # 4. attempted = spawned_chars + skip_only_chars
    # 5. captured = spawned_chars
    # 6. If attempted == 0 → PASS "no activity"
    # 7. Compute ratio = captured / attempted
    # 8. Thresholds: <70% warn, <85% info, else PASS
    # 9. Return CheckResult with detail including captured/attempted numbers

def check_flush_pipeline_correctness() -> CheckResult:
    """Catch Bug H regressions: zero 'Fatal error in message reader' lines expected."""
    # 1. Same file-load / cutoff pattern
    # 2. Count lines matching 'Fatal error in message reader' within window
    # 3. Track most recent occurrence timestamp
    # 4. errors == 0 → PASS
    # 5. errors > 0 → FAIL with count + most-recent timestamp + hint "Bug H regression, see #16"
```

All three share common parsing code — **consider extracting a `_parse_flush_log_events()` helper** that reads the file once and returns structured data (`fired`, `spawned`, `spawned_chars`, `skip_only_chars`, `fatal_errors`, `latest_fatal_ts`). This avoids reading the file three times.

### Step 3 — Register в both `get_quick_checks` and `get_full_checks`

Replace single `check_flush_capture_health()` call с three new check calls in same position в the list. Both quick и full modes should include all three.

### Step 4 — Verification

See Verification phases below.

---

## Verification phases

### Phase 1 — pre-edit snapshot (Codex runs first)

```bash
uv run python scripts/doctor.py --quick 2>&1 | grep -E "(flush_capture|structural_lint)"
```

Record exact output. **Expected** [EMPIRICAL]: `[PASS] flush_capture_health: Last 7d: N/M flushes spawned (skip rate X%)...`.

### Phase 2 — implement + unit test each new check on real flush.log

After implementation, for each of the 3 new functions run:

```bash
uv run python -c "
import sys
sys.path.insert(0, 'scripts')
from doctor import check_flush_throughput, check_flush_quality_coverage, check_flush_pipeline_correctness
for check_fn in [check_flush_throughput, check_flush_quality_coverage, check_flush_pipeline_correctness]:
    r = check_fn()
    print(f'[{\"PASS\" if r.ok else \"FAIL\"}] {r.name}: {r.message}')
"
```

Capture exact output in report. Each check should return sensible values based on real `flush.log` data.

**Quality bar**:
- `flush_throughput`: detail должен match what existing check produced (same numbers, different framing)
- `flush_quality_coverage`: должен return meaningful ratio (not 100%, not 0% на real data)
- `flush_pipeline_correctness`: должен return real count of `Fatal error in message reader` lines in last 7 days. **Test that Bug H historical entries are captured** — run `grep -c "Fatal error in message reader" scripts/flush.log` and verify the check's count matches what's within 7-day window.

### Phase 3 — doctor --quick full run

```bash
uv run python scripts/doctor.py --quick 2>&1 | tail -40
```

Should show **three new check lines** instead of one `flush_capture_health`. Old name should NOT appear.

### Phase 4 — doctor --full regression

```bash
uv run python scripts/doctor.py --full 2>&1 | tail -50
```

All previously-PASS checks should remain PASS. New three checks should appear in full mode too.

### Phase 5 — regression on unrelated lint

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -5
```

Should be unchanged: `0 errors, 0 warnings, 37 suggestions` (or similar).

---

## Acceptance criteria

- ✅ Doc verification: 2 URLs re-read, цитаты в report
- ✅ Mandatory tools table filled — no dashes
- ✅ Old `check_flush_capture_health` removed from `scripts/doctor.py`
- ✅ Three new functions implemented: `check_flush_throughput`, `check_flush_quality_coverage`, `check_flush_pipeline_correctness`
- ✅ Common parsing helper `_parse_flush_log_events` (or similar) avoids triple file-read (or explicit justification in report why single-pass was rejected)
- ✅ All three registered в `get_quick_checks` AND `get_full_checks`
- ✅ Phase 2 unit-test each new check standalone on real flush.log — all three return sensible values
- ✅ Phase 3 `doctor --quick` shows three new check lines, old name absent
- ✅ Phase 4 `doctor --full` shows three new check lines, no regression
- ✅ Phase 5 lint unchanged
- ✅ Bug H historical entries captured by `flush_pipeline_correctness` — verify count matches real grep output
- ✅ Whitelist: only `scripts/doctor.py` modified
- ✅ No commit / push

---

## Out of scope

- Fixing Bug H (#16) — orthogonal
- Lowering `WIKI_MIN_FLUSH_CHARS` — separate policy
- Updating `hooks/` to log additional fields — don't touch hooks
- Updating `scripts/flush.py` — don't touch
- Adding new metrics beyond the three specified
- Changing `CAPTURE_HEALTH_WINDOW_DAYS` constant

---

## Rollback

```bash
git checkout scripts/doctor.py
```

---

## Pending user actions

After Codex completes:
1. Review the three new check outputs — are thresholds actionable?
2. Decide whether to PR as separate commit or bundle with other changes
3. Confirm Bug H tracking via new check — useful signal или too noisy?

---

## Notes для исполнителя (Codex)

- **One file change only**. Don't touch hooks, flush.py, or anywhere else.
- **Doc verification IS mandatory** — re-fetch URLs even if you think you know them.
- **Source markers** `[OFFICIAL]` / `[EMPIRICAL]` / `[PROJECT]` on every technical claim в report. If you find one без marker in this plan, escalate.
- **Quality coverage metric** has three alternative implementations (simple/less-simple/simplest). **Pick the simplest that works robustly** and document the choice in report. Don't over-engineer.
- **Helper function** `_parse_flush_log_events` is recommended но не required — if single-pass vs three-pass tradeoff isn't clear, document reasoning и pick one.
- **Real `flush.log`** has 272 relevant entries as of 2026-04-14 (per Claude's pre-flight grep). Use this as test data for Phase 2.
- **`Fatal error in message reader`** count in current log includes Bug H historical failures. Verify new check catches them within 7-day window.
- **NO commit / push** — leave diff for user review.
- **Placeholder convention** in report: `${USER}`, `<repo-root>`, `<user-home>`.
- Create report в `docs/codex-tasks/split-doctor-flush-capture-health-report.md` следуя стандартной структуре (Pre-flight, Doc verification, Implementation, Phase 1-5 verification, Tools used, Discrepancies, Self-audit).
- **Verifier для самопроверки**: после написания каждого раздела report, ask: *"можно ли удалить этот claim и report остаётся consistent?"*. Если да — claim из головы, escalate.
