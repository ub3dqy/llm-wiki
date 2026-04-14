# Report — Split doctor flush_capture_health into three independent checks

> Заполнено по фактическим командам и текущему состоянию `<repo-root>`. Технические утверждения помечены `[OFFICIAL]`, `[EMPIRICAL]` или `[PROJECT]`.

---

## Pre-flight

- [x] Read `docs/codex-tasks/split-doctor-flush-capture-health.md` fully `[PROJECT]`
- [x] Read `scripts/doctor.py:94-168` (current `check_flush_capture_health`) `[EMPIRICAL-<repo-root>/scripts/doctor.py:94-168]`
- [x] Read `scripts/doctor.py:32` (`CAPTURE_HEALTH_WINDOW_DAYS = 7`) `[EMPIRICAL-<repo-root>/scripts/doctor.py:32-34]`
- [x] Read `scripts/doctor.py:650-680` (check registration в quick/full) `[EMPIRICAL-<repo-root>/scripts/doctor.py:652-675]`
- [x] Read `hooks/session-end.py` and `hooks/pre-compact.py` (SKIP message formats) `[EMPIRICAL-<repo-root>/hooks/session-end.py:62-137] [EMPIRICAL-<repo-root>/hooks/pre-compact.py:60-135]`
- [x] Read `scripts/flush.py` (Starting/Flushed/Fatal error formats) `[EMPIRICAL-<repo-root>/scripts/flush.py:147-243]`
- [x] Understand: whitelist = ONLY `scripts/doctor.py` `[PROJECT]`
- [x] Understand: one file modified, three new functions replacing one old `[PROJECT]`
- [x] Understand: real `flush.log` is test data source `[EMPIRICAL-<repo-root>/scripts/flush.log]`

---

## Doc verification

> Re-read now, not from memory.

### Python `re`

URL: `https://docs.python.org/3/library/re.html`

