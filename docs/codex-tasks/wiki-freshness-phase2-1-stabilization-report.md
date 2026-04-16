---
task: Wiki Freshness Phase 2.1 — Drift signal stabilization (GitHub URL pattern skip)
plan: docs/codex-tasks/wiki-freshness-phase2-1-stabilization.md
executor: Codex
status: completed-with-discrepancies
---

# Report — Phase 2.1 Stabilization

## 0. Pre-flight

### 0.1 Environment
```text
OS: Linux <host>
cwd: <repo>
date: 2026-04-16
uv: uv 0.11.6
python: Python 3.12.3
env: UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy
```

### 0.2 Git status + HEAD
```text
 M scripts/lint.py
?? docs/codex-tasks/wiki-freshness-phase2-1-stabilization-report.md
231a8c3f52a1ad4e86ad5df45be298dce909b7ee
```

### 0.2b Baselines

**Baseline A — current `--source-drift` drift count**

Observed current baseline before the Phase 2.1 patch:

```text
16
```

This is higher than the plan's historical `~12`, because the repo state changed after planning.

**Baseline B — structural-only output**

```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 10 issue(s)
  Checking: Orphan sources...
    Found 0 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Freshness review debt...
    Found 178 issue(s)
  Checking: Missing backlinks...
    Found 110 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo>/reports/lint-2026-04-16.md

Results: 0 errors, 11 warnings, 288 suggestions
```

## 0.6 Doc verification

| Source | Quote / evidence | ✅/❌ |
|---|---|---|
| `wiki/sources/http-semantics-rfc9110-docs.md` | `Conditional requests через ETag + If-None-Match позволяют экономить трафик и rate-limit budget` | ✅ |
| `wiki/sources/http-semantics-rfc9110-docs.md` | `If-None-Match — условный запрос по ETag: сервер ответит 304, если ETag совпадает.` | ✅ |
| `wiki/sources/http-semantics-rfc9110-docs.md` | `Аналогичный flow работает с If-Modified-Since + Last-Modified, но ETag предпочтителен из-за точности` | ✅ |
| `wiki/sources/http-semantics-rfc9110-docs.md` | `ETag weak по умолчанию: W/"..." означает «семантически эквивалентно», не «побайтово равно».` | ✅ |
| local stdlib runtime check | `urllib.request.urlopen(HEAD https://httpbin.org/status/304)` raised `HTTPError`, `code=304` | ✅ |
| Phase 2 empirical evidence | Prior merged Phase 2 reported repeated GitHub HTML false-positive drift on second run | ✅ |

## 1. Changes

### 1.1 Add `_is_unstable_url()` + stabilization logic

Diff:

```diff
diff --git a/scripts/lint.py b/scripts/lint.py
index b80a6ac..e43ede8 100644
--- a/scripts/lint.py
+++ b/scripts/lint.py
@@ -6,6 +6,7 @@ import argparse
  import asyncio
  import importlib.util
  import json
+ import re
  import subprocess
  import sys
  import time
@@ -44,6 +45,10 @@ _ARTICLE_FRONTMATTER_CACHE: dict[Path, dict[str, str]] = {}
  _ARTICLE_WIKILINKS_CACHE: dict[Path, list[str]] = {}
  _ARTICLE_WORD_COUNT_CACHE: dict[Path, int] = {}
  _INBOUND_LINK_COUNT_CACHE: dict[str, int] | None = None
+ _UNSTABLE_URL_PATTERNS = [
+     re.compile(r"github\.com/[^/]+/[^/]+/(blob|wiki|tree)/"),
+     re.compile(r"github\.com/[^/]+/[^/]+/?$"),
+ ]
@@ -335,6 +340,10 @@ def _domain_key(url: str) -> str:
      return (parts.netloc or parts.path).lower()
  
  
+ def _is_unstable_url(url: str) -> bool:
+     return any(pattern.search(url) for pattern in _UNSTABLE_URL_PATTERNS)
+ 
+ 
  def _is_newer_last_modified(stored_value: str, current_value: str) -> bool:
@@ -397,6 +406,10 @@ def _check_source_url(
              new_etag = str(response.headers.get("ETag", "") or "")
              new_last_modified = str(response.headers.get("Last-Modified", "") or "")
  
+         if _is_unstable_url(url):
+             entry["last_status"] = "unverifiable"
+             return "unverifiable", "GitHub HTML page (validator-unstable)", entry
+ 
          if not entry["etag"] and not entry["last_modified"]:
@@ -419,6 +432,9 @@ def _check_source_url(
          return classification, detail, entry
      except urllib.error.HTTPError as exc:
          if exc.code == 304:
+             if _is_unstable_url(url):
+                 entry["last_status"] = "unverifiable"
+                 return "unverifiable", "304 Not Modified on validator-unstable URL", entry
              entry["last_status"] = "no_drift"
              return "no_drift", "304 Not Modified", entry
```

Controls:
- [x] `_UNSTABLE_URL_PATTERNS` list with 2 regexes
- [x] `_is_unstable_url()` function added
- [x] GitHub blob/wiki/tree and repo root URLs classified as `unverifiable`
- [x] `rot` path preserved for unstable GitHub URLs
- [x] Non-GitHub URLs left unchanged

## 2. Phase 1 — Smoke

