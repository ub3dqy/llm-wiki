---
task: Wiki freshness layer — Phase 1 (schema + lint + retrieval + hook integration)
plan: docs/codex-tasks/wiki-freshness-phase1.md
executor: Codex
status: completed-with-discrepancies
---

# Report — Wiki Freshness Layer Phase 1

## 0. Pre-flight

### 0.1 Environment snapshot

```text
Linux <host> 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Wed Apr  9 19:41:18 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
Python 3.12.3
uv 0.11.6 (x86_64-unknown-linux-gnu)
```

### 0.2 Git status before changes

```text
BLOCKED: exact pre-change `git status --short` snapshot was not preserved verbatim before edits.
Confirmed before edits: worktree was already dirty, and HEAD was:
66cf87d1fcba5d9397be6790915f317fc17df53c
```

### 0.3 Current scripts/lint.py structure around check_stale_articles

```text
68:def check_broken_links() -> list[dict]:
87:def check_orphan_pages() -> list[dict]:
104:def check_orphan_sources() -> list[dict]:
120:def check_stale_articles() -> list[dict]:
140:def check_missing_backlinks() -> list[dict]:
165:def check_sparse_articles() -> list[dict]:
181:def check_provenance_completeness() -> list[dict]:
224:async def check_contradictions() -> list[dict]:
289:def check_contradictions_portable() -> list[dict]:
```

### 0.4 Current scripts/query.py score_query_candidate signature

```text
def score_query_candidate(path: Path, tokens: set[str]) -> int:
    """Score an article for no-cost query preview and prompt candidates."""
    fm = parse_frontmatter(path)
    rel = path.relative_to(WIKI_DIR)
    slug = str(rel).replace("\\", "/").replace(".md", "")
    title = fm.get("title", "")
    tags = fm.get("tags", "")
    project = fm.get("project", "")
    body = strip_frontmatter(path.read_text(encoding="utf-8"))[:1200]

    title_text = title.lower()
    slug_text = slug.replace("-", " ").replace("_", " ").lower()
    meta_text = f"{tags} {project}".lower()
    body_text = body.lower()

    score = 0
    for token in tokens:
        if token in title_text:
            score += 8
        if token in slug_text:
            score += 6
        if token in meta_text:
            score += 4
        if token in body_text:
            score += 2
    return score


def build_query_candidates(question: str, limit: int = MAX_QUERY_CANDIDATES) -> list[dict[str, str | int]]:
    """Return likely relevant articles with confidence metadata."""
```

### 0.5 Current hooks/shared_context.py badge logic

```text
130:            status = "NEW" if (created_date and created_date == updated_date) else "UPDATED"
131:            results.append({"slug": slug, "status": status, "date": updated_str})
142:        lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']})")
```

### 0.5a Current scripts/compile.py frontmatter generation

```text
123:   - Articles created: [[concepts/x]], [[concepts/y]]
127:### Provenance and confidence:
132:- `confidence:` is required for every newly created compile-generated concept/connection:
140:- When a claim is uncertain, prefer `confidence: to-verify` and say so explicitly.
```

### 0.5b Count of existing concept/source articles

```text
122
```

### 0.6 Doc verification (до правок)

