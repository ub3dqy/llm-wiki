# Plan — Repo Hygiene PR 1: Add `dev` dependency group (PEP 735)

## Revision history

- **v1 (initial)** — использовал `[project.optional-dependencies].dev`. **Отозван** 2026-04-15 после того как Codex на doc verification pre-flight'е поймал семантический блокер: uv docs явно различают `optional-dependencies` (extras, published) и `dependency-groups` (local-only dev layer, PEP 735). Для dev-only tooling в непубликуемом проекте правильный путь — PEP 735 dependency groups.
- **v2 (this revision)** — использует `[dependency-groups].dev` per PEP 735. Verification переключена с `uv sync --extra dev` на `uv sync` (dev — default group в uv) + `uv sync --no-dev` как regression check. Минимальная uv версия: `0.10.2` (уже в окружении, verified через `uv sync --help`).
- **v2.1 (mid-execution patch)** — acceptance "untouched paths check" переписана с **global empty diff** на **baseline-delta approach**. Предыдущая формулировка ожидала что `git diff -- scripts/ hooks/ ...` пустой, но эти пути уже содержали baseline dirt (вероятно line-ending CRLF/LF churn) до старта задачи. Правильный подход: Codex снимает baseline этих путей в секции 0.2b ПЕРЕД правкой кода, затем в acceptance сравнивает current diff с baseline. Равенство = Codex не трогал ни один out-of-scope файл. Это был мой второй blunder подряд с dirty worktree assumption.

## Иерархия источников правды

1. **Официальная документация** — primary source of truth:
   - **PEP 735 — Dependency Groups for Python** — https://peps.python.org/pep-0735/
   - uv — Dependency groups — https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
   - uv — CLI reference `uv sync` (для `--group` / `--no-dev` / `--only-dev`) — https://docs.astral.sh/uv/reference/cli/#uv-sync
   - PEP 621 — https://peps.python.org/pep-0621/ (для понимания что `[project]` требует минимум и что `optional-dependencies` — extras, не dev)
2. **Реальное состояние кода** — secondary:
   - `<repo-root>/pyproject.toml` текущее содержимое
   - `<repo-root>/.github/workflows/wiki-lint.yml` — текущий CI gate (контекст, не трогаем)
   - `<repo-root>/.gitignore` — `uv.lock` gitignored
3. **Этот план** — derived artifact, написан Claude'ом, может содержать ошибки. Если план и дока расходятся — приоритет у доки.

## Context

