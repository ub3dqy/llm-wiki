# Plan — Fix 15 pre-existing ruff errors + broaden CI gate

## Иерархия источников правды

1. **Ruff docs** (F401, F841, F541, E402 rules) — https://docs.astral.sh/ruff/rules/
2. **Реальное состояние кода** — `ruff check scripts/ hooks/` output (15 errors)
3. **Этот план** — derived, при расхождении → Discrepancy

## Context

После repo hygiene sequence (PRs #33-#38) CI gate проверяет только `--select I` (isort) + `ruff format --check`. 15 pre-existing errors (F401/F841/F541/E402) были deliberately deferred.

Этот PR:
1. Фиксит все 15 errors
2. Broadens CI gate с `ruff check --select I` до `ruff check` (full default rules)

Одним PR'ом потому что broadening без fix = CI instant fail, fix без broadening = мёртвая работа.

## ⚠️ CRITICAL: hook_utils.py parse_frontmatter — FALSE POSITIVE

**[EMPIRICAL]** `hooks/hook_utils.py:21` — `from utils import parse_frontmatter` помечен ruff как F401 (unused). Но это **re-export**: `hooks/shared_context.py:22` и `hooks/shared_wiki_search.py:18` import'ят `parse_frontmatter` из `hook_utils`.

**Если `ruff --fix` удалит этот import — сломает два hook'а.**

Fix: добавить `# noqa: F401` к этой строке **ДО** запуска `ruff --fix`. Это защитит re-export от удаления.

## Doc verification

| URL | Что искать |
|---|---|
| https://docs.astral.sh/ruff/rules/unused-import/ | F401 definition + `# noqa: F401` для re-exports |
| https://docs.astral.sh/ruff/rules/unused-variable/ | F841 definition + `--unsafe-fixes` requirement |
| https://docs.astral.sh/ruff/rules/f-string-missing-placeholders/ | F541 definition |
| https://docs.astral.sh/ruff/rules/module-import-not-at-top-of-file/ | E402 definition |

## Whitelist (9 файлов)

**Production code (8 .py)**:

1. `hooks/hook_utils.py` — add `# noqa: F401` to re-export line (NOT remove import)
2. `hooks/codex/stop.py` — remove dead `cwd` assignment (F841)
3. `scripts/compile.py` — remove unused `WIKI_DIR` import (F401)
4. `scripts/doctor.py` — remove unused `shutil` (F401) + move `runtime_utils` import up (E402)
5. `scripts/lint.py` — remove unused `frontmatter_sources_include_prefix` (F401) + remove unused `AssistantMessage`/`TextBlock` (F401 ×2) + remove dead `sources` var (F841)
6. `scripts/rebuild_index.py` — remove unused `now_iso` (F401)
7. `scripts/seed.py` — remove unused `json` (F401) + unused `WIKI_DIR` (F401) + fix f-string (F541)
8. `scripts/wiki_cli.py` — remove unused `DAILY_DIR`/`REPORTS_DIR` (F401 ×2)

**CI workflow (1 .yml)**:

9. `.github/workflows/wiki-lint.yml` — change `ruff check --select I` → `ruff check`

**НЕ трогать**: hooks/*.py кроме hook_utils и codex/stop, pyproject.toml, CLAUDE.md, wiki/, docs/ (кроме handoff)

## Changes

### Change 1 — Protect re-export BEFORE autofix

**Вручную** добавить `# noqa: F401` к `hooks/hook_utils.py:21`:

```diff
-from utils import parse_frontmatter  # noqa: E402
+from utils import parse_frontmatter  # noqa: E402, F401  # re-export for shared_context/shared_wiki_search
```

**ДЕЛАТЬ ПЕРВЫМ** — до любого `ruff --fix`.

### Change 2 — Autofix 11 safe errors

```bash
uv run ruff check --fix scripts/ hooks/
```

Ожидание: removes 10 F401 (unused imports) + 1 F541 (f-string). `hook_utils.py:21` protected by noqa. Output: `Found 14 errors (11 fixed, 3 remaining)`.

### Change 3 — Manual fix F841 (2 unused vars)

**3a** `hooks/codex/stop.py:95` — remove dead `cwd` assignment:

```diff
     session_id = hook_input.get("session_id", "unknown")
     turn_id = hook_input.get("turn_id", "unknown")
-    cwd = hook_input.get("cwd", "")
     transcript_path_str = get_transcript_path(hook_input)
```

**[EMPIRICAL]** Confirmed: `main_worker()` has own `cwd = hook_input.get("cwd", "")` at line 136. Worker doesn't depend on main_light's variable.

**3b** `scripts/lint.py:327` — remove dead `sources` assignment:

```diff
     for article in _wiki_articles():
         fm = _article_frontmatter(article)
         page_type = fm.get("type", "").strip()
-        sources = fm.get("sources", "")
         if page_type not in {"concept", "connection"}:
```

### Change 4 — Manual fix E402 (move import up)

`scripts/doctor.py:36` — move `from runtime_utils import find_uv, is_wsl` up to import block:

```diff
 from zoneinfo import ZoneInfo
 
+from runtime_utils import find_uv, is_wsl
+
 try:
     import tomllib
 except ModuleNotFoundError:  # pragma: no cover
     tomllib = None
 
 ROOT_DIR = Path(__file__).resolve().parent.parent
 ...
 CAPTURE_HEALTH_WINDOW_DAYS = 7
-from runtime_utils import find_uv, is_wsl
```

### Change 5 — Broaden CI gate

`.github/workflows/wiki-lint.yml` — remove `--select I`:

```diff
-      - name: Ruff check (I rule)
-        run: uv run ruff check --select I scripts/ hooks/
+      - name: Ruff check
+        run: uv run ruff check scripts/ hooks/
```

Step rename: `Ruff check (I rule)` → `Ruff check` (no longer narrow).

## Verification phases

### Phase 1 — Codex sам

**1.1** After Change 1 (noqa protection): verify shared_context/shared_wiki_search still import parse_frontmatter:
```bash
PYTHONPATH=hooks:scripts uv run python -c "from hook_utils import parse_frontmatter; print('re-export ok')"
```

**1.2** After Change 2 (autofix): `ruff check scripts/ hooks/` shows exactly 3 remaining (2 F841 + 1 E402).

**1.3** After Changes 3+4 (manual): `ruff check scripts/ hooks/` → **0 errors**.

**1.4** After Change 5 (CI broadening): `ruff check scripts/ hooks/` still 0 (same command CI will run).

**1.5** Negative acceptance — format still clean:
```bash
uv run ruff format --check scripts/ hooks/
```
Ожидание: `25 files already formatted`.

**1.6** I rule still clean:
```bash
uv run ruff check --select I scripts/ hooks/
```
Ожидание: `All checks passed!`.

**1.7** AST + import smoke on all 8 modified .py files.

**1.8** `lint.py --structural-only` exit 0.

**1.9** `doctor --quick` exit 0 (only pre-existing Bug H if within 24h window).

**1.10** Path-scoped diff: 8 .py + 1 .yml.

**1.11** Baseline-delta out-of-scope paths SHA256 unchanged.

### Phase 2 — `[awaits user + CI]`

After PR push: CI runs new broad `ruff check` step — should pass with 0 errors.

## Acceptance criteria

- ✅ `ruff check scripts/ hooks/` → **0 errors** (down from 15)
- ✅ `ruff format --check` → still clean
- ✅ `ruff check --select I` → still clean
- ✅ Re-export `parse_frontmatter` in hook_utils.py preserved (import smoke)
- ✅ AST + import sanity on all modified files
- ✅ lint + doctor pass
- ✅ CI step renamed `Ruff check` (not `Ruff check (I rule)`)
- ✅ CI command = `uv run ruff check scripts/ hooks/` (no `--select`)
- ✅ Path-scoped: 9 files only
- ✅ Baseline-delta: out-of-scope unchanged

## Out of scope

- UP/B rules — separate future decision
- pre-commit — not planned
- Fix any NEW diagnostics that might appear from broadened default set (shouldn't happen — we verified 0 after fixes)
- hooks per-file-ignores for I rule (stays from PR #34, unrelated)

## Rollback

```bash
git checkout -- hooks/hook_utils.py hooks/codex/stop.py scripts/compile.py scripts/doctor.py scripts/lint.py scripts/rebuild_index.py scripts/seed.py scripts/wiki_cli.py .github/workflows/wiki-lint.yml
```

## Discrepancy handling

- **`ruff --fix` removes parse_frontmatter** despite noqa → Change 1 wasn't applied first. **CRITICAL STOP**, rollback, re-apply Change 1.
- **Post-fix error count ≠ 0** → something not caught by plan. Record exact errors, escalate.
- **Format check shows "would reformat"** after fixes → fix introduced formatting regression, run `ruff format` on affected file.
- **Import smoke fails** → removal broke a dependency. Rollback affected file, investigate.

## Notes для Codex

- **Change 1 ПЕРВЫМ**. Если запустишь `ruff --fix` до добавления `# noqa: F401` в hook_utils.py — сломаешь shared_context и shared_wiki_search. Это **единственный** dangerous moment в этом PR.
- **F841 requires manual edit**, не `--fix`. Ruff не auto-removes assigned-but-unused vars без `--unsafe-fixes`, и даже с ним может удалить side-effectful assignments. Ручная правка безопаснее.
- **E402 в doctor.py** — просто переместить import выше. Не нужен per-file-ignores.
- **CI broadening (Change 5) — последним**. Сначала убедись что `ruff check` = 0, потом меняй CI step.
- **Step rename** — `Ruff check (I rule)` → `Ruff check`. Не забудь поменять и `name:` и `run:`.
- **No commit/push**. Финал = отчёт. Personal data sanitize.
