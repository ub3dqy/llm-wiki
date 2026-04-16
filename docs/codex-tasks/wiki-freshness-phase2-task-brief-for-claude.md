# Wiki Freshness Phase 2 — ТЗ для Claude

## Контекст

Phase 1 freshness layer уже реализована и зафиксирована:

- `status: active | stale | superseded | archived`
- `reviewed: YYYY-MM-DD`
- `superseded_by: [[...]]`
- freshness-aware ranking в retrieval / hook injection
- advisory lint по review debt

См.:

- [wiki/concepts/wiki-knowledge-freshness-lifecycle.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/wiki-knowledge-freshness-lifecycle.md)
- [docs/codex-tasks/wiki-freshness-phase1.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase1.md)
- [docs/codex-tasks/wiki-freshness-phase1-report.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase1-report.md)

Нерешённый кусок общей проблемы устаревания — **Basis axis**: изменился ли внешний источник, на котором основана страница в `wiki/sources/`.

Phase 2 нужна не для всей wiki сразу, а именно для **source-drift / source-rot detection**.

## Что нужно от Claude

Подготовить **execution-ready plan**, а не код.

Ожидаемый результат от Claude:

1. новый план-файл для Codex в стиле текущего handoff workflow;
2. при необходимости — отдельный report template;
3. чёткое решение по scope, whitelist, acceptance и discrepancy checkpoints;
4. если в процессе планирования выяснится, что исходная идея слабая или слишком дорогая, это нужно явно написать и предложить более узкий вариант.

## Цель Phase 2

Добавить минимально полезный и технически защищённый механизм, который:

1. проверяет статьи в `wiki/sources/` на признаки того, что upstream-источник изменился;
2. различает как минимум:
   - **source_drift** — источник изменился;
   - **source_rot** — источник недоступен / 404 / 410 / hard failure;
   - **no_validator / unverifiable** — нельзя надёжно проверить;
3. сообщает это как **advisory**, не как blocking merge gate;
4. не ломает Phase 1 семантику freshness;
5. не записывает автоматически `reviewed`.

## Уже принятые решения, которые нельзя тихо переиграть

Эти вещи уже стабилизированы предыдущим циклом review и Phase 1:

1. **Freshness не смешивается с confidence.**
   `confidence` — эпистемическая ось, source drift — темпоральная / operational.

2. **`reviewed` остаётся strictly manual human review field.**
   Ни `compile.py`, ни drift-check, ни doctor не имеют права auto-stamp'ить `reviewed`.

3. **Phase 2 касается в первую очередь `wiki/sources/`, не всей wiki.**
   Не надо тащить source-drift на `concepts/` в первом заходе.

4. **Это advisory layer, не deterministic CI blocker.**
   Если drift-check нестабилен, сеть флакит, сервер не даёт валидаторы — merge gate из этого делать нельзя.

5. **Нужно исходить из официальной HTTP-семантики, а не из удобных эвристик.**
   Формула `HEAD + Last-Modified и готово` уже была признана слишком наивной.

## Что особенно важно продумать

### 1. Какой именно HTTP контракт использовать

Claude должен отдельно решить и обосновать:

- достаточно ли `HEAD`;
- когда нужен fallback на `GET`;
- как использовать:
  - `ETag`
  - `Last-Modified`
  - `If-None-Match`
  - `If-Modified-Since`
- как классифицировать:
  - `304 Not Modified`
  - `200 OK` с новым validator
  - `404 / 410`
  - `403 / 429 / 5xx`
  - отсутствие validator headers вообще

### 2. Что считать drift, а что нет

Нужен явный operational contract.

Примеры вопросов, которые план должен закрыть:

- Если `ETag` изменился, а `Last-Modified` нет — это drift?
- Если `Last-Modified` новее `updated` статьи, но `ETag` нет — достаточно ли этого?
- Если сервер всегда отдаёт `200` и не даёт ни `ETag`, ни `Last-Modified`, это:
  - drift unknown,
  - unverifiable,
  - или reason to skip?

### 3. Как не превратить это в noisy lint

Phase 2 не должна завалить repo постоянным шумом.

План должен решить:

