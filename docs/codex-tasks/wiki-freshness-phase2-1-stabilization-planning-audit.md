# Planning Audit — Wiki Freshness Phase 2.1: Drift Signal Stabilization

## 1. Files read

| File | Lines | What I extracted |
|---|---|---|
| Phase 2 report (drift findings section) | grep "drift:" | All 12 false positives: 10 github.com blob/wiki, 1 github.com repo root, 1 semver.org |
| Phase 2.1 ТЗ | full | Strategy options A/B/C/D, constraints, success criteria |
| wiki/sources/http-semantics-rfc9110-docs.md | 100-120 | Weak ETag `W/"..."` vs strong, conditional request semantics |

## 2. Commands run

| Command | Output | What it proved |
|---|---|---|
| `grep "drift:" report.md` | 12 entries | 10/12 = github.com HTML pages, pattern clear |
| URL pattern analysis | github.com/.../blob/*, /wiki/*, repo root | Single regex covers 10/12 false positives |

## 3. Assumptions + verification

| Assumption | Verified? | How |
|---|---|---|
| GitHub HTML pages rotate ETags per-request | ✅ empirical | Phase 2 report: same URLs flagged as drift within minutes of baseline |
| URL pattern match covers 10/12 false positives | ✅ | Manual inspection of all 12 URLs in report |
| semver.org is single remaining outlier (1/289 = 0.3%) | ✅ | Only non-GitHub false positive in report |
| Rot signal (404/410) is unaffected by this change | ✅ design | Skip applies only before HEAD request, rot check path unchanged |
| No state model changes needed | ✅ design | Pattern skip happens before HTTP request, no pending/counter needed |
