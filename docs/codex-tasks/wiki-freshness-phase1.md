---
task: Wiki freshness layer — Phase 1 (schema + lint + retrieval + hook integration)
executor: Codex
revision: v2 (2026-04-15) — corrections applied after Codex feedback review
whitelist: [scripts/lint.py, scripts/query.py, scripts/compile.py, hooks/shared_context.py, hooks/shared_wiki_search.py, CLAUDE.md, wiki/concepts/llm-wiki-architecture.md]
parent_discussion: docs/codex-tasks/wiki-freshness-preliminary-plan.md
feedback_review: docs/codex-tasks/wiki-freshness-claude-feedback-review.md
---

## Revision v2 changelog (2026-04-15)

This plan was revised after Codex's feedback review (`wiki-freshness-claude-feedback-review.md`) found 5 substantive issues in v1. All 5 are accepted as valid corrections:

1. **Do not conflate `confidence` with freshness.** `confidence: extracted|inferred|to-verify` is epistemic axis (what we know). Freshness (`status` / `reviewed`) is temporal axis (when we last checked). A page can be `extracted` AND `stale`. Removed `confidence=to-verify → [UNVERIFIED]` marker from Change 6 — it belonged to a different axis and was outside Phase 1 scope.

2. **`updated` is not `reviewed`.** `updated` changes on any edit (typo, backlink, section rename). `reviewed` is a semantic claim that content was re-evaluated for current relevance. Kept as distinct fields.

3. **Phase 2 source-drift uses `ETag → Last-Modified → fallback`, not Last-Modified only.** Per RFC 9110, ETag is stronger validator (SHOULD when computable), Last-Modified is secondary. Phase 2 out-of-scope note updated; no Phase 1 code impact.

4. **Scoring penalties switched from absolute values (`-3/-8/-15`) to multiplicative factors (`*1.0 / *0.7 / *0.3 / *0.05`).** Absolute penalties are premature without knowing real score distributions. Multipliers auto-scale to any distribution and establish relative ordering `active > stale > superseded > archived` without accidentally erasing archived pages from retrieval entirely. Changes 2 and 2b (new) use multipliers.

5. **`compile.py` no longer auto-stamps `reviewed: <today>`.** `reviewed` remains strictly manual human review event, not machine side-effect. `compile.py` may still stamp `status: active` explicitly (optional, since active is default anyway). This preserves the trust semantic of `reviewed` field.

Also:
- **Numbers updated**: 109 wiki pages (41 concepts, 60 sources, 8 other), 45 with `confidence`. v1 used stale "97 articles" count.
- **Change 2 split into 2a and 2b**: freshness-aware ranking must be added to **both** `scripts/query.py:score_query_candidate` (manual query preview path) AND `hooks/shared_wiki_search.py:score_article` (UserPromptSubmit injection path, which is the real behavioral lever per Codex review point 3). v1 only covered query.py.

# Plan — Wiki Freshness Layer Phase 1

## Иерархия источников правды

1. **Официальная документация** (Python stdlib, YAML spec, markdown frontmatter conventions) — primary source of truth для API и format contracts.
2. **Реальное состояние кода проекта** на момент исполнения — `scripts/lint.py`, `scripts/query.py`, `scripts/compile.py`, `hooks/shared_context.py`, `hooks/shared_wiki_search.py`, `CLAUDE.md`, существующие frontmatter статей в `wiki/` — secondary.
3. **Этот план** — derived artifact, написан Claude'ом на основе чтения preliminary plan Codex'а + source dive в существующий код. При расхождении плана с офдокой или реальным кодом — приоритет у офдоки/кода, не у плана.

## Context

Preliminary plan от Codex (`docs/codex-tasks/wiki-freshness-preliminary-plan.md`) предложил 5-фазный rollout freshness/staleness tracking для LLM Wiki с 5 candidate approaches (A-E). Claude провёл критическое чтение и source dive, и сократил scope до **двух** фаз. Данный план — **Phase 1 only**. Phase 2 (source-drift detection для `sources/`) будет отдельным follow-up handoff'ом после merge Phase 1 и ~1 недели observation.

**[PROJECT]** Ключевые решения по scoping'у (обоснование в Claude's view раздел `docs/codex-tasks/wiki-freshness-preliminary-plan.md` — обсуждение в чате):

- **Убрано из scope Phase 1**: access-log analytics, usage-weighted review queue, source-hash sync, `verified_at` metadata, `freshness_horizon_days` per-page, per-type TTL в frontmatter. YAGNI до конкретного pain point'а.
- **Добавлено в scope Phase 1** (относительно Codex Option A): интеграция с **существующим** `confidence` полем и `hooks/shared_context.py` badge mechanism, вместо введения всего с нуля.
- **Deferred to Phase 2**: source URL drift detection (HEAD + Last-Modified) — ценно, но требует отдельной верификации после того как schema Phase 1 стабилизируется.

