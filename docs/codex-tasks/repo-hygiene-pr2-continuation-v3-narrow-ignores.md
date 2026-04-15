# Plan Continuation v3 — Repo Hygiene PR 2: narrow per-file-ignores for `["I"]`

## Context

Этот файл — **continuation v3** после того как v2 (per-file-ignores `E402`) не сошёлся. v2 reasoning был: "если убрать E402 pressure, ruff --fix перестанет split'ить imports и clean-up'ит". Эксперимент показал: `per-file-ignores "hooks/*.py" = ["E402"]` **не** решил проблему — `ruff --fix --select I` оставил **11 remaining I001** ошибок, и это после того как C6 negative check подтвердил отсутствие new non-I regressions.

**Root cause** (установлен Claude'ом экспериментально 2026-04-15):

Шесть hook'ов (`hook_utils.py`, `post-tool-capture.py`, `pre-compact.py`, `session-end.py`, `shared_context.py`, `shared_wiki_search.py`) имеют паттерн:

```python
import <stdlib>
...
sys.path.insert(0, ...)

from config import ...  # noqa: E402
from utils import ...  # noqa: E402
```

Это **два раздельных import блока** с runtime code между ними. Isort'овское понимание — "все imports в одном блоке в начале файла". Runtime `sys.path.insert` посередине создаёт **фундаментальный conflict** с isort invariant'ом. Ruff пытается решить через различные reformatting strategies — все из них либо destructive (v1 split), либо неудачно (v2 still-unsorted).

**Три файла** где v1 дал **destructive split** (создание новых E402): `hook_utils.py`, `pre-compact.py`, `session-end.py`. Это те hooks у которых `from config import (...)` — **multiline с `as` aliases** внутри первого post-sys.path блока. Это конкретная комбинация (multiline + aliases + inline noqa) триггерит destructive behavior.

**Остальные 3 hook'а** с sys.path.insert паттерном (`post-tool-capture.py`, `shared_context.py`, `shared_wiki_search.py`) используют **single-line imports** после sys.path insert — ruff handle'ит их cleanly (просто убирает blank lines между).

## Decision (experimentally verified by Claude)

**Option C с narrow per-file-ignores на `["I"]` для 3 файлов с destructive split pattern**:

```toml
[tool.ruff.lint.per-file-ignores]
"hooks/hook_utils.py" = ["I"]
"hooks/pre-compact.py" = ["I"]
"hooks/session-end.py" = ["I"]
```

**Verified locally** by Claude 2026-04-15 (experimental, rolled back before this handoff):
- `uv run ruff check --fix --select I scripts/ hooks/` → `Found 9 errors (9 fixed, 0 remaining)` — cleanly succeeds
- `uv run ruff check --select I scripts/ hooks/` → `All checks passed!` — zero I errors
- `uv run ruff check scripts/ hooks/` → 15 errors pre-apply, 15 errors post-apply (only column drift из-за import sort) — zero new regressions
- **Zero new E402** — `scripts/doctor.py:35:1 E402` который есть в baseline post-apply — это **pre-existing**, не created by fix

**Почему именно `["I"]` для 3 файлов, а не другие варианты**:
- `["E402"]` (v2) — недостаточно, ruff всё равно не мог consolidate multiline с aliases + inline noqa
- `["I"]` для всех `hooks/*.py` — overkill, теряем valid I coverage на post-tool-capture, shared_context, shared_wiki_search, session-start, user-prompt-wiki (те hooks могут получить legit I fix)
- `["I"]` narrow на 3 файла — минимальное исключение, сохраняет coverage где возможна, tech debt минимизирован

## Tech debt acknowledgment

3 исключённых файла (`hook_utils.py`, `pre-compact.py`, `session-end.py`) не имеют I coverage. Это **осознанный design trade-off**, не hidden bug:
- Причина: intentional `sys.path.insert` паттерн несовместим с isort invariant'ом
- Альтернатива: рефакторить эти файлы чтобы не нужен был runtime `sys.path.insert` (например, через package layout + `[project.scripts]` entry point). Это **Finding #2 из analyses/repo-hygiene-findings-2026-04-15.md**, который мы уже решили отложить indefinitely.
- Когда Finding #2 будет выполнен (если будет) — эти per-file-ignores можно снять, файлы получат I coverage

## Scope

### Что надо сделать

1. **Rollback** любых worktree changes в scripts/ hooks/ pyproject.toml (если уже были)
2. **Apply pyproject.toml** с:
   - `target-version = "py312"` в `[tool.ruff]`
   - `[tool.ruff.lint]` с `extend-select = ["I"]`
   - `[tool.ruff.lint.per-file-ignores]` с 3 narrow entries
3. **Run** `uv run ruff check --fix --select I scripts/ hooks/` — ожидается ровно **9 fixed, 0 remaining**
4. **Verify zero** — `uv run ruff check --select I scripts/ hooks/` → `All checks passed!`
5. **Negative acceptance** — `uv run ruff check scripts/ hooks/` exit 1 с **exactly 15 errors** (baseline). Не больше, не меньше.
6. **Empirical whitelist** — `git status --short -- pyproject.toml scripts/ hooks/` → ожидается **10 файлов** (pyproject + 9 affected .py files)

### Ожидаемый affected files list (9 Python files)

На основе Claude experimental run:

1. `hooks/session-start.py`
2. `hooks/user-prompt-wiki.py`
3. `hooks/shared_context.py`
4. `hooks/shared_wiki_search.py`
5. `scripts/compile.py`
6. `scripts/doctor.py`
7. `scripts/lint.py`
8. `scripts/query.py`
9. `scripts/wiki_cli.py`

**Исключены** через per-file-ignores (не тронуты): `hooks/hook_utils.py`, `hooks/pre-compact.py`, `hooks/session-end.py`

Если Codex получает другой список — Discrepancy, но не блокер (zero new errors + zero I remaining — главные critera).

## Verification phases (v3)

Все команды с `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy` из WSL.

### Phase V3.1 — Rollback state verification

```bash
git checkout -- pyproject.toml scripts/ hooks/
git status --short -- pyproject.toml scripts/ hooks/
```

Ожидание: пустой output (worktree clean в этих путях).

### Phase V3.2 — Pre-apply baseline snapshot

```bash
uv run ruff check scripts/ hooks/ --output-format=concise > /tmp/pre-apply-baseline.txt 2>&1 || true
cat /tmp/pre-apply-baseline.txt
wc -l /tmp/pre-apply-baseline.txt
```

Ожидание: 15 errors зафиксированы (если sandbox не даёт `/tmp`, использовать Python one-liner как в v2).

### Phase V3.3 — Apply pyproject.toml v3 config

Правка `pyproject.toml`:

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

Verify:

```bash
uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('target:', d['tool']['ruff']['target-version']); print('select:', d['tool']['ruff']['lint']['extend-select']); print('per-file:', d['tool']['ruff']['lint']['per-file-ignores'])"
```

Ожидание:
```
target: py312
select: ['I']
per-file: {'hooks/hook_utils.py': ['I'], 'hooks/pre-compact.py': ['I'], 'hooks/session-end.py': ['I']}
```

### Phase V3.4 — Apply ruff --fix --select I

```bash
uv run ruff check --fix --select I scripts/ hooks/
```

Ожидание: **`Found 9 errors (9 fixed, 0 remaining)`**, exit 0. Если количество ≠ 9 — Discrepancy, но не блокер (могло измениться pre-existing state).

### Phase V3.5 — Zero I diagnostics

```bash
uv run ruff check --select I scripts/ hooks/
```

Ожидание: `All checks passed!`, exit 0.

### Phase V3.6 — Negative acceptance (CRITICAL)

```bash
uv run ruff check scripts/ hooks/ --output-format=concise > /tmp/post-apply.txt 2>&1 || true
wc -l /tmp/post-apply.txt
echo "---"
diff /tmp/pre-apply-baseline.txt /tmp/post-apply.txt
```

Ожидание:
- `wc -l` показывает **15 errors** (тот же count что pre-apply)
- `diff` показывает **только column drift** в 2-3 строках (сортировка import'ов меняет column offset'ы). Никаких новых error types, никакого file:line add или remove.
- Специфично для verify: **zero new E402 errors** (проверить через `grep "E402" /tmp/post-apply.txt | wc -l` — должен быть тот же count что `grep "E402" /tmp/pre-apply-baseline.txt | wc -l`)

Если отличается больше чем column drift — **стоп**, Discrepancy, rollback, эскалация.

### Phase V3.7 — Empirical whitelist capture

```bash
git status --short -- pyproject.toml scripts/ hooks/
git diff --stat -- pyproject.toml scripts/ hooks/
```

Ожидание:
- 10 modified files (pyproject.toml + 9 expected affected)
- 3 excluded (hook_utils, pre-compact, session-end) **не** в diff

Зафиксировать **реальный** список в отчёт. Если отличается от плана — Discrepancy для записи, но не блокер.

### Phase V3.8 — Regression chain

Стандартный smoke chain как в v1 Phase 2.6-2.9:

1. **Python AST sanity** на affected files (список из V3.7):
   ```bash
   uv run python -c "import ast; files=['<list-from-V3.7>']; [ast.parse(open(f).read()) for f in files]; print('all ok')"
   ```

2. **Import smoke**:
   ```bash
   PYTHONPATH=hooks:scripts uv run python -c "import hook_utils, shared_context, shared_wiki_search; import compile as _c, doctor, lint, query, wiki_cli; print('all imports ok')"
   ```

3. **`lint.py --structural-only`**:
   ```bash
   uv run python scripts/lint.py --structural-only
   ```
   Ожидание: exit 0, same check set.

4. **`doctor --quick`**:
   ```bash
   uv run python scripts/wiki_cli.py doctor --quick
   ```
   Ожидание: exit 0, только pre-existing Bug H FAIL.

### Phase V3.9 — Out-of-scope baseline-delta

```bash
python3 - <<'PY'
import hashlib, subprocess
cmd = ['git', 'diff', '--', '.github/', 'wiki/', 'CLAUDE.md', 'AGENTS.md', 'README.md', 'docs/', '.gitignore']
out = subprocess.check_output(cmd)
print(hashlib.sha256(out).hexdigest())
PY
```

Ожидание: SHA256 identical to v1 baseline A (`cb94ab8c24099e65e6b7fe509166bbe93c2eaaf36f87494842f75f5fd20ad93e`).

## Acceptance criteria (v3)

- ✅ V3.1: rollback clean, worktree в scope paths пусто
- ✅ V3.2: pre-apply baseline = 15 errors (или фактическое число baseline)
- ✅ V3.3: pyproject.toml dict access показывает все 3 опции
- ✅ V3.4: `ruff --fix --select I` → `9 fixed, 0 remaining` (или близко)
- ✅ V3.5: zero I errors post-fix
- ✅ V3.6 (CRITICAL): negative acceptance — post-apply errors ≤ pre-apply, **zero new E402**, только column drift
- ✅ V3.7: empirical whitelist = 10 files (pyproject.toml + ожидаемо 9)
- ✅ V3.8: AST + import + lint + doctor all pass
- ✅ V3.9: out-of-scope SHA256 identical

## Update the existing report file

**Не создавать** новый report. Расширить `docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort-report.md`:

1. Frontmatter: `status: continuation-v3-in-progress` → после V3.9 → `completed`
2. Добавить в section 7 Discrepancies:
   - **D7**: Continuation v2 `per-file-ignores E402` не устранил I001 (11 remaining). Root cause: sys.path.insert паттерн fundamentally conflicts с isort invariant. Option B недостаточен.
   - **D8**: Continuation v3 переключена на **narrow per-file-ignores** `["I"]` для 3 files с destructive split pattern (`hook_utils.py`, `pre-compact.py`, `session-end.py`). Experimentally verified Claude'ом до handoff.
3. Добавить **section 10 Continuation v3** с outputs V3.1-V3.9.
4. Self-audit расширить пунктами V3.1-V3.9.

## Out of scope (v3)

- Manual file edits — zero
- Fix pre-existing 15 errors (F401/F841/F541/E402 doctor.py) — outside scope, separate future PR
- Broader per-file-ignores — scope narrow на 3 файла, не trogать другие
- Рефакторинг `sys.path.insert` pattern в hook'ах — связан с Finding #2, отдельный большой PR
- CI integration — PR 3

## Rollback

```bash
git checkout -- pyproject.toml scripts/ hooks/
```

Полный возврат к state c42cccd (PR 1 merged).

## Discrepancy handling

- **V3.4 fix count ≠ 9** — не блокер, но записать. Pre-existing state мог измениться.
- **V3.5 non-zero I errors** — **стоп**, Discrepancy, rollback. Per-file-ignores должны были покрыть все проблемные файлы.
- **V3.6 new E402 or other new errors** — **стоп**, rollback. Это значит что-то другое помимо 3 files имеет split issue.
- **V3.7 whitelist significantly different** (> 12 или < 7 файлов) — записать, но не блокер если V3.5 и V3.6 pass.
- **V3.8 doctor показывает NEW FAIL** — **стоп**, rollback.
- Любое другое отклонение — Discrepancies перед continuation.

## Notes для исполнителя (Codex)

- **v2 в корзину, v3 — новый подход**. Не пытаться спасти что-то из v2 continuation section — полный rollback, потом v3 с нуля.
- **Per-file-ignores на уровне `["I"]` (не `["E402"]`)** — это критично. v2 использовал E402 и не работал. v3 использует I.
- **Claude experimentally verified** что v3 работает до этого handoff'а (он rolled back experiment, но output был captured). Если у тебя что-то другое — Discrepancy, но base case — `9 fixed, 0 remaining, All checks passed!`.
- **Phase V3.6 — самый важный**. Не пропускать. Если post-apply != pre-apply (кроме column drift) — rollback.
- **F401 baseline в 15 errors** — игнорировать, не фиксить. Все они pre-existing. `scripts/doctor.py:35:1 E402` — тоже pre-existing, не regression.
- **Empirical whitelist V3.7 — после fix, не до**. Не предсказывать — фиксировать реальность.
- **No git commit/push**. Финал = updated existing report + V3.1-V3.9 outputs.
- **Personal data sanitize** как всегда.
- **Self-audit extended** с V3.1-V3.9 пунктами.