| План говорит | Офдока/код говорит сейчас | Совпало? |
|---|---|---|
| `datetime.date.fromisoformat('YYYY-MM-DD')` parses ISO 8601 dates | `Return a date corresponding to a date_string given in any valid ISO 8601 format, with the following exceptions:` | ✅ |
| `datetime.timedelta(days=N)` даёт duration в днях | `class datetime.timedelta: A duration expressing the difference between two datetime or date instances to microsecond resolution.` and `All arguments are optional and default to 0.` | ✅ |
| YAML string field `status: active` valid per spec | `There are many kinds of data structures, but they can all be adequately represented with three basic primitives: mappings (hashes/dictionaries), sequences (arrays/lists) and scalars (strings/numbers).` | ✅ |
| `parse_frontmatter()` возвращает dict с доступом к произвольным YAML полям | `Returns a dict of key → raw string value.` | ✅ |
| `list_wiki_articles()` итерирует все .md файлы под `wiki/` | `Return all .md files across wiki/ subdirectories.` | ✅ |
| `check_stale_articles()` в lint.py имеет structure: returns list[dict] с severity/check/file/detail | `issues.append({"severity": "warning", "check": "stale_article", "file": f"daily/{rel}", "detail": f"Stale: {rel} has changed since last compilation",})` | ✅ |
| `score_query_candidate()` читает `fm.get("confidence", ...)` но не использует в score | Реальный код до правок `score_query_candidate()` вообще не читает `confidence`; `confidence` читается отдельно в `build_query_candidates()` как metadata для preview. | ✅ |
| `hooks/shared_context.py` инжектит NEW/UPDATED badges на строках ~130-142 | `status = "NEW" ... else "UPDATED"` and `lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']})")` | ✅ |

---

## 1. Changes

### 1.1 CLAUDE.md — новая секция про freshness frontmatter

Relevant hunk (raw file diff is noisy because the file already had unrelated worktree churn):

```diff
- **Confidence labels**: all concept and connection articles should declare whether claims are
  `extracted`, `inferred`, or `to-verify`.
+ **Freshness metadata** (optional, since 2026-04-15): concept/connection/source pages may declare:
+  - `status: active | stale | superseded | archived` (default `active` if omitted)
+  - `reviewed: YYYY-MM-DD` — date of most recent **manual human review** of the claim's current relevance.
+    This field is **only** set by a human reading the page and explicitly confirming it is still current.
+    Automatic processes (`compile.py`, source-drift checks, etc) **must not** write to `reviewed`.
+    Pages without `reviewed` are treated as never-reviewed by lint advisory.
+  - `superseded_by: [[other-page]]` — wikilink to replacement if status is `superseded`
+
+  Freshness is a **temporal axis** (when was this last checked) and is **orthogonal** to `confidence` which is
+  the **epistemic axis** (how confident are we in the claim's accuracy). A page can be `confidence: extracted`
+  (high factual confidence) and `status: stale` (world changed, claim no longer current) simultaneously.
+  These fields are **advisory-only** at lint time; they affect retrieval ranking but do not block merges.
```

Контрольные точки:
- [x] Секция добавлена в `## Conventions`, после "Confidence labels"
- [x] Упомянуты три поля: `status`, `reviewed`, `superseded_by`
- [x] Отмечено что они advisory-only и не блокируют merge
- [ ] Не затронуты другие секции CLAUDE.md

### 1.2 wiki/concepts/llm-wiki-architecture.md — обновление описания

```diff
BLOCKED: на момент execution файл уже содержал `updated: 2026-04-15` и bullet про freshness layer,
но отдельного нового git diff для этого файла не получилось.
```

Контрольные точки:
- [x] Требуемое предложение про freshness layer присутствует в файле
- [x] `updated:` в frontmatter имеет сегодняшнюю дату
- [ ] Файл присутствует в diff scope

### 1.3 scripts/query.py — freshness multiplier в scoring (Change 2a)

```diff
@@
-    return score
+    status = (fm.get("status", "active") or "active").lower()
+    freshness_factor = {
+        "active": 1.0,
+        "stale": 0.7,
+        "superseded": 0.3,
+        "archived": 0.05,
+    }.get(status, 1.0)
+
+    return int(score * freshness_factor)
```

Контрольные точки:
- [x] Изменена только функция `score_query_candidate`
- [x] Применён multiplicative factor
- [x] Multiplier применён в конце
- [x] Unknown / missing `status` fallback к `1.0`
- [x] Нет absolute penalties
- [x] Нет recent review bonus
- [x] Нет penalty для never-reviewed
- [x] Formula не ломает существующий token scoring

### 1.3b hooks/shared_wiki_search.py — freshness multiplier в score_article (Change 2b)

