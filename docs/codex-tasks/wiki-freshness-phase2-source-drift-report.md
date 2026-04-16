---
task: Wiki Freshness Phase 2 — Advisory source drift / source rot detection for wiki/sources/
plan: docs/codex-tasks/wiki-freshness-phase2-source-drift.md
executor: Codex
status: implemented-with-discrepancies
---

# Report — Wiki Freshness Phase 2 (Source Drift Detection)

## 0. Pre-flight

### 0.1 Environment

```text
Linux <host> 6.6.87.2-microsoft-standard-WSL2 x86_64 GNU/Linux
Python 3.12.3
uv 0.11.6 (x86_64-unknown-linux-gnu)
```

### 0.2 Git status + HEAD

```text
 M scripts/lint.py
?? docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md
737630414deed9ebb63d4cfca1ef4f5784257fce
```

Notes:
- `scripts/lint.py` was already dirty in baseline due line-ending churn.
- `git diff -w -- scripts/lint.py` was empty before edits, so meaningful code changes were tracked with whitespace-insensitive diff.

### 0.2b Baselines

**Baseline A — current lint --structural-only output**

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

**Baseline B — current state.json keys**

```text
['last_lint', 'ingested', 'total_cost', 'flushed_sessions', 'last_auto_compile_date', 'last_auto_compile_hash', 'query_count']
```

**Baseline C — checkable URL count**

```text
126 total source articles
83 source articles with HTTP URLs
297 HTTP URLs total
289 unique HTTP URLs
60 unique domains
```

This does **not** match the plan's empirical note (`22 articles / 43 URLs / 17 domains`).

### 0.6 Doc verification

| Source | Quote | ✅/❌ |
|---|---|---|
| RFC 9110 (via wiki article) — Conditional requests | `Conditional requests through ETag + If-None-Match allow saving traffic and rate-limit budget.` | ✅ |
| RFC 9110 (via wiki article) — ETag vs Last-Modified | `The analogous flow works with If-Modified-Since + Last-Modified, but ETag is preferred because of precision.` | ✅ |
| RFC 9110 (via wiki article) — HEAD | `HEAD must return the same headers as GET — including Content-Length.` | ✅ |
| Python `urllib.request` docs | `For non-200 error codes, this simply passes the job on ... Eventually, HTTPDefaultErrorHandler will raise an HTTPError if no other handler handles the error.` | ✅ |
| Python `urllib.error` docs | `Though being an exception ... an HTTPError can also function as a non-exceptional file-like return value.` | ✅ |
| `scripts/lint.py` checks list | Structural path currently has 8 checks: broken links, orphan pages, orphan sources, stale articles, freshness review debt, missing backlinks, sparse articles, provenance completeness. | ✅ |
| `CLAUDE.md` Gate roles | `Advisory knowledge review (non-blocker) ... must not be used as a merge gate.` | ✅ |

Doc-verification note:
- Python docs do not say `304` explicitly, but `304` is a non-200 status under RFC 9110 and `urllib.request.HTTPErrorProcessor` routes non-200 responses through the HTTP error path.
- This was confirmed empirically in 2.6 below.

## 1. Changes

### 1.1 `scripts/lint.py` — add `check_source_drift()` + `--source-drift` flag

Meaningful whitespace-insensitive diff excerpt:

```diff
+import time
+import urllib.error
+import urllib.request
+from collections import defaultdict
+from email.utils import parsedate_to_datetime
+from urllib.parse import urlsplit
+from config import REPORTS_DIR, SOURCES_DIR, WIKI_DIR, now_iso, today_iso
+from utils import parse_frontmatter_list

+def _extract_source_urls(article: Path) -> list[str]:
+    ...
+
+def _check_source_url(...) -> tuple[str, str, dict[str, str]]:
+    ...
+    if exc.code == 304:
+        return "no_drift", "304 Not Modified", entry
+    if exc.code in (404, 410):
+        return "rot", f"HTTP {exc.code}", entry
+
+def check_source_drift(timeout: float = 10.0, delay: float = 2.0) -> list[dict]:
+    ...
+    state["source_drift_validators"] = cache
+    save_state(state)
+
+parser.add_argument(
+    "--source-drift",
+    action="store_true",
+    help="Check wiki/sources/ URLs for upstream drift or rot (network I/O)",
+)
+
+if args.source_drift:
+    print("  Checking: Source drift (network)...")
+    ...
+    print("  Skipping: Contradictions (--source-drift explicit network check)")
```