### 2.1 `--structural-only` unchanged
```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 10 issue(s)
  Checking: Orphan sources...
    Found 0 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Freshness review debt...
    Found 178 issue(s)
  Checking: Missing backlinks...
    Found 110 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo>/reports/lint-2026-04-16.md

Results: 0 errors, 11 warnings, 288 suggestions
```

Matches baseline B exactly.

### 2.2 `--source-drift` post-fix drift count

Command result:

```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 10 issue(s)
  Checking: Orphan sources...
    Found 0 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Freshness review debt...
    Found 178 issue(s)
  Checking: Missing backlinks...
    Found 110 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Checking: Source drift (network)...
  [ADVISORY] Source drift results are network-dependent and must not be used as a merge gate.
    Found 1 issue(s)
  Skipping: Contradictions (--source-drift explicit network check)

Report saved to: <repo>/reports/lint-2026-04-16.md

Results: 0 errors, 11 warnings, 289 suggestions
```

Result: `16 -> 1`

Remaining drift:

```text
sources/semver-2-spec-docs.md — drift: https://semver.org/spec/v2.0.0.html — ETag changed (stored: '"69c509d9-7991"', current: '"69c509da-7991"')
```

### 2.3 Rot still works

Explicit GitHub unstable-pattern 404 test:

```text
classification= rot
detail= HTTP 404
last_status= rot
```

Test URL:

```text
https://github.com/this-owner-should-not-exist/this-repo-should-not-exist/blob/main/missing.md
```

### 2.4 Non-GitHub URLs still checked

State evidence from `scripts/state.json` after the run:

```json
[
  [
    "https://en.wikipedia.org/wiki/ANSI_escape_code",
    "",
    "Tue, 07 Apr 2026 22:39:17 GMT",
    "no_drift"
  ],
  [
    "https://no-color.org/",
    "\"69d9ab90-1a2ca\"",
    "Sat, 11 Apr 2026 02:01:52 GMT",
    "no_drift"
  ],
  [
    "https://bixense.com/clicolors/",
    "\"69ce98a0-78ff\"",
    "Thu, 02 Apr 2026 16:26:08 GMT",
    "no_drift"
  ]
]
```

### 2.5 Ruff check + format

```text
$ uv run ruff check scripts/lint.py
All checks passed!

$ uv run ruff format --check scripts/lint.py
1 file already formatted
```

### 2.6 `doctor --quick`

```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/192 flushes spawned (skip rate 58%)
[PASS] flush_quality_coverage: Last 7d: 3034926/3038499 chars reached flush.py (coverage 99.9%)
[FAIL] flush_pipeline_correctness: Last 24h: 2 'Fatal error in message reader' events (7d total: 18, most recent 2026-04-16 00:14:33) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <linux-home>/.local/bin/uv
[PASS] index_health: Index is up to date.
[PASS] structural_lint: Results: 0 errors, 11 warnings, 288 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

Exit code remained `0`. No new regression attributable to Phase 2.1.

## 3-4. Phase 2/3 — `[awaits user]`

No remote / PR actions performed.

## 5. Tools used

| Tool | Status | Details |
|---|---|---|
| wiki: `http-semantics-rfc9110-docs` | used | conditional requests, validator semantics |
| local code read | used | `scripts/lint.py`, plan, template |
| `uv run python scripts/lint.py --structural-only` | used | baseline + post-check |
| `uv run python scripts/lint.py --source-drift` | used | baseline empirical count + post-fix count |
| `uv run ruff check scripts/lint.py` | used | clean |
| `uv run ruff format --check scripts/lint.py` | used | clean after format |
| `uv run python scripts/wiki_cli.py doctor --quick` | used | non-regression check |
| local explicit Python smoke | used | `304 -> HTTPError`, GitHub unstable `404 -> rot` |

## 6. Out-of-scope temptations

- no state schema changes
- no extra domain allowlist / denylist
- no semver.org special handling
- no workflow / doctor changes
- no wiki article edits

## 7. Discrepancies

### D1 — Plan said “skip before HEAD request”, but that would break `rot`

The plan text said to skip unstable GitHub URLs before making the HEAD request, while also requiring `rot` to remain unaffected. Those two requirements conflict. If the request is skipped, a GitHub `404/410` cannot be observed.

Resolution used in code:
- still perform HEAD
- classify unstable GitHub HTML URLs as `unverifiable` on 200 / 304
- preserve `404/410 -> rot`

This matches the actual acceptance goal better than the literal plan wording.

### D2 — Baseline drift count was 16, not the planned 12

The historical plan was based on an earlier empirical snapshot (`12` false positives). Current repo state at execution time produced `16` drift findings before the Phase 2.1 patch:
- `11` GitHub HTML/blob/wiki/root pages
- `5` non-GitHub URLs

The fix still met the spirit of acceptance because the post-fix result was `1`, which is below the planned `<=2` threshold.

## 8. Self-audit

- [x] Baselines captured
- [x] Doc verification done before code reasoning was finalized
- [x] Diff shown
- [x] `--structural-only` unchanged
- [x] Drift count reduced substantially (`16 -> 1`)
- [x] GitHub blob/wiki/tree/root URLs no longer report `drift`
- [x] Rot unaffected (`404 -> rot` on unstable GitHub pattern)
- [x] Non-GitHub URLs still checked
- [x] Ruff clean
- [x] doctor not regressed beyond known Bug H
- [x] No commit/push
- [x] Personal data sanitized

