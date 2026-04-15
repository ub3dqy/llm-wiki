# Plan — Repo Hygiene PR 2: Ruff config `target-version` + `extend-select = ["I"]`

## Иерархия источников правды

1. **Официальная документация** — primary source of truth:
   - Ruff — configuration — https://docs.astral.sh/ruff/configuration/
   - Ruff — settings reference (`target-version`, `lint.extend-select`, `lint.select`) — https://docs.astral.sh/ruff/settings/
   - Ruff — rule `I` (isort) — https://docs.astral.sh/ruff/rules/#isort-i
   - PEP 8 — imports section (context, why `I` rule exists) — https://peps.python.org/pep-0008/#imports
2. **Реальное состояние кода** — secondary:
   - `<repo-root>/pyproject.toml` текущее содержимое
   - `<repo-root>/scripts/` и `<repo-root>/hooks/` — 8 файлов с I-диагностиками, точный список зафиксирован в Baseline measurements ниже
   - `<repo-root>/.gitignore` — `uv.lock` gitignored, `.venv` gitignored
3. **Этот план** — derived artifact, написан Claude'ом, может содержать ошибки. Если план и дока расходятся — приоритет у доки.

## Context

PR 2 из 5-PR repo hygiene sequence. Предыдущий — PR 1 (dev dependency group, merged как commit `c42cccd`). Этот PR:

- Добавляет `target-version = "py312"` в `[tool.ruff]`
- Добавляет `[tool.ruff.lint]` секцию с `extend-select = ["I"]`
- Применяет `ruff check --fix --select I` к 8 файлам в `scripts/` и `hooks/` — autofix всех 12 I-диагностик в том же PR

**Scope — только I (isort), не UP, не B**. `UP` и `B` — отдельные последующие задачи (не в текущей sequence как committed milestones; вернёмся позже осознанно).

### Почему `I` отдельно от `UP`/`B`

- `I` (import sorting/organization) — почти полностью механический, zero behavioral change, 1-commit cleanup, no debate
- `UP` (pyupgrade) — может менять синтаксис (`typing.List` → `list`, `Union[X, Y]` → `X | Y`), иногда спорные edge cases в публичных сигнатурах
- `B` (bugbear) — может найти **реальные баги**, которые требуют отдельного обсуждения как их фиксить

Codex и Claude согласовали этот decomposition в `docs/codex-tasks/repo-hygiene-response-to-claude-followup.md`.

### Почему `target-version = "py312"`, а не из `requires-python`

Ruff умеет инферить `target-version` из `requires-python`, но **явное лучше неявного** per PEP 20 + Ruff docs рекомендуют явно задавать чтобы избежать неоднозначности между `>=3.12` (минимум) и "target what syntax to emit/expect". `py312` совпадает с `requires-python = ">=3.12"` из текущего pyproject.toml, так что behavioral change = 0.

## Baseline measurements (captured 2026-04-15 by Claude)

**[EMPIRICAL]** Перед написанием плана Claude прогнал `uv run ruff check --select I scripts/ hooks/` и зафиксировал:

```
Found 12 errors.
[*] 12 fixable with the `--fix` option.
```

**Affected files (8 total)**:
- `hooks/hook_utils.py`
- `hooks/shared_context.py`
- `hooks/shared_wiki_search.py`
- `scripts/compile.py`
- `scripts/doctor.py`
- `scripts/lint.py`
- `scripts/query.py`
- `scripts/wiki_cli.py`

**Характер диагностик** (выборочно из `--diff` preview):
- `hooks/session-start.py`, `hooks/user-prompt-wiki.py` — лишние пустые строки между import блоками (но эти файлы не в списке affected — возможно warning-only)
- `hooks/shared_context.py` — лишние пустые строки + порядок импортов

Codex **обязан сам** перепрогнать эту команду на pre-flight этапе и зафиксировать актуальные числа в 0.2b отчёта. Если count ≠ 12 или список affected files расходится — в Discrepancies, не continue.