**[EMPIRICAL-wiki/]** Текущий frontmatter `concept`/`source` статей содержит (проверено на `llm-wiki-architecture.md`, `doctor-health-metric-design.md`, `codex-stop-hook-reliability.md`, `anthropic-claude-code-hooks-docs.md`):

```yaml
title, type, created, updated, sources, confidence, project, tags
```

**[EMPIRICAL-wiki/, verified 2026-04-15]** Размер wiki base на момент написания плана:
- 109 total wiki pages
- 41 pages under `wiki/concepts/`
- 60 pages under `wiki/sources/`
- ~8 other pages (connections, entities, qa, analyses, overview)
- 45 pages have `confidence:` field (concepts + compile-generated sources)

**[EMPIRICAL-scripts/lint.py:120-137]** `check_stale_articles()` уже использует content-hash сравнение для daily logs. Механизм существует, можно расширить на wiki articles.

**[EMPIRICAL-scripts/query.py:61-86]** `score_query_candidate()` читает только `title`, `tags`, `project` и первые 1200 символов body. `confidence` и `status` в этой функции **не читаются вообще**. Confidence читается отдельно в `build_query_candidates()` как metadata для preview output, но не влияет на scoring. Строки 76-86 — текущая формула scoring (только token matching по title/slug/meta/body, без freshness и без confidence).

**[EMPIRICAL-hooks/shared_wiki_search.py:177-253]** `score_article()` это **отдельный** scorer используемый на UserPromptSubmit injection path'е. Имеет собственные веса (title=16/10, slug=14, tags, aliases, body snippet) плюс project-match bonus (+6) плюс существующий recency bonus (+1 если `updated <= 14 days`). Typical score range наблюдался 20-200+.

**[EMPIRICAL-hooks/shared_wiki_search.py:286-318]** `format_matched_articles()` форматирует каждый candidate как `### [[{slug}]] (score: {score})\n\n{content}` с per-article char cap, возвращает готовый additionalContext block для hook JSON output.

**[EMPIRICAL-hooks/shared_context.py:130-142]** Уже есть status badge injection (`NEW | UPDATED`) в SessionStart. Это прецедент для freshness badge.

## Design goal

Добавить минимально-достаточный freshness layer для wiki который:

1. **Различает** в schema 4 состояния статьи: `active` (default), `stale`, `superseded`, `archived`
2. **Позволяет** отмечать manual human review date через `reviewed:` поле (поле заполняется исключительно вручную человеком; автоматические процессы — `compile.py`, source-drift checks, rebuild_index и т.п. — **не имеют права** писать в `reviewed`)
3. **Трекает** supersession через `superseded_by:` wikilink
4. **Штрафует** stale/superseded в retrieval ranking (`query.py`)
5. **Показывает** freshness state в hook-инжектированном контексте (`hooks/shared_context.py` и `shared_wiki_search.py`)
6. **Сообщает** advisory в `lint.py` про overdue review и missing review
7. **Автоматически** ставит `status: active` при `compile.py` генерации новых концептов (**НЕ** трогает `reviewed` — это строго manual field, см. revision v2 changelog point 5)

Это **не** решает все freshness проблемы. Это фундамент (schema + visible signals) поверх которого Phase 2 и Phase 3 сделают более сложные вещи.

## Doc verification

Codex обязан перечитать ПЕРЕД правкой:

| URL / Path | Что проверить |
|---|---|
| https://yaml.org/spec/1.2.2/ | YAML 1.2 spec — формат frontmatter полей (string, list, date) |
| https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat | `datetime.date.fromisoformat()` контракт для парсинга `reviewed: YYYY-MM-DD` |
| https://docs.python.org/3/library/datetime.html#datetime.timedelta | `timedelta(days=...)` контракт для age calculation |
| `CLAUDE.md` (repo root) | секции "Conventions" и "Agent operating rules" — их формат нельзя нарушать |
| `wiki/concepts/llm-wiki-architecture.md` | существующий frontmatter пример для согласованности полей |
| `docs/codex-tasks/wiki-freshness-preliminary-plan.md` | preliminary plan от Codex — reference для того что он предлагал изначально |
| `scripts/lint.py:check_stale_articles` (существующая функция) | не дублировать её логику, а дополнить новой функцией |
| `scripts/query.py:score_query_candidate` | текущая формула scoring (строки 76-86) |
| `hooks/shared_context.py:build_recent_changes` (если существует) | текущая логика инжекта status badges |

## Mandatory external tools