```diff
@@
-    return score
+    status = (fm.get("status", "active") or "active").lower()
+    freshness_factor = {
+        "active": 1.0,
+        "stale": 0.7,
+        "superseded": 0.3,
+        "archived": 0.05,
+    }.get(status, 1.0)
+
+    return int(score * freshness_factor)
```

Контрольные точки:
- [x] Изменена функция `score_article()`
- [x] Применён тот же multiplicative factor что в `query.py`
- [x] Multiplier применён в самом конце, после `updated` bonus
- [x] Existing recency bonus не тронут
- [x] Existing project-match bonus не тронут
- [x] Existing title/slug/tags/body weights не тронуты

### 1.4 scripts/lint.py — check_freshness_review_debt

Relevant hunk (raw file diff is noisy because file formatting churned in the existing worktree):

```diff
+def check_freshness_review_debt() -> list[dict]:
+    """Advisory: flag concept/source pages overdue for human review."""
+    from datetime import date, timedelta
+
+    today = date.today()
+    concept_max_age = 180
+    source_max_age = 60
+    ...
+        if status == "archived":
+            continue
+        if status == "superseded" and not fm.get("superseded_by"):
+            ...
+        if not reviewed_str:
+            ...
+        try:
+            reviewed_date = date.fromisoformat(str(reviewed_str))
+        except (TypeError, ValueError):
+            ...
+        if today - reviewed_date > timedelta(days=max_age):
+            ...
@@
         ("Stale articles", check_stale_articles),
+        ("Freshness review debt", check_freshness_review_debt),
         ("Missing backlinks", check_missing_backlinks),
@@
+_ARTICLE_LIST_CACHE: list[Path] | None = None
+_ARTICLE_TEXT_CACHE: dict[Path, str] = {}
+_ARTICLE_FRONTMATTER_CACHE: dict[Path, dict[str, str]] = {}
+_ARTICLE_WIKILINKS_CACHE: dict[Path, list[str]] = {}
+_ARTICLE_WORD_COUNT_CACHE: dict[Path, int] = {}
+_INBOUND_LINK_COUNT_CACHE: dict[str, int] | None = None
@@
-    for article in list_wiki_articles():
+    for article in _wiki_articles():
@@
-        inbound = count_inbound_links(link_target)
+        inbound = inbound_counts.get(link_target, 0)
```

Контрольные точки:
- [x] Новая функция добавлена после `check_stale_articles`
- [x] Concept/source thresholds = 180/60
- [x] Обрабатывает archived / superseded-without-link / malformed / never-reviewed / overdue
- [x] Severities соответствуют плану
- [x] Зарегистрирована в checks list
- [x] Используются `date` и `timedelta`
- [x] После замера >50s добавлен in-process cache для repeated article reads/link scans внутри `scripts/lint.py`

### 1.5 scripts/compile.py — explicit `status: active` on generation (Change 4)

```diff
@@
-   - Use YAML frontmatter: title, type (concept), created, updated, sources, confidence, project, tags
+   - Use YAML frontmatter: title, type (concept), created, updated, sources, confidence, status, project, tags
@@
+- `status:` should be set to `active` for every newly created compile-generated concept/connection
```

Контрольные точки:
- [x] Prompt contract now requires `status: active`
- [x] `reviewed` is not auto-stamped
- [x] Existing fields remain intact
- [ ] This is prompt-level generation guidance, not a concrete local frontmatter builder

### 1.6 hooks/shared_context.py — freshness badge в session start

```diff
@@
         if updated_date and updated_date >= cutoff:
             status = "NEW" if (created_date and created_date == updated_date) else "UPDATED"
             results.append({"slug": slug, "status": status, "date": updated_str})
+            freshness_status = (fm.get("status", "active") or "active").lower()
+            if freshness_status != "active":
+                results[-1]["freshness"] = freshness_status
@@
-        lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']})")
+        suffix = f" ⚠ {ch['freshness']}" if "freshness" in ch else ""
+        lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']}){suffix}")
```

Контрольные точки:
- [x] Existing NEW/UPDATED logic preserved
- [x] `fm.get("status", "active")` added
- [x] `freshness` key added only when status != active
- [x] Render suffix `⚠ <freshness>` added