## Doc verification (обязательно перечитать ПЕРЕД правкой)

Codex **обязан** открыть эти URL'ы и заполнить `## 0.6 Doc verification` дословными цитатами.

| URL | Что искать |
|---|---|
| https://docs.astral.sh/ruff/configuration/ | Цитата про `[tool.ruff]` vs `[tool.ruff.lint]` sections — где именно `target-version` и где `select`/`extend-select` |
| https://docs.astral.sh/ruff/settings/#target-version | Цитата про valid values (`py38`, `py39`, `py310`, `py311`, `py312`, `py313`, `py314`) и что target-version управляет |
| https://docs.astral.sh/ruff/settings/#lint_select | Цитата про различие `select` и `extend-select` — extend **добавляет** к default set, не заменяет |
| https://docs.astral.sh/ruff/rules/#isort-i | Цитата что `I` — это isort-compatible rules, что именно они проверяют |
| Local: `uv run ruff --version` | Зафиксировать актуальную версию (после PR 1 это ≥0.15) |
| Local: `uv run ruff check --select I --diff scripts/ hooks/` | Полный вывод **перед** правкой — это baseline, сравнивать с планом |

Если любая цитата расходится с планом — Discrepancies, стоп.

## Mandatory external tools

Codex **обязан** использовать все доступные инструменты:

- **LLM Wiki**: прочитать перед работой:
  - `wiki/sources/astral-ruff-docs.md` — ruff reference
  - `wiki/sources/python-pep8-pep257-docs.md` — PEP 8 context для import sorting
  - `wiki/analyses/repo-hygiene-findings-2026-04-15.md` — Finding #1 в контексте
  - `wiki/sources/python-pyproject-toml-docs.md` — TOML structure для `[tool.*]` sections
- **WebFetch**: все URL из Doc verification таблицы выше
- **MCP git**: `git_status`, `git_diff` для snapshot до/после + baseline-delta
- **Repo-local docs**: `CLAUDE.md` (Gate roles), `AGENTS.md` (WSL env discipline)
- **Subagent делегирование**: не требуется для задачи такого размера
- **Линтеры**: ruff сам по себе — цель задачи, использовать активно

## Contracts which cannot be violated

**[OFFICIAL-ruff-config]** Ruff TOML config structure:
- **`[tool.ruff]`** — general options: `line-length`, `target-version`, `extend-exclude`, etc.
- **`[tool.ruff.lint]`** — lint-specific options: `select`, `extend-select`, `ignore`, `extend-ignore`, `unfixable`, per-rule settings
- **`[tool.ruff.format]`** — format-specific options (не используется в этом PR)
- **`target-version`** живёт в `[tool.ruff]` (top-level), **не** в `[tool.ruff.lint]`. Это частая ошибка — путать эти две секции.

**[OFFICIAL-ruff-select]** `select` vs `extend-select`:
- `select = [...]` — **заменяет** default set (`["E4", "E7", "E9", "F"]`)
- `extend-select = [...]` — **добавляет** к default set, сохраняя существующие rules
- Для этого PR нужен `extend-select`, не `select`. Если использовать `select = ["I"]`, мы **отключим** pyflakes/pycodestyle, что не intended.

**[OFFICIAL-ruff-fix]** `ruff check --fix --select I` — автоматически применяет fixable diagnostics только для указанной категории. Не трогает `UP`/`B`/etc.

**[EMPIRICAL-pyproject.toml]** Текущее состояние `[tool.ruff]` (14 строк файла, после PR 1 merge):

```toml
[tool.ruff]
line-length = 100
```

Одна опция. Target-version не задан, lint subsection отсутствует.

## Files to modify (whitelist)

**Strict whitelist — 9 файлов**:

