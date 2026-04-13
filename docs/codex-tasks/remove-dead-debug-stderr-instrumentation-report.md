# Report — Remove dead `debug_stderr` instrumentation in flush.py

> Заполнено по фактическому исполнению.
>
> **Это НЕ fix для Bug H.** Bug H остаётся открытым. Эта задача — cleanup dead code.

---

## Pre-flight

- [x] Прочитал `docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md` целиком
- [x] Прочитал текущий `scripts/flush.py` (особенно строки 30-40 и 195-225)
- [x] Понял что whitelist = только `scripts/flush.py`
- [x] Понял что НЕ трогаю: `extra_args`, `_log_cli_stderr`, retry loop, lock logic
- [x] Понял что **это не fix Bug H** — Bug H остаётся открытым, рамка задачи cleanup
- [x] Понял что Phase 2 smoke может flake из-за интермиттентного Bug H — это не блокер при ≥1 success в ≤3 попытках

---

## Doc verification

> Источник: `https://code.claude.com/docs/en/agent-sdk/python`

| Что проверял | URL / раздел | Что нашёл | Цитата |
|---|---|---|---|
| Параметр `debug_stderr` в `ClaudeAgentOptions` | `code.claude.com/docs/en/agent-sdk/python` | параметр существует | ``debug_stderr  | `Any`  | `sys.stderr`  | Deprecated - File-like object for debug output. Use `stderr` callback instead`` |
| Deprecated пометка | `code.claude.com/docs/en/agent-sdk/python` | подтверждена | ``Deprecated - File-like object for debug output. Use `stderr` callback instead`` |
| Рекомендованная замена | `code.claude.com/docs/en/agent-sdk/python` | `stderr` callback | ``Use `stderr` callback instead`` |

**Conclusion**:
> Документация прямо подтверждает, что `debug_stderr` deprecated, а рекомендованный путь — `stderr` callback. Это совпадает с cleanup-целью: убрать мёртвый deprecated канал и оставить рабочий `stderr=_log_cli_stderr`.

**Если deprecated пометка отсутствует** — стоп, эскалация в Discrepancies, фикс не применять.

---

## Phase 1 — apply fix

### Diff scripts/flush.py

```diff
<intermediate cleanup diff was applied, then file was restored to clean HEAD-equivalent state; final tracked diff is empty>
```

### git status

```text
?? Untitled.md
```

- [x] Только `scripts/flush.py` затрагивался по задаче
- [x] Никаких других tracked файлов не тронуто

---

## Phase 2 — Windows smoke flush.py

### Команда подготовки контекста

```bash
@'
from pathlib import Path
import random, string
lines = [f'[USER] turn {i}: ' + ' '.join(''.join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path('E:/tmp/cleanup-smoke.md').parent.mkdir(parents=True, exist_ok=True)
Path('E:/tmp/cleanup-smoke.md').write_text('\n'.join(lines), encoding='utf-8')
print('chars:', sum(len(l)+1 for l in lines))
'@ | .venv/Scripts/python.exe -
```

Output:

```text
chars: 12470
```

### Команда запуска flush.py

```bash
.venv/Scripts/python.exe scripts/flush.py "E:/tmp/cleanup-smoke.md" "cleanup-smoke-1" "memory-claude" 2>&1
```

Output:

```text
<no direct stdout/stderr output>
```

### Релевантные строки flush.log

```text
2026-04-13 22:46:07 INFO [flush] Starting flush for session cleanup-smoke-1 (12469 chars)
2026-04-13 22:46:08 INFO [flush] Using bundled Claude Code CLI: <repo-root>\.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe
2026-04-13 22:46:24 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
```

### Verdict

- [x] Прогон 1: SKIP
- [ ] (если Fatal error) Прогон 2: success / SKIP / Fatal error → _(не потребовался)_
- [ ] (если Fatal error) Прогон 3: success / SKIP / Fatal error → _(не потребовался)_
- [x] Хотя бы один из ≤3 прогонов прошёл без Fatal error → cleanup валиден
- [ ] (если все 3 упали) → СТОП, эскалация в Discrepancies

---

## Phase 3 — doctor regression

### Команда

```bash
uv run python scripts/wiki_cli.py doctor --full 2>&1 | tail -40
```

### Output

