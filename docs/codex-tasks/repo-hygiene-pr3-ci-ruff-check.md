# Plan — Repo Hygiene PR 3: add `ruff check --select I` to CI gate

## Иерархия источников правды

1. **Официальная документация** — primary source of truth:
   - GitHub Actions — workflow syntax — https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
   - GitHub Actions — workflow commands and steps — https://docs.github.com/en/actions/using-jobs/setting-default-values-for-jobs
   - Ruff — CLI `check` command — https://docs.astral.sh/ruff/linter/
   - Ruff — exit codes — https://docs.astral.sh/ruff/linter/#exit-codes
   - `astral-sh/setup-uv@v4` — https://github.com/astral-sh/setup-uv
2. **Реальное состояние кода** — secondary:
   - `<repo-root>/.github/workflows/wiki-lint.yml` — текущий CI workflow
   - `<repo-root>/pyproject.toml` — Ruff config с `extend-select = ["I"]` и per-file-ignores (merged в PR 2)
   - Empirical baseline: `ruff check --select I scripts/ hooks/` → `All checks passed!` (2026-04-15 Claude verified after PR 2 merge)
3. **Этот план** — derived, при расхождении с docs/code — приоритет docs/code, Discrepancy.

## Context

PR 3 из 5-PR repo hygiene sequence. Предыдущие: PR 1 (dev deps, merged `c42cccd`), PR 2 (ruff config + I autofix, merged `cb85a28`). Этот PR:

- Добавляет единственный step в `.github/workflows/wiki-lint.yml`: `uv run ruff check --select I scripts/ hooks/`
- **Narrow scope** — только rule `I`, не broad `ruff check`
- Превращает PR 2 runtime verification в **enforced gate**: любой future regression в I rule не сможет попасть в master

### Критический design decision: `--select I` vs broad `ruff check`

**[EMPIRICAL-2026-04-15]** Проверено Claude'ом локально:
- `uv run ruff check --select I scripts/ hooks/` → `All checks passed!` (0 errors)
- `uv run ruff check scripts/ hooks/` (defaults + I) → **15 errors** (pre-existing F401/F841/F541 + 1 E402 в `scripts/doctor.py:35`)

Все 15 — **pre-existing baseline** который существовал до PR 2 и был **deliberately не fix'ен** в PR 2 (outside scope). PR 2 negative acceptance явно подтвердил что эти ошибки не regressed, а baseline.

**Если добавить broad `ruff check scripts/ hooks/` в CI сейчас** — CI **сразу упадёт** на этих 15. Это блокирует merge любого PR (включая сам PR 3).

**Правильный путь — narrow `--select I`**:
1. Матчит точно ту green baseline которую PR 2 установил — CI pass на merge
2. Создаёт реальный gate — future I regression не пройдёт
3. Broadening (fix 15 baseline → broaden CI) — legitimate future work, отдельный PR
4. Не нарушает "do exactly what is asked" rule

**Что это означает для overall hygiene sequence**: PR 3 фиксирует **текущий** уровень coverage (I only). Расширение до full `ruff check` зависит от fix'а 15 pre-existing — это tracked в Out-of-scope секции ниже как deferred follow-up.

## Doc verification (обязательно перечитать ПЕРЕД правкой)

Codex **обязан** открыть эти URL'ы и заполнить `## 0.6 Doc verification` дословными цитатами.

| URL | Что искать |
|---|---|
| https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions | Цитата про `jobs.<id>.steps` structure, `name`, `run` keys |
| https://docs.astral.sh/ruff/linter/ | Цитата про `ruff check --select <rules>` — как работает narrow selection |
| https://docs.astral.sh/ruff/linter/#exit-codes | Цитата про exit codes — 0 success, non-zero на errors, CI fail behaviour |
| https://github.com/astral-sh/setup-uv | Цитата про что `astral-sh/setup-uv@v4` даёт на runner'е — `uv` binary availability for subsequent steps |
| Local: `uv run ruff check --select I scripts/ hooks/` | Подтверждение что actual output = `All checks passed!` на post-PR 2 baseline |

Если расходится — Discrepancy, стоп.

## Mandatory external tools

- **LLM Wiki**: прочитать
  - `wiki/sources/github-actions-docs.md` — GitHub Actions reference
  - `wiki/sources/astral-ruff-docs.md` — Ruff reference  
  - `wiki/sources/yaml-1-2-spec-docs.md` — YAML syntax (workflow файл — YAML)
  - `wiki/analyses/repo-hygiene-findings-2026-04-15.md` — Finding #4 в контексте