1. **`pyproject.toml`** — добавить `target-version = "py312"` в `[tool.ruff]` + создать `[tool.ruff.lint]` с `extend-select = ["I"]`
2. **`hooks/hook_utils.py`** — autofix I diagnostics via `ruff check --fix --select I`
3. **`hooks/shared_context.py`** — autofix
4. **`hooks/shared_wiki_search.py`** — autofix
5. **`scripts/compile.py`** — autofix
6. **`scripts/doctor.py`** — autofix
7. **`scripts/lint.py`** — autofix
8. **`scripts/query.py`** — autofix
9. **`scripts/wiki_cli.py`** — autofix

**Handoff artifacts (не в whitelist по определению)**:
- `docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort-report.md` — этот отчёт

**НЕ трогать** (out of scope):
- Любые другие файлы в `scripts/` и `hooks/` — если `ruff --fix` неожиданно трогает не-whitelisted файл, **стоп**, Discrepancy, эскалация
- `.github/workflows/*` — CI gate меняется в PR 3, не здесь
- `CLAUDE.md`, `AGENTS.md`, `README.md`, wiki статьи — out of scope
- `.venv`, `uv.lock` — gitignored local side effects

Видишь рядом что-то грязное — в Out-of-scope-temptations отчёта, не править.

## Change 1 — `pyproject.toml` add ruff config

### Где
`<repo-root>/pyproject.toml`, блок `[tool.ruff]` и новый блок `[tool.ruff.lint]`.

### Текущее состояние (до правки)

```toml
[tool.ruff]
line-length = 100
```

### Что добавить

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = ["I"]
```

### Точный diff expectation

```diff
@@ pyproject.toml @@
 [tool.ruff]
 line-length = 100
