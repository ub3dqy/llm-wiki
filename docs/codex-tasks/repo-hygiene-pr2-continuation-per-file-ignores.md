# Plan Continuation — Repo Hygiene PR 2 v2: rollback + per-file-ignores + re-apply

## Context

Этот файл — **continuation** к original plan `docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort.md`. Не новый handoff, не v2 replace — amendment после blocker'а на independent review Claude'а.

**Blocker** (зафиксирован Claude'ом в independent review 2026-04-15):

1. **Destructive ruff behavior**: `ruff --fix --select I` на `hooks/hook_utils.py`, `hooks/pre-compact.py`, `hooks/session-end.py` разбил один multiline `from config import (...)` с inline `# noqa: E402` на несколько отдельных import statement'ов. `# noqa: E402` сохранился только на первом split'е. Результат — **3 новых E402 violation'а** в `hook_utils.py` (и аналогичные в остальных двух файлах), которых до --fix не было.
2. **Scope creep — 4 файла вне whitelist**: реально изменены 12 файлов, план предполагал 8. Extra files: `hooks/pre-compact.py`, `hooks/session-end.py`, `hooks/session-start.py`, `hooks/user-prompt-wiki.py`.
3. **Root cause — flawed preflight regex**: Claude (и Codex, следуя плану) использовал `grep -oE "(scripts|hooks)[/\\][a-zA-Z_]+\.py"` — этот regex не матчит файлы с дефисами. Поэтому файлы с `-` в имени выпали из baseline C и whitelist был составлен неполно.

**Decision**: Option B — per-file-ignores. Это правильный structural fix, потому что hooks намеренно делают `sys.path.insert` **до** imports — это не bug, это deliberate design. Per-file-ignores для `hooks/*.py = ["E402"]` выражает этот intent cleanly и устраняет необходимость inline `# noqa: E402` вообще.

## Иерархия источников правды

Без изменений от original plan. Добавляем только одну ссылку:

- **Ruff per-file-ignores reference** — https://docs.astral.sh/ruff/settings/#lint_per-file-ignores

## Scope

### Что надо сделать

1. **Rollback всех 12 файлов** которые были изменены в первом проходе: `git checkout -- pyproject.toml hooks/hook_utils.py hooks/pre-compact.py hooks/session-end.py hooks/session-start.py hooks/user-prompt-wiki.py hooks/shared_context.py hooks/shared_wiki_search.py scripts/compile.py scripts/doctor.py scripts/lint.py scripts/query.py scripts/wiki_cli.py`
2. **Добавить в `pyproject.toml`** конфигурацию из original plan Change 1 **плюс** новый `per-file-ignores` блок:
   ```toml
   [tool.ruff]
   line-length = 100
   target-version = "py312"

   [tool.ruff.lint]
   extend-select = ["I"]

   [tool.ruff.lint.per-file-ignores]
   "hooks/*.py" = ["E402"]
   ```
3. **Re-run** `uv run ruff check --fix --select I scripts/ hooks/` — с новыми per-file-ignores ruff не должен преследовать E402 semantic preservation, и split destructive behavior не должен повториться.
4. **Empirically** определить новый whitelist: запустить `git status --short -- scripts/ hooks/` **после** re-apply'а и зафиксировать ровно тот список файлов которые реально изменились. Не сравнивать с original-plan whitelist (он был неправильным) — использовать реальный.
5. **Negative acceptance check**: прогнать `uv run ruff check scripts/ hooks/` (**без** `--select`) — должен показывать **zero errors за исключением pre-existing known F401 в hook_utils.py (`utils.parse_frontmatter` unused)**. Этот F401 — baseline, не regression. Любые другие errors — блокер.
6. **Оставить F401 baseline как-is** — в scope этого PR починка pre-existing pyflakes не входит.

### Что НЕ делать

- **Не** fix'ить F401 `utils.parse_frontmatter` unused в `hook_utils.py` — это pre-existing issue, outside scope
- **Не** трогать другие pre-existing warnings (если их много — все в Out-of-scope-temptations)
- **Не** добавлять `UP` / `B` / другие rules — scope всё ещё только I
- **Не** использовать `ruff format` — это PR 4, не сейчас
- **Не** редактировать hook/script файлы вручную — только через `ruff --fix`

## Files to modify (revised whitelist)

**Empirical — определяется re-apply'ом**, не preplanned. Ожидания:

1. **`pyproject.toml`** — tracked, 3 новых секции: `target-version`, `[tool.ruff.lint].extend-select`, `[tool.ruff.lint.per-file-ignores]`
2. **Python files from re-apply** — список зафиксировать в 0.2b baseline C отчёта v2 **после** re-apply, не до

**Ожидаемо**: ruff --fix тронет где-то между 7 и 12 Python files в scripts/ и hooks/. Точный список — зафиксировать empirically.

**Handoff artifacts (не в whitelist)**:
- Existing `docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort-report.md` — **добавить D4/D5 discrepancies + v2 section** вместо создания нового
- Этот continuation plan — reference only

## Verification phases (continuation)

Все с префиксом `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy` из WSL.

### Phase C1 — Rollback state verification

```bash
git checkout -- pyproject.toml hooks/hook_utils.py hooks/pre-compact.py hooks/session-end.py hooks/session-start.py hooks/user-prompt-wiki.py hooks/shared_context.py hooks/shared_wiki_search.py scripts/compile.py scripts/doctor.py scripts/lint.py scripts/query.py scripts/wiki_cli.py
git diff --stat -- scripts/ hooks/ pyproject.toml
```

Ожидание: **пустой** diff для всех 13 файлов. Worktree в этих путях = state c42cccd (PR 1 merged HEAD).

### Phase C2 — Apply pyproject.toml с per-file-ignores

Правка `pyproject.toml` как показано в Scope секции 2. Затем verify:

```bash
uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('target-version:', d['tool']['ruff']['target-version']); print('extend-select:', d['tool']['ruff']['lint']['extend-select']); print('per-file-ignores:', d['tool']['ruff']['lint']['per-file-ignores'])"
```

Ожидание:
```
target-version: py312
extend-select: ['I']
per-file-ignores: {'hooks/*.py': ['E402']}
```

### Phase C3 — Pre-apply baseline (negative acceptance reference)

**Критично**: эта команда запускается **после** pyproject.toml правки, но **до** ruff --fix. Фиксирует snapshot ошибок которые были до массового fix — это reference для C6 negative check.

```bash
uv run ruff check scripts/ hooks/ 2>&1 > /tmp/pre-apply-errors.txt
cat /tmp/pre-apply-errors.txt
wc -l /tmp/pre-apply-errors.txt
```

Сохранить полный output в report v2.

### Phase C4 — Re-apply ruff --fix --select I

```bash
uv run ruff check --fix --select I scripts/ hooks/
```

Ожидание: exit 0. Output показывает N fixed. **Важно**: сравнить этот output с original v1 run — ожидается ЛИБО same count (12 fixed) и ЛИБО меньше (если per-file-ignores предотвратили некоторые split'ы). Больше 12 — Discrepancy.

### Phase C5 — Zero I diagnostics

```bash
uv run ruff check --select I scripts/ hooks/
```

Ожидание: `All checks passed!` или exit 0 без I errors.

### Phase C6 — Negative acceptance: no new non-I errors (CRITICAL)

Это новый check который отсутствовал в v1. Ловит regression'ы типа E402 split'а.

```bash
uv run ruff check scripts/ hooks/ 2>&1 > /tmp/post-apply-errors.txt
diff /tmp/pre-apply-errors.txt /tmp/post-apply-errors.txt
echo "---"
uv run ruff check scripts/ hooks/ 2>&1 | tail -5
```

Ожидание:
- `diff` показывает **уменьшение или равенство** в количестве errors (pre-apply минус I count = post-apply). НЕ увеличение.
- Specifically: **zero new E402 errors**. F401 `utils.parse_frontmatter` — допустимый pre-existing baseline, можно игнорировать.
- Если есть новый E-класс (E4xx, E7xx) или F-класс error — **стоп**, Discrepancy, rollback, эскалация.

### Phase C7 — Empirical whitelist (post-apply git status)

```bash
git status --short -- scripts/ hooks/ pyproject.toml
git diff --stat -- scripts/ hooks/ pyproject.toml
```

Зафиксировать **полный** список изменённых файлов в 0.2b baseline C отчёта v2. Этот список — реальный whitelist PR 2. Если в нём больше 13 файлов или меньше 9 (7 Python + pyproject.toml + 1 зависит от per-file-ignores efficacy) — выделить в Discrepancy для обсуждения.

### Phase C8 — Regression chain как v1 Phase 1.6-1.9

Прогнать ровно те же smokes что в v1:

1. `uv run python -c "import ast; files=[...list from C7...]; [ast.parse(open(f).read()) for f in files]; print('all ok')"` — AST smoke на реальном списке из C7
2. `PYTHONPATH=hooks:scripts uv run python -c "import hook_utils, shared_context, shared_wiki_search; import compile as _c, doctor, lint, query, wiki_cli; print('all imports ok')"`
3. `uv run python scripts/lint.py --structural-only` — exit 0
4. `uv run python scripts/wiki_cli.py doctor --quick` — exit 0, только pre-existing Bug H FAIL

### Phase C9 — Baseline-delta для out-of-scope (как в v1 1.6 последней части)

Проверить что ничего не тронуто вне `scripts/ hooks/ pyproject.toml`:

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', '.github/', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore']
out = subprocess.check_output(cmd)
print(hashlib.sha256(out).hexdigest())
PY
```

Ожидание: SHA256 совпадает с original 0.2b baseline A из v1 report'а (`cb94ab8c24099e65e6b7fe509166bbe93c2eaaf36f87494842f75f5fd20ad93e`).

## Acceptance criteria (continuation)

- ✅ Phase C1: rollback successful, 13 файлов back to baseline
- ✅ Phase C2: pyproject.toml содержит `target-version`, `extend-select = ["I"]`, `per-file-ignores = {"hooks/*.py": ["E402"]}`
- ✅ Phase C3: pre-apply errors snapshot captured
- ✅ Phase C4: `ruff --fix --select I` exit 0, fix count ≤ 12
- ✅ Phase C5: zero I errors post-fix
- ✅ Phase C6 (CRITICAL NEW): **zero new non-I errors** после fix. Specifically zero new E402. F401 baseline — acceptable.
- ✅ Phase C7: empirical whitelist captured, ожидаемо 7-13 Python файлов + pyproject.toml
- ✅ Phase C8: AST + import + lint + doctor smokes все pass
- ✅ Phase C9: out-of-scope SHA256 identical to v1 baseline

## Update the existing report file

**Не создавать** новый report. Вместо этого:

1. Открыть `docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort-report.md`
2. **Добавить** в конец section 7 Discrepancies:
   - **D4**: Destructive `ruff --fix --select I` behavior на `hook_utils.py`/`pre-compact.py`/`session-end.py`. Раздел original multiline `from config import (...)` с inline `# noqa: E402` на multiple split statement'ов, сохраняя `# noqa` только на первом → 3 new E402 errors in hook_utils.py. Resolved in continuation by adding `per-file-ignores = {"hooks/*.py": ["E402"]}` to `[tool.ruff.lint]` which removes the noqa-preservation pressure on ruff's isort reformatting.
   - **D5**: Scope creep — 4 файла вне whitelist (`hooks/pre-compact.py`, `hooks/session-end.py`, `hooks/session-start.py`, `hooks/user-prompt-wiki.py`) были изменены в v1. Root cause: preflight regex `[a-zA-Z_]+\.py` в plan не матчил файлы с дефисами. Resolved in continuation by empirical whitelist derivation (git status after re-apply) вместо preplanned list.
3. **Добавить** новую section `## 9. Continuation v2 — per-file-ignores rollout` с outputs всех C1-C9 phases. Каждый phase — свой block с command + полный stdout + exit code + контрольные точки ✅/❌.
4. **Обновить** section 8 Self-audit checklist — добавить пункты для C1-C9 phases, отметить ✅/❌.
5. **Сменить** frontmatter `status: completed-with-discrepancies` → `status: continuation-v2-in-progress` → после C9 complete → `status: completed`.

## Out of scope (continuation specifically)

- Manual edit любых файлов (ни одного вручную — только ruff --fix)
- Починка pre-existing F401 `utils.parse_frontmatter` unused — это outside scope PR 2
- Добавление UP/B/other rules — scope остаётся I only
- Правка CI gate — PR 3
- Изменения в CLAUDE.md / README.md / docs/ — out of scope

## Rollback (если continuation тоже неудачный)

```bash
git checkout -- pyproject.toml scripts/ hooks/
```

Полный возврат к state c42cccd (PR 1 merged).

## Discrepancy handling

- **Если per-file-ignores синтаксис не работает** в current ruff version — **стоп**, эскалация, прочитать актуальную офдоку ruff/settings про per-file-ignores format
- **Если ruff --fix всё равно делает destructive split** после per-file-ignores — это означает что per-file-ignores не решают проблему на корне. **Стоп**, эскалация, обсудить Option A (manual consolidation) или Option C (per-file `["I"]` exclusion)
- **Если C6 показывает новые non-I errors** — **стоп**, rollback C7, Discrepancy, эскалация
- **Если C7 empirical whitelist содержит больше файлов чем ожидалось** (> 13) — не блокер сам по себе, но записать в Discrepancy для обсуждения с user'ом
- **Если doctor --quick показывает новый FAIL** кроме Bug H — **стоп**, rollback, эскалация

## Notes для исполнителя (Codex)

- **Rollback C1 первым делом**, до любой другой правки. Не пытаться "сохранить" что-то из v1 работы — всё из v1 проблемного. Rollback полный.
- **Per-file-ignores — это TOML dict внутри `[tool.ruff.lint]`**, не отдельная top-level секция. Синтаксис:
  ```toml
  [tool.ruff.lint.per-file-ignores]
  "hooks/*.py" = ["E402"]
  ```
  Это правильно. Не ставить в `[tool.ruff]` или как array.
- **Phase C6 — самый важный check**. Он ловит regression'ы, которые v1 plan пропустил. Не пропускать, даже если "всё выглядит нормально".
- **Empirical whitelist C7 — после fix, не до**. Не пытаться предсказывать какие файлы будут тронуты. Просто прогнать fix, потом записать реальный результат.
- **F401 baseline в hook_utils.py** — игнорировать. Не фиксить. Это scope другого PR.
- **No git commit/push**. Финал — updated report + continuation section в отчёте + user review.
- **Personal data sanitize** как всегда.
- **Self-audit extended** с C1-C9 пунктами перед сдачей.

Compact prompt для user'а — не нужен, пользователь уже в теме continuation, передаёт этот файл Codex'у напрямую.