Задача — первый шаг из 5-PR repo hygiene sequence (Finding #3 из [[analyses/repo-hygiene-findings-2026-04-15]]). Обсуждение между Claude и Codex:

- `docs/codex-tasks/repo-hygiene-opinion-on-claude-proposal.md` (Codex's first opinion)
- `docs/codex-tasks/repo-hygiene-response-to-claude-followup.md` (Codex's follow-up, final agreement)

Финальный согласованный sequence (обе стороны):

1. **PR 1 (этот план)**: `[dependency-groups]` с `dev = [...]` per PEP 735
2. PR 2: Ruff config `target-version = "py312"` + `extend-select = ["I"]` (отдельным handoff'ом)
3. PR 3: `ruff check` в `.github/workflows/wiki-lint.yml` (отдельным handoff'ом)
4. PR 4: первый `ruff format` style-only commit + `.git-blame-ignore-revs` (отдельным handoff'ом)
5. PR 5: `ruff format --check` в CI (отдельным handoff'ом)

**Этот план покрывает ТОЛЬКО PR 1**. Остальные — отдельные задачи, отдельные handoff'ы. Scope creep запрещён.

### Почему PEP 735 `[dependency-groups]`, а не `[project.optional-dependencies]`

Это был сам blocker v1 плана. Разница семантическая, не синтаксическая.

**[OFFICIAL-uv-docs]** Из https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups:

- `project.optional-dependencies`: *"Published optional dependencies, or 'extras'"* — попадают в published wheel metadata, юзер может установить через `pip install pkg[extra-name]`. Семантика: **optional runtime features** (например, `async`, `pandas`, `numpy`).
- `dependency-groups`: *"Unlike optional dependencies, development dependencies are local-only and will not be included in the project requirements when published... uv uses the [dependency-groups] table (as defined in PEP 735) for declaration of development dependencies."*

**Для этого репо конкретно**:
- `llm-personal-kb` — personal knowledge base tool, **никогда не публикуется на PyPI**. "published vs local-only" функционально не важно.
- **Но семантически**: ruff и pytest — это dev tooling, не optional runtime features. Класть их в `optional-dependencies` — значит лgать читателю `pyproject.toml` о том что они являются "optional way to extend runtime". Они не runtime, они dev.
- **`dev` — default group в uv**: `uv sync` без флагов автоматически включает `[dependency-groups].dev`. `uv sync --no-dev` отключает для production install. Это native UX, без необходимости помнить `--extra dev`.

**Portable?** PEP 735 — стандарт (2024), принят, reference implementation в pip `25.1+`, поддержан uv `0.4.27+`, Poetry планирует поддержку. Это **не** uv-specific lock-in. Если в будущем уйдём с uv — pip читает PEP 735 nativly.

**Что не делаем**:
- НЕ используем `[tool.uv] dev-dependencies` — это pre-PEP-735 legacy uv-specific синтаксис, deprecated в пользу PEP 735.
- НЕ используем `[project.optional-dependencies].dev` — семантически неправильно (см. выше).

## Doc verification (обязательно перечитать ПЕРЕД правкой)

Codex **обязан** открыть эти URL'ы и заполнить `## 0.6 Doc verification` в отчёте дословными цитатами перед любой правкой `pyproject.toml`.

| URL | Что искать |
|---|---|
| https://peps.python.org/pep-0735/ | Цитата про цель PEP 735: `[dependency-groups]` — top-level TOML table for declaring groups of dependencies that are not published, specifically для development/testing/linting/etc. |
| https://peps.python.org/pep-0735/ | Цитата про формат: dict of group-name → list of PEP 508 strings, groups могут ссылаться друг на друга через `{include-group = "<name>"}` |
| https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups | Цитата про различие: `optional-dependencies` = published extras, `dependency-groups` = local-only dev layer. **Дословно** процитировать эти два определения |
| https://docs.astral.sh/uv/reference/cli/#uv-sync | Цитата про `--group`, `--no-dev`, `--only-dev`, `dev` как default group |
| Local: `uv sync --help` output в текущем окружении | Подтверждение что установленный uv поддерживает `--group`, `--no-dev`, `--only-dev`. Если любой флаг отсутствует — **стоп**, нужен апгрейд uv, в Discrepancies |
| Local: `uv --version` | Зафиксировать текущую версию. Должна быть ≥ 0.4.27 для PEP 735 support. Claude проверил `uv 0.10.2` 2026-04-15, Codex обязан перепроверить сам |

Если любой URL недоступен, content не совпадает с планом, или local uv не поддерживает нужные флаги — **стоп**, в Discrepancies, не кодировать вслепую.

## Mandatory external tools

Codex **обязан** использовать все доступные инструменты:

- **LLM Wiki**: прочитать перед работой:
  - `wiki/sources/python-pyproject-toml-docs.md` — PEP 621 reference (но **обратить внимание** на строку 278: этот файл **НЕ покрывает** PEP 735, поэтому для dependency-groups использовать primary source напрямую, не этот файл)
  - `wiki/sources/astral-uv-docs.md` — uv sync behavior
  - `wiki/sources/uv-lockfile-format-docs.md` — понимание что lockfile надо регенерировать
  - `wiki/analyses/repo-hygiene-findings-2026-04-15.md` — Finding #3 в контексте
- **WebFetch (critical)**: все URL из таблицы Doc verification выше. **PEP 735 primary** — https://peps.python.org/pep-0735/ — обязательно прочитать первой секции про rationale и examples, и uv docs на https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
- **MCP git**: `git_status`, `git_diff` для snapshot до/после
- **MCP filesystem**: допустимо вместо локального Read, если удобно
- **Repo-local docs**: `CLAUDE.md` (правило Gate roles), `AGENTS.md` (environment discipline)
- **Subagent делегирование**: не требуется для задачи такого размера
- **Линтеры**: не запускать до применения правки (см. Verification phases)

Игнорирование инструмента = халтура, не "оптимизация".

## Contracts which cannot be violated

**[OFFICIAL-PEP-735]** `[dependency-groups]` — это top-level TOML table (НЕ внутри `[project]`, а на корневом уровне файла). Ключи — имена групп, значения — массивы PEP 508 dependency strings. Формат:

```toml
[dependency-groups]
<group-name> = ["<pep508>", "<pep508>", ...]
```

**Важно**: `[dependency-groups]` **не** внутри `[project]`. Это отдельная top-level секция, sibling к `[project]` и `[tool.ruff]`. Ошибка размещения внутри `[project.dependency-groups]` — invalid TOML per PEP 735 spec.

**[OFFICIAL-uv-sync]** Для `[dependency-groups]`:
- `uv sync` **по умолчанию** включает группу с именем `dev` (это specially-cased convention в uv)
- `uv sync --group <name>` — включить конкретную группу
- `uv sync --no-dev` — отключить автоматическое включение `dev` (для production install)
- `uv sync --only-dev` — только dev группа, без runtime dependencies
- После изменения `pyproject.toml` uv регенерирует `uv.lock` при следующем `uv lock` или `uv sync`

**[OFFICIAL-uv-docs]** `uv.lock` — human-readable TOML, управляется исключительно uv, ручное редактирование запрещено.

**[EMPIRICAL-.gitignore:21]** В этом репо `uv.lock` **не tracked** — он явно игнорируется через `.gitignore:21`. Lockfile — **local autogenerated side effect**, не review artifact. Не попадает в git diff и не является частью PR.

**[EMPIRICAL-uv-0.10.2-help]** Установленный локально uv 0.10.2 **поддерживает** `--group`, `--no-dev`, `--only-dev`, `--no-default-groups` флаги (проверено Claude'ом через `uv sync --help` на 2026-04-15). PEP 735 support доступен начиная с uv 0.4.27, так что 0.10.2 — запас по совместимости.

**[EMPIRICAL-.gitignore]** Repo policy: `uv.lock` — локальный артефакт. Scope PR 1 ограничен единственным tracked файлом — `pyproject.toml`.

## Files to modify (whitelist — ровно эти файлы)

**Strict whitelist — ровно один tracked файл**:

1. **`pyproject.toml`** — добавить top-level секцию `[dependency-groups]` с `dev = [...]` per PEP 735

**Local side effects (не в whitelist, не в git)**:
- **`uv.lock`** — **автоматически** регенерируется командой `uv lock` (или `uv sync`, который включает dev группу по дефолту). Этот файл gitignored (`.gitignore:21`), не попадает в PR. Codex **не редактирует** его руками. Регенерация нужна только как sanity check что resolution работает, не как review artifact.
- **`.venv/` / `$HOME/.cache/llm-wiki/.venv`** — локальные venv, gitignored, меняются при `uv sync`.

**Handoff artifacts (не в whitelist по определению)**:
- `docs/codex-tasks/repo-hygiene-pr1-dev-extras-report.md` — этот отчёт

**НЕ трогать**:
- `scripts/*` — ни один скрипт не меняется
- `hooks/*` — ни один хук не меняется
- `.github/workflows/*` — CI gate меняется в PR 3, не здесь
- `CLAUDE.md` — документация про dev tooling в CLAUDE.md обновляется отдельно если нужно, НЕ в этом PR
- `AGENTS.md` — environment rule фиксится отдельной задачей (D1 из wiki-freshness-phase1-report)
- Любые wiki статьи — не в scope PR 1

Видишь что-то рядом грязное — в `Out-of-scope-temptations` отчёта, **не править**.

## Change 1 — `pyproject.toml` add top-level `[dependency-groups]`

### Где
`<repo-root>/pyproject.toml`, после блока `[project]` (после `dependencies = [...]`) и **перед** `[tool.ruff]`. **Не** внутри `[project]` — это top-level sibling секция per PEP 735.

### Текущее состояние

**[EMPIRICAL-pyproject.toml:1-14]** Файл сейчас содержит ровно 14 строк:

```toml
[project]
name = "llm-personal-kb"
version = "0.1.0"
description = "Personal knowledge base compiled from AI conversations — inspired by Karpathy's LLM Wiki"
requires-python = ">=3.12"
dependencies = [
    "claude-agent-sdk>=0.1.59",
    "python-dotenv>=1.2.2",
    "tzdata>=2026.1",
]

[tool.ruff]
line-length = 100
```

### Что добавить

Одна новая **top-level** секция между `[project]` блоком и `[tool.ruff]`:

```toml
[dependency-groups]
dev = [
    "ruff>=0.14",
    "pytest>=8",
]
```

**Критично**: это top-level table, не nested в `[project]`. PEP 735 явно определяет `[dependency-groups]` как корневую секцию.

### Обоснование выбора инструментов и версий

- **`ruff`** — уже упомянут в `[tool.ruff]` секции, но нигде не объявлен как dependency. Codex **обязан проверить** актуальную major version через `uv pip index versions ruff` или WebFetch https://pypi.org/project/ruff/ перед фиксацией constraint'а. Текущий plan использует `ruff>=0.14` как conservative lower bound, но если на момент выполнения актуальная — `0.15` или выше, зафиксировать `>=<major>.<minor>` соответственно. Записать результат в Discrepancies если план и реальность расходятся.
- **`pytest`** — не используется сейчас в репо, но объявляется как стандартный dev tool на будущее. Codex **обязан проверить** актуальную major через `uv pip index versions pytest` или WebFetch https://pypi.org/project/pytest/. `pytest>=8` — текущий major на момент написания плана; если стал 9 — обновить.

**[EMPIRICAL-pyproject.toml]** Policy на version constraints в этом репо (из текущего `dependencies` блока: `claude-agent-sdk>=0.1.59`, `python-dotenv>=1.2.2`, `tzdata>=2026.1`): `>=<major>.<minor>` lower bound без upper cap. Следовать тому же стилю.

### Точный diff expectation

```diff
@@ pyproject.toml @@
 dependencies = [
     "claude-agent-sdk>=0.1.59",
     "python-dotenv>=1.2.2",
     "tzdata>=2026.1",
 ]

+[dependency-groups]
+dev = [
+    "ruff>=0.14",
+    "pytest>=8",
+]
+
 [tool.ruff]
 line-length = 100
```

Если реальный diff отличается чем-то кроме exact version numbers (см. обоснование выше) — Discrepancies.

### Acceptance criteria для Change 1

- [ ] Top-level секция `[dependency-groups]` добавлена в `pyproject.toml` (не `[project.dependency-groups]`, не `[project.optional-dependencies]`)
- [ ] Секция размещена после `[project]` блока и до `[tool.ruff]`
- [ ] Под ключом `dev` ровно два PEP 508 string'а: `ruff` и `pytest`
- [ ] Version constraints установлены по актуальному major (проверено через pypi/uv pip index)
- [ ] Формат отступов (4 spaces inside array) совпадает с существующей `dependencies` секцией
- [ ] Никакие другие ключи или секции в `pyproject.toml` не изменены
- [ ] `[project.optional-dependencies]` **НЕ добавляется** — это был v1 blocker
- [ ] Комментарии не добавляются

## Verification phases

### Phase 1 — Unit smoke (Codex выполняет прямо в отчёт)

Все команды — с `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy` префиксом если запускаются из WSL (см. memory rule про WSL uv discipline).

**1.1** TOML valid:

```bash
uv run python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('TOML ok')"
```

Ожидание: `TOML ok`, exit 0.

**1.2** `[dependency-groups].dev` реально виден как top-level ключ:

```bash
uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['dependency-groups']['dev']); assert 'optional-dependencies' not in d.get('project', {}), 'v1 mistake: optional-dependencies should not exist'"
```

Ожидание: `['ruff>=<version>', 'pytest>=<version>']`, exit 0. Assertion гарантирует что v1 ошибка не повторена.

**1.3** Lockfile resolution работает (sanity check, файл gitignored):

```bash
uv lock
ls -la uv.lock
```

Ожидание: `uv lock` exit 0, `uv.lock` существует на диске. `git diff` проверять НЕ нужно — файл gitignored. Если `uv lock` падает с resolution conflict — **стоп**, в Discrepancies.

**1.4** Sync с dev группой работает (дефолтное поведение uv):

```bash
uv sync
uv run ruff --version
uv run pytest --version
```

Ожидание: `uv sync` включает `dev` группу автоматически (это special-cased default в uv). `ruff X.Y.Z`, `pytest X.Y.Z`, оба exit 0. Если любой из бинарей не запускается — стоп, Discrepancies.

**1.4b** Explicit `--group dev` тоже работает (sanity check, эквивалент 1.4):

```bash
uv sync --group dev
uv run ruff --version
```

Ожидание: то же что в 1.4. Это verification что explicit `--group` flag работает, а не только default behavior.

**1.5** Regression — `uv sync --no-dev` отключает dev группу, runtime dependencies остаются рабочими:

```bash
uv sync --no-dev
uv run python -c "import claude_agent_sdk; import dotenv; print('runtime ok')"
uv run ruff --version || echo "ruff unavailable after --no-dev (expected)"
```

Ожидание: `runtime ok`, exit 0. Второй `uv run ruff --version` **ожидаемо падает** (dev группа отключена, ruff удалён из active venv) — это correct behavior. Если ruff всё ещё работает после `--no-dev` — что-то не так с конфигурацией, Discrepancies.

**1.6** Existing structural lint не регрессировал:

```bash
uv run python scripts/lint.py --structural-only
```

Ожидание: exit 0, тот же набор checks что до правки, никаких новых errors/warnings от `lint.py` (оно не должно реагировать на `pyproject.toml`).

**1.7** `doctor --quick` проходит:

```bash
uv run python scripts/wiki_cli.py doctor --quick
```

Ожидание: exit 0, pre-existing FAIL'ы (`flush_pipeline_correctness` Bug H, `index_health` если стал stale после правок) — baseline, не новые. Никаких **новых** FAIL'ов связанных с `pyproject.toml`.

### Phase 2 — Integration `[awaits user]`

**2.1** Пользователь делает `git diff -- pyproject.toml` и ревью новой секции руками.

**2.2** Пользователь запускает `uv sync` (дефолт включает dev группу) на чистой клон-копии (если хочет удостовериться что install from scratch работает на свежем lockfile, который генерируется локально каждому разработчику).

**2.3** `[awaits user — merge decision]`

### Phase 3 — Statistical

Не применимо для этого PR. Эффект измеряется сразу после merge.

## Acceptance criteria

- ✅ Phase 1.1: `pyproject.toml` парсится как valid TOML
- ✅ Phase 1.2: `[dependency-groups].dev` (top-level) содержит `ruff` и `pytest` с version constraints; `[project.optional-dependencies]` **отсутствует**
- ✅ Phase 1.3: `uv lock` exit 0, resolution без конфликтов (sanity check, lockfile gitignored)
- ✅ Phase 1.4: `uv sync` (дефолт) включает dev группу, оба бинаря запускаются, версии выводятся
- ✅ Phase 1.4b: `uv sync --group dev` (explicit) тоже работает
- ✅ Phase 1.5: `uv sync --no-dev` даёт рабочий runtime без dev tooling; ruff после этого недоступен (expected)
- ✅ Phase 1.6: `lint.py --structural-only` exit 0, без новых issues
- ✅ Phase 1.7: `doctor --quick` exit 0 без новых FAIL
- ✅ **Path-scoped diff check (positive)**: `git diff -- pyproject.toml` показывает **только** добавление top-level `[dependency-groups]` секции, **ничего больше** в этом файле. Глобальный `git diff` **не используется** для acceptance.
- ✅ **Path-scoped status check**: `git status --short -- pyproject.toml` показывает ровно `M pyproject.toml`
- ✅ **Baseline-delta check (untouched paths)**: current `git diff -- scripts/ hooks/ .github/ wiki/ CLAUDE.md AGENTS.md` **bit-identical** baseline captured в 0.2b ПЕРЕД правкой. Равенство = Codex не трогал эти пути. Если есть delta — что-то в out-of-scope изменилось, Discrepancy.
- ✅ Pre-existing worktree dirt (baseline в out-of-scope paths, untracked `.codex/` и т.п.) — **не блокер**, это just-is, acceptance сравнивает с ним, не требует чистоты

## Out of scope

1. **Ruff rules расширение** — Finding #1, отдельный PR (PR 2)
2. **Ruff в CI gate** — Finding #4, отдельный PR (PR 3)
3. **`ruff format` style commit** — Finding #4b, отдельный PR (PR 4)
4. **`[project.scripts]` CLI entry point** — Finding #2, deferred indefinitely
5. **`pre-commit-config.yaml`** — после PR 5, только если будет отдельное решение
6. **CLAUDE.md update** про `uv sync` с dev группой и `uv sync --no-dev` для production install — отдельное обсуждение, не в этом PR
7. **AGENTS.md WSL env fix** (D1 из wiki-freshness-phase1-report) — отдельная задача
8. **Документация нового extras в README** — если нужно, отдельным docs PR

Видишь любое из этого в процессе работы — **Out-of-scope-temptations** в отчёте, не трогать.

## Rollback

```bash
git checkout -- pyproject.toml
# uv.lock gitignored — чтобы вернуть к исходному lockfile, перезапустить uv sync без dev группы
uv sync --no-dev
```

Никаких commit'ов до полной верификации Phase 1. Никаких push'ей до явного go от пользователя.

## Discrepancy handling

- Если актуальная мажорная версия `ruff` или `pytest` отличается от указанной в плане — в Discrepancies с точным числом из `uv pip index versions <pkg>`, продолжать с актуальной версией (это ожидаемо, версии в плане были снапшотом).
- Если `pyproject.toml` перед работой уже имеет `[dependency-groups]` или `[project.optional-dependencies]` (кто-то добавил параллельно) — **стоп**, не перезаписывать, в Discrepancies, эскалация.
- Если `uv sync --help` **не показывает** `--group` / `--no-dev` флаги — значит uv слишком старый, не поддерживает PEP 735. **Стоп**, в Discrepancies, эскалация (план предполагает uv ≥ 0.4.27).
- Если `uv lock` выдаёт resolution error (конфликт версий) — **стоп**, в Discrepancies с полным stderr, не пытаться fix руками через version pinning.
- Если `uv lock` после правки `pyproject.toml` не создаёт/не обновляет `uv.lock` на диске — **стоп**, что-то не так с uv или cache, в Discrepancies с полным stderr.
- Если `uv sync --no-dev` **всё ещё** оставляет ruff доступным (ожидалось удаление) — конфигурация может быть в неожиданном состоянии, в Discrepancies.
- Любое другое отклонение от плана — в Discrepancies перед continuation.

## Notes для исполнителя (Codex)

- **Задача очень маленькая** (буквально 5 строк в одном файле + lockfile regen). Это НЕ освобождает от полного Doc verification + full Tools used + Self-audit. Incident 2026-04-14 (doctor 24h window): "задача малая" = соблазн пропустить структуру = correction wave. Не поддаваться.
- **Doc verification ПЕРЕД правкой кода, не после.** Открой все три URL'а из таблицы Doc verification, процитируй дословно, заполни `## 0.6 Doc verification` таблицу в отчёте. Только потом правка.
- **Version constraints — по pypi.org актуальному major**, не по снапшоту плана. Обнови план в Discrepancies если разошлись.
- **Не коммитить, не пушить.** Финал — заполненный отчёт, review делает пользователь, commit решает пользователь.
- **Не лезть в `[tool.ruff]` секцию** — это PR 2, отдельный handoff.
- **Не добавлять `ruff-format`, `pytest-cov`, `mypy`, `pre-commit`** или любые другие инструменты в `dev` группу. Scope — ровно `ruff` + `pytest`. Если хочется добавить — Out-of-scope-temptations.
- **НЕ использовать `[project.optional-dependencies]`** — это был v1 blocker, не повторять. Семантически неправильно для dev-only tooling в непубликуемом проекте. Ссылка на обоснование — раздел "Почему PEP 735" выше.
- **НЕ класть `[dependency-groups]` внутрь `[project]`** — это top-level sibling секция per PEP 735, не nested. Ошибка размещения = invalid per spec.
- **Baseline snapshot (0.2b) ДО любой правки `pyproject.toml`.** Если ты начал с правки pyproject.toml и только потом вспомнил про 0.2b — это уже не baseline, это post-edit state, и delta comparison в 1.3 станет невалидным. Порядок: 0.1 → 0.2 → 0.2b → 0.3 → 0.4 → 0.5 → 0.6 → **только затем** Change 1 и правка кода.
- **Никакие рефакторы в других файлах**. Если lint.py после твоей правки показывает какой-то pre-existing issue — игнор, это baseline.
- **uv.lock регенерация — нормальная часть задачи**, не scope creep. Но **редактировать `uv.lock` руками — запрещено**. Только через `uv lock` или `uv sync` (который включает dev группу по дефолту).
- **WSL uv discipline**: каждая команда `uv run ...` или `uv sync ...` из WSL должна иметь префикс `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy`. Если запускаешь из Windows host (native), префикс не нужен.
- **Self-audit checklist в конце отчёта** — каждый пункт ✅ или ❌. Любой ❌ → вернись и доделай, не сдавай "почти готово".

Compact prompt для user'а (для копирования в Codex) — пользователь попросит отдельно после того как план и отчёт-темплейт будут готовы.
