# Planning Audit — Fix 15 pre-existing ruff errors + broaden CI gate

## 1. Files read

| File | Lines | What I extracted |
|---|---|---|
| hooks/codex/stop.py | 85-115 | `main_light()` extracts `cwd` at line 95 but never uses it; `main_worker()` has own `cwd` at 136. Line 95 is dead code. |
| hooks/codex/stop.py | full grep `cwd` | 4 occurrences: line 37 (import), 95 (dead), 136 (used), 184 (used). Confirmed 95 is safe to remove. |
| hooks/hook_utils.py | 21 | `from utils import parse_frontmatter  # noqa: E402` — imported but ruff says unused |
| hooks/shared_context.py | 22 | `from hook_utils import infer_project_name_from_cwd, parse_frontmatter` — USES parse_frontmatter from hook_utils |
| hooks/shared_wiki_search.py | 18 | `from hook_utils import infer_project_name_from_cwd, parse_frontmatter` — USES parse_frontmatter from hook_utils |
| scripts/lint.py | 320-335 | `sources = fm.get("sources", "")` at 327 assigned but never used in function. Dead code. |
| scripts/doctor.py | 1-36 | Imports at 8-22, constants at 29-35, then `from runtime_utils import find_uv, is_wsl` at 36 — E402 because after constants. Can be moved up. |
| scripts/seed.py | 240 | `f"..."` without placeholders — should be regular string |
| .github/workflows/wiki-lint.yml | 33-34 | Current: `ruff check --select I scripts/ hooks/`. To broaden: remove `--select I`. |

## 2. Commands run

| Command | Output (key) | What it proved |
|---|---|---|
| `uv run ruff check scripts/ hooks/ --output-format=concise` | 15 errors listed | Exact baseline: 11 F401 + 2 F841 + 1 F541 + 1 E402 |
| `grep -rn "from hook_utils import.*parse_frontmatter" hooks/ scripts/` | shared_context:22, shared_wiki_search:18 | parse_frontmatter IS re-exported — F401 is FALSE POSITIVE, must not remove |
| `grep -n "cwd" hooks/codex/stop.py` | 4 lines | line 95 dead (main_light), line 136+184 live (main_worker) |

## 3. URLs fetched

None needed — this is a code cleanup, not new tool integration. Ruff rules F401/F841/F541/E402 are already documented in wiki.

## 4. Wiki articles consulted

| Article | What I used |
|---|---|
| wiki/sources/astral-ruff-docs.md | F401 = unused import, F841 = unused local, F541 = f-string no placeholder, E402 = import not at top |

## 5. Assumptions + verification

| Assumption | Verified? | How |
|---|---|---|
| hook_utils.py parse_frontmatter is unused | ✅ verified FALSE — it's a re-export | `grep -rn` showed 2 consumers |
| cwd at stop.py:95 is dead code | ✅ verified | grep showed line 95 not used, worker has own at 136 |
| sources at lint.py:327 is dead code | ✅ verified | read function body, variable never referenced after assignment |
| doctor.py E402 can be fixed by moving import up | ✅ verified | no dependency on constants defined before it |
| After fixing all 15, `ruff check` will show 0 errors | ⚠️ assumed | depends on correct application of all fixes; Codex verifies |
| Broadening CI from `--select I` to full check will pass | ⚠️ assumed | depends on fixing all 15 first; Codex verifies sequentially |

## 6. Baselines captured

| Measurement | Value | Command |
|---|---|---|
| Total error count | 15 | `uv run ruff check scripts/ hooks/` |
| Autofixable | 12 (10 F401 + 1 F541 + 1 parse_frontmatter which is FALSE POSITIVE) | ruff output |
| Unsafe-fixable | 2 (F841) | ruff output |
| Manual | 1 (E402) | ruff output |
| Affected files | 8 (.py) + 1 (.yml for CI broadening) = 9 | ruff output + plan scope |