- **WebFetch**: все URL из Doc verification
- **MCP git**: snapshot до/после
- **Repo-local docs**: `CLAUDE.md` Gate roles section, `AGENTS.md` WSL discipline
- **Subagent**: не требуется
- **Линтеры**: `actionlint` если доступен (optional sanity), иначе YAML parse через Python `yaml` module

## Contracts which cannot be violated

**[OFFICIAL-github-actions]** Workflow step structure:
```yaml
- name: <human-readable step name>
  run: <shell command>
```
`name` optional but рекомендуется для читаемости. `run` — single command или multi-line через `|`.

**[OFFICIAL-ruff-exit-codes]** `ruff check` exit codes:
- `0` — no violations found (or all were autofixed)
- `1` — violations found
- `2` — linter error (config issue, IO error)

GitHub Actions treats **any non-zero exit** as step failure → job failure → PR status red → merge blocked.

**[OFFICIAL-setup-uv]** `astral-sh/setup-uv@v4` installs `uv` to runner's PATH. После этого action'а любой subsequent step может вызывать `uv run ...`.

**[EMPIRICAL-workflow-current]** Текущий workflow уже имеет:
- `actions/checkout@v4`
- `astral-sh/setup-uv@v4`
- `uv sync` (dependencies install)
- `uv run python scripts/rebuild_index.py --check`
- `uv run python scripts/lint.py --structural-only`
- Inline Python AST syntax check

**[PROJECT]** Repo policy: CI gate — deterministic, blocking. Advisory checks (lint --full) отдельны.

## Files to modify (whitelist)

**Strict whitelist — ровно 1 tracked file**:

1. **`.github/workflows/wiki-lint.yml`** — добавить один step `Ruff check (I rule)` между существующим `Run structural lint` и `Syntax check all Python files`

**Handoff artifacts (не в whitelist по определению)**:
- `docs/codex-tasks/repo-hygiene-pr3-ci-ruff-check-report.md` — report template

**НЕ трогать** (out of scope):
- `pyproject.toml` — Ruff config finalized в PR 2, не менять
- Python файлы в `scripts/` и `hooks/` — любой fix baseline errors это future PR
- Другие workflow'ы (`personal-data-check.yml` и т.д.) — scope narrow
- `CLAUDE.md` документация — опционально в отдельном docs PR

Видишь что-то рядом — Out-of-scope-temptations.

## Change 1 — insert Ruff check step в `.github/workflows/wiki-lint.yml`

### Где
`<repo-root>/.github/workflows/wiki-lint.yml`, между существующими steps `Run structural lint` и `Syntax check all Python files`.

### Текущее состояние (relevant portion)

```yaml
      - name: Run structural lint
        run: uv run python scripts/lint.py --structural-only

      - name: Syntax check all Python files
        run: |
          uv run python -c "
          ...
          "
```

### Что добавить

Один новый step between them:

```yaml
      - name: Run structural lint
        run: uv run python scripts/lint.py --structural-only

      - name: Ruff check (I rule)
        run: uv run ruff check --select I scripts/ hooks/

      - name: Syntax check all Python files
        run: |
          uv run python -c "
          ...
          "
```

### Точный diff expectation

```diff
@@ .github/workflows/wiki-lint.yml @@
       - name: Run structural lint
         run: uv run python scripts/lint.py --structural-only
 
+      - name: Ruff check (I rule)
+        run: uv run ruff check --select I scripts/ hooks/
+
       - name: Syntax check all Python files
         run: |
```

### Acceptance criteria Change 1

- [ ] Новый step добавлен **после** `Run structural lint` и **перед** `Syntax check all Python files`
- [ ] Step name ровно `Ruff check (I rule)` (консистентно с существующими step names)
- [ ] Command ровно `uv run ruff check --select I scripts/ hooks/` — без `--fix`, без других flag'ов, без broad `ruff check`
- [ ] YAML indentation consistent с существующими steps (6 spaces перед `-`, 8 spaces перед `name`/`run`)
- [ ] Никаких других изменений в workflow file (триггеры, job setup, existing steps — без правок)

## Verification phases

### Phase 1 — Unit smoke (Codex выполняет сам)

Все команды из repo root. Ubuntu/WSL окружение.