| Tool | Purpose |
|---|---|
| Wiki read: `wiki/concepts/llm-wiki-architecture.md` | Контекст архитектуры |
| Wiki read: `wiki/concepts/doctor-health-metric-design.md` | Паттерн one-metric-per-dimension — применять к новым lint check'ам |
| Wiki read: `wiki/concepts/claude-code-memory-tooling-landscape.md` | Отметка про риск noise/stale articles при heavy automation |
| Wiki read: `wiki/concepts/agent-memory-production-schema.md` | Reference для `validity_to`, `archived_at` паттернов (но НЕ внедрять их в этом Phase — только cross-reference) |
| Repo read: `docs/codex-tasks/wiki-freshness-preliminary-plan.md` | Codex's own discussion draft |
| Repo read: `scripts/lint.py` (весь файл) | Существующая структура checks и их return format |
| Repo read: `scripts/query.py` (весь файл) | Существующая формула scoring и call sites |
| Repo read: `scripts/compile.py` | Где compile генерирует frontmatter для новых статей |
| Repo read: `hooks/shared_context.py` | Текущий badge injection pattern |
| Repo read: `hooks/shared_wiki_search.py` | Где search results форматируются для injection в UserPromptSubmit |
| Repo read: `scripts/utils.py` (функции `parse_frontmatter`, `list_wiki_articles`) | Утилиты которые уже существуют — не переписывать |
| `uv run python scripts/wiki_cli.py lint --structural-only` | Проверить что новый check корректно регистрируется |
| `uv run python scripts/wiki_cli.py doctor --quick` | Убедиться что изменения не сломали doctor gate |
| `uv run python -c "..."` для локальных smoke тестов frontmatter парсинга | |
| WebFetch: https://yaml.org/spec/1.2.2/ (раздел Schema) | Процитировать дословно типы YAML которые мы используем |
| WebFetch: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat | Процитировать дословно контракт `fromisoformat` |

## Files to modify (whitelist)

**Strict whitelist — ровно эти файлы для code/doc changes, ничего больше**:

> **Важное уточнение про whitelist vs handoff artifacts**: whitelist описывает
> **production code/doc changes** которые попадут в git diff. Файл отчёта
> `docs/codex-tasks/wiki-freshness-phase1-report.md` — это **handoff artifact**,
> часть контракта задачи, а **не** production change. Он заполняется по мере
> выполнения Phases 0-1, это ожидаемый side effect задачи и в whitelist
> **не входит по определению**. Git diff будет содержать 7 whitelisted файлов
> + заполненный report. Любые другие изменения — Discrepancies.


1. **`scripts/lint.py`** — добавить `check_freshness_review_debt()` функцию и зарегистрировать в `run_all_checks()`
2. **`scripts/query.py`** — модифицировать `score_query_candidate()` чтобы применять freshness multiplier (`active=1.0 / stale=0.7 / superseded=0.3 / archived=0.05`) на финальный score. См. Change 2a ниже для точной формулы. Никакого recent-reviewed bonus'а на Phase 1 нет (убрано в v2).
3. **`scripts/compile.py`** — при генерации новых концептов добавлять **только** `status: active` в frontmatter. `reviewed` поле **не** auto-stamp'ить (см. Change 4 и revision v2 changelog point 5)
4. **`hooks/shared_context.py`** — extend `NEW/UPDATED` badge logic новым маркером `[stale]`/`[superseded]` когда status != active
5. **`hooks/shared_wiki_search.py`** — добавить freshness indicator в форматирование поисковых results которые инжектятся в UserPromptSubmit context
6. **`CLAUDE.md`** — документировать новые frontmatter поля в секции "Conventions" (одним подпунктом про `status`/`reviewed`/`superseded_by`)
7. **`wiki/concepts/llm-wiki-architecture.md`** — обновить описание lifecycle + добавить упоминание freshness layer

**НЕ трогать**:
- `wiki/*.md` (все остальные статьи) — миграция существующих статей на новый schema это отдельная задача, не Phase 1
- `hooks/session-start.py`, `hooks/session-end.py` — они уже работают через `shared_context.py` helper, достаточно правки хелпера
- `scripts/doctor.py` — `check_freshness_debt` metric это Phase 2, не сейчас
- `scripts/utils.py` — `parse_frontmatter` уже умеет читать произвольные YAML поля, не надо менять
- `scripts/rebuild_index.py` — не требует изменений (index не показывает freshness directly)

## Fix design

### Change 1 — Schema (`CLAUDE.md` + `wiki/concepts/llm-wiki-architecture.md`)

**Где в `CLAUDE.md`**: секция "Conventions", после "Confidence labels" добавить новый bullet:

