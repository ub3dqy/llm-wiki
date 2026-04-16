# Wiki Freshness Phase 2.1 — ТЗ для Claude

## Контекст

Phase 2 source-drift detection уже **замержена**.

Реализовано:

- explicit `--source-drift` в `scripts/lint.py`
- `urllib.request` only
- `HEAD` + conditional validators
- state persistence в `scripts/state.json` (`source_drift_validators`)
- `drift -> suggestion`, `rot -> warning`

Но execution показал важную operational problem:

- первый run = baseline capture, `0` issues
- второй run почти сразу дал **12 drift findings**
- почти все на:
  - GitHub `blob` pages
  - GitHub `wiki` pages
  - похожих HTML endpoints

См.:

- [wiki-freshness-phase2-source-drift-report.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md)
- [wiki-knowledge-freshness-lifecycle.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/wiki-knowledge-freshness-lifecycle.md)

Вывод: код уже landed, но **signal quality для drift недостаточно надёжна**.

## Что нужно от Claude

Подготовить **execution-ready follow-up plan** на **Phase 2.1 refinement**.

Нужен не большой redesign freshness, а узкий stabilizing pass после уже замерженной Phase 2.

## Цель Phase 2.1

Сделать `source-drift` **менее шумным и более интерпретируемым**, не ломая уже полезную часть feature.

Практически:

1. сохранить надёжный `rot` signal;
2. понизить false positives для `drift`;
3. не превращать это в broad new subsystem;
4. не ломать уже существующий merged contract без причины.

## Уже известные факты, которые нужно принять как исходные

1. **Problem не в wiring.**  
   Phase 2 корректно:
   - сохраняет baseline validators,
   - обрабатывает `304` через `HTTPError`,
   - пишет state,
   - не трогает `reviewed`,
   - не лезет в `--structural-only`.

2. **Problem в signal quality.**  
   Часть upstream endpoints отдаёт validators, которые выглядят недостаточно стабильными для прямой интерпретации “ETag changed -> source drift”.

3. **`rot` сейчас выглядит более надёжным, чем `drift`.**  
   `404/410` — сильный сигнал.  
   `ETag changed on GitHub blob page` — слабее и требует refinement.

4. **Phase 2 уже замержена.**  
   Значит Phase 2.1 не должна исходить из “можно всё переиграть с нуля”.  
   Нужен post-merge stabilization mindset.

## Основной вопрос, который должен решить Claude

Что именно надо считать достаточно сильным drift-сигналом, чтобы показывать его пользователю как advisory finding?

Сейчас это слишком прямолинейно:

- validator changed -> drift

Phase 2.1 должна предложить более надёжную политику.

## Что именно хотелось бы, чтобы Claude оценил

### 1. Надо ли разделить `rot` и `drift` policy жёстче

На текущих данных выглядит так:

- `rot` — оставляем почти как есть
- `drift` — ужесточаем

План должен явно сказать, согласен ли он с этим и почему.

### 2. Какой refinement strategy лучше

Пусть Claude выберет и обоснует, но как минимум нужно оценить такие варианты:

#### Вариант A — Two-hit confirmation

`drift` показывается только если одно и то же изменение подтверждается **два запуска подряд**.

Плюсы:
- дешёвый upgrade
- не требует provider-specific logic

Минусы:
- slower signal
- state model усложняется

#### Вариант B — Domain / URL-class policy

Сразу признать некоторые URL-классы плохими кандидатами для validator-based drift:

- GitHub `blob`
- GitHub `wiki`
- возможно другие HTML endpoints

И переводить их в:

- `unverifiable`
- или отдельный `unstable_validator`

Плюсы:
- быстрый шумодав
- честнее operationally

Минусы:
- provider-specific knowledge
- надо поддерживать policy list

#### Вариант C — Canonicalization

Проблемные источники не исключать, а переводить в более стабильную форму:

- например GitHub docs/article URLs -> raw content URL / API URL / canonical raw endpoint

Плюсы:
- сохраняется drift coverage

Минусы:
- scope легко распухает
- много provider-specific mapping logic

#### Вариант D — Severity downgrade / wording-only

Не менять логику детекции, а просто сделать wording мягче:

- не “source changed”
- а “validator changed; review if important”

Плюсы:
- почти нулевой риск

Минусы:
- не лечит noise, только переименовывает noise

## Мой рабочий уклон

Я ожидаю, что лучший practical plan будет где-то между **A + B**:

- `rot` оставить
- для `drift`:
  - либо two-hit confirmation,
  - либо unstable URL classes -> `unverifiable`,
  - либо комбинация этих двух вещей

Но это именно ожидание, не жёсткая директива. Claude должен сам это проверить и аргументировать.

## Чего не хочется в Phase 2.1

Не хочется, чтобы follow-up расползся в:

- full source refresh framework
- background polling system
- embeddings / semantic source diff
- content hashing через массовый `GET` body download для всех URL
- broad rewrite `lint.py`
- auto-edit wiki articles
- auto-stamping `reviewed`

Это должен быть **stabilization pass**, а не новая платформа.

## Обязательный source dive для Claude

Перед планированием перечитать:

- [wiki-freshness-phase2-source-drift-report.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md)
- [wiki-freshness-phase2-source-drift.md](/mnt/e/project/memory%20claude/memory%20claude/docs/codex-tasks/wiki-freshness-phase2-source-drift.md)
- [wiki-knowledge-freshness-lifecycle.md](/mnt/e/project/memory%20claude/memory%20claude/wiki/concepts/wiki-knowledge-freshness-lifecycle.md)
- current `scripts/lint.py`
- `wiki/sources/http-semantics-rfc9110-docs.md`

И отдельно посмотреть реальные noisy examples из report:

- GitHub blob URLs
- GitHub wiki URL
- `semver.org/spec/v2.0.0.html`

## Что должен содержать хороший plan

Нужен нормальный handoff artifact для Codex. В нём должны быть:

1. **Truth hierarchy**
2. **Pre-flight**
3. **Чёткий whitelist**
4. **Изменение operational contract**
   - что теперь считается drift-worthy finding
5. **Verification**
   - positive cases
   - negative/noise cases
6. **Discrepancy checkpoints**
7. **Self-audit**

## Критерии успеха для Phase 2.1

План хороший, если после него будет ясно:

1. как именно снижать false positives;
2. что делать с GitHub blob/wiki type URLs;
3. остаётся ли `rot` как есть;
4. надо ли усложнять state;
5. как проверить improvement не на словах, а на реальном повторном прогоне.

## Короткая формулировка задачи для Claude

Подготовь execution-ready plan для **Wiki Freshness Phase 2.1** — post-merge stabilization pass для advisory `source-drift`. Цель: сохранить полезный `rot` signal и уменьшить false-positive `drift`, особенно на GitHub blob/wiki и других validator-unstable endpoints, без broad redesign и без auto-editing wiki metadata.