- какие findings реально стоит показывать в `lint.py`;
- как назвать check;
- будет ли он идти в `--structural-only` или только в более дорогой режим;
- нужен ли summary в `doctor.py`, или это premature.

### 4. Rate limits и network cost

Нужно заранее продумать:

- сколько URL реально придётся проверять;
- нужен ли timeout / retry policy;
- нужна ли локальная cache / memoization в рамках одного run;
- как не бить GitHub / docs-сайты бессмысленными запросами.

### 5. Что делать с multi-source статьями

У некоторых source pages список `sources:` содержит несколько URL.

План должен определить:

- как агрегировать результат по нескольким upstream источникам;
- когда страница считается drifted:
  - если изменился хотя бы один source,
  - или если изменился primary source,
  - или если изменились все.

## Обязательный source dive для Claude

Перед планированием Claude должен перечитать:

### Локальные файлы

- [wiki/concepts/wiki-knowledge-freshness-lifecycle.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/wiki-knowledge-freshness-lifecycle.md)
- [docs/codex-tasks/wiki-freshness-phase1.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase1.md)
- [docs/codex-tasks/wiki-freshness-phase1-report.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase1-report.md)
- [wiki/sources/http-semantics-rfc9110-docs.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/sources/http-semantics-rfc9110-docs.md)
- [wiki/sources/github-rest-api-docs.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/sources/github-rest-api-docs.md)
- текущие `scripts/lint.py`, `scripts/doctor.py`, `scripts/utils.py`

### Официальные документы

Минимум:

- RFC 9110 sections on:
  - `HEAD`
  - validators
  - `ETag`
  - `Last-Modified`
  - conditional requests
- при необходимости official docs конкретных frequently-hit providers, если они реально влияют на дизайн

## Предпочтительный scope для плана

Это не жёсткий диктат, а рекомендуемая стартовая рамка.

### In-scope кандидаты

С высокой вероятностью достаточно Phase 2 в таком виде:

1. новый advisory check в `scripts/lint.py` для `wiki/sources/`;
2. классификация результатов по validator-aware policy;
3. понятный output:
   - drift
   - rot
   - unverifiable
4. optional summary metric в `doctor.py` только если это не раздувает scope.

### Out of scope

Пока не тащить:

- access-log analytics;
- auto-refresh задач;
- background polling;
- auto-update `reviewed`;
- body hashing всех страниц через `GET` download content by default;
- drift logic для `concepts/`;
- blocking CI gate.

## Что хотелось бы увидеть в плане

Хороший план для Codex должен содержать:

1. **Truth hierarchy**
   - офдока -> код -> план

2. **Pre-flight**
   - где смотреть реальный код
   - какие official docs перечитать

3. **Чёткий whitelist**
   - без размытого “может понадобиться ещё что-то”

4. **Discrepancy-first checkpoints**
   - на каких местах Codex обязан остановиться, если реальность расходится с ожиданием

5. **Verification**
   - конкретные команды
   - реальные expected outputs
   - отдельно negative cases

6. **Self-audit**
   - чтобы после исполнения было видно, что Phase 2 действительно закрыла Basis axis, а не просто добавила ещё один warning.

## Критерии хорошего Phase 2 плана

План считаю удачным, если после его чтения будет ясно:

1. какой exact behavior считается drift detection;
2. почему выбранный HTTP contract корректен;
3. как система ведёт себя на flaky / validator-less sources;
4. почему это advisory, а не merge gate;
5. что именно будет делать Codex пошагово, без догадок.

## Нежелательные паттерны

Не хочется снова видеть:

- “HEAD + Last-Modified и достаточно” без caveats;
- смешивание freshness с `confidence`;
- auto-stamping `reviewed`;
- broad scope без whitelist;
- идеи уровня “сначала сделаем, потом подумаем про rate limits”;
- plan, который выглядит как исследовательское эссе, а не handoff artifact.

## Короткая формулировка задачи для Claude

Подготовь execution-ready handoff plan для **Wiki Freshness Phase 2**: advisory source-drift / source-rot detection для `wiki/sources/`, основанный на официальной HTTP-семантике (`ETag -> Last-Modified -> conditional/fallback policy`), без смешивания с `confidence`, без auto-update `reviewed`, без превращения в blocking CI gate.