```markdown
- **Freshness metadata** (optional, since 2026-04-15): concept/connection/source pages may declare:
  - `status: active | stale | superseded | archived` (default `active` if omitted)
  - `reviewed: YYYY-MM-DD` — date of most recent **manual human review** of the claim's current relevance.
    This field is **only** set by a human reading the page and explicitly confirming it is still current.
    Automatic processes (`compile.py`, source-drift checks, etc) **must not** write to `reviewed`.
    Pages without `reviewed` are treated as never-reviewed by lint advisory.
  - `superseded_by: [[other-page]]` — wikilink to replacement if status is `superseded`

  Freshness is a **temporal axis** (when was this last checked) and is **orthogonal** to `confidence` which is
  the **epistemic axis** (how confident are we in the claim's accuracy). A page can be `confidence: extracted`
  (high factual confidence) and `status: stale` (world changed, claim no longer current) simultaneously.
  These fields are **advisory-only** at lint time; they affect retrieval ranking but do not block merges.
```

**Где в `wiki/concepts/llm-wiki-architecture.md`**: одним предложением в секции "Key Points" добавить:

> Freshness layer (2026-04-15): `status`/`reviewed`/`superseded_by` фронтматтер-поля влияют на retrieval ranking и lint advisory, но не блокируют merge.

Плюс обновить `updated:` в frontmatter самой `llm-wiki-architecture.md` на сегодняшнюю дату.

### Change 2a — `scripts/query.py` scoring с freshness multiplier

**Где**: `score_query_candidate()` в `scripts/query.py:61-86`.

**Что сделать**: применить **multiplicative** freshness factor к token-based score в конце функции. Использование multiplier'а (а не absolute penalty) даёт auto-scaling к любому score distribution и сохраняет относительный порядок `active > stale > superseded > archived` без необходимости знать реальные значения заранее.

```python
# freshness multiplier — applied at end of token scoring
# Initial factor estimates; to be tuned after observation on real queries (see revision v2 point 4)
status = (fm.get("status", "active") or "active").lower()
freshness_factor = {
    "active": 1.0,
    "stale": 0.7,
    "superseded": 0.3,
    "archived": 0.05,
}.get(status, 1.0)

# Preserve score as int for existing comparator; round after multiplication
score = int(score * freshness_factor)
```

**Контракт**:
- Multipliers установлены **как initial estimates**, подлежат tuning после недельного observation на реальных запросах. Не фиксировать как final values.
- Relative ordering гарантирован: `archived` статья получит `score * 0.05` → почти исчезнет из retrieval при любом типичном score (20-100), но не обнулится до нуля если score очень высокий (e.g. 200 × 0.05 = 10 всё ещё retrievable как last resort).
- `active` (default) не изменяет score.
- `unknown / missing status` трактуется как `active` через `.get(..., 1.0)`.
- `int()` round в конце сохраняет существующий comparator (tuple(score, slug)).

**Что НЕ добавляем в v2** (было в v1, убрано):
- Absolute penalty'и `-3/-8/-15` — заменено multiplier'ами выше.
- `recent review bonus` (+2 / +1 за reviewed < 30d / < 90d) — не нужен на Phase 1, можно добавить позже если multiplier недостаточен.
- `never-reviewed small penalty` — создаёт lint noise pressure на все unmigrated статьи. Достаточно того что lint advisory сам флагнёт их как `freshness_never_reviewed`.

### Change 2b — `hooks/shared_wiki_search.py` scoring с тем же multiplier

**Где**: `score_article()` в `hooks/shared_wiki_search.py:177-253`.

**Почему отдельно**: `shared_wiki_search.py` это **injection path** для UserPromptSubmit hook — то что реально влияет на Claude context в каждом turn'е. `query.py` это manual preview path. Если freshness ranking только в `query.py` — injection продолжит подсовывать stale/superseded статьи агенту, freshness система фактически не работает. Claude's review point 3 прямо на это указывает.

**Что сделать**: идентичная логика в `score_article()`, **в самом конце** (после существующего `updated` recency бонуса, прямо перед `return score`):

```python
# freshness multiplier — same policy as scripts/query.py:score_query_candidate
# Initial factor estimates, tune after observation
status = (fm.get("status", "active") or "active").lower()
freshness_factor = {
    "active": 1.0,
    "stale": 0.7,
    "superseded": 0.3,
    "archived": 0.05,
}.get(status, 1.0)

score = int(score * freshness_factor)
```

**Контракт**:
- Идентичная политика с `query.py` — если позже захочется tune, править надо в **обоих** местах (или вынести в shared helper, но это не Phase 1).
- Существующий +1 recency bonus за `updated <= 14 days` не трогать — это отдельный весьма слабый recency signal, параллельный freshness status'у.
- Существующий project-match bonus (+6) не трогать.

### Change 3 — `scripts/lint.py` freshness review debt check

**Где**: `scripts/lint.py` — добавить новую функцию **после** существующей `check_stale_articles()`, зарегистрировать в `run_all_checks()` (или где там registry).

