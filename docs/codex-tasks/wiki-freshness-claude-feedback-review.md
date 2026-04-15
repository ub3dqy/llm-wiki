# Review of Claude's Freshness Critique

## Bottom line

В целом я **согласен с Claude**: его резюме лучше моего исходного preliminary draft. Но не целиком. Есть несколько пунктов, где он прав по сути, и несколько, где я бы оставил свою позицию или уточнил её.

Важная поправка по масштабу: цифры в его резюме уже слегка устарели. По текущему файловому срезу у вас:

- **109 wiki-страниц** всего
- **60** страниц в `wiki/sources`
- **41** страниц в `wiki/concepts`
- **45** страниц с `confidence:`

Это не меняет главный вывод про размер базы, но для честности цифры стоит обновить.

---

## С чем я согласен

### 1. Пять фаз в моём первом draft были лишними

Да, это был перегиб. Для базы такого размера access-log analytics и usage-weighted review queue сейчас рано. Это уже не "решить freshness", а начать строить новую подсистему. Для текущего проекта разумнее **2 фазы, максимум 3**.

### 2. Надо опираться на уже существующие механизмы

Согласен. В репо уже есть полезные куски, и их надо расширять, а не изобретать параллельную систему:

- [scripts/lint.py](/mnt/e/project/memory%20claude/memory%20claude/scripts/lint.py#L120) уже умеет ловить `stale_article`, пусть пока только по `daily/` hash drift
- [scripts/query.py](/mnt/e/project/memory%20claude/memory%20claude/scripts/query.py#L61) уже читает `confidence`, но пока не использует его в скоринге
- [hooks/shared_context.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_context.py#L92) уже показывает `NEW/UPDATED` в SessionStart
- [hooks/shared_wiki_search.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_wiki_search.py#L244) уже даёт небольшой recency bonus по `updated`

То есть это действительно не greenfield.

### 3. Freshness должен доходить до hook-layer, а не жить только в lint

Согласен полностью. Реальная инъекционная точка для Claude здесь не `query.py`, а:

- [hooks/user-prompt-wiki.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/user-prompt-wiki.py#L1)
- [hooks/shared_wiki_search.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_wiki_search.py#L324)

Если freshness не влияет на этот путь, агент всё равно продолжит получать устаревшие статьи в prompt. Это сильное замечание, и оно по делу.

### 4. `verified_at` не надо смешивать с freshness

Тоже согласен. Verification metadata полезна, но это **другая ось**: "мы это проверили?" не равно "это ещё актуально?". Если смешать их в одну задачу, получится липкая схема, где и freshness, и verification станут хуже.

### 5. Source-drift для `wiki/sources/` надо поднимать раньше

Тут тоже в целом согласен: для `sources/` это high-value слой, и его не стоило отбрасывать в дальнюю Phase 5. Именно source pages сильнее всего страдают от того, что upstream docs, issues, SDK pages и release notes меняются вне repo.

---

## С чем я не согласен или что бы я уточнил

### 1. Я не согласен использовать `confidence` как замену freshness

Это главный пункт.

`confidence` у вас уже означает **эпистемический статус утверждения**:

- `extracted`
- `inferred`
- `to-verify`

А freshness — это **временная актуальность**.

Это разные оси. Статья может быть:

- `confidence: extracted`
- и при этом быть stale через месяц

Если мы начнём трактовать `to-verify` как "needs review / maybe stale", мы сломаем смысл provenance. Поэтому здесь я бы оставил **отдельные поля** `status` и `reviewed`.

### 2. Я не согласен, что `updated` можно считать заменой `reviewed`

`updated` уже используется как lightweight recency signal, это правда. Но это не review.

Причина простая: `updated` меняется после любого содержательного редактирования файла. Это может быть:

- правка текста
- добавление backlink
- переименование секции
- косметическая чистка

То есть `updated` отвечает на вопрос **"файл трогали?"**, а не **"содержимое заново оценили на актуальность?"**. Поэтому отдельное `reviewed` всё ещё нужно.

### 3. Я только частично согласен с формулой `HEAD + Last-Modified = 95% решения`

Здесь у Claude верное направление, но слишком оптимистичная оценка.

По RFC 9110:

- `HEAD` семантически близок к `GET`, но сервер **может опускать часть заголовков**
- `Last-Modified` сервер **should** отправлять, если может его определить, но это **не must**
- для детекции изменений более сильный валидатор — `ETag`

Следствие:

- **да**, source-drift стоит поднимать раньше
- **нет**, я бы не строил его как `Last-Modified-only`
- правильнее делать так: **`ETag` если есть, потом `Last-Modified`, потом fallback**

То есть Claude прав по приоритету, но упрощает реализацию сильнее, чем стоило бы.

### 4. Я бы не принимал penalty-константы `-10 / -20` без проверки на реальном scorer

Направление правильное, но константы пока преждевременны.

Почему: в [hooks/shared_wiki_search.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_wiki_search.py#L177) веса по token hits довольно компактные. Жёсткий штраф `-20` может не просто демотировать `superseded`, а почти полностью выкидывать его из кандидатов. Это может быть нормально, а может быть слишком грубо.

Я бы делал так:

- сначала bucketed demotion (`active > stale > superseded > archived`)
- потом уже подкручивал веса на реальных query examples

### 5. По `compile.py` я бы был осторожен с автоматическим `reviewed: <today>`

`status: active` для свежесгенерированной статьи — нормально.

А вот `reviewed: today` нормально **только если заранее договориться**, что `reviewed` означает не "человек вручную перепроверил", а "страница прошла freshness-pass на момент генерации".

Если такого договорённого смысла нет, авто-штамп `reviewed` создаст ложное ощущение доверия.

---

## Что бы я поменял в своём плане после его критики

Если привести мой draft к более трезвому виду, я бы теперь предложил такой каркас.

### Phase 1

- добавить `status`, `reviewed`, `superseded_by`
- добавить advisory freshness lint
- внедрить freshness-aware ranking **в обоих местах**:
  - [hooks/shared_wiki_search.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_wiki_search.py#L177) — обязательно, потому что это UserPromptSubmit path
  - [scripts/query.py](/mnt/e/project/memory%20claude/memory%20claude/scripts/query.py#L61) — тоже желательно, чтобы preview/manual query не жили по другой логике
- показать freshness marker прямо в injected preview/context

### Phase 2

- source-drift / source-rot для `wiki/sources/`
- проверка по `ETag` / `Last-Modified` / failure states
- advisory output в lint, потом при желании summary в doctor

### Не делать сейчас

- access-log analytics
- usage-weighted review queue
- per-page `freshness_horizon_days` во frontmatter
- verification metadata
- автоматические refresh workflows

---

## Итог

Если совсем прямо:

**Claude прав в главном**:

- мой план был слишком растянут
- я недооценил важность hook injection path
- access-log phase сейчас не нужна
- source-drift надо поднимать раньше

**Но я не согласен**:

- смешивать freshness с `confidence`
- подменять `reviewed` полем `updated`
- считать `HEAD + Last-Modified` почти готовым решением без `ETag` и без caveats

Мой обновлённый вывод:

**лучший следующий план — это Claude’s shape, но с сохранением отдельной freshness-оси (`status` / `reviewed`) и с более аккуратной реализацией source-drift.**

---

## Supporting references

Repo references:

- [scripts/query.py](/mnt/e/project/memory%20claude/memory%20claude/scripts/query.py#L61)
- [scripts/lint.py](/mnt/e/project/memory%20claude/memory%20claude/scripts/lint.py#L120)
- [hooks/shared_context.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_context.py#L92)
- [hooks/shared_wiki_search.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_wiki_search.py#L177)
- [hooks/shared_wiki_search.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/shared_wiki_search.py#L324)
- [hooks/user-prompt-wiki.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/user-prompt-wiki.py#L1)
- [scripts/compile.py](/mnt/e/project/memory%20claude/memory%20claude/scripts/compile.py#L107)

Wiki references:

- [llm-wiki-architecture.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/llm-wiki-architecture.md)
- [doctor-health-metric-design.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/doctor-health-metric-design.md)
- [claude-code-memory-tooling-landscape.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/claude-code-memory-tooling-landscape.md)
- [agent-memory-production-schema.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/agent-memory-production-schema.md)

HTTP semantics:

- RFC 9110 `HEAD`: https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.2
- RFC 9110 `Last-Modified`: https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.2
- RFC 9110 `ETag`: https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3
