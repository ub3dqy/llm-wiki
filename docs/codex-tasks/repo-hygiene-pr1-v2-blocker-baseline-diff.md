# Repo Hygiene PR 1 v2 — Blocker: untouched-path check conflicts with dirty baseline

Я начал выполнение v2 плана и дошёл до path-scoped verification. На этом месте есть новый реальный blocker.

## Что уже успел подтвердить

Уже выполнено и прошло:

- `pyproject.toml` изменён только в нужном месте: добавлена top-level секция
  ```toml
  [dependency-groups]
  dev = [
      "ruff>=0.15",
      "pytest>=9.0",
  ]
  ```
- TOML валиден: `TOML ok`
- top-level ключ читается корректно: `['ruff>=0.15', 'pytest>=9.0']`
- `[project.optional-dependencies]` не появился

## Где именно сломался план

План и шаблон отчёта требуют такой acceptance check:

```bash
git diff -- scripts/ hooks/ .github/ wiki/ CLAUDE.md AGENTS.md
```

с ожиданием:

> should be empty

Но в реальном репозитории это **не может быть пустым уже до старта задачи**, потому что эти пути были грязными baseline'ом.

### Что реально показал check

Команда сразу вернула большой diff по уже изменённым файлам, например:

- `.github/workflows/wiki-lint.yml`
- `CLAUDE.md`
- `scripts/utils.py`
- и далее много baseline-грязи

То есть проверка в текущем виде отвечает не на вопрос

> «я тронул эти пути в рамках этой задачи?»

а на вопрос

> «есть ли вообще какой-либо diff в этих путях в worktree?»

И при текущем baseline ответ заранее: **да, есть**.

## Почему это blocker, а не просто неудобство

По твоему правилу я не должен делать вид, что acceptance check выполним, если он логически не может пройти в текущем состоянии репо.

Сейчас конфликт такой:

- план признаёт pre-existing worktree dirt baseline
- но untouched-path acceptance сформулирован так, как будто baseline по этим путям чистый

Обе вещи одновременно истинны быть не могут.

## Что предлагаю вместо этого

Нужна одна из двух корректных формулировок.

### Вариант A — baseline snapshot compare

До правок:

```bash
git diff -- scripts/ hooks/ .github/ wiki/ CLAUDE.md AGENTS.md > /tmp/repo-hygiene-pr1-baseline.diff
```

После правок:

```bash
git diff -- scripts/ hooks/ .github/ wiki/ CLAUDE.md AGENTS.md > /tmp/repo-hygiene-pr1-after.diff
cmp /tmp/repo-hygiene-pr1-baseline.diff /tmp/repo-hygiene-pr1-after.diff
```

Смысл: diff по out-of-scope путям может быть непустым, но он должен остаться **идентичным baseline**.

### Вариант B — weaker path guarantee

Оставить только:

```bash
git diff -- pyproject.toml
```

и считать достаточным, что:

- whitelist tracked file = только `pyproject.toml`
- его diff правильный
- никакие дополнительные файлы я не редактировал руками

Это слабее, но проще.

## Почему я остановился сейчас

Потому что дальше по плану идут `uv lock`, `uv sync`, `lint`, `doctor --quick`, и я не хочу продолжать в ситуацию, где acceptance уже противоречит baseline и потом придётся задним числом объяснять, почему один из обязательных checks заведомо не мог стать пустым.

## Текущее состояние

- `pyproject.toml` уже изменён
- smokes 2.1 и 2.2 уже фактически прошли
- `uv lock`, `uv sync`, `lint`, `doctor --quick` я **пока не гоню дальше**, пока не решим, как трактуем untouched-path acceptance against dirty baseline

## Что нужно от тебя

Нужно выбрать трактовку:

1. **Baseline snapshot compare** — строгий и правильный вариант
2. **Убрать untouched-path empty requirement** и оставить только `pyproject.toml`-scoped diff/status

После этого я сразу продолжу выполнение без пересборки всего контекста.
