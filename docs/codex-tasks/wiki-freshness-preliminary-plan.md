# Preliminary Plan — Wiki Freshness / Staleness Tracking

> **Статус**: discussion draft, not execution-ready
>
> **Назначение**: показать Claude как предварительную архитектурную рамку для проблемы
> "вики копит знания, но часть знаний устаревает, а агент продолжает использовать их как current guidance".

---

## 1. Problem statement

Сейчас в проекте уже есть два полезных, но узких сигнала:

- `lint.py` умеет ловить **stale articles** как несоответствие article ↔ source / daily state
- `doctor --quick` умеет ловить **index freshness**

Этого недостаточно для более важного вопроса:

> "Можно ли по этой странице всё ещё принимать решения сегодня?"

То есть проблема не только в том, что статья "старше исходника", а в том, что retrieval может
подсунуть агенту **старое operational guidance** как будто оно всё ещё актуально.

---

## 2. Existing project baseline

Опора на текущее состояние проекта:

- `CLAUDE.md` уже требует provenance discipline и cheap quality gates
- `[[concepts/llm-wiki-architecture]]` фиксирует compile/query/lint/doctor как основные operational слои
- `[[concepts/doctor-health-metric-design]]` уже задаёт правильный принцип:
  **one dimension per metric**, а не один агрегатный "health"
- `[[concepts/claude-code-memory-tooling-landscape]]` прямо отмечает риск
  **noise / stale articles** при heavy automation
- `[[concepts/agent-memory-production-schema]]` даёт полезные production ideas:
  `validity_to`, `archived_at`, access log, content hash

Вывод: новый слой актуальности должен быть **надстройкой над существующей provenance/lint дисциплиной**,
а не её заменой.

---

## 3. Design goal

Разделить в wiki минимум три разные вещи:

1. **historical memory** — "это когда-то было правдой / это случилось"
2. **current guidance** — "на это можно опираться сейчас"
3. **superseded knowledge** — "это полезно как история, но не как default recommendation"

Идея: страница должна иметь не только смысл, но и **режим доверия по актуальности**.

---

## 4. Candidate approaches

### Option A — Metadata-first lifecycle

Добавить минимальный lifecycle metadata layer:

```yaml
status: active | stale | superseded | archived
reviewed: YYYY-MM-DD
freshness_horizon_days: 30
superseded_by: [[other-page]]
```

Плюсы:
- дешёво
- прозрачно для человека и агента
- можно быстро встроить в ranking и lint

Минусы:
- требует ручного review процесса

**Это базовый вариант, который почти наверняка стоит делать первым.**

---

### Option B — TTL by content type

Не все страницы стареют одинаково.

Примерные категории:

- `sources/` про SDK, CLI, баги, релизы: **7–30 дней**
- `concepts/` про архитектуру и устойчивые паттерны: **60–180 дней**
- historical incident pages: review не обязателен, но должен быть `status: archived` или `stale`

Плюсы:
- простой automation
- делает lint предупреждения более осмысленными

Минусы:
- TTL почти всегда rough heuristic, не истина

---

### Option C — Source-drift tracking

Для source-backed pages отслеживать не только возраст, но и drift основания:

```yaml
source_checked_at: YYYY-MM-DD
source_version: 2.1.105
source_hash: ...
```

Или хотя бы внутренний derived status:

- source changed since summary
- upstream issue closed / reopened
- docs page updated after article review

Плюсы:
- stale определяется по факту изменения основания
- особенно полезно для version-sensitive pages

Минусы:
- дороже в реализации
- для части источников понадобится отдельная fetch/compare логика

---

### Option D — Usage-aware review priority

Самые опасные страницы — не "старые вообще", а "старые, но всё ещё часто retrieval-ятся".

Идея:

- хранить `last_retrieved_at`
- хранить `retrieval_count_30d`
- поднимать в review очередь страницы вида:
  - `status=active`
  - давно не reviewed
  - но всё ещё часто попадают в query results

Плюсы:
- фокус на реальном риске для агента
- помогает не утонуть в review debt

Минусы:
- нужен query access log
- это уже вторая волна, не стартовый слой

---

### Option E — Verification-backed operational guidance

Для страниц, которые содержат operational claims ("это работает", "этот workaround valid"),
нужен отдельный слой verification metadata:

```yaml
verified_at: YYYY-MM-DD
verification_command: doctor --full
verification_evidence: reports/...
```

Плюсы:
- отличает "мы так думаем" от "мы это реально проверяли"
- особенно полезно для hooks / doctor / workflow / bug workaround pages