| Что проверял | Цитата |
|---|---|
| `re.search` return value | `[OFFICIAL-https://docs.python.org/3/library/re.html]` `re.search()` scans through a string looking for the first location where the regular expression pattern produces a match, and returns a corresponding Match object. Return None if no position in the string matches the pattern.` |
| Group capture syntax | `[OFFICIAL-https://docs.python.org/3/library/re.html]` `Without arguments, group1 defaults to zero (the whole match is returned). If a groupN argument is zero, the corresponding return value is the entire matching string; if it is a positive integer, it is the string matching the corresponding parenthesized group.` |
| `re.findall` vs `re.finditer` | `[OFFICIAL-https://docs.python.org/3/library/re.html]` `The result depends on the number of capturing groups in the pattern. If there are no groups, return a list of strings matching the whole pattern. If there is exactly one group, return a list of strings matching that group. If multiple groups are present, return a list of tuples of strings matching the groups.` |

### Python `datetime`

URL: `https://docs.python.org/3/library/datetime.html#datetime.timedelta`

| Что проверял | Цитата |
|---|---|
| `timedelta(days=N)` construction | `[OFFICIAL-https://docs.python.org/3/library/datetime.html#datetime.timedelta]` `>>> year = dt.timedelta(days=365)` |
| `datetime.now() - timedelta(...)` arithmetic | `[OFFICIAL-https://docs.python.org/3/library/datetime.html#datetime.timedelta]` `date2 = date1 - timedelta` ... `Computes date2 such that date2 + timedelta == date1.` |

### Conclusion

`re.search(...).group(1)` и `re.search(...).group(2)` безопасны для нашей задачи при проверке на `None`, а `timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)` остаётся корректным способом задать 7-дневное окно `[OFFICIAL-https://docs.python.org/3/library/re.html] [OFFICIAL-https://docs.python.org/3/library/datetime.html#datetime.timedelta]`.

---

## Initial state

### doctor --quick output (relevant subset)

```powershell
uv run python scripts/doctor.py --quick 2>&1 | Select-String 'flush_capture|flush_throughput|flush_quality|flush_pipeline|structural_lint'
```

```text
[PASS] flush_capture_health: Last 7d: 66/159 flushes spawned (skip rate 58%) [attention: high skip rate — consider lowering WIKI_MIN_FLUSH_CHARS]
[PASS] structural_lint: Results: 0 errors, 0 warnings, 37 suggestions
```

`flush_capture_health` до правки был одним агрегированным сигналом и реально показывал `66/159` при `58%` skip rate `[EMPIRICAL-<repo-root>/scripts/doctor.py:94-168] [EMPIRICAL-command-output-above]`.

### grep stats on real flush.log

```powershell
@('SessionEnd fired|PreCompact fired','Spawned flush.py','Flushed.*chars to daily log','Fatal error in message reader','SKIP: only .* chars') | ForEach-Object { (Select-String -Path scripts/flush.log -Pattern $_ -AllMatches | Measure-Object).Count }
```

```text
159
148
43
16
16
```

Это подтвердило, что в логе уже есть и throughput-данные, и `SKIP: only`, и исторические Bug H события `[EMPIRICAL-<repo-root>/scripts/flush.log]`.

---

## Implementation

### Parsing helper (chosen approach)

Choice: `_parse_flush_log_events()` с `@lru_cache(maxsize=1)` `[EMPIRICAL-<repo-root>/scripts/doctor.py:100-145]`

Reason: один проход по `flush.log` на один запуск doctor, без тройного file-read, и без лишней корреляционной логики поверх живого, постоянно растущего лога `[PROJECT] [EMPIRICAL-<repo-root>/scripts/doctor.py:100-145]`.

### New function: `check_flush_throughput`

```python
def check_flush_throughput() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_throughput",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_throughput", False, f"Could not read flush.log: {exc}")

    fired = int(stats["fired"])
    spawned = int(stats["spawned"])
    if fired == 0:
        return CheckResult(
            "flush_throughput",
            True,
            f"No SessionEnd/PreCompact events in last {CAPTURE_HEALTH_WINDOW_DAYS} days (possibly idle)",
        )

    skip_rate = 1.0 - (spawned / fired)
    detail = (
        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned}/{fired} flushes spawned "
        f"(skip rate {skip_rate:.0%})"
    )
    if spawned == 0:
        return CheckResult(
            "flush_throughput",
            False,
            f"{detail}. Pipeline appears broken: SessionEnds fired but nothing was spawned.",
        )
    if skip_rate > 0.85:
        return CheckResult(
            "flush_throughput",
            True,
            f"{detail} [attention: very high skip rate — possible pipeline issue, investigate flush.py]",
        )
    if skip_rate > 0.70:
        return CheckResult("flush_throughput", True, f"{detail} [info: moderate skip rate — monitor]")
    return CheckResult("flush_throughput", True, detail)
```

Notes:
- Thresholds updated to `>85%` attention and `>70%` info `[PROJECT] [EMPIRICAL-<repo-root>/scripts/doctor.py:181-189]`
- Special case `spawned == 0 && fired > 0` preserved as FAIL `[PROJECT] [EMPIRICAL-<repo-root>/scripts/doctor.py:175-180]`

### New function: `check_flush_quality_coverage`

```python
def check_flush_quality_coverage() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_quality_coverage",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_quality_coverage", False, f"Could not read flush.log: {exc}")

    spawned_chars = int(stats["spawned_chars"])
    skip_only_chars = int(stats["skip_only_chars"])
    attempted_chars = spawned_chars + skip_only_chars
    if attempted_chars == 0:
        return CheckResult(
            "flush_quality_coverage",
            True,
            f"No size-qualified capture candidates in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
        )

    quality_ratio = spawned_chars / attempted_chars
    detail = (
        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned_chars}/{attempted_chars} chars reached flush.py "
        f"(coverage {quality_ratio:.1%})"
    )
    if quality_ratio < 0.70:
        return CheckResult(
            "flush_quality_coverage",
            True,
            f"{detail} [attention: significant content filtered before flush.py]",
        )
    if quality_ratio < 0.85:
        return CheckResult(
            "flush_quality_coverage",
            True,
            f"{detail} [info: moderate content filtered before flush.py]",
        )
    return CheckResult("flush_quality_coverage", True, detail)
```

Notes on quality coverage approach chosen:

- Chosen approach: **the simplest allowed one** — `attempted = all Spawned chars + all SKIP: only N chars`, `captured = all Spawned chars` `[PROJECT] [EMPIRICAL-<repo-root>/scripts/doctor.py:205-232]`
- Reason: correctness/failures are now split into a separate check, so this metric can stay focused on “what fraction of substantive input made it past pre-spawn filtering” without brittle session correlation `[PROJECT]`.

### New function: `check_flush_pipeline_correctness`

```python
def check_flush_pipeline_correctness() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_pipeline_correctness", False, f"Could not read flush.log: {exc}")

    fatal_errors = int(stats["fatal_errors"])
    latest_fatal_ts = stats["latest_fatal_ts"]
    if fatal_errors == 0:
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            f"No 'Fatal error in message reader' events in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
        )

    latest_detail = (
        latest_fatal_ts.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(latest_fatal_ts, datetime)
        else "unknown"
    )
    return CheckResult(
        "flush_pipeline_correctness",
        False,
        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {fatal_errors} 'Fatal error in message reader' events "
        f"(most recent {latest_detail}) — likely Bug H regression, investigate issue #16",
    )
```

Notes:
- `errors == 0` -> PASS, `errors > 0` -> FAIL `[PROJECT] [EMPIRICAL-<repo-root>/scripts/doctor.py:248-267]`
- `most recent` timestamp included from the parsed log window `[EMPIRICAL-<repo-root>/scripts/doctor.py:257-266]`

### Diff vs old function

```diff
diff --git a/scripts/doctor.py b/scripts/doctor.py
index 978f255..2261d25 100644
--- a/scripts/doctor.py
+++ b/scripts/doctor.py
@@ -8,6 +8,7 @@ from __future__ import annotations
 import argparse
 import json
 import os
+import re
 import shutil
 import subprocess
 import sys
@@ -15,6 +16,7 @@ import time
 import uuid
 from dataclasses import dataclass
 from datetime import datetime, timedelta
+from functools import lru_cache
 from pathlib import Path
 from zoneinfo import ZoneInfo
 
@@ -91,23 +93,23 @@ def check_env_settings() -> CheckResult:
         return CheckResult("env_settings", False, f"Failed to load settings: {exc}")
 
 
-def check_flush_capture_health() -> CheckResult:
-    if not FLUSH_LOG.exists():
-        return CheckResult(
-            "flush_capture_health",
-            True,
-            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
-        )
+SPAWN_CHARS_RE = re.compile(r"Spawned flush\.py .* \((\d+) turns, (\d+) chars\)")
+SKIP_ONLY_CHARS_RE = re.compile(r"SKIP: only (\d+) chars \(min \d+\)")
 
-    cutoff = datetime.now() - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
-    session_fired = 0
-    spawned = 0
 
-    try:
-        text = FLUSH_LOG.read_text(encoding="utf-8", errors="replace")
-    except OSError as exc:
-        return CheckResult("flush_capture_health", False, f"Could not read flush.log: {exc}")
+@lru_cache(maxsize=1)
+def _parse_flush_log_events() -> dict[str, object]:
+    cutoff = datetime.now() - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
+    stats: dict[str, object] = {
+        "fired": 0,
+        "spawned": 0,
+        "spawned_chars": 0,
+        "skip_only_chars": 0,
+        "fatal_errors": 0,
+        "latest_fatal_ts": None,
+    }
 
+    text = FLUSH_LOG.read_text(encoding="utf-8", errors="replace")
     for line in text.splitlines():
         parts = line.split(None, 3)
         if len(parts) < 4:
@@ -120,52 +122,149 @@ def check_flush_capture_health() -> CheckResult:
             continue
 
         tail = parts[3]
-        if "[session-end]" not in tail and "[pre-compact]" not in tail:
-            continue
-        if "SessionEnd fired" in tail or "PreCompact fired" in tail:
-            session_fired += 1
-        elif "Spawned flush.py" in tail:
-            spawned += 1
+        if "[session-end]" in tail or "[pre-compact]" in tail:
+            if "SessionEnd fired" in tail or "PreCompact fired" in tail:
+                stats["fired"] = int(stats["fired"]) + 1
+            elif "Spawned flush.py" in tail:
+                stats["spawned"] = int(stats["spawned"]) + 1
+
+            skip_match = SKIP_ONLY_CHARS_RE.search(tail)
+            if skip_match:
+                stats["skip_only_chars"] = int(stats["skip_only_chars"]) + int(skip_match.group(1))
+
+        spawn_match = SPAWN_CHARS_RE.search(tail)
+        if spawn_match:
+            stats["spawned_chars"] = int(stats["spawned_chars"]) + int(spawn_match.group(2))
+
+        if "Fatal error in message reader" in tail:
+            stats["fatal_errors"] = int(stats["fatal_errors"]) + 1
+            latest = stats["latest_fatal_ts"]
+            if latest is None or ts > latest:
+                stats["latest_fatal_ts"] = ts
+
+    return stats
+
 
-    if session_fired == 0:
+def check_flush_throughput() -> CheckResult:
+    if not FLUSH_LOG.exists():
         return CheckResult(
-            "flush_capture_health",
+            "flush_throughput",
             True,
-            f"No SessionEnd/PreCompact events in last {CAPTURE_HEALTH_WINDOW_DAYS} days (possibly idle)",
+            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
         )
 
-    skip_rate = 1.0 - (spawned / session_fired)
+    try:
+        stats = _parse_flush_log_events()
+    except OSError as exc:
+        return CheckResult("flush_throughput", False, f"Could not read flush.log: {exc}")
+
+    fired = int(stats["fired"])
+    spawned = int(stats["spawned"])
+    if fired == 0:
+        return CheckResult(
+            "flush_throughput",
+            True,
+            f"No SessionEnd/PreCompact events in last {CAPTURE_HEALTH_WINDOW_DAYS} days (possibly idle)",
+        )
+
+    skip_rate = 1.0 - (spawned / fired)
     detail = (
-        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned}/{session_fired} flushes spawned "
+        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned}/{fired} flushes spawned "
         f"(skip rate {skip_rate:.0%})"
     )
-
-    # FAIL only when the pipeline is observably broken: many SessionEnds fired
-    # but zero flushes actually spawned. A high skip rate on its own is an
-    # observability signal, not a correctness failure — it reflects historical
-    # usage (lots of short sessions under WIKI_MIN_FLUSH_CHARS), and blocking
-    # the merge gate on historical data would be wrong because it cannot be
-    # fixed by changing the current code.
     if spawned == 0:
         return CheckResult(
-            "flush_capture_health",
+            "flush_throughput",
             False,
             f"{detail}. Pipeline appears broken: SessionEnds fired but nothing was spawned.",
         )
+    if skip_rate > 0.85:
+        return CheckResult(
+            "flush_throughput",
+            True,
+            f"{detail} [attention: very high skip rate — possible pipeline issue, investigate flush.py]",
+        )
+    if skip_rate > 0.70:
+        return CheckResult("flush_throughput", True, f"{detail} [info: moderate skip rate — monitor]")
+    return CheckResult("flush_throughput", True, detail)
+
 
-    if skip_rate > 0.5:
+def check_flush_quality_coverage() -> CheckResult:
+    if not FLUSH_LOG.exists():
         return CheckResult(
-            "flush_capture_health",
+            "flush_quality_coverage",
             True,
-            f"{detail} [attention: high skip rate — consider lowering WIKI_MIN_FLUSH_CHARS]",
+            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
         )
-    if skip_rate > 0.3:
+
+    try:
+        stats = _parse_flush_log_events()
+    except OSError as exc:
+        return CheckResult("flush_quality_coverage", False, f"Could not read flush.log: {exc}")
+
+    spawned_chars = int(stats["spawned_chars"])
+    skip_only_chars = int(stats["skip_only_chars"])
+    attempted_chars = spawned_chars + skip_only_chars
+    if attempted_chars == 0:
+        return CheckResult(
+            "flush_quality_coverage",
+            True,
+            f"No size-qualified capture candidates in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
+        )
+
+    quality_ratio = spawned_chars / attempted_chars
+    detail = (
+        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {spawned_chars}/{attempted_chars} chars reached flush.py "
+        f"(coverage {quality_ratio:.1%})"
+    )
+    if quality_ratio < 0.70:
+        return CheckResult(
+            "flush_quality_coverage",
+            True,
+            f"{detail} [attention: significant content filtered before flush.py]",
+        )
+    if quality_ratio < 0.85:
         return CheckResult(
-            "flush_capture_health",
+            "flush_quality_coverage",
             True,
-            f"{detail} [info: moderate skip rate]",
+            f"{detail} [info: moderate content filtered before flush.py]",
         )
-    return CheckResult("flush_capture_health", True, detail)
+    return CheckResult("flush_quality_coverage", True, detail)
+
+
+def check_flush_pipeline_correctness() -> CheckResult:
+    if not FLUSH_LOG.exists():
+        return CheckResult(
+            "flush_pipeline_correctness",
+            True,
+            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
+        )
+
+    try:
+        stats = _parse_flush_log_events()
+    except OSError as exc:
+        return CheckResult("flush_pipeline_correctness", False, f"Could not read flush.log: {exc}")
+
+    fatal_errors = int(stats["fatal_errors"])
+    latest_fatal_ts = stats["latest_fatal_ts"]
+    if fatal_errors == 0:
+        return CheckResult(
+            "flush_pipeline_correctness",
+            True,
+            f"No 'Fatal error in message reader' events in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
+        )
+
+    latest_detail = (
+        latest_fatal_ts.strftime("%Y-%m-%d %H:%M:%S")
+        if isinstance(latest_fatal_ts, datetime)
+        else "unknown"
+    )
+    return CheckResult(
+        "flush_pipeline_correctness",
+        False,
+        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {fatal_errors} 'Fatal error in message reader' events "
+        f"(most recent {latest_detail}) — likely Bug H regression, investigate issue #16",
+    )
 
 
 def check_total_tokens_injection() -> CheckResult:
@@ -653,7 +752,9 @@ def get_quick_checks() -> list[CheckResult]:
     return [
         check_wiki_structure(),
         check_env_settings(),
-        check_flush_capture_health(),
+        check_flush_throughput(),
+        check_flush_quality_coverage(),
+        check_flush_pipeline_correctness(),
         check_python(),
         check_uv(),
         check_index_health(),
@@ -671,7 +772,9 @@ def get_full_checks() -> list[CheckResult]:
     return [
         check_wiki_structure(),
         check_env_settings(),
-        check_flush_capture_health(),
+        check_flush_throughput(),
+        check_flush_quality_coverage(),
+        check_flush_pipeline_correctness(),
         check_python(),
         check_uv(),
         check_runtime_mode(),
```

---

## Phase 1 — standalone unit test each new check

### Command

```powershell
@'
import sys
sys.path.insert(0, 'scripts')
from doctor import check_flush_throughput, check_flush_quality_coverage, check_flush_pipeline_correctness
for check_fn in [check_flush_throughput, check_flush_quality_coverage, check_flush_pipeline_correctness]:
    r = check_fn()
    status = 'PASS' if r.ok else 'FAIL'
    print(f'[{status}] {r.name}: {r.detail}')
'@ | uv run python -
```

### Output

```text
[PASS] flush_throughput: Last 7d: 67/161 flushes spawned (skip rate 58%)
[PASS] flush_quality_coverage: Last 7d: 1436765/1438360 chars reached flush.py (coverage 99.9%)
[FAIL] flush_pipeline_correctness: Last 7d: 16 'Fatal error in message reader' events (most recent 2026-04-14 15:21:06) — likely Bug H regression, investigate issue #16
```

### Verdict

- [x] `flush_throughput` returns same framing and same skip-rate class as old check; raw counts drifted from `66/159` to `67/161` because `flush.log` kept growing during verification `[EMPIRICAL-command-output-above] [EMPIRICAL-Initial-state]`
- [x] `flush_quality_coverage` returns meaningful ratio (`99.9%`, not `0%`; after formatting fix no longer rounds to a misleading `100%`) `[EMPIRICAL-command-output-above]`
- [x] `flush_pipeline_correctness` matches real grep count of `Fatal error in message reader` lines within 7-day window `[EMPIRICAL-command-output-below]`
- [x] All three return expected statuses; the lone FAIL is the intentional Bug H detector `[PROJECT] [EMPIRICAL-command-output-above]`

### Bug H historical verification

```powershell
@'
from pathlib import Path
from datetime import datetime, timedelta
text = Path('scripts/flush.log').read_text(encoding='utf-8', errors='replace')
cutoff = datetime.now() - timedelta(days=7)
count = 0
for line in text.splitlines():
    parts = line.split(None, 3)
    if len(parts) < 4:
        continue
    try:
        ts = datetime.strptime(f'{parts[0]} {parts[1]}', '%Y-%m-%d %H:%M:%S')
    except ValueError:
        continue
    if ts < cutoff:
        continue
    if 'Fatal error in message reader' in line:
        count += 1
print(f'7d window count: {count}')
'@ | python -
(Select-String -Path scripts/flush.log -Pattern 'Fatal error in message reader' -AllMatches | Measure-Object).Count
```

Output:
```text
7d window count: 16
16
```

Verify: `check_flush_pipeline_correctness` count matches 7-day window count exactly `[EMPIRICAL-command-output-above]`.

---

## Phase 2 — doctor --quick integration

### Command

```powershell
$env:NO_COLOR='1'; uv run python scripts/doctor.py --quick 2>&1 | Where-Object { $_ -match 'flush_|structural_lint' }
```

### Output

```text
[PASS] flush_throughput: Last 7d: 69/165 flushes spawned (skip rate 58%)
[PASS] flush_quality_coverage: Last 7d: 1463303/1465534 chars reached flush.py (coverage 99.8%)
[FAIL] flush_pipeline_correctness: Last 7d: 16 'Fatal error in message reader' events (most recent 2026-04-14 15:21:06) � likely Bug H regression, investigate issue #16
[PASS] structural_lint: Results: 0 errors, 0 warnings, 37 suggestions
```

### Verdict

- [x] Three new check lines visible: `flush_throughput`, `flush_quality_coverage`, `flush_pipeline_correctness` `[EMPIRICAL-command-output-above]`
- [x] Old `flush_capture_health` line is absent `[EMPIRICAL-command-output-above]`
- [x] No regression in nearby quick checks; `structural_lint` stayed PASS `[EMPIRICAL-command-output-above]`

---

## Phase 3 — doctor --full regression

### Command

```powershell
$env:NO_COLOR='1'; uv run python scripts/doctor.py --full 2>&1 | Where-Object { $_ -match 'flush_|total_tokens_injection' }
```

### Output

```text
[PASS] flush_throughput: Last 7d: 69/165 flushes spawned (skip rate 58%)
[PASS] flush_quality_coverage: Last 7d: 1463303/1465534 chars reached flush.py (coverage 99.8%)
[FAIL] flush_pipeline_correctness: Last 7d: 16 'Fatal error in message reader' events (most recent 2026-04-14 15:21:06) � likely Bug H regression, investigate issue #16
[PASS] flush_roundtrip: session-end -> flush.py chain completed in test mode
[PASS] total_tokens_injection: NOT active � model does not observe <total_tokens> in its input context
```

### Verdict

- [x] Three new checks present in full mode too `[EMPIRICAL-command-output-above]`
- [x] Existing full-mode checks in this subset still run: `flush_roundtrip` PASS `[EMPIRICAL-command-output-above]`
- [x] `total_tokens_injection` still runs and passes `[EMPIRICAL-command-output-above]`

---

## Phase 4 — lint regression guard

### Command

```powershell
uv run python scripts/lint.py --structural-only 2>&1 | Select-Object -Last 5
```

### Output

```text
  Skipping: Contradictions (--structural-only)

Report saved to: E:\Project\memory claude\memory claude\reports\lint-2026-04-14.md

Results: 0 errors, 0 warnings, 37 suggestions
```

### Verdict

- [x] Lint state unchanged from pre-edit: `0 errors, 0 warnings, 37 suggestions` `[EMPIRICAL-command-output-above]`
- [x] No new broken links introduced by the code-only change in `doctor.py` `[EMPIRICAL-command-output-above]`

---

## Final state

### git status --short

```text
 M scripts/doctor.py
?? Untitled.md
?? docs/codex-tasks/split-doctor-flush-capture-health-report.md
?? docs/codex-tasks/split-doctor-flush-capture-health.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-c-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-c.md
```

Expected whitelist was preserved for tracked files: only `<repo-root>/scripts/doctor.py` is modified `[EMPIRICAL-command-output-above]`.

### git diff --stat scripts/doctor.py

```text
 scripts/doctor.py | 185 ++++++++++++++++++++++++++++++++++++++++++------------
 1 file changed, 144 insertions(+), 41 deletions(-)
```

### Files touched

- `scripts/doctor.py` — modified

---

## Tools used

- [x] **WebFetch** `https://docs.python.org/3/library/re.html` — regex semantics `[OFFICIAL]`
- [x] **WebFetch** `https://docs.python.org/3/library/datetime.html#datetime.timedelta` — timedelta semantics `[OFFICIAL]`
- [x] **Read** `scripts/doctor.py` (lines 94-168, 32, 650-680) `[EMPIRICAL]`
- [x] **Read** `hooks/session-end.py` — SKIP message formats `[EMPIRICAL]`
- [x] **Read** `hooks/pre-compact.py` — SKIP message formats `[EMPIRICAL]`
- [x] **Read** `scripts/flush.py` — Starting/Flushed/Fatal error formats `[EMPIRICAL]`
- [x] **Bash** `uv run python scripts/doctor.py --quick` (pre и post) — executed via PowerShell shell equivalent because `bash` is unavailable on this host (`execvpe(/bin/bash) failed`) `[EMPIRICAL-command-output]`
- [x] **Bash** `uv run python scripts/doctor.py --full` (post) — executed via PowerShell shell equivalent because `bash` is unavailable on this host (`execvpe(/bin/bash) failed`) `[EMPIRICAL-command-output]`
- [x] **Bash** `uv run python scripts/lint.py --structural-only` (regression) — executed via PowerShell shell equivalent because `bash` is unavailable on this host `[EMPIRICAL-command-output]`
- [x] **Bash** standalone Python unit test per new check — executed via PowerShell here-string + `uv run python -` `[EMPIRICAL-command-output]`
- [x] **Bash** grep counts on flush.log for Phase 1 Bug H verification — executed via PowerShell `Select-String` and inline Python because `bash` is unavailable on this host `[EMPIRICAL-command-output]`
- [x] **Edit** `scripts/doctor.py`
- [x] **MCP filesystem** — BLOCKED: no filesystem MCP server registered in this `${USER}` session under `<user-home>` `[EMPIRICAL-list_mcp_resources]`
- [x] **MCP git** — BLOCKED: no git MCP server registered in this `${USER}` session under `<user-home>` `[EMPIRICAL-list_mcp_resource_templates]`

---

## Out-of-scope temptations

- Did not touch `hooks/` logging to make quality coverage smarter; the task explicitly scoped the fix to `scripts/doctor.py` `[PROJECT]`
- Did not change `CAPTURE_HEALTH_WINDOW_DAYS = 7` even though a shorter live window might be interesting for Bug H triage `[PROJECT]`
- Did not fix `index_health` / `wiki_cli_rebuild_check_smoke`; those failures pre-existed and are unrelated to this split `[EMPIRICAL-command-output-Phase-2/3]`

---

## Discrepancies

- `bash` is not installed/usable in the current host shell: `execvpe(/bin/bash) failed: No such file or directory`. I used PowerShell equivalents for all required shell commands and preserved the outputs `[EMPIRICAL-command-output]`.
- The plan’s sample numbers drifted during verification because `scripts/flush.log` is live and Codex/flush activity continued while checks were running. Pre-edit snapshot was `66/159`; standalone test moved to `67/161`; integration snapshots moved to `69/165`. The skip rate class stayed stable at `58%`, so the split behavior remained consistent `[EMPIRICAL-command-output-above]`.
- The plan’s “All previously-PASS checks should remain PASS” is too strong in this repo snapshot: `index_health` and `wiki_cli_rebuild_check_smoke` were already failing before this task and remained out of scope `[EMPIRICAL-command-output-Phase-2/3]`.

---

## Self-audit

- [x] Doc verification filled with real citations (not placeholder text)
- [x] Mandatory tools table все ticked или BLOCKED
- [x] Old `check_flush_capture_health` removed
- [x] Three new functions implemented
- [x] Helper function choice documented (created and justified)
- [x] All three registered in `get_quick_checks` and `get_full_checks`
- [x] Phase 1 standalone unit tests captured in report with real output
- [x] Phase 1 Bug H historical count verified matches check output
- [x] Phase 2 doctor --quick shows three new lines, old name absent
- [x] Phase 3 doctor --full shows three new lines, no regression in touched area
- [x] Phase 4 lint unchanged
- [x] Quality coverage approach documented (simplest)
- [x] No files modified outside whitelist
- [x] No commit / push
- [x] Report uses placeholders (`${USER}`, `<repo-root>`, `<user-home>`)

---

## Notes / observations

- Splitting one noisy check into three made the current state much easier to read: throughput is merely middling, quality coverage is excellent, and the only hard red signal is the real Bug H failure count `[PROJECT] [EMPIRICAL-command-output-Phase-1/2/3]`.
- The new quality metric is intentionally optimistic because it measures “made it past pre-spawn filtering,” not “finished end-to-end successfully.” That tradeoff is acceptable here because pipeline correctness is now broken out into its own FAILing check `[PROJECT] [EMPIRICAL-<repo-root>/scripts/doctor.py:205-267]`.