```python
def check_freshness_review_debt() -> list[dict]:
    """Advisory: flag concept/source pages overdue for human review."""
    from datetime import date, timedelta

    today = date.today()
    CONCEPT_MAX_AGE = 180  # days — concepts are architectural, review rarely
    SOURCE_MAX_AGE = 60    # days — sources reference external docs that drift faster

    issues: list[dict] = []

    for article in list_wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        rel_str = str(rel).replace("\\", "/")
        if not (rel_str.startswith("concepts/") or rel_str.startswith("sources/")):
            continue

        fm = parse_frontmatter(article)
        status = (fm.get("status", "active") or "active").lower()

        # skip archived — they don't need review
        if status == "archived":
            continue

        # superseded without superseded_by link is a separate issue
        if status == "superseded" and not fm.get("superseded_by"):
            issues.append({
                "severity": "warning",
                "check": "freshness_superseded_without_link",
                "file": rel_str,
                "detail": f"{rel_str}: status=superseded but no superseded_by wikilink",
            })
            continue  # don't also flag as overdue

        reviewed_str = fm.get("reviewed", "")
        max_age = SOURCE_MAX_AGE if rel_str.startswith("sources/") else CONCEPT_MAX_AGE

        if not reviewed_str:
            issues.append({
                "severity": "suggestion",
                "check": "freshness_never_reviewed",
                "file": rel_str,
                "detail": f"{rel_str}: no 'reviewed' field — consider adding review date",
            })
            continue

        try:
            reviewed_date = date.fromisoformat(str(reviewed_str))
        except (ValueError, TypeError):
            issues.append({
                "severity": "warning",
                "check": "freshness_malformed_reviewed",
                "file": rel_str,
                "detail": f"{rel_str}: 'reviewed' field not valid ISO date (got {reviewed_str!r})",
            })
            continue

        age = (today - reviewed_date).days
        if age > max_age:
            issues.append({
                "severity": "suggestion",
                "check": "freshness_review_overdue",
                "file": rel_str,
                "detail": f"{rel_str}: last reviewed {age} days ago (max {max_age} for {rel.parts[0]}/)",
            })

    return issues
```

**Регистрация**: в `check_structural()` или `run_all_checks()` (точное имя подтвердить при чтении файла) добавить вызов `check_freshness_review_debt()` в список advisory checks. Severity `suggestion` по умолчанию, не blocking.

**[EMPIRICAL-scripts/lint.py:500]** Текущий список checks заканчивается на `("Stale articles", check_stale_articles),`. Добавить новую строку `("Freshness review debt", check_freshness_review_debt),` в ту же структуру, сохраняя alignment.

### Change 4 — `scripts/compile.py` explicit `status: active` on generation

**Где**: в функции которая генерирует frontmatter для новых концептов из daily logs (найти по grep на `type: concept` или `confidence:` в compile.py).

**Что добавить**: при генерации frontmatter новой статьи автоматически включать **только** `status: active`. `reviewed` поле **НЕ** проставляется автоматически.

```python
"status": "active",
# NOTE: do NOT auto-stamp `reviewed` here — see revision v2 point 5.
# `reviewed` remains strictly a manual human review event.
```

Existing fields (`title`, `type`, `created`, `updated`, `sources`, `confidence`, `project`, `tags`) не трогаются.

**Почему только `status: active` без `reviewed`**:
- `status: active` это **default** (код трактует missing status как active), но **explicit better than implicit**: читатель frontmatter видит что lifecycle considered, а не что забыли добавить поле. Cost — 1 строка YAML на статью.
- `reviewed` с auto-stamp на compile создаёт **false trust signal** — читатель увидит "reviewed: 2026-04-15" и подумает что человек проверил, хотя на самом деле это просто дата compile'а. Это размывает семантику поля и делает `freshness_never_reviewed` lint check бесполезным (все статьи формально "reviewed" со дня рождения).
- **Explicit contract**: `reviewed` = человек прочитал content и явно подтвердил актуальность. Compile — это акт **создания**, не акт review. Другое событие.
- Если позже нужно будет auto-pass freshness на compile (например, для source-drift Phase 2), можно добавить **отдельное** поле вроде `freshness_passed_at` с другим name → clear semantics, не конфликтующее с `reviewed`.

### Change 5 — `hooks/shared_context.py` freshness badges

**Где**: `hooks/shared_context.py:130-142` — где формируется `NEW | UPDATED` badge для `results` dict.

**Что добавить**: после определения `status` (NEW/UPDATED) прочитать freshness `status` поле и, если оно не `active`, добавить дополнительный маркер:

```python
# existing:
status = "NEW" if (created_date and created_date == updated_date) else "UPDATED"
results.append({"slug": slug, "status": status, "date": updated_str})

# after the append, enrich with freshness:
freshness_status = (fm.get("status", "active") or "active").lower()
if freshness_status != "active":
    results[-1]["freshness"] = freshness_status  # stale | superseded | archived
```

