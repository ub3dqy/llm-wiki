# Planning Audit — Wiki Freshness Phase 2: Source Drift Detection

## 1. Files read

| File | Lines | What I extracted |
|---|---|---|
| wiki/concepts/wiki-knowledge-freshness-lifecycle.md | full | 4-axis model (Age/Status/Basis/Usage), Phase 1 design decisions, explicit note that Phase 2 = Basis axis |
| wiki/sources/http-semantics-rfc9110-docs.md | full | HEAD safe+idempotent+cacheable, ETag/Last-Modified validators, conditional request flow (If-None-Match→304), 404/410 semantics |
| docs/codex-tasks/wiki-freshness-phase2-task-brief-for-claude.md | full | All design questions, constraints, scope, anti-patterns |
| scripts/lint.py | 181-200, 655-680 | check_stale_articles pattern (load_state, hash compare, issue dict), checks registration list, structural-only vs full mode split |
| scripts/utils.py | 25-35 | load_state/save_state pattern using STATE_FILE (JSON) |
| scripts/config.py | via grep | STATE_FILE location |

## 2. Commands run

| Command | Output (key) | What it proved |
|---|---|---|
| Count sources with HTTP URLs | 22 articles with HTTP, 43 total URLs | Scope = ~22 articles checkable, 104 unverifiable |
| Count by domain | 17 unique domains | No single domain dominance, rate limiting per-domain feasible |
| Exact URL list | 43 URLs listed | docs.bullmq.io(4), anthropic(10), github(3), flutter(2), go(2), grafana(2), minio(2), nodejs(2), postgresql(3), etc. |
| lint.py checks registration | 8 structural + 1 LLM (non-structural) | New check goes to non-structural (network I/O), not structural-only |
| state.json keys | last_lint, ingested, total_cost, flushed_sessions, etc. | Can add `source_drift_cache` key to existing state pattern |

## 3. URLs fetched

None needed — HTTP semantics already documented in wiki article. RFC 9110 conditional request flow fully covered there.

## 4. Wiki articles consulted

| Article | What I used |
|---|---|
| wiki/concepts/wiki-knowledge-freshness-lifecycle.md | Phase 1 design decisions, 4-axis model, "Basis axis = Phase 2" |
| wiki/sources/http-semantics-rfc9110-docs.md | HEAD method, ETag, Last-Modified, If-None-Match, 304/200/404/410 semantics |

## 5. Assumptions + verification

| Assumption | Verified? | How |
|---|---|---|
| ~22 source articles have HTTP URLs | ✅ | Python script counting `http` in frontmatter `sources:` |
| 43 total URLs across those articles | ✅ | Same script |
| 17 unique domains | ✅ | Same script |
| lint.py structural-only checks are offline | ✅ | Read code: structural checks = list[8], LLM check separate, gated by `not args.structural_only` |
| state.json exists and has key-value structure | ✅ | `cat scripts/state.json` + Python parse |
| load_state/save_state pattern exists | ✅ | Read utils.py:25-35 |
| Source drift check should NOT be in structural-only | ✅ verified correct | Network I/O is non-deterministic, per CLAUDE.md gate roles "Advisory knowledge review (non-blocker)" |
| `reviewed` must not be auto-stamped by drift check | ✅ constraint from Phase 1 + ТЗ |

## 6. Baselines captured

| Measurement | Value | Command |
|---|---|---|
| Total source articles | 126 | list_wiki_articles() + filter sources/ |
| HTTP-checkable articles | 22 | frontmatter `sources:` contains `http` |
| Total HTTP URLs | 43 | parsed from sources field |
| Unique domains | 17 | split URL by `/` |
| Current structural lint checks | 8 | grep lint.py checks list |
| Current state.json keys | 7 | json.load + keys() |