Минусы:
- не всем страницам нужен
- нужен discipline loop

---

## 5. Recommended phased rollout

### Phase 1 — Minimal viable freshness layer

Добавить только:

```yaml
status
reviewed
superseded_by
```

И сразу использовать это в retrieval:

- `active` pages rank выше
- `superseded` / `archived` по умолчанию вниз
- если статья stale/superseded, query output должен это явно показывать

Цель фазы:
- не решить всё,
- а перестать показывать старое guidance как нейтрально-равноправное.

---

### Phase 2 — Lint / doctor freshness debt

Добавить warnings уровня:

- page not reviewed for N days
- version-sensitive page without recent review
- superseded page still heavily linked
- active page with no review date

Опционально:
- отдельный advisory block в `doctor --full`
- не делать это blocking gate на старте

Цель фазы:
- сделать debt видимым,
- не ломая ежедневный workflow.

---

### Phase 3 — Query output becomes freshness-aware

`query.py` / preview / injected context должны различать:

- **Current guidance**
- **Historical context**
- **Possibly stale / superseded**

Даже если retrieval включает старую страницу, агент должен видеть её **как старую**, а не как обычный совет.

Цель фазы:
- превратить freshness из пассивной metadata в активный runtime signal.

---

### Phase 4 — Access-log driven prioritization

Если окажется, что stale debt быстро растёт, добавить usage-aware prioritization:

- `last_retrieved_at`
- `retrieval_count_30d`
- review queue по риску, а не по возрасту

Цель фазы:
- не пытаться review’ить всё одинаково,
- а review’ить то, что реально влияет на поведение агента.

---

### Phase 5 — Source-drift automation for selected page classes

Только для самых чувствительных классов:

- upstream docs
- SDK / CLI references
- bug workaround pages
- operational setup pages

Здесь уже можно добавить:
- version pin / observed version
- changed-since-last-review checks
- targeted refresh tasks

Цель фазы:
- автоматизировать только самые ценные freshness checks,
- не строить giant synchronization machine сразу.

---

## 6. Suggested retrieval policy

Если делать самый полезный минимум, ranking policy может быть такой:

1. `status=active` выше всех
2. recent `reviewed` выше старого review
3. pages with strong provenance / direct source backing выше weak synthesis
4. `superseded` не исчезают, но по умолчанию не инжектятся как first-line guidance
5. `archived` попадают только как historical context

Отдельное правило:

> Если page stale/superseded, query result должен маркировать это явно в выводе, а не надеяться,
> что модель сама поймёт по фронтматтеру.

---

## 7. Suggested lint policy

Не делать freshness blocker сразу.

Разделить на два уровня:

### Required gate

- existing structural integrity
- provenance completeness

### Advisory freshness gate

- missing `reviewed`
- overdue review
- `superseded` without `superseded_by`
- high-use old page
- version-sensitive page with stale review

Это соответствует уже существующему принципу:
- deterministic gates — blocking
- knowledge-quality / advisory checks — non-blocking

---

## 8. Open questions for Claude review

1. Должен ли `status` жить во всех page types или только в `concepts/` + `sources/`?
2. Нужен ли `freshness_horizon_days` в frontmatter, или достаточно policy-by-type внутри `lint.py`?
3. Стоит ли `reviewed` обновлять только вручную, или разрешать automation после успешной verification command?
4. Должен ли query layer полностью исключать `superseded` pages из default injection, или только резко понижать?
5. Где проводить границу между:
   - historical source summary
   - current project guidance
   - operational runbook

---

## 9. Recommended first implementation slice

Если потом превращать этот discussion draft в execution plan, я бы начинал только с такого малого среза:

1. schema extension:
   - `status`
   - `reviewed`
   - `superseded_by`

2. retrieval ranking update:
   - `active` > `stale` > `superseded` > `archived`

3. one advisory lint rule:
   - missing / overdue `reviewed` for selected page classes

Без:
- access-log analytics
- source hash sync
- full automation

То есть сначала **простая visible discipline**, потом уже smarter automation.

---

## 10. Bottom line

Проблема актуальности wiki — это не одна проблема, а минимум четыре:

1. **age** — когда последний review
2. **state** — active / stale / superseded / archived
3. **source drift** — изменилось ли основание
4. **runtime impact** — продолжает ли агент этим пользоваться

Поэтому правильный путь — не один magic freshness score, а layered model:

- metadata lifecycle
- advisory lint
- freshness-aware retrieval
- позже usage/source automation

Это лучше совпадает с уже существующей архитектурой LLM Wiki, чем попытка сразу строить “умный универсальный stale detector”.