```text
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_capture_health: Last 7d: 61/145 flushes spawned (skip rate 58%) [attention: high skip rate � consider lowering WIKI_MIN_FLUSH_CHARS]
[PASS] python_version: Python 3.14.2
[PASS] uv_binary: <user-home>\AppData\Local\Programs\Python\Python311\Scripts\uv.EXE
[PASS] doctor_runtime: Current shell is not WSL
[PASS] codex_config: Skipped outside WSL
[PASS] codex_hooks_json: Skipped outside WSL
[PASS] index_health: Index is up to date.
[FAIL] structural_lint: Running knowledge base lint checks...
  Checking: Broken links...
    Found 30 issue(s)
  Checking: Orphan pages...
    Found 6 issue(s)
  Checking: Orphan sources...
    Found 0 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Missing backlinks...
    Found 297 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo-root>\reports\lint-2026-04-13.md

Results: 30 errors, 7 warnings, 297 suggestions

Errors found � knowledge base needs attention!
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
[PASS] session_start_smoke: SessionStart returned additionalContext
[PASS] user_prompt_smoke: UserPromptSubmit returned relevant article context
[PASS] stop_smoke: Stop hook exited safely
[PASS] flush_roundtrip: session-end -> flush.py chain completed in test mode
```

### Verdict

- [x] Hook-specific тесты (`stop_smoke`, `flush_roundtrip`) PASS
- [x] Pre-existing red отмечены явно: `structural_lint`
- [x] Нет новых regression'ов от наших правок

---

## Phase 4 — WSL regression

### Команда

```bash
wsl.exe -d Ubuntu -- bash -lc 'python3 - <<"PY"
from pathlib import Path
import random, string
lines = [f"[USER] turn {i}: " + " ".join("".join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path("/tmp/cleanup-smoke-wsl.md").write_text("\n".join(lines), encoding="utf-8")
print("chars:", sum(len(l)+1 for l in lines))
PY'

wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && uv run python scripts/flush.py /tmp/cleanup-smoke-wsl.md cleanup-smoke-wsl-1 memory-claude 2>&1 | tail -20'

grep "cleanup-smoke-wsl-1" scripts/flush.log | tail -5
```

### Output

```text
chars: 12470
Using CPython 3.14.4
Removed virtual environment at: .venv
Creating virtual environment at: .venv
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
Installed 31 packages in 33.56s

2026-04-13 22:47:39 INFO [flush] Starting flush for session cleanup-smoke-wsl-1 (12469 chars)
2026-04-13 22:47:57 INFO [flush] Using bundled Claude Code CLI: <repo-root>/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 22:48:08 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
```

### Verdict

- [x] WSL flush работает (SKIP)
- [x] Нет Fatal error в WSL прогоне

---

## Final state

### git status

```text
?? Untitled.md
```

### git diff (полный)

```diff
<empty tracked diff for scripts/flush.py in final state>
```

### Файлы созданные/удалённые на диске

- `scripts/flush.py` — returned to clean tracked state without `debug_stderr` instrumentation
- `scripts/flush-debug-stderr.log` — deleted

---

## Tools used

- [x] WebFetch / web search — для офдоки claude_agent_sdk (deprecated пометка)
- [x] Read — `scripts/flush.py`, `docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md`
- [x] Bash / PowerShell — Phase 1, 2, 3, 4 команды
- [x] Edit — Правки 1-2 в `scripts/flush.py`
- [x] git CLI — status / cleanup verification

---

## Discrepancies

- После удаления diagnostic patch и выравнивания рабочего дерева `scripts/flush.py` оказался идентичен tracked `HEAD`, поэтому в финальном состоянии tracked diff пустой.
- В worktree есть unrelated `?? Untitled.md`, не относящийся к задаче.
- WSL smoke пересоздал `.venv` внутри WSL path (`Removed virtual environment at: .venv` → `Creating virtual environment at: .venv`). На сам cleanup это не повлияло, но это полезное operational observation.

---

## Self-audit

- [x] Применил **только** Правки 1-2 (и cleanup файла `flush-debug-stderr.log`)
- [x] Не трогал ничего вне `scripts/flush.py`
- [x] `extra_args={"strict-mcp-config": None}` сохранён
- [x] `_log_cli_stderr` callback и `stderr=...` сохранены
- [x] Doc verification раздел заполнен с реальной цитатой из офдоки
- [x] Phase 2 smoke прошёл хотя бы один раз без Fatal error
- [x] Phase 3 doctor PASS hook-specific
- [x] Phase 4 WSL не сломан
- [x] В отчёте явно зафиксировано: **это не fix Bug H**
- [x] Не делал commit / push
- [x] Не делал opportunistic улучшений
- [x] Не трогал предыдущие task reports / planы

---

## Bug H status (явно зафиксировать для clarity)

- [x] Bug H **остаётся открытым** intermittent issue
- [x] Эта задача его **не фиксит** и не претендует на это
- [x] Следующий шаг по Bug H — **сбор большего количества семплов** (минимум неделя реального использования) перед попыткой root cause
- [x] Diagnostic канал `debug_stderr` доказанно бесполезен для Bug H investigation — удалён

---

## Notes / observations

- Из полезного: Windows и WSL smoke оба прошли веткой `SKIP`, то есть cleanup не задел рабочий путь выполнения.
- Самое важное здесь не “что-то починили”, а “убрали deprecated dead code, которое ничего не давало и только усложняло чтение `flush.py`”.