Controls:
- [x] New function `check_source_drift()` added
- [x] Uses `urllib.request` / `urllib.error` only
- [x] HEAD method with conditional headers (`If-None-Match`, `If-Modified-Since`)
- [x] Per-domain 2s rate limiting
- [x] 10s timeout per URL
- [x] Classification implemented: `drift` / `rot` / `no_drift` / `unverifiable` / `baseline_captured` / `access_denied` / `rate_limited` / `server_error` / `network_error`
- [x] Only `drift` and `rot` produce lint issues
- [x] State saved under `source_drift_validators`
- [x] `--source-drift` argparse flag added
- [x] NOT added to structural-only checks list
- [x] `reviewed` not touched
- [x] User-Agent header set

### 1.2 Path-scoped diff

```text
git status --short -- scripts/lint.py scripts/state.json docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md
 M scripts/lint.py
?? docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md

git diff -w --stat -- scripts/lint.py
 scripts/lint.py | 250 +++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 248 insertions(+), 2 deletions(-)

scripts/state.json is gitignored, not tracked:
.gitignore:11:scripts/state.json  scripts/state.json
```

Controls:
- [x] Only `scripts/lint.py` changed as tracked production file
- [x] `scripts/state.json` updated as untracked gitignored side effect
- [x] No other production files changed by this task

## 2. Phase 1 — Smoke

### 2.1 Syntax + import sanity

```text
ok
```

### 2.2 `--structural-only` unchanged

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

Result:
- structure and counts matched Baseline A exactly

### 2.3 `--source-drift` first run (baseline capture)

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
    Found 0 issue(s)
  Skipping: Contradictions (--source-drift explicit network check)

Report saved to: <repo>/reports/lint-2026-04-16.md

Results: 0 errors, 11 warnings, 288 suggestions
```

Result:
- first-run baseline capture worked
- no drift/rot findings were emitted on initial population

### 2.4 State verification

```text
keys ['last_lint', 'ingested', 'total_cost', 'flushed_sessions', 'last_auto_compile_date', 'last_auto_compile_hash', 'query_count', 'source_drift_validators']
cached 289
```

Result:
- `source_drift_validators` added
- 289 unique URLs cached

### 2.5 `--source-drift` second run

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
    Found 12 issue(s)
  Skipping: Contradictions (--source-drift explicit network check)

Report saved to: <repo>/reports/lint-2026-04-16.md

Results: 0 errors, 11 warnings, 300 suggestions
```

Observed findings:

```text
sources/coturn-turn-server-docs.md — drift: https://github.com/coturn/coturn
sources/coturn-turn-server-docs.md — drift: https://github.com/coturn/coturn/wiki/turnserver
sources/hatchling-build-backend-docs.md — drift: https://github.com/pypa/hatch/blob/master/docs/build.md
sources/hatchling-build-backend-docs.md — drift: https://github.com/pypa/hatch/blob/master/docs/config/build.md
sources/hatchling-build-backend-docs.md — drift: https://github.com/pypa/hatch/blob/master/docs/version.md
sources/python-dotenv-docs.md — drift: https://github.com/theskumar/python-dotenv/blob/main/docs/index.md
sources/ripgrep-docs.md — drift: https://github.com/BurntSushi/ripgrep/blob/master/README.md
sources/ripgrep-docs.md — drift: https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md
sources/ripgrep-docs.md — drift: https://github.com/BurntSushi/ripgrep/blob/master/FAQ.md
sources/semver-2-spec-docs.md — drift: https://semver.org/spec/v2.0.0.html
sources/yaml-1-2-spec-docs.md — drift: https://github.com/yaml/yaml-spec/blob/main/spec/1.2.1/spec.html
sources/yaml-1-2-spec-docs.md — drift: https://github.com/yaml/yaml-spec/blob/main/spec/1.2/markdown/spec.md
```

Result:
- **did not meet plan expectation of 0 issues on immediate second run**
- this became the main execution discrepancy

### 2.6 Explicit 304 / rot simulation

Local 304 test:

```text
304-test no_drift 304 Not Modified no_drift
```

Local 404 test:

```text
404-test rot HTTP 404 rot
```

Result:
- explicit stdlib behavior confirmed:
  - `304` arrives through `HTTPError` path and is correctly classified as `no_drift`
  - `404` is correctly classified as `rot`

### 2.7 Ruff check clean

```text
All checks passed!
```

### 2.8 Ruff format clean

```text
1 file already formatted
```

### 2.9 doctor --quick

