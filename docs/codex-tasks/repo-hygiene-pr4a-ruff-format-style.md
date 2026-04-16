# Plan — Repo Hygiene PR 4a: `ruff format` style-only commit

## Иерархия источников правды

1. **Официальная документация** — primary:
   - Ruff — formatter — https://docs.astral.sh/ruff/formatter/
   - Ruff — format CLI — https://docs.astral.sh/ruff/formatter/#ruff-format
   - GitHub docs — `.git-blame-ignore-revs` — https://docs.github.com/en/repositories/working-with-files/using-files/viewing-a-file#ignore-commits-in-the-blame-view
   - Git docs — `blame.ignoreRevsFile` — https://git-scm.com/docs/git-blame#_the_ignore_revs_file
2. **Реальное состояние кода** — secondary:
   - 25 Python файлов в `scripts/` и `hooks/` (including subdirs)
   - 24 из них требуют formatting per `ruff format --check`
   - 1 уже clean: `scripts/runtime_utils.py`
   - `pyproject.toml` `[tool.ruff]` config из PR 2 (target-version="py312", extend-select=["I"], per-file-ignores для 3 hook'ов)
3. **Этот план** — derived. Расхождения → Discrepancy.

## Context

PR 4a из 5-PR repo hygiene sequence. Предыдущие:
- PR 1 (`#33`) — dev deps (ruff + pytest)
- PR 2 (`#34`) — ruff config + I autofix
- PR 3 (`#35`) — ruff I-rule CI gate

**Этот PR**:
- Применяет `uv run ruff format scripts/ hooks/` к 24 .py файлам
- **Style-only** — zero semantic changes, только PEP 8 whitespace/blank-line/slice-spacing
- Commit message начинается с `style:` (не `feat:`, не `chore:`) — explicit сигнал что это pure formatting

**После merge PR 4a** — отдельная задача PR 4b добавит `.git-blame-ignore-revs` с SHA post-squash commit'а PR 4a. Это invariant standard workflow: blame-ignore-revs файл references SHA который становится known только после merge.

### Why two PRs, не single

Squash-merge меняет commit SHA в master относительно того что был в feature branch. Если делать `.git-blame-ignore-revs` в том же branch, файл будет reference SHA branch-commit'а, а после squash-merge этот SHA не существует в master. Значит blame-ignore не сработает.

**Правильный flow**:
1. PR 4a merged → master получает squash commit SHA X
2. PR 4b создаёт `.git-blame-ignore-revs` с содержимым `X` → merged
3. `git blame --ignore-revs-file .git-blame-ignore-revs` (и GitHub UI автоматически) пропускает SHA X

## Preflight measurements (by Claude 2026-04-15)

**[EMPIRICAL]** Запущено локально:

```bash
uv run ruff format --check scripts/ hooks/
```

Результат: `24 files would be reformatted, 1 file already formatted`.

**Files which would be reformatted** (24):
- `scripts/compile.py`, `scripts/config.py`, `scripts/doctor.py`, `scripts/flush.py`, `scripts/lint.py`, `scripts/query.py`, `scripts/rebuild_index.py`, `scripts/seed.py`, `scripts/setup.py`, `scripts/utils.py`, `scripts/wiki_cli.py`
- `hooks/hook_utils.py`, `hooks/post-tool-capture.py`, `hooks/pre-compact.py`, `hooks/session-end.py`, `hooks/session-start.py`, `hooks/shared_context.py`, `hooks/shared_wiki_search.py`, `hooks/stop-wiki-reminder.py`, `hooks/user-prompt-wiki.py`
- `hooks/codex/post-tool-capture.py`, `hooks/codex/session-start.py`, `hooks/codex/stop.py`, `hooks/codex/user-prompt-wiki.py`

**Already clean** (1): `scripts/runtime_utils.py`

**Diff size**: approximately 1178 lines (with context) = ~400-500 actual change lines. Большой, но cosmetic.

**Character of changes**: spot-checked на ранее проблемных `hook_utils.py`, `pre-compact.py`, `session-end.py`:
- Добавление blank line после module docstring перед `from __future__ import annotations`
- Slice spacing: `context[boundary + 1:]` → `context[boundary + 1 :]`
- Другие PEP 8 whitespace tweaks

**Critical**: **no destructive multiline import splits** — unlike PR 2 v1 `ruff check --fix --select I` behavior. `ruff format` применяет только whitespace-level PEP 8 rules, не reorganize'ит imports semantically. 3 hook'а с `sys.path.insert`-then-import паттерном получают clean formatting без split'а.

## Doc verification (обязательно перечитать ПЕРЕД правкой)

Codex **обязан** заполнить `## 0.6 Doc verification` дословными цитатами.

| URL | Что искать |
|---|---|
| https://docs.astral.sh/ruff/formatter/ | Цитата про что `ruff format` делает — Black-compatible, whitespace, blank lines, docstring formatting |
| https://docs.astral.sh/ruff/formatter/#black-compatibility | Что format — cosmetic, не semantic |
| https://docs.astral.sh/ruff/formatter/ | `ruff format <path>` — modifies files in place; `ruff format --check` — non-modifying exit codes |
| https://docs.astral.sh/ruff/settings/ (`format`) | Настройки `[tool.ruff.format]` — что их нет в pyproject.toml этого репо (defaults), Black-compatible defaults |
| Local: `uv run ruff format --check scripts/ hooks/` | Подтверждение 24/1 baseline |

Если расходится с планом — Discrepancy, стоп.

## Mandatory external tools

- **Wiki**: `wiki/sources/astral-ruff-docs.md`, `wiki/sources/python-pep8-pep257-docs.md`, `wiki/analyses/repo-hygiene-findings-2026-04-15.md`
- **WebFetch**: 4 URL из Doc verification
- **Local ruff**: version check + baseline measurements
- **MCP git**: snapshots
- **Repo-local**: `CLAUDE.md`, `AGENTS.md`, pyproject.toml `[tool.ruff]` reference
- **Subagent**: не требуется

## Contracts which cannot be violated

**[OFFICIAL-ruff-format]** `ruff format` — это drop-in Black-compatible formatter. Без `[tool.ruff.format]` section в pyproject.toml — использует defaults (line-length из `[tool.ruff]`, quote-style double, indent-style space).

**[OFFICIAL-ruff-semantic]** `ruff format` **не меняет semantics** кода — только whitespace, blank lines, line wrapping, string quote normalization, trailing commas. AST эквивалентен pre-format AST.

**[EMPIRICAL-pyproject.toml]** Текущий `[tool.ruff]` (post-PR 2 state):
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = ["I"]

[tool.ruff.lint.per-file-ignores]
"hooks/hook_utils.py" = ["I"]
"hooks/pre-compact.py" = ["I"]
"hooks/session-end.py" = ["I"]
```

**Важно**: `per-file-ignores` живёт в `[tool.ruff.lint]`, **не влияет** на `ruff format`. `format` — отдельная подкоманда со своей независимой config surface `[tool.ruff.format]` (которая у нас пустая = defaults).

**[PROJECT]** Commit message convention — этот PR **должен** начинаться с `style:` (не `feat:`, не `chore:`). Convention сигналит future readers что это pure formatting, без semantic изменений.

## Files to modify (whitelist)

**Strict whitelist** — 24 production файла:

Все .py файлы в `scripts/` и `hooks/` (recursive) **кроме** `scripts/runtime_utils.py` (уже clean).

Точный список — см. Preflight measurements выше.

**Handoff artifact (не в whitelist)**:
- `docs/codex-tasks/repo-hygiene-pr4a-ruff-format-style-report.md`

**НЕ трогать**:
- `scripts/runtime_utils.py` — уже formatted, не должен быть в diff (sanity check: если ruff format его тронет — Discrepancy)
- `pyproject.toml` — не трогаем, format конфиг используется default
- `.github/workflows/*` — не трогаем
- `wiki/`, `docs/`, CLAUDE.md, AGENTS.md, README.md — не трогаем
- `.git-blame-ignore-revs` — **это PR 4b**, не сейчас. Не создавать этот файл в PR 4a.
- Python файлы вне `scripts/` и `hooks/` (например `tests/` если когда-то появится) — not in scope

## Change 1 — apply `ruff format` to scripts/ hooks/

### Команда

```bash
uv run ruff format scripts/ hooks/
```

### Ожидаемый output

```
24 files reformatted, 1 file left unchanged
```

### Acceptance criteria для Change 1

- [ ] Команда завершилась exit 0
- [ ] Output показывает `24 files reformatted, 1 file left unchanged` (или идентичное если baseline drift'нул)
- [ ] `scripts/runtime_utils.py` **не** в списке modified files
- [ ] **Zero semantic changes**: `git diff --stat` показывает только .py файлы, ни одного другого tracked file
- [ ] Ни одного **нового** файла в diff (format не создаёт файлы)

## Verification phases

Все с префиксом `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy` из WSL.

### Phase 1 — Unit smoke

**1.1** Post-format check — нулевые diagnostics:

```bash
uv run ruff format --check scripts/ hooks/
```

Ожидание: `25 files already formatted` (exit 0). Если осталось "Would reformat" — ruff format не сошёлся за один проход (очень редкий случай), Discrepancy.

**1.2** Post-format I rule clean (PR 2/3 invariant):

```bash
uv run ruff format --check scripts/ hooks/
uv run ruff check --select I scripts/ hooks/
```

Ожидание: оба exit 0. I rule продолжает проходить (format обычно I-compatible).

**1.3** Negative acceptance — non-I baseline unchanged:

```bash
uv run ruff check scripts/ hooks/ --output-format=concise 2>&1 | tail -5
```

Ожидание: **15 errors** (тот же baseline что после PR 2). F401/F841/F541/E402 counts unchanged. Если больше 15 — format создал new non-I issue, Discrepancy. Если меньше 15 — format случайно fixed что-то, это OK но Discrepancy для записи.

**1.4** AST sanity на всех 24 reformatted файлах:

```bash
uv run python -c "
import ast
files = [
    'scripts/compile.py', 'scripts/config.py', 'scripts/doctor.py',
    'scripts/flush.py', 'scripts/lint.py', 'scripts/query.py',
    'scripts/rebuild_index.py', 'scripts/seed.py', 'scripts/setup.py',
    'scripts/utils.py', 'scripts/wiki_cli.py',
    'hooks/hook_utils.py', 'hooks/post-tool-capture.py',
    'hooks/pre-compact.py', 'hooks/session-end.py',
    'hooks/session-start.py', 'hooks/shared_context.py',
    'hooks/shared_wiki_search.py', 'hooks/stop-wiki-reminder.py',
    'hooks/user-prompt-wiki.py',
    'hooks/codex/post-tool-capture.py', 'hooks/codex/session-start.py',
    'hooks/codex/stop.py', 'hooks/codex/user-prompt-wiki.py',
]
for f in files:
    ast.parse(open(f).read())
print(f'all {len(files)} files parse ok')
"
```

Ожидание: `all 24 files parse ok`, exit 0.

**1.5** Import smoke — все модули импортируются после format'а:

```bash
PYTHONPATH=hooks:scripts uv run python -c "
import hook_utils, shared_context, shared_wiki_search
import compile as _c, config, doctor, flush, lint, query
import rebuild_index, seed, utils, wiki_cli
print('all imports ok')
"
```

Ожидание: `all imports ok`, exit 0. (hooks/codex/* — отдельные hook entry points, не импортируются как modules; setup.py может не импортироваться, skip если так)

**1.6** `lint.py --structural-only` не regressed:

```bash
uv run python scripts/lint.py --structural-only
```

Ожидание: exit 0, тот же check set что до формата.

**1.7** `doctor --quick` не regressed:

```bash
uv run python scripts/wiki_cli.py doctor --quick
```

Ожидание: exit 0, только pre-existing Bug H FAIL.

**1.8** Path-scoped + baseline-delta + CRLF-aware diff:

```bash
git diff -w --stat -- scripts/ hooks/
git status --short -- scripts/ hooks/
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', '.github/', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore', 'pyproject.toml']
out = subprocess.check_output(cmd)
print('out-of-scope sha256:', hashlib.sha256(out).hexdigest())
PY
```

Ожидание:
- `git diff -w --stat` показывает ~24 файла в scripts/ + hooks/ с небольшим числом change lines на каждый
- `git status` показывает ровно 24 modified .py файла
- Out-of-scope SHA256 совпадает с baseline из 0.2b

### Phase 2 — Integration `[awaits user + PR push]`

**2.1** PR push → CI runs `Wiki Lint / lint` workflow. Включая новый `Ruff check (I rule)` step из PR 3.

**2.2** Ожидание: **все steps pass** — в particular, новый I-rule step должен пройти (мы verified локально что I всё ещё clean).

**2.3** `[awaits user — merge decision]`

### Phase 3 — Statistical

Не применимо. Effect измеряется непосредственно: 24 файла теперь PEP 8 clean.

## Acceptance criteria

- ✅ Change 1: `ruff format` applied, 24 files reformatted, 1 unchanged
- ✅ Phase 1.1: post-format check → all files already formatted
- ✅ Phase 1.2: I rule still clean
- ✅ **Phase 1.3 (CRITICAL)**: non-I baseline = 15 errors exactly, zero regressions
- ✅ Phase 1.4: all 24 files parse as valid AST
- ✅ Phase 1.5: all modules import
- ✅ Phase 1.6: `lint --structural-only` exit 0
- ✅ Phase 1.7: `doctor --quick` exit 0 с только pre-existing Bug H
- ✅ **Path-scoped diff**: scripts/ hooks/ modifications only, ни одного other production file
- ✅ **Baseline-delta**: out-of-scope SHA256 unchanged
- ✅ `scripts/runtime_utils.py` **не** в diff (он уже был formatted, должен остаться unchanged)
- ✅ Commit message convention: ПОЛЬЗОВАТЕЛЬ commit'нёт с `style:` prefix (handoff только готовит файлы, не commit'ит)

## Out of scope (PR 4b и дальше)

1. **`.git-blame-ignore-revs`** — PR 4b, отдельный handoff после merge PR 4a. **НЕ создавать в этом PR**.
2. **`ruff format --check` в CI** — PR 5 (после PR 4b)
3. **Fix 15 pre-existing non-I errors** — отдельный future PR
4. **Расширение rule set** (UP, B) — future PR
5. **Format других Python файлов** (setup scripts, tests если будут) — current scope = `scripts/` + `hooks/`
6. **Update CLAUDE.md / README.md** про format usage — docs PR
7. **pre-commit config** — после PR 5 если будет

## Rollback

```bash
git checkout -- scripts/ hooks/
```

Никаких commit'ов до полной верификации Phase 1.

## Discrepancy handling

- **Format count ≠ 24** — baseline drift. Записать actual count, продолжать.
- **`runtime_utils.py` оказался в diff** — что-то изменилось в нём между preflight и execution. Discrepancy, записать diff, решать включать или excluding.
- **Phase 1.3 shows ≠ 15 errors**:
  - **> 15**: format создал new issue. **Стоп**, rollback, Discrepancy с описанием какой новый error.
  - **< 15**: format случайно fix'ил что-то (e.g. F541 empty f-string). Это OK, но Discrepancy для записи.
- **AST parse fail** — format что-то сломал (очень редко). **Стоп**, rollback, bug report to Ruff upstream.
- **Import smoke fail** — такая же редкая проблема. **Стоп**, rollback.
- **`doctor --quick` new FAIL** — **стоп**, rollback, Discrepancy.
- **Out-of-scope SHA256 changed** — что-то тронулось вне whitelist. **Стоп**, эскалация.

## Notes для исполнителя (Codex)

- **Commit message должен быть `style:`**, не `feat:`/`chore:`. Это сигнал future readers + инструмент для `git blame` filtering когда PR 4b добавит blame-ignore-revs.
- **Phase 1.3 негативная acceptance — КРИТИЧНА**. Baseline = 15 pre-existing errors. Любое отклонение — Discrepancy. Особенно: format не должен create **новых** F401/F841/F541/E402 или других Ruff default errors.
- **`runtime_utils.py` — expected NOT в diff**. Преflight showed оно already formatted. Sanity check в 1.8 diff --stat — если появился — Discrepancy.
- **24 файла — много**, но **все cosmetic**. Не смотри на каждую строку diff'а глазами, доверься `ruff format` + AST + import + CI. Spot check на 3 проблемных hook'а (hook_utils, pre-compact, session-end) уже сделан Claude'ом preflight — чистый format без destructive splits.
- **НЕ редактируй файлы вручную**. Только через `ruff format`. Если какой-то файл выглядит "криво" после format'а — это style Ruff, не вкусовщина.
- **Path-scoped + baseline-delta + git diff -w** как acceptance (lessons из PR 2/3). Line-ending churn в touched files — expected, use `-w` для meaningful diff.
- **`.git-blame-ignore-revs` НЕ создавать в этом PR**. Это PR 4b после merge 4a.
- **No git commit/push**. Финал = заполненный отчёт, user делает commit/push/PR.
- **Personal data sanitize**.
- **Self-audit** перед сдачей.

Compact prompt для user'а — после того как этот plan + report template готовы, user даст отдельно Codex'у.
