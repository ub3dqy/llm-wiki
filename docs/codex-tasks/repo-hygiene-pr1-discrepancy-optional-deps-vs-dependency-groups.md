# Repo Hygiene PR 1 — Discrepancy: `optional-dependencies` vs `dependency-groups`

Я остановил выполнение на doc verification. Код не менял.

## Что именно не сошлось

План требует оформить dev-инструменты как:

```toml
[project.optional-dependencies]
dev = ["ruff>=...", "pytest>=..."]
```

Но официальная документация `uv` описывает это иначе.

## Что говорит офдока `uv`

Из `https://docs.astral.sh/uv/concepts/projects/dependencies/`:

- `project.optional-dependencies: Published optional dependencies, or "extras".`
- `Unlike optional dependencies, development dependencies are local-only and will not be included in the project requirements when published...`
- `uv uses the [dependency-groups] table (as defined in PEP 735) for declaration of development dependencies.`

То есть:

- `project.optional-dependencies` в uv — это **extras**
- dev dependencies в uv-native модели — это **`[dependency-groups]`**, а не extras

## Что это значит practically

Синтаксически план валиден:
- PEP 621 действительно разрешает `[project.optional-dependencies]`
- `uv sync --extra dev` действительно умеет ставить extras

Но семантически это уже не совсем то, что план заявляет как «dev dependencies». Это будет:
- published extra `dev`
- а не локальный dev-layer в модели uv

## Почему это blocker

По контракту задачи:
- офдока выше плана
- при расхождении нужно остановиться и зафиксировать discrepancy
- нельзя кодировать вслепую

Именно это я и сделал.

## Варианты решения

### Вариант 1 — продолжить по плану как есть
Осознанно принимаем, что:
- `dev` будет оформлен как **extra**
- а не как uv-native development dependency

Это допустимо, если цель — portability / PEP 621 standard first.

### Вариант 2 — переписать план под `dependency-groups`
Тогда PR 1 надо делать через:

```toml
[dependency-groups]
dev = ["ruff>=...", "pytest>=..."]
```

И verification тоже нужно будет менять:
- не `uv sync --extra dev`
- а uv-native путь для dependency groups

### Вариант 3 — остановить задачу и заново согласовать контракт
Если хочешь именно «правильно по uv», а не «portable через PEP 621 extras», то план надо переписать до старта.

## Мой вывод

Я бы не продолжал без твоего явного решения.

Потому что сейчас вопрос не в синтаксисе, а в том, **что именно мы хотим получить**:

- стандартный PEP 621 extra `dev`
- или uv-native local dev dependency group

До этого решения код трогать не надо.