И в рендере (строка ~142):

```python
# existing:
lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']})")

# new:
suffix = ""
if "freshness" in ch:
    suffix = f" ⚠ {ch['freshness']}"
lines.append(f"- {ch['status']}: [[{ch['slug']}]] ({ch['date']}){suffix}")
```

**Формат badge**: unicode warning sign `⚠` + slaveword. Short and visible. Claude увидит это в SessionStart context и поймёт что статья помечена как не-current guidance.

### Change 6 — `hooks/shared_wiki_search.py` freshness indicator в retrieval injection

**Где**: `format_matched_articles()` в `hooks/shared_wiki_search.py:286-318`. Это функция которая форматирует каждый candidate как `### [[slug]] (score: N)\n\n{content}` перед инжектом в UserPromptSubmit additionalContext.

**Что добавить**: при рендере каждого candidate прочитать `fm.status`; если он не `active`, prepend status marker перед existing `### [[slug]]` заголовком:

```python
# inside the loop where each entry is built (after slug computation, before `entry = f"### [[{slug}]]...`)
fm = parse_frontmatter(path)
status = (fm.get("status", "active") or "active").lower()

status_marker = ""
if status == "superseded":
    status_marker = "[SUPERSEDED — historical context only] "
elif status == "stale":
    status_marker = "[STALE — verify before acting] "
elif status == "archived":
    status_marker = "[ARCHIVED — do not use as current guidance] "

entry = f"### {status_marker}[[{slug}]] (score: {score})\n\n{content}"
```

**Цель**: Claude в момент использования retrieval result сам видит что article помечена freshness status'ом. Это runtime-level signal, а не метадата которую надо парсить.

**Что НЕ добавляем** (было в v1, убрано):
- **`confidence == to-verify` → `[UNVERIFIED]` marker**. Per revision v2 point 1, `confidence` это **эпистемическая** ось (точность факта), freshness это **временная** ось (актуальность). Смешивать их в одном display layer неверно: статья может быть `extracted` (факты точные, высокое доверие) и при этом `stale` (мир изменился, факты больше не current). Или `to-verify` (неуверенность в точности) но `active` (guidance ещё current в том что мы знаем). Если позже понадобится показывать `to-verify` статус в injection — это отдельное изменение с собственной логикой, не часть freshness Phase 1.

**Важно**: `archived` статьи **могут** попадать в search results если их score достаточно высокий даже после `* 0.05` multiplier (теоретически возможно при очень релевантных keyword matches). Defensive rendering branch для `archived` оставлен — если такое случится, Claude хотя бы будет предупреждён что контент archived.

### What NOT to change

- **Не** мигрировать существующие 97 статей на новый schema в Phase 1. Они останутся без `status`/`reviewed` полей — код должен корректно трактовать их как `active` (default) и never-reviewed. Lint будет выдавать advisory suggestions, не errors. Миграция — отдельная follow-up задача.
- **Не** добавлять `freshness_horizon_days` в frontmatter. Политика 180/60 дней хардкодится в `lint.py` для простоты.
- **Не** трогать `scripts/doctor.py`. Freshness metric в doctor — Phase 2.
- **Не** писать новые утилитные функции в `scripts/utils.py`. Всё что нужно уже есть (`parse_frontmatter`, `list_wiki_articles`).
- **Не** добавлять access logging. YAGNI.
- **Не** добавлять verification metadata (`verified_at`, `verification_command`). Отдельная задача.

## Verification

### Phase 1 — Unit smoke (Codex выполняет сам)

**1.1** `uv run python scripts/wiki_cli.py lint --structural-only`

Ожидания:
- Exit code 0 (нет errors, только suggestions/warnings)
- Новый check `freshness_review_debt` появляется в output
- `freshness_never_reviewed` suggestions для большинства существующих concept/source статей (поскольку они не мигрированы, это ожидаемо)
- Total suggestions вырастет примерно на ~100 (количество concept+source статей без `reviewed` = 41 concepts + 60 sources − 1 для `llm-wiki-architecture` которая получит updated frontmatter в этом же diff, хотя `reviewed` в ней всё равно не добавляется поскольку это manual field)

Скопировать полный tail вывода в отчёт раздел 2.1.

**1.2** `uv run python scripts/wiki_cli.py doctor --quick`

Ожидания:
- Все pre-existing checks как были (PASS/FAIL не должны измениться)
- `structural_lint` check может показать увеличенное количество suggestions (≈100 new) — это **ожидаемо**, не regression (каждый concept/source без `reviewed` даёт один `freshness_never_reviewed` suggestion)
- Никаких новых FAIL checks

Полный stdout в отчёт.

**1.3** Python smoke для `query.py` freshness scoring

```bash
uv run python -c "
from pathlib import Path
from scripts.query import score_query_candidate
from scripts.config import WIKI_DIR