**1.1** YAML valid после правки:

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/wiki-lint.yml'))" && echo "YAML ok"
```

Ожидание: `YAML ok`, exit 0. Если parse error — indentation нарушена.

**1.2** Workflow structure preserved — dict keys intact:

```bash
uv run python -c "
import yaml
wf = yaml.safe_load(open('.github/workflows/wiki-lint.yml'))
assert wf['name'] == 'Wiki Lint', 'workflow name changed'
assert 'lint' in wf['jobs'], 'job lint missing'
steps = wf['jobs']['lint']['steps']
names = [s.get('name') or s.get('uses') for s in steps]
print('steps:', names)
assert 'Ruff check (I rule)' in names, 'new step missing'
assert 'Run structural lint' in names, 'structural lint step missing (regression)'
assert 'Syntax check all Python files' in names, 'syntax check step missing (regression)'
print('structure ok')
"
```

Ожидание: печатает список steps с `Ruff check (I rule)` между `Run structural lint` и `Syntax check all Python files`, затем `structure ok`.

**1.3** Step ordering verified — new step между specific neighbours:

```bash
uv run python -c "
import yaml
wf = yaml.safe_load(open('.github/workflows/wiki-lint.yml'))
names = [s.get('name') or s.get('uses') for s in wf['jobs']['lint']['steps']]
idx_struct = names.index('Run structural lint')
idx_ruff = names.index('Ruff check (I rule)')
idx_syntax = names.index('Syntax check all Python files')
assert idx_struct < idx_ruff < idx_syntax, f'ordering wrong: struct={idx_struct} ruff={idx_ruff} syntax={idx_syntax}'
print('ordering ok')
"
```

Ожидание: `ordering ok`, exit 0.

**1.4** Local equivalent of new step (precisely the command CI will run):

```bash
uv run ruff check --select I scripts/ hooks/
```

Ожидание: `All checks passed!`, exit 0. Это тот самый command что CI будет запускать.

**1.5** Что broad `ruff check` всё ещё показывает baseline (документирует что мы **deliberately** не gate'им его):

```bash
uv run ruff check scripts/ hooks/ --output-format=concise 2>&1 | tail -3
```

Ожидание: `Found 15 errors.` — тот же baseline что был после PR 2. Этот шаг **не gate**, просто фиксирует что broadening отложено.

**1.6** `actionlint` (optional если installed):

```bash
command -v actionlint && actionlint .github/workflows/wiki-lint.yml || echo "actionlint not available, skipped"
```

Ожидание: либо `actionlint not available`, либо clean output без errors.

**1.7** Pre-existing regression chain (должно всё ещё работать):

```bash
uv run python scripts/lint.py --structural-only
uv run python scripts/wiki_cli.py doctor --quick
```

Ожидание: оба exit 0 с baseline stat'ом (только pre-existing Bug H FAIL в doctor). Workflow не зависит от этих команд, но sanity что ничего не сломано случайно.

### Phase 2 — CI actual run `[awaits user + PR push]`

Это основная verification — реальный workflow run на GitHub после push branch'а.

**2.1** Push branch + open PR

**2.2** GitHub Actions trigger `Wiki Lint / lint` workflow. Ожидание:
- Job `lint` runs
- **Все steps pass** — в том числе новый `Ruff check (I rule)` с `All checks passed!`
- Job status green
- PR merge gate clears

**2.3** Visual check на GitHub PR status: зелёная галочка напротив `Wiki Lint / lint`

**2.4** `[awaits user — merge decision]`

### Phase 3 — Statistical

Не применимо. Effect — gate активен с момента merge. Future PR test'ит реально через собственные CI run'ы.

## Acceptance criteria

- ✅ Phase 1.1: YAML parse ok
- ✅ Phase 1.2: workflow structure preserved, new step present
- ✅ Phase 1.3: new step correctly positioned between structural lint и syntax check
- ✅ Phase 1.4: local `uv run ruff check --select I scripts/ hooks/` → `All checks passed!`
- ✅ Phase 1.5: broad `ruff check` shows same 15 pre-existing baseline (documents что не gate'им)
- ✅ Phase 1.6: actionlint clean or unavailable
- ✅ Phase 1.7: existing regression chain не regressed
- ✅ **Whitespace-insensitive content diff** (PRIMARY): `git diff -w -- .github/workflows/wiki-lint.yml` показывает **только 3 meaningful новые строки** (step name + command + blank line separator). Использовать `-w` вместо plain diff потому что target файл может иметь CRLF/LF line-ending churn в baseline — это known pervasive issue в репо, не блокер, и `-w` корректно изолирует semantic content changes. Perfect equivalent: `diff --ignore-all-space`.
- ✅ **Raw diff sanity (advisory, не block)**: `git diff -- .github/workflows/wiki-lint.yml` может содержать существенно больше строк из-за CRLF/LF churn. Это ожидаемо и НЕ блокер. Raw diff фиксируется в отчёт для transparency.
- ✅ **Baseline-delta for untouched paths**: `git diff -- scripts/ hooks/ pyproject.toml wiki/ CLAUDE.md AGENTS.md README.md docs/ .gitignore` SHA256 совпадает с pre-task baseline из 0.2b
- ✅ Pre-existing worktree dirt в out-of-scope paths — baseline, не trogaem

## Out of scope (deferred to future PRs)

1. **Broad `ruff check scripts/ hooks/`** в CI — требует fix'а 15 pre-existing baseline (F401/F841/F541/E402). Separate future PR, не в этой sequence как committed milestone.
2. **`ruff format --check`** в CI — PR 5 (после PR 4 format commit)
3. **Fix pre-existing 15 non-I errors** — отдельный future PR. Может быть разбит на несколько (F401 unused imports, F841 unused locals, F541 f-string, E402 scripts/doctor.py line 35)
4. **`actionlint` как gate** — могли бы добавить, но scope jump
5. **CI badge в README** — docs update, отдельно
6. **`UP` / `B` / других Ruff categories** в CI — depends on broadening, future
7. **Trigger workflow на `pull_request` changes в `.github/workflows/**`** — current workflow не triggers на changes в self, optional improvement
8. **Update CLAUDE.md** с новым CI step — docs update, отдельно

Видишь что-то — Out-of-scope-temptations.

## Rollback

```bash
git checkout -- .github/workflows/wiki-lint.yml
```

Чистый rollback одного файла. Никаких commit'ов до полной верификации Phase 1.

## Discrepancy handling

- **Если YAML parse падает** — indentation нарушена, **стоп**, fix indentation перед continuation
- **Если Phase 1.4 показывает non-zero errors** — значит `ruff check --select I scripts/ hooks/` не clean. Это было clean 2026-04-15 Claude'ом и merge PR 2. Если теперь не clean — что-то изменилось, **стоп**, эскалация.
- **Если Phase 1.5 показывает другое число** (не 15) — baseline drift, записать актуальное число, продолжать. Не блокер для PR 3 (narrow gate стабилен независимо от broad count).
- **Если workflow file содержит unexpected sections** (другие triggers, jobs) — проверить что вносим изменение только в `jobs.lint.steps`, не в другие места. Если нет — стоп.
- Любое другое отклонение — Discrepancies перед continuation.

## Notes для исполнителя (Codex)

- **Задача очень маленькая** — буквально 3 новых строк в 1 YAML файл. Это НЕ освобождает от полного Doc verification + Tools used + Self-audit. Incident 2026-04-14/15 показал что "малая задача" — соблазн пропустить структуру = correction wave.
- **Narrow `--select I`, НЕ broad `ruff check`**. Это осознанный выбор — см. "Critical design decision" секцию в Context. Если broaden'ишь — CI сразу упадёт на 15 pre-existing. 
- **CRLF/LF line-ending churn в `.github/workflows/wiki-lint.yml` — known issue** в этом репо (Windows/WSL filesystem boundary). Если `git status` показывает файл как `M` ДО твоей правки — это именно line-ending drift, **не** блокер. Acceptance использует `git diff -w` (whitespace-insensitive), который изолирует content changes от line-ending noise. НЕ пытаться "clean up" CRLF отдельно — out of scope, это global repo issue.
- **Не добавлять `--fix`** — CI не должен autofix'ить, он должен **fail** на нарушениях. PR author сам fix'ит локально и push'ит.
- **Не трогать другие steps** — `Run structural lint`, `Syntax check`, checkout, setup-uv, install — все как есть.
- **Step name ровно `Ruff check (I rule)`** — explicit про narrow scope. Когда broaden'ят в future — переименуют в `Ruff check`.
- **Placement — между structural lint и syntax check**, не в начало и не в конец. Это логическая группировка: сначала структурный wiki lint, потом python code lint, потом AST syntax sanity.
- **Phase 2 — GitHub Actions real run** — это основная acceptance. Codex не может его запустить локально, только после push PR (который делает user). В отчёте помечать `[awaits user + PR push]`.
- **Personal data sanitize**: hostname → `<host>` etc. как всегда.
- **No git commit/push**. Финал = заполненный отчёт + Claude review + user merge decision.
- **Self-audit в конце**. Любой ❌ — вернись и доделай.