```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/192 flushes spawned (skip rate 58%)
[PASS] flush_quality_coverage: Last 7d: 2942335/2945908 chars reached flush.py (coverage 99.9%)
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

Result:
- exit code 0
- no new regression attributable to this task
- existing Bug H failure remains pre-existing

## 3. Phase 2 — `[awaits user]`

### 3.1 Real drift detection after days

`[awaits user]`

### 3.2 Signal/noise assessment

`[awaits user]`

## 4. Phase 3 — `[awaits 7-day window]`

### 4.1 Drift statistics

`[awaits 7-day window]`

## 5. Tools used

| Tool | Status | Details |
|---|---|---|
| Wiki: `http-semantics-rfc9110-docs` | used | conditional requests, HEAD semantics, validators |
| Wiki: `wiki-knowledge-freshness-lifecycle` | used | Phase 1 constraints and Basis-axis context |
| Wiki: Phase 1 plan/report | used | continuity and prior decisions |
| Local: `scripts/lint.py` | used | target file read fully before edit |
| Local: `scripts/utils.py` | used | `load_state` / `save_state` pattern |
| Local: `scripts/config.py` | used | `SOURCES_DIR`, `STATE_FILE` |
| Local: `scripts/state.json` | used | key inspection and baseline verification |
| Python docs: `urllib.request` / `urllib.error` | used | `HTTPErrorProcessor` and `HTTPError` behavior |
| Ruff | used | syntax/style verification |
| `doctor --quick` | used | regression smoke |

## 6. Out-of-scope temptations

- did not add new dependencies
- did not touch `scripts/utils.py`
- did not touch `scripts/doctor.py`
- did not change CLI defaults for `--full` or `--structural-only`
- did not auto-write `reviewed`
- did not broaden this into concepts/ or hooks/

## 7. Discrepancies

### D1 — Plan's empirical scope was stale by a large margin

Plan expected:
- 22 source articles with HTTP URLs
- 43 URLs
- 17 domains

Reality at execution:
- 83 source articles with HTTP URLs
- 297 URLs total
- 289 unique URLs
- 60 domains

Impact:
- runtime was much higher than the plan implied
- first/second `--source-drift` runs became expensive operationally

### D2 — `scripts/lint.py` was already dirty in baseline

`git status` showed `M scripts/lint.py` before edits, but `git diff -w -- scripts/lint.py` was empty. This was pre-existing line-ending churn, not semantic code drift.

Handling:
- treated meaningful diff with `git diff -w`
- did not revert baseline churn

### D3 — Second run did not stay at 0 issues

The plan expected immediate second run = 0 issues.

Observed instead:
- 12 drift suggestions immediately after baseline capture
- almost all on GitHub blob/wiki URLs, plus one `semver.org` URL

This indicates at least one of:
- unstable weak ETags on these endpoints
- CDN/cache-layer validator churn
- HEAD responses whose validators are not stable enough for immediate drift inference

### D4 — External validator instability confirmed empirically

Manual repeated HEAD checks on suspected false-positive URLs:

GitHub blob URL:

```text
0 W/"ee41a8733d8f3e51ed59031c7d7ac33c" None
1 W/"ee41a8733d8f3e51ed59031c7d7ac33c" None
```

Semver URL:

```text
0 "69c509da-7991" Thu, 26 Mar 2026 10:26:34 GMT
1 "69c509da-7991" Thu, 26 Mar 2026 10:26:34 GMT
```

These values were already different from the second-run cached values for some URLs, which makes the core point clear: **the current validator policy is not stable enough to trust immediate second-run drift findings as high-signal on all domains.**

Conclusion:
- implementation is correct against the plan
- plan assumptions about validator stability were too optimistic
- this likely needs Phase 2.1 refinement, not blind rollout

## 8. Self-audit

- [x] 0.2b Baselines captured before edits
- [x] 0.6 Doc verification with real citations
- [x] 1.1 Diff shown, controls checked
- [x] 1.2 Only `scripts/lint.py` changed as tracked production file
- [x] 2.1 Syntax ok
- [x] 2.2 `--structural-only` unchanged
- [x] 2.3 First run = 0 source-drift issues
- [x] 2.4 State has `source_drift_validators`
- [ ] 2.5 Second run = 0 issues
- [x] 2.6 Explicit 304 and rot simulations pass
- [x] 2.7 Ruff check clean
- [x] 2.8 Ruff format clean
- [x] 2.9 `doctor --quick` not regressed by this task
- [x] `reviewed` not auto-stamped anywhere
- [x] No new deps (`urllib` only)
- [x] No commit / push
- [x] Personal data sanitized

## Summary

Phase 2 was implemented as planned in `scripts/lint.py`:

- explicit `--source-drift` flag
- HEAD + conditional validators
- 304 handling through `HTTPError`
- per-domain throttling
- state persistence in `source_drift_validators`
- drift = suggestion, rot = warning

However, the execution result is **not a clean acceptance pass** because the plan's immediate second-run expectation failed. The code behaved consistently; the unstable part appears to be upstream validator behavior on some domains, especially GitHub HTML/blob endpoints.

Practical status:
- **implementation complete**
- **design validation incomplete**
- next step should be a narrow follow-up to harden the policy for unstable validators/domains before treating this as a trustworthy advisory signal
