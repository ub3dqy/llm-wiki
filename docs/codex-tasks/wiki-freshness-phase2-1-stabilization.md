# Plan — Wiki Freshness Phase 2.1: Drift Signal Stabilization

## Иерархия источников правды

1. **Phase 2 report** (actual drift findings) — primary empirical source
2. **RFC 9110** (via wiki article) — HTTP semantics
3. **Реальный код** — `scripts/lint.py` current `check_source_drift()`
4. **Этот план** — derived. Расхождения → Discrepancy.

## Context

Phase 2 (`--source-drift`) merged in PR #41. Implementation correct, but second run produced **12 false drift findings** within minutes of baseline capture — all from validator-unstable endpoints.

**[EMPIRICAL]** Breakdown of 12 false positives:
- **10/12**: `github.com/.../blob/*`, `github.com/.../wiki/*`, `github.com/user/repo` (repo root HTML)
- **1/12**: `semver.org/spec/v2.0.0.html`
- **0/12**: actual content drift

Root cause: GitHub HTML pages serve session-dependent content (CSRF tokens, CDN edge variation) → ETags rotate every request → every second run sees "ETag changed" → false drift.

## Strategy chosen: B-minimal (URL pattern skip)

### Why B, not A/C/D

| Option | Verdict | Reason |
|---|---|---|
| **A (two-hit)** | ❌ rejected | GitHub ETags rotate EVERY request — two-hit would also trigger. N-of-M over time adds complexity for no gain on this failure mode |
| **B (URL pattern skip)** | ✅ chosen | 10/12 false positives match one regex. Cheap, precise, no state changes |
| **C (canonicalization)** | ❌ rejected | Overkill for stabilization pass. `github.com/blob` → raw.githubusercontent.com mapping is provider-specific scope creep |
| **D (wording only)** | ❌ rejected | Doesn't reduce noise, just renames it |

### Why pattern skip is honest

GitHub blob/wiki/tree HTML pages are fundamentally **not validatable** via ETag — their content changes on every request due to session injection. Classifying them as `unverifiable` is semantically correct per RFC 9110: the validator doesn't represent stable resource state.

### Residual noise after fix

`semver.org/spec/v2.0.0.html` — 1 remaining false positive out of 289 URLs = **0.3% noise rate**. Acceptable for advisory lint. If more patterns emerge after 7-day window, add them to the skip list in a future pass.

## Constraints (unchanged from Phase 2)

1. `reviewed` never auto-stamped
2. Advisory only, not merge gate
3. `rot` signal unchanged
4. `--structural-only` unchanged
5. No new dependencies

## Whitelist (strict)

1. **`scripts/lint.py`** — modify `_check_source_url()` or `check_source_drift()` to skip GitHub HTML URLs

**НЕ трогать**: state.json schema, utils.py, config.py, doctor.py, CLAUDE.md, wiki articles, hooks, pyproject.toml, workflows

## Change 1 — Add GitHub HTML URL skip in `scripts/lint.py`

### Where

Inside `check_source_drift()` or `_check_source_url()`, before the HEAD request.

### What

Add URL pattern check that classifies known-unstable URLs as `unverifiable` before making HTTP request:

```python
import re

_UNSTABLE_URL_PATTERNS = [
    re.compile(r"github\.com/[^/]+/[^/]+/(blob|wiki|tree)/"),  # GitHub file/wiki/tree views
    re.compile(r"github\.com/[^/]+/[^/]+/?$"),                  # GitHub repo root HTML
]

def _is_unstable_url(url: str) -> bool:
    """URLs known to have validator-unstable HTML responses."""
    return any(p.search(url) for p in _UNSTABLE_URL_PATTERNS)
```

In the check function, before HEAD request:

```python
if _is_unstable_url(url):
    return "unverifiable", "GitHub HTML page (validator-unstable)", entry
```

### What this preserves

- `github.com/repos/owner/repo` (API endpoints) — NOT matched, still checked
- `raw.githubusercontent.com/*` — NOT matched, still checked
- `github.com/.../releases` — NOT matched (no `blob/wiki/tree` in path)
- All non-GitHub URLs — unchanged
- `rot` for ANY URL (including GitHub) — unchanged (skip only applies to drift check, not 404/410)

### Expected impact

- **Before**: 12 false drift findings on second run
- **After**: ≤2 false drift findings (semver.org + maybe 1 edge case)
- **0 real drift findings lost** (GitHub HTML pages never had real drift signal anyway)

## Verification phases

### Phase 1 — Codex сам

**1.1** `--structural-only` unchanged (same 8 checks, same output).

**1.2** `--source-drift` run after change: count drift findings. Expected: ≤2 (down from 12).

**1.3** Negative: `rot` still works. Insert fake 404 URL → verify rot classification → remove.

**1.4** Negative: non-GitHub URLs still checked. Verify at least one non-GitHub URL in state has validators stored.

**1.5** Ruff check + format clean on lint.py.

**1.6** `doctor --quick` not regressed.

### Phase 2 — `[awaits user]`

**2.1** Run `--source-drift` after 7 days. Count real drift vs false positives. Assess signal quality.

## Acceptance criteria

- ✅ `--structural-only` unchanged
- ✅ `--source-drift` false positives: ≤2 (down from 12)
- ✅ GitHub blob/wiki/tree/root URLs classified as `unverifiable` (not `drift`)
- ✅ `rot` still works for ANY URL including GitHub 404s
- ✅ Non-GitHub URLs unchanged (still checked, drift/no_drift as before)
- ✅ Ruff clean, format clean
- ✅ `doctor --quick` not regressed
- ✅ Only `scripts/lint.py` modified

## Out of scope

- Two-hit confirmation (not needed after pattern skip)
- Domain allowlist/blocklist config file (patterns hardcoded is fine for 2 regexes)
- Canonicalization (GitHub blob → raw.githubusercontent)
- Content-Length as secondary signal
- State model changes
- Wording/severity changes
- semver.org special handling (0.3% noise acceptable)

## Rollback

```bash
git checkout -- scripts/lint.py
```

## Notes для Codex

- **~15 lines of code change.** This is a stabilization pass, not a feature.
- **Two regex patterns** cover 10/12 false positives. Don't over-engineer.
- **GitHub API URLs ≠ GitHub HTML URLs.** API endpoints (`api.github.com`, or `github.com` with `Accept: application/vnd.github+json`) have stable ETags. HTML pages don't. We skip only HTML patterns.
- **Verify `_is_unstable_url` doesn't match too broadly.** Test against actual URL list: `github.com/coturn/coturn` should match (repo root). `github.com/coturn/coturn/releases` should NOT match.
- **Rot is unaffected.** If a GitHub URL returns 404 — it's rot regardless of URL pattern. Skip only applies BEFORE the HEAD request for drift classification, not after.
- **No commit/push.** Personal data sanitize. WSL uv discipline.