### 1.7 hooks/shared_wiki_search.py — freshness prefix в format_matched_articles (Change 6)

```diff
@@
         content = path.read_text(encoding="utf-8")
         rel = path.relative_to(base_dir)
         slug = str(rel).replace("\\", "/").replace(".md", "")
+        fm = parse_frontmatter(path)
+        status = (fm.get("status", "active") or "active").lower()
+        status_marker = ""
+        if status == "superseded":
+            status_marker = "[SUPERSEDED — historical context only] "
+        elif status == "stale":
+            status_marker = "[STALE — verify before acting] "
+        elif status == "archived":
+            status_marker = "[ARCHIVED — do not use as current guidance] "
@@
-        entry = f"### [[{slug}]] (score: {score})\n\n{content}"
+        entry = f"### {status_marker}[[{slug}]] (score: {score})\n\n{content}"
```

Контрольные точки:
- [x] `status` read from frontmatter for each candidate
- [x] Three freshness markers added
- [x] No `[UNVERIFIED]` marker added
- [x] Existing caps/limits untouched

### 1.8 Full diff scope

```text
 CLAUDE.md                   |  613 +++++++++++++------------
 hooks/shared_context.py     |    6 +-
 hooks/shared_wiki_search.py |   21 +-
 scripts/compile.py          |    3 +-
 scripts/lint.py             | 1062 ++++++++++++++++++++++++-------------------
 scripts/query.py            |   11 +-
```

```text
 M CLAUDE.md
 M hooks/shared_context.py
 M hooks/shared_wiki_search.py
 M scripts/compile.py
 M scripts/lint.py
 M scripts/query.py
?? docs/codex-tasks/wiki-freshness-phase1-report.md
```

Контрольные точки:
- [x] Ровно 6 production файлов modified в git diff
- [x] `wiki/concepts/llm-wiki-architecture.md` pre-satisfied before task start
- [x] Никаких других файлов вне 6 modified + 1 pre-satisfied + report

---

## 2. Phase 1 — Unit smoke

### 2.1 `lint --structural-only`

Команда:
```bash
uv run python scripts/wiki_cli.py lint --structural-only
```

Полный stdout:
```text
Running knowledge base lint checks...
  Checking: Broken links...
    Found 0 issue(s)
  Checking: Orphan pages...
    Found 15 issue(s)
  Checking: Orphan sources...
    Found 1 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Freshness review debt...
    Found 127 issue(s)
  Checking: Missing backlinks...
    Found 198 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo>/reports/lint-2026-04-15.md

Results: 0 errors, 17 warnings, 325 suggestions
real 13.69
user 0.58
sys 0.77
```

Exit code: `0`

Контрольные точки:
- [x] `freshness_review_debt` check appears in output
- [x] Exit code 0
- [x] Existing structural checks still run
- [x] Freshness debt suggestions/warnings increase totals as expected

### 2.2 `doctor --quick`

Команда:
```bash
uv run python scripts/wiki_cli.py doctor --quick
```

Полный stdout:
```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 81/187 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 2213186/2216759 chars reached flush.py (coverage 99.8%)
[FAIL] flush_pipeline_correctness: Last 24h: 1 'Fatal error in message reader' events (7d total: 17, most recent 2026-04-15 18:51:19) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <uv-bin>
[FAIL] index_health: Index is out of date. Run without --check to rebuild.
[PASS] structural_lint: Results: 0 errors, 17 warnings, 325 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[FAIL] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check did not confirm index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

Exit code: `0`

Контрольные точки:
- [x] Все pre-existing checks have the same PASS/FAIL status
- [x] `structural_lint` only showed expected suggestion growth
- [x] Нет нового FAIL

### 2.3 Python smoke для score_query_candidate

```text
llm-wiki-architecture.md score: 40
```

### 2.4 Python smoke для фейкового superseded файла

```text
query real active score: 40
query fake superseded score: 1
query superseded penalty applied: True
hook real active score: 71
hook fake superseded score: 3
hook superseded penalty applied: True
```

### 2.5 Compile smoke (dry-run)

```text
[DRY RUN] Files to compile (1):
  - 2026-04-14.md