+target-version = "py312"
+
+[tool.ruff.lint]
+extend-select = ["I"]
```

### Acceptance criteria Change 1

- [ ] `target-version = "py312"` добавлен в `[tool.ruff]` (после `line-length`)
- [ ] Новая секция `[tool.ruff.lint]` добавлена в конце файла
- [ ] `extend-select = ["I"]` (именно extend, не select — см. contracts)
- [ ] **Ничего** не добавлено в `[project]` или `[dependency-groups]` блоки
- [ ] Никаких новых комментариев
- [ ] Отступы/quoting совпадают с существующим стилем

## Change 2 — apply `ruff check --fix --select I` to 8 files

### Команда

```bash
uv run ruff check --fix --select I scripts/ hooks/
```

### Expected output

```
Found 12 errors (12 fixed, 0 remaining).
```

### Что это делает

Autofix I category diagnostics — реорганизация импортов по isort convention (grouping stdlib / third-party / local, сортировка внутри группы, единичные пустые строки между группами).

### Acceptance criteria Change 2

- [ ] `ruff check --fix --select I scripts/ hooks/` exit 0
- [ ] Output содержит `12 fixed, 0 remaining` (или совпадает с baseline 0.2b count, если baseline показал другое число)
- [ ] Только 8 whitelisted файлов изменились, ни одного другого
- [ ] После fix: `uv run ruff check --select I scripts/ hooks/` возвращает `All checks passed!` или `Found 0 errors`
- [ ] Python syntax всех 8 файлов всё ещё валиден (проверяется в Phase 1.6)

## Verification phases

Все команды с `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy` префиксом если из WSL.

### Phase 1 — Unit smoke

**1.1** TOML valid после правки pyproject.toml:

```bash
uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['tool']['ruff']['target-version']); print(d['tool']['ruff']['lint']['extend-select'])"
```

Ожидание: `py312`, `['I']`, exit 0. Если `KeyError` — структура неправильная.

**1.2** Ruff config видит новые опции:

```bash
uv run ruff check --show-settings scripts/lint.py 2>&1 | grep -E "target-version|extend-select|select"
```

Ожидание: target-version показывает `py312`, extend-select включает `I`.

**1.3** Baseline I-diagnostics count (до fix):

```bash
uv run ruff check --select I scripts/ hooks/ 2>&1 | tail -3
```

Ожидание: `Found N errors` где N = 12 (если Codex'овский preflight показал другое число — использовать то).

**1.4** Apply fix:

```bash
uv run ruff check --fix --select I scripts/ hooks/
```

Ожидание: `Found 12 errors (12 fixed, 0 remaining)` или эквивалент.

**1.5** Post-fix — zero I diagnostics:

```bash
uv run ruff check --select I scripts/ hooks/
```

Ожидание: `All checks passed!` или exit 0 без errors.

**1.6** Python syntax sanity на каждом из 8 затронутых файлов:

```bash
uv run python -c "import ast; files=['hooks/hook_utils.py','hooks/shared_context.py','hooks/shared_wiki_search.py','scripts/compile.py','scripts/doctor.py','scripts/lint.py','scripts/query.py','scripts/wiki_cli.py']; [ast.parse(open(f).read()) for f in files]; print('all 8 files parse ok')"
```

Ожидание: `all 8 files parse ok`, exit 0.

**1.7** Import smoke — что импорты реально работают после переупорядочивания:

```bash
PYTHONPATH=hooks:scripts uv run python -c "import hook_utils, shared_context, shared_wiki_search; import compile, doctor, lint, query, wiki_cli; print('all imports ok')"
```

Ожидание: `all imports ok`, exit 0. Если хоть один модуль не импортируется — `ruff --fix` что-то сломал, Discrepancy.

**1.8** `lint.py --structural-only` не regressed:

```bash
uv run python scripts/lint.py --structural-only
```

Ожидание: exit 0, тот же набор checks что до правки.

**1.9** `doctor --quick` exit 0:

```bash
uv run python scripts/wiki_cli.py doctor --quick
```

Ожидание: exit 0, только pre-existing `flush_pipeline_correctness` FAIL (Bug H, baseline). Никаких новых FAIL.

### Phase 2 — Integration `[awaits user]`

**2.1** Пользователь делает `git diff -- pyproject.toml` и `git diff -- scripts/ hooks/` и ревью глазами.

**2.2** `[awaits user — merge decision]`

### Phase 3 — Statistical

Не применимо. Эффект — zero diagnostics в `I` category, измеряется немедленно.

## Acceptance criteria

- ✅ Phase 1.1: TOML valid, новые опции видны как dict keys
- ✅ Phase 1.2: ruff `--show-settings` подтверждает `target-version=py312` и `I` в active rules
- ✅ Phase 1.3: baseline I errors count зафиксирован (ожидается 12)
- ✅ Phase 1.4: `ruff check --fix --select I` успешно фиксит всё
- ✅ Phase 1.5: после fix — 0 I errors
- ✅ Phase 1.6: все 8 affected файлов парсятся как valid Python AST
- ✅ Phase 1.7: import sanity — все модули импортируются
- ✅ Phase 1.8: `lint.py --structural-only` exit 0
- ✅ Phase 1.9: `doctor --quick` exit 0, нет новых FAIL
- ✅ **Path-scoped diff check**: `git diff -- pyproject.toml scripts/ hooks/` содержит только ожидаемые изменения (новая ruff config + 12 fix'ов в 8 файлах)
- ✅ **Baseline-delta check (out-of-scope paths)**: SHA256 `git diff -- .github/ wiki/ CLAUDE.md AGENTS.md README.md docs/ .gitignore` идентичен baseline captured в 0.2b
- ✅ Pre-existing worktree dirt в out-of-scope paths — baseline, не regressed

## Out of scope

1. **`UP` rule (pyupgrade)** — отдельный future PR, не в этой sequence
2. **`B` rule (bugbear)** — отдельный future PR после обсуждения
3. **`ruff format`** — PR 4 style-only commit
4. **Ruff в CI gate** — PR 3
5. **`[project.scripts]`** — deferred indefinitely
6. **Pre-commit config** — после PR 5, optional
7. **Update `CLAUDE.md`** про новые ruff rules — отдельно
8. **Fix pre-existing non-I diagnostics** (если `ruff check` без `--select` покажет что-то ещё) — **не трогать**, это separate scope

Видишь любое из этого — в Out-of-scope-temptations.

## Rollback

```bash
git checkout -- pyproject.toml hooks/hook_utils.py hooks/shared_context.py hooks/shared_wiki_search.py scripts/compile.py scripts/doctor.py scripts/lint.py scripts/query.py scripts/wiki_cli.py
```

Никаких commit'ов до полной верификации Phase 1. Никаких push'ей до явного go от пользователя.

## Discrepancy handling

- **Если preflight count ≠ 12** (Codex считает на своей стороне другое число) — записать актуальное в Discrepancy, продолжать с реальным числом. Это ожидаемо, количество может дрейфовать между измерениями если кто-то правил файлы.
- **Если список affected файлов отличается от whitelist'а** (например, `ruff --fix` хочет тронуть не 8 файлов, а 9) — **стоп**, эскалация. Whitelist — hard constraint.
- **Если `ruff --fix` оставляет нефиксируемые I errors** — **стоп**, Discrepancy с полным output'ом. I rule почти полностью autofixable, если что-то не исправилось — это означает edge case (circular imports, conditional imports) требующий ручного вмешательства.
- **Если import smoke (1.7) падает** — `ruff --fix` что-то сломал, **стоп**, rollback через `git checkout --`, Discrepancy с полным stacktrace.
- **Если `doctor --quick` показывает НОВЫЙ FAIL** (не pre-existing Bug H) — **стоп**, Discrepancy.
- **Если `target-version` ruff не принимает** (например, `py312` стало deprecated в новой версии) — записать актуальное valid values, использовать `py312` если всё ещё supported или эскалация если нет.
- Любое другое отклонение — Discrepancies перед continuation.

## Notes для исполнителя (Codex)

- **Preflight измерения важны**: перед правкой `pyproject.toml` прогони `uv run ruff check --select I scripts/ hooks/` и зафиксируй полный output в 0.2b. Если baseline count не совпадает с планом (12) — это Discrepancy, но не блокер, просто записать.
- **Baseline out-of-scope paths**: **до** правки pyproject.toml — `git diff -- .github/ wiki/ CLAUDE.md AGENTS.md README.md docs/ .gitignore > /tmp/baseline.diff || (python one-liner SHA256)`. После работы — сравнить. Equal = not touched. Urgent lesson из PR 1 — baseline-delta **default** для acceptance в грязном worktree, не option.
- **Порядок действий**:
  1. Pre-flight 0.1-0.5, 0.6 Doc verification
  2. Baseline I count + baseline out-of-scope SHA256
  3. Правка pyproject.toml (Change 1)
  4. Phase 1.1, 1.2 — подтвердить config загрузился
  5. Правка кода через `ruff check --fix` (Change 2)
  6. Phase 1.3-1.9 — весь smoke chain
  7. Path-scoped + baseline-delta acceptance
  8. Self-audit
- **НЕ использовать `--select` вместо `--extend-select`** в config. Read-carefully contracts — это частый ошибочный способ отключить default pyflakes. Тестовый прогон после Change 1: если `ruff check scripts/lint.py` внезапно показывает 0 errors (включая те что были бы pyflakes'ом), значит select используется неправильно.
- **Не лезть в `UP`/`B`/etc**. Scope жёстко ограничен `I`. Если после fix `ruff check scripts/` без `--select` показывает другие diagnostics (pyflakes etc) — это pre-existing, не трогать, записать в Out-of-scope-temptations.
- **Не редактировать файлы руками**. Change 2 — автоматический `ruff --fix`. Если ты видишь что-то "неидеальное" в результате — не править, это стиль ruff, не вкусовщина.
- **WSL uv discipline**: префикс `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy` для всех uv run из WSL.
- **No commit/push**. Финал = заполненный отчёт, review делает пользователь.
- **Personal data sanitize**: hostname → `<host>`, `/home/<user>` → `<linux-home>`, и т.п.
- **Self-audit перед сдачей**: любой ❌ — вернись и доделай.
