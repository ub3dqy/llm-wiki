# Plan — Wiki Freshness Phase 2: Advisory Source Drift / Source Rot Detection

## Иерархия источников правды

1. **RFC 9110** (HTTP Semantics) — primary для HTTP contract decisions. Wiki article: `wiki/sources/http-semantics-rfc9110-docs.md`
2. **Реальное состояние кода** — `scripts/lint.py`, `scripts/utils.py`, `scripts/config.py`, `scripts/state.json`
3. **Phase 1 design decisions** — `wiki/concepts/wiki-knowledge-freshness-lifecycle.md`, `CLAUDE.md` Freshness metadata section
4. **Этот план** — derived. Расхождения → Discrepancy.

## Context

Phase 1 (PR #32) added temporal freshness: `status`/`reviewed`/`superseded_by` fields + scoring multipliers + lint advisory. Covers **Age** and **Status** axes.

Phase 2 adds the **Basis** axis: "did the upstream source change since we wrote the wiki article?" This is source-drift / source-rot detection for `wiki/sources/` articles.

**[EMPIRICAL]** Scope measured by Claude 2026-04-16:
- 126 total source articles
- **22 have HTTP URLs** (43 total URLs across 17 unique domains) → checkable
- 40 have only `raw/` local refs → `unverifiable`
- 64 have no `sources:` field → `no_sources`

So Phase 2 realistically checks **~43 HTTP URLs** in **~22 articles**. The other 104 are classified immediately without network I/O.

## Constraints (from Phase 1 + ТЗ, non-negotiable)

1. **Freshness ≠ confidence.** Source drift is temporal/operational, not epistemic.
2. **`reviewed` stays strictly manual.** Drift check **must not** auto-stamp `reviewed`.
3. **Phase 2 = sources/ only.** Not concepts/, not connections/.
4. **Advisory, not CI blocker.** Network I/O is non-deterministic → cannot be merge gate.
5. **Official HTTP semantics.** No naive `HEAD + Last-Modified` without caveats.

## Doc verification (Codex mandatory pre-flight)

| URL / Reference | What to verify |
|---|---|
| wiki/sources/http-semantics-rfc9110-docs.md → Conditional Requests section | ETag + If-None-Match flow, 304 semantics, HEAD safe+idempotent |
| RFC 9110 §8.8.1 (ETag) | ETag is opaque validator; weak `W/"..."` vs strong |
| RFC 9110 §8.8.2 (Last-Modified) | Second-precision, less reliable than ETag |
| RFC 9110 §13 (Conditional Requests) | If-None-Match → 304 or 200; If-Modified-Since as fallback |
| scripts/lint.py → main() checks list | Where new check registers |
| scripts/utils.py → load_state/save_state | JSON state pattern to follow |
| CLAUDE.md → Gate roles section | Advisory check = non-structural, non-blocking |

## Design Decisions

### D1. HTTP Contract — Validator Priority

**[OFFICIAL-RFC9110 §8.8]** ETag is preferred over Last-Modified for precision.

**Policy (per URL):**

```
1. Send HEAD with stored validators (if any):
   - If-None-Match: <stored_etag>     (if etag available)
   - If-Modified-Since: <stored_lm>   (if last-modified available)
   
2. Classify response:
   - 304 Not Modified        → no_drift (source unchanged)
   - 200 OK with new ETag    → drift (source changed)
   - 200 OK, no ETag, new LM → drift (source likely changed)
   - 200 OK, no validators   → unverifiable (can't determine)
   - 404 / 410               → rot (source gone)
   - 403                     → access_denied (skip, not rot)
   - 429                     → rate_limited (skip, retry later)
   - 5xx                     → server_error (skip, transient)
   - Connection error/timeout → network_error (skip, transient)
   
3. First run (no stored validators):
   - Send plain HEAD (no conditional headers)
   - Store received ETag + Last-Modified as baseline
   - Classify as "baseline_captured" (not drift, not clean — unknown)
```

### D2. What Counts as Drift

| Situation | Classification | Rationale |
|---|---|---|
| ETag changed (304→200 with new ETag) | `drift` | Strongest signal — opaque content hash |
| Last-Modified newer than stored | `drift` | Weaker signal but sufficient |
| ETag unchanged, LM unchanged (304) | `no_drift` | Both validators agree |
| ETag changed, LM unchanged | `drift` | ETag takes precedence (finer granularity) |
| ETag unchanged, LM newer | `no_drift` | ETag takes precedence |
| No validators at all | `unverifiable` | Can't determine, not drift |
| 404 / 410 | `rot` | Source gone |

### D3. Multi-Source Articles

**Policy**: article flagged if **any** of its HTTP URLs reports `drift` or `rot`. Conservative approach — avoids "primary source" complexity.

### D4. Lint Placement

**NOT in `--structural-only`** — network I/O is non-deterministic. Goes into the "full" lint path alongside contradiction check. Specifically:

- New CLI flag: `--source-drift` (explicit opt-in for network-dependent check)
- OR: auto-runs in `lint --full` mode (alongside contradictions)
- NOT in `lint --structural-only` (which is CI gate and must be deterministic)

**Preferred**: separate `--source-drift` flag so user can run just drift check without expensive LLM contradiction check.

### D5. Rate Limiting

- **Per-domain delay**: 2 seconds between requests to same domain
- **Global timeout**: 10 seconds per URL (connect + read)
- **No retry**: on transient failure → classify as `network_error`, move on
- **Memoize within single run**: if same URL appears in multiple articles, check once

### D6. State Storage

Add `source_drift_validators` key to existing `scripts/state.json`:

```json
{
  "source_drift_validators": {
    "https://docs.anthropic.com/en/api/getting-started": {
      "etag": "\"abc123\"",
      "last_modified": "Tue, 15 Apr 2026 10:00:00 GMT",
      "last_checked": "2026-04-16",
      "last_status": "no_drift"
    }
  }
}
```

First run populates baseline. Second run compares.

## Whitelist (strict)

1. **`scripts/lint.py`** — add `check_source_drift()` function + register in checks list + add `--source-drift` flag
2. **`scripts/state.json`** — auto-updated by new check (via existing `save_state`)

**Handoff artifacts (not in whitelist)**:
- `docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md`

**НЕ трогать**: `scripts/utils.py`, `scripts/config.py`, `scripts/doctor.py`, `CLAUDE.md`, wiki articles, hooks, pyproject.toml, `.github/workflows/`

## Change 1 — `check_source_drift()` in `scripts/lint.py`

### Function signature

```python
def check_source_drift(timeout: float = 10.0, delay: float = 2.0) -> list[dict]:
    """Advisory: check wiki/sources/ HTTP URLs for upstream changes.
    
    Uses RFC 9110 conditional requests (ETag + If-None-Match, Last-Modified
    + If-Modified-Since) to detect source drift without downloading full
    page content. Results are advisory — network I/O is non-deterministic.
    
    First run captures baseline validators. Second run detects drift.
    """
```

### Classification output

Each issue dict:
```python
{
    "severity": "suggestion",  # drift = suggestion, rot = warning
    "check": "source_drift",
    "file": "sources/<slug>",
    "detail": "drift: https://... — ETag changed (stored: \"abc\", current: \"def\")"
}
```

Severity mapping:
- `drift` → `suggestion` (informational — source may have changed)
- `rot` (404/410) → `warning` (source gone — article may be orphaned from upstream)
- `baseline_captured` → no issue (silent — first run establishing validators)
- `unverifiable` / `no_sources` → no issue (silent — nothing actionable)
- `network_error` / `rate_limited` / `access_denied` → no issue (transient, silent)

### Registration in checks list

**NOT** in the main `checks` list (which runs in `--structural-only`).

Add separate path after contradictions, gated by `--source-drift` flag:

```python
if args.source_drift:
    print("  Checking: Source drift (network)...")
    print(f"  {ADVISORY_BANNER}")
    issues = check_source_drift()
    all_issues.extend(issues)
    print(f"    Found {len(issues)} issue(s)")
```

New argparse flag:
```python
parser.add_argument("--source-drift", action="store_true",
                    help="Check wiki/sources/ URLs for upstream changes (network I/O)")
```

### HTTP implementation

Use `urllib.request` (stdlib, no deps). Pattern:

```python
import urllib.request
import urllib.error
import time
from collections import defaultdict

def _check_url(url: str, stored: dict, timeout: float) -> tuple[str, dict]:
    """Check single URL. Returns (classification, updated_validators)."""
    headers = {"User-Agent": "llm-wiki-drift-checker/1.0"}
    if stored.get("etag"):
        headers["If-None-Match"] = stored["etag"]
    if stored.get("last_modified"):
        headers["If-Modified-Since"] = stored["last_modified"]
    
    req = urllib.request.Request(url, method="HEAD", headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        # 200 OK — check if validators changed
        new_etag = resp.headers.get("ETag", "")
        new_lm = resp.headers.get("Last-Modified", "")
        ...
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return "no_drift", stored  # unchanged
        elif e.code in (404, 410):
            return "rot", stored
        elif e.code == 403:
            return "access_denied", stored
        elif e.code == 429:
            return "rate_limited", stored
        else:
            return "server_error", stored
    except (urllib.error.URLError, TimeoutError, OSError):
        return "network_error", stored
```

**Important**: `304` comes as `HTTPError` in urllib, not as normal response. This is a known Python stdlib behavior.

## Verification phases

### Phase 1 — Codex сам

**1.1** Syntax + import: lint.py parses, no new deps needed (urllib is stdlib).

**1.2** `--structural-only` unchanged: existing 8 checks same count, same output.

**1.3** `--source-drift` first run (baseline capture):
```bash
uv run python scripts/lint.py --source-drift
```
Expected: "Checking: Source drift (network)... Found 0 issue(s)" (first run captures validators, reports nothing).

**1.4** State verification: `state.json` now has `source_drift_validators` key with entries for each checkable URL.

**1.5** `--source-drift` second run (should show `no_drift` since nothing changed in minutes):
```bash
uv run python scripts/lint.py --source-drift
```
Expected: "Found 0 issue(s)" (no drift detected — validators match).

**1.6** Negative acceptance: `ruff check scripts/lint.py` — zero new errors.

**1.7** `ruff format --check scripts/lint.py` — already formatted.

**1.8** `doctor --quick` — exit 0, no regression.

**1.9** Simulate rot: Codex manually inserts a fake URL `https://httpstat.us/404` into a test and verifies `rot` classification returned. Then removes test.

### Phase 2 — `[awaits user]`

**2.1** User runs `lint --source-drift` after a few days to see if real drift is detected.

**2.2** User reviews whether output is noisy or useful.

### Phase 3 — `[awaits 7-day window]`

**3.1** After 7 days, review: how many drift vs unverifiable vs rot findings? Is signal/noise acceptable?

## Acceptance criteria

- ✅ `lint --structural-only` unchanged (8 checks, same output)
- ✅ `lint --source-drift` runs, checks ~43 URLs, classifies each
- ✅ First run: captures validators, reports 0 issues (baseline)
- ✅ Second run: reports 0 issues (no drift in short interval)
- ✅ Rot test: fake 404 URL correctly classified as `rot`
- ✅ State saved: `state.json` has `source_drift_validators` with entries
- ✅ Rate limiting: per-domain 2s delay observed in logs
- ✅ No new ruff errors, format clean
- ✅ `doctor --quick` not regressed
- ✅ `reviewed` field **not** touched by any part of this change
- ✅ Only `scripts/lint.py` modified (+ `state.json` auto-updated)

## Out of scope

1. `doctor.py` summary metric — premature, wait for Phase 2 to prove signal
2. CI gate integration — advisory only, never blocking
3. Auto-update `reviewed` or `status` based on drift — explicitly prohibited
4. Body content hashing via GET — too expensive, Phase 3+ if needed
5. Drift detection for `concepts/` — Phase 2 = sources/ only
6. Background polling / cron — overkill for 43 URLs
7. Access-log analytics / usage axis — deferred

## Rollback

```bash
git checkout -- scripts/lint.py
# Remove source_drift_validators from state.json manually if needed
```

## Discrepancy handling

- **urllib 304 not raised as HTTPError** in some Python versions → test empirically, document behavior
- **CDN-served docs (Anthropic, Astral)** may return no ETag/Last-Modified → `unverifiable`, not `drift`
- **GitHub raw URLs** return ETag reliably → good signal
- **Rate-limited (429)** → silent skip, not failure. Log and continue
- **Actual drift count on first real run** may be high if many docs updated recently → not a bug, just needs human triage

## Notes для Codex

- **urllib.request, not requests.** Zero new deps. stdlib only.
- **304 comes as HTTPError** in Python stdlib. Test this explicitly.
- **Per-domain delay** — use `time.sleep(delay)` between requests to same domain. Track last-request-time per domain.
- **State persistence** — use existing `load_state()`/`save_state()` from `utils.py`. Add `source_drift_validators` key, don't touch other keys.
- **First run = baseline only.** Don't report drift on first run — you have nothing to compare against. Report "baseline_captured" in log, issue count = 0.
- **Silence is good.** `unverifiable`, `no_sources`, `access_denied`, `network_error`, `rate_limited` — all silent (no lint issue). Only `drift` (suggestion) and `rot` (warning) produce visible output.
- **User-Agent required.** Many servers reject requests without it. Use `llm-wiki-drift-checker/1.0`.
- **`--source-drift` is separate from `--full`.** Don't auto-run drift in `--full` mode for now — keep it explicit opt-in until we validate signal quality.
- **No commit/push.** Финал = заполненный отчёт. Personal data sanitize.
- **WSL uv discipline** if running from WSL.