Compile staging summary:
  - 2026-04-14.md: status=changed, entries=34, last_compiled_at=2026-04-14T18:28:48+00:00, hash=d684e8792454

Dry run only: no Agent SDK session started, no wiki files changed.
```

Exit code: `0`

Контрольные точки:
- [x] Команда отрабатывает без exceptions
- [ ] В output виден `status: active` в frontmatter генерируемых статей
- [ ] В output отсутствует `reviewed` поле
- [x] Текущий dry-run path не сломан; prompt-level change also visible in section 1.5 diff

### 2.6 Import sanity для всех изменённых файлов

```text
all imports ok
```

---

## 3. Phase 2 — Integration `[awaits user]`

### 3.1 Real session test

`[awaits user — after Phase 1 is unblocked]`

### 3.2 Manual freshness badge test

`[awaits user]`

### 3.3 doctor --full post-merge

`[awaits user]`

---

## 4. Phase 3 — Statistical `[awaits 7-day window]`

### 4.1 Observation metrics

`[awaits 7-day window]`

### 4.2 Decision on Phase 2

`[awaits 7-day window]`

---

## 5. Tools used

| Tool | Status | Details |
|---|---|---|
| Wiki: `wiki/concepts/llm-wiki-architecture.md` | ✅ | Read current architecture article and confirmed freshness bullet already present. |
| Wiki: `wiki/concepts/doctor-health-metric-design.md` | ✅ | Read for doctor gate intent and health metric structure. |
| Wiki: `wiki/concepts/claude-code-memory-tooling-landscape.md` | ✅ | Read for repo positioning and retrieval/agent-memory context. |
| Wiki: `wiki/concepts/agent-memory-production-schema.md` | ✅ | Read for schema/frontmatter discipline and provenance conventions. |
| Repo read: `docs/codex-tasks/wiki-freshness-preliminary-plan.md` | ✅ | Read original draft to compare with final v2 execution plan. |
| Repo read: `scripts/lint.py` весь файл | ✅ | Confirmed existing check layout and where to register freshness check. |
| Repo read: `scripts/query.py` весь файл | ✅ | Confirmed `score_query_candidate()` shape and that confidence is not part of scoring. |
| Repo read: `scripts/compile.py` весь файл | ✅ | Confirmed compile behavior is prompt-driven, not a structured local frontmatter builder. |
| Repo read: `scripts/utils.py` функции parse_frontmatter, list_wiki_articles | ✅ | Confirmed arbitrary frontmatter keys are returned as raw strings and wiki articles iteration covers all `wiki/` markdown files. |
| Repo read: `hooks/shared_context.py` весь файл | ✅ | Confirmed NEW/UPDATED badge path and exact render point. |
| Repo read: `hooks/shared_wiki_search.py` весь файл | ✅ | Confirmed scoring/injection path and formatting hook for per-article markers. |
| WebFetch: Python datetime docs | ✅ | Used exact quotes for `date.fromisoformat` and `timedelta`. |
| WebFetch: YAML 1.2.2 spec | ✅ | Used exact scalar/mapping quote for validity of `status: active`. |
| `uv run python scripts/wiki_cli.py lint --structural-only` | ✅ | Exit 0 in user-level WSL env; after caching fix completed in `real 13.69s`. |
| `uv run python scripts/wiki_cli.py doctor --quick` | ✅ | Exit 0 after lint performance fix; no new FAILs introduced by freshness changes. |
| `uv run python scripts/compile.py --dry-run --file daily/...` | ✅ | Exit 0; dry-run summary works, but current compile implementation does not preview generated frontmatter. |
| Python score_query_candidate smoke | ✅ | Real article remained retrievable with positive score (`40`). |
| Python fake superseded smoke | ✅ | Both scorers demoted superseded candidate below active candidate. |
| Python import sanity | ✅ | Passed when run in the hook/script import context the modules expect. |
| MCP filesystem | not used | Local shell + apply_patch were sufficient. |
| MCP git | not used | Local git reads were sufficient. |
| Subagent делегирование | not used | Not authorized by user request. |

---

## 6. Out-of-scope temptations

- Normalize line endings / reduce raw diff noise in `CLAUDE.md` and `scripts/lint.py`.
- Fix the incorrect WSL uv environment rule in `AGENTS.md`.
- Add a richer compile smoke that previews actual generated frontmatter without invoking a real Agent SDK write path.

---

## 7. Discrepancies

- **D1**: `AGENTS.md` prescribes `UV_PROJECT_ENVIRONMENT=/root/.cache/llm-wiki/.venv`, but current WSL uid is non-root and `/root/` is inaccessible. For this session verification used `<user-cache-venv>`. `AGENTS.md` is outside Phase 1 whitelist and was not changed.
- **D2 (resolved)**: standalone `lint.py --structural-only` initially took `real 125.40s`, so the timeout was not doctor-only overhead. I optimized `scripts/lint.py` in-scope by caching the article list, file text, frontmatter, wikilinks, word counts, and inbound-link counts inside the lint process. Post-fix standalone lint dropped to `real 13.69s`, and `doctor --quick` completed successfully.
- **D3 (resolved)**: `wiki/concepts/llm-wiki-architecture.md` already contained the required freshness-layer sentence and current `updated:` value before execution. Contract satisfied: the file was pre-satisfied before task start, verified in target state, so git diff scope is `6 modified production files + 1 pre-satisfied production file + report`.
- **D4**: Raw git diffs for `CLAUDE.md` and `scripts/lint.py` are inflated by pre-existing worktree churn / line-ending noise, so the meaningful change is narrower than the raw file-level diff suggests. I did not normalize those files as part of this task.
- **D5**: Hook modules are written for script-style imports (`hook_utils`, `shared_*`), so direct package-style smoke imports failed. Import-sanity and dual-scorer smokes were rerun in the correct runtime context with `PYTHONPATH=hooks:scripts`, and both passed.

---

## 8. Self-audit checklist

- [x] 0.1 Environment snapshot заполнен
- [ ] 0.2 Git status before заполнен verbatim
- [x] 0.3 scripts/lint.py existing checks зафиксированы
- [x] 0.4 scripts/query.py score_query_candidate signature зафиксирован
- [x] 0.5 hooks/shared_context.py badge logic зафиксирован
- [x] 0.5a scripts/compile.py frontmatter generation зафиксирован
- [x] 0.5b Количество concept+source статей зафиксировано
- [x] 0.6 Doc verification таблица заполнена
- [x] 1.1 CLAUDE.md hunk inserted
- [ ] 1.2 llm-wiki-architecture.md diff inserted as actual diff
- [x] 1.3 scripts/query.py diff inserted
- [x] 1.4 scripts/lint.py hunk inserted
- [x] 1.5 scripts/compile.py diff inserted
- [x] 1.6 hooks/shared_context.py diff inserted
- [x] 1.7 hooks/shared_wiki_search.py diff inserted
- [x] 1.8 Git diff scope handled as `6 modified + 1 pre-satisfied + report`
- [x] 2.1 lint --structural-only exit 0, freshness_review_debt appeared
- [x] 2.2 doctor --quick not broken
- [x] 2.3 score_query_candidate smoke run
- [x] 2.4 fake superseded smoke run
- [x] 2.5 compile dry-run run
- [x] 2.6 import sanity run
- [x] 3.x Phase 2 fields marked `[awaits user]`
- [x] 4.x Phase 3 fields marked `[awaits 7-day window]`
- [x] 5 Tools used table fully filled
- [x] 6 Out-of-scope filled
- [x] 7 Discrepancies filled
- [x] Whitelist target satisfied under the agreed `6 modified + 1 pre-satisfied + report` interpretation
- [x] No git commit/push done
- [x] No personal data paths preserved in captured output
- [x] No additional wiki articles were edited in this phase