# найти concept статью для теста
article = WIKI_DIR / 'concepts' / 'llm-wiki-architecture.md'
tokens = {'wiki', 'architecture'}
score = score_query_candidate(article, tokens)
print(f'llm-wiki-architecture.md score: {score}')
"
```

Ожидание: score положительный (статья релевантна).

**1.4** Python smoke для фейкового superseded файла

Codex должен **временно** создать тестовый файл `/tmp/test_freshness.md`:

```markdown
---
title: Test Superseded
type: concept
status: superseded
superseded_by: [[some-other-page]]
sources: [test]
project: memory-claude
tags: [test]
confidence: inferred
---

# Test

Test content about wiki.
```

Затем убедиться что **оба** scorer'а (`score_query_candidate` в `scripts/query.py` И `score_article` в `hooks/shared_wiki_search.py`) на этом fake файле с релевантными токенами возвращают score который **≈ 30% от** score реальной `llm-wiki-architecture.md` статьи на тех же токенах (потому что оба scorer'а применяют `superseded → * 0.3` multiplier к одинаковому base). Точное значение: `round(real_score * 0.3)` через `int()` truncation. **Не коммитить** fake файл, удалить после теста.

**1.5** Compile smoke (dry-run)

```bash
uv run python scripts/compile.py --dry-run --file daily/2026-04-14.md
```

Ожидания:
- Команда отрабатывает без exceptions
- В dry-run выводе виден `status: active` в генерируемом frontmatter
- В dry-run выводе `reviewed` поле **отсутствует** (не auto-stamp'ится, это manual field — см. Change 4 и revision v2 point 5)

Если `compile.py` не поддерживает `--dry-run` с precise frontmatter preview — достаточно что команда отрабатывает без crash'ей, а фактическая проверка генерации сделана грепом после запуска без dry-run на non-critical daily log.

**1.6** Git diff scope check

```bash
git diff --stat scripts/lint.py scripts/query.py scripts/compile.py hooks/shared_context.py hooks/shared_wiki_search.py CLAUDE.md wiki/concepts/llm-wiki-architecture.md
git status --short
```

Ожидание:
- Ровно 7 файлов modified (3 scripts: `lint.py`, `query.py`, `compile.py` + 2 hooks: `shared_context.py`, `shared_wiki_search.py` + 1 doc: `CLAUDE.md` + 1 wiki article: `llm-wiki-architecture.md`)
- Никаких других файлов

### Phase 2 — Integration `[awaits user]`

**2.1** После merge Phase 1, user запускает одну реальную Codex сессию в проекте.

`[awaits user]`

**2.2** User проверяет что SessionStart hook корректно инжектит `⚠ stale/superseded` маркеры если вручную добавить `status: stale` в одну из статей.

`[awaits user]`

**2.3** User запускает `doctor --full` и подтверждает что advisory lint показывает новые `freshness_*` checks без поломки других.

`[awaits user]`

### Phase 3 — Statistical `[awaits 7-day window]`

**3.1** Через неделю observation после merge — проверить:

- Сколько статей Claude'ом инжектировалось с `[STALE]`/`[SUPERSEDED]` маркерами
- Изменилось ли поведение агента (качественная оценка — ссылается ли на superseded articles реже)
- Не появились ли false positives `freshness_review_overdue` на статьях которые на самом деле current

На основе этих данных решить, стоит ли идти в Phase 2 (source-drift detection для `sources/`).

`[awaits 7-day window]`

## Acceptance criteria (Codex phase)

- ✅ Phase 1.1: `lint --structural-only` returns exit 0, новый `freshness_review_debt` check зарегистрирован
- ✅ Phase 1.2: `doctor --quick` не сломан, все pre-existing checks остаются в предыдущем состоянии
- ✅ Phase 1.3: `score_query_candidate` продолжает работать на существующих статьях без exceptions
- ✅ Phase 1.4: test с fake superseded frontmatter показывает что superseded candidate ranks **strictly lower** чем equivalent active candidate на тех же токенах. Конкретное соотношение: `superseded_score ≈ round(active_score × 0.3)` через `int()` truncation (multiplier `0.3` применяется в обоих scorer'ах — `score_query_candidate` и `score_article`)
- ✅ Phase 1.5: compile.py dry-run показывает `status: active` в генерируемом frontmatter, **и** `reviewed` поле **отсутствует** в output (auto-stamp убран в v2, см. Change 4 и revision v2 changelog point 5)
- ✅ Phase 1.6: git diff содержит ровно 7 whitelisted production файлов + `docs/codex-tasks/wiki-freshness-phase1-report.md` (handoff artifact, не в whitelist по определению). Никаких других файлов
- ✅ `CLAUDE.md` обновлён с новой секцией про freshness frontmatter, существующие правила не нарушены
- ✅ `wiki/concepts/llm-wiki-architecture.md` обновлён одним предложением + `updated:` bumped
- ✅ Нет ни одного wiki article (кроме `llm-wiki-architecture.md`) в diff — миграция не делается в Phase 1

## Out of scope

1. **Phase 2 (source-drift)** — detection of external source change для `sources/`. Правильный порядок валидаторов per RFC 9110: **`ETag` если сервер предоставляет (primary validator), `Last-Modified` как secondary, content HEAD comparison как fallback**. Не `Last-Modified only` как было в v1 плана. Отдельная задача после Phase 1 merge + 1 неделя observation.
2. **Миграция существующих статей** на новый schema (добавление `status`/`reviewed` в 109 статей). Отдельная задача, возможно через массовый script. Phase 1 code должен корректно трактовать missing status как `active` (default), а missing `reviewed` как never-reviewed → advisory suggestion в lint.
3. **Access-log analytics, usage-weighted review queue**. YAGNI до проблемы.
4. **`verified_at` / verification metadata** (Codex's Option E). Отдельный класс проблемы — это **другая ось** ("проверяли ли мы что это реально работает"), не freshness ("актуально ли сейчас"). Смешивать нельзя.
5. **Full source-hash sync**. Заменяется `ETag → Last-Modified → HEAD` chain в Phase 2 если понадобится.
6. **`doctor.py` `freshness_debt` metric**. Phase 2.
7. **`confidence=to-verify → [UNVERIFIED]` маркер в injection render**. Это отдельная ось (epistemic, не temporal), требует отдельного обсуждения и отдельного кода. Не в Phase 1.
8. **Small penalty for never-reviewed pages в scoring**. Было в v1, убрано в v2 — advisory lint уже флагнёт эти страницы как `freshness_never_reviewed`, дополнительный score penalty создаёт noise pressure на все unmigrated pages.
9. **Recent review bonus (+2/+1)** в scoring. Было в v1, убрано в v2 — multiplier alone handles relative ordering без необходимости дополнительного bonus слоя.

## Rollback

```bash
git checkout scripts/lint.py scripts/query.py scripts/compile.py hooks/shared_context.py hooks/shared_wiki_search.py CLAUDE.md wiki/concepts/llm-wiki-architecture.md
```

Чистый rollback, никаких side effects — существующие wiki статьи не затрагивались.

## Notes для исполнителя

- **Doc-first**: ПЕРЕД правкой кода открой документацию Python `datetime.date.fromisoformat` и YAML spec, процитируй дословные контракты в раздел `0.6 Doc verification` отчёта. Не пиши по памяти, даже если "знаешь".
- **Читай существующий код ДО правок**. `scripts/lint.py`, `scripts/query.py`, `scripts/compile.py`, `hooks/shared_context.py`, `hooks/shared_wiki_search.py` — каждый файл целиком. Без этого не начинать правки. Это **именно** тот принцип `"Research the codebase before editing"` который мы только что внесли в `CLAUDE.md` — план должен пройти первый тест на этом правиле.
- **Минимальный patch**: каждая правка делает **одну** вещь. Не bundle'ить unrelated изменения. Не добавлять helper функции "по дороге" которые могли бы быть полезны в будущем.
- **Не трогать `wiki/*.md`** кроме `llm-wiki-architecture.md`. Если соблазн пофиксить попутный typo где-то ещё — в раздел Out-of-scope-temptations, не в код.
- **Whitelist строгий** — 7 production файлов. Отчёт `wiki-freshness-phase1-report.md` — handoff artifact, не в whitelist по определению, заполняется параллельно. Любое отклонение от этих 7+1 → Discrepancies, не коммитить.
- **Никаких commit/push** — финал = заполненный отчёт. User ревьюит и коммитит сам.
- **Никаких personal data** путей (`/mnt/<letter>/<Caps>`, `<Letter>:/<Caps>`, `C:\Users`, username substring) в captured output.
- **Self-audit перед сдачей** — любой ❌ → вернись и доделывай. Не сдавай отчёт с неполными секциями.
- **Discrepancy first**: если при чтении существующего кода оказывается что какая-то из описанных в плане строк не соответствует реальности (например, `check_stale_articles` на другой строке, или `score_query_candidate` имеет другую сигнатуру) — **стоп**, записать в раздел Discrepancies, не кодировать вслепую.
- **Отчёт** обязателен: `docs/codex-tasks/wiki-freshness-phase1-report.md` — шаблон создан Claude'ом параллельно, заполняй последовательно.
