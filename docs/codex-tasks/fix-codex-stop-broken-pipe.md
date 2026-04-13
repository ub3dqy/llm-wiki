# Task — Fix Codex Stop BrokenPipeError after successful spawn

> **Роль**: исполнитель — Codex. Этот файл — **derived plan**, написанный Claude'ом
> на основе чтения официальной документации и анализа реального traceback'а.
> Это **не** primary source of truth.
>
> ## Иерархия источников правды (от высшей к низшей)
>
> 1. **Официальная документация** — primary source.
>    - `developers.openai.com/codex/hooks`
>    - `developers.openai.com/codex/config-advanced`
> 2. **Реальное состояние кода и логов проекта** — secondary.
> 3. **Этот план** — derived artifact, может содержать ошибки или быть устаревшим.
>
> **Правило двойной проверки**: перед правкой кода открой офдоку **сейчас** и сверь.
> Если план и дока расходятся — приоритет у доки, фиксируй в `Discrepancies`.

## Источники, на которые опирается план

- `[OFFICIAL-CODEX]` — `developers.openai.com/codex/hooks` (output контракт Stop)
- `[STACK-TRACE]` — дословно из traceback в `scripts/flush.log`
- `[EMPIRICAL]` — наблюдается в реальном файле/коде на диске
- `[PROJECT]` — собственное архитектурное решение проекта

## Контекст — что уже сделано и что осталось

Предыдущий fix-wave (5 багов A-E) в файлах `hooks/hook_utils.py`, `hooks/codex/stop.py`,
`codex-hooks.template.json` закрыл "память не пишется вообще". См. отчёт прошлой задачи:
`docs/codex-tasks/fix-codex-stop-hook-report.md`.

После этого fix'а в `scripts/flush.log` появилась **новая** ошибка:

```
2026-04-13 13:20:27 INFO  [codex-stop] Stop fired: session=019d4435-...
2026-04-13 13:20:38 INFO  [codex-stop] Spawned flush.py for session ... (30 turns, 9359 chars)
2026-04-13 13:20:38 ERROR [codex-stop] Stop hook failed: [Errno 32] Broken pipe
```

С traceback **[STACK-TRACE]** (дословно из `scripts/flush.log`):

```
File "<repo-root>/hooks/codex/stop.py", line 56, in _emit_ok
    print(json.dumps(payload, ensure_ascii=False), flush=True)
BrokenPipeError: [Errno 32] Broken pipe
```

Capture **уже** запустился (`Spawned flush.py` записан в той же секунде, **до** ERROR).
Это **post-capture cosmetic failure**, но валит exit code и вызывает `Stop failed` в UI Codex.

## Root cause (из анализа Claude'а)

1. **[STACK-TRACE]** Падение в `_emit_ok()` на `print(json.dumps(...), flush=True)` — единственная точка записи в stdout во всём `stop.py`.

2. **[EMPIRICAL]** Hook реально работал **11 секунд** (`13:20:27` → `13:20:38`). Время уходит на `extract_conversation_context()` на 90MB Codex jsonl + bash + uv venv resolve + `subprocess.Popen` инициализацию под Windows/WSL.

3. **[EMPIRICAL]** Локальный `~/.codex/hooks.json:22` всё ещё содержит `"timeout": 10` для Stop. Codex обновил **только** template (`codex-hooks.template.json`), локальный пользовательский конфиг не трогал. Это правильно архитектурно — пользовательский конфиг трогает только пользователь.

4. **Цепочка**: hook идёт 11 секунд → локальный timeout=10s превышен → Codex закрыл stdout pipe → `_emit_ok()` в success path → `print(...)` → `BrokenPipeError`.

5. **[EMPIRICAL]** В `hooks/codex/stop.py:176-181` outer wrapper после exception вызывает `_emit_ok()` ещё раз → второй BrokenPipeError → traceback в stderr (Codex редиректит в свой лог) → exit code != 0 → UI показывает `Stop failed`.

## Контракт (перепроверить ОБЯЗАТЕЛЬНО до правки)

**[OFFICIAL-CODEX]** Из `developers.openai.com/codex/hooks`:

> "Stop expects JSON on stdout when it exits 0. Plain text output is invalid for this event."

Что **НЕ задокументировано**:
- Когда именно Codex закрывает stdin/stdout pipe.
- Грейс-период чтения stdout после exit / timeout / kill.
- Поведение при превышении timeout.
- SIGPIPE / EPIPE / BrokenPipe handling со стороны Codex.

**Вывод**: pipe closure поведение не специфицировано. Hook **обязан** быть defensive
к записи в stdout, который может оказаться закрыт в любой момент.

## Bonus discovery (Bug G — OUT OF SCOPE для этой задачи)

**[EMPIRICAL]** В `scripts/flush.log` сразу после BrokenPipe:

```
2026-04-13 13:20:39 INFO  [flush] Starting flush for session 019d4435-... (9359 chars)
2026-04-13 13:20:40 INFO  [flush] Using bundled Claude Code CLI: .../claude_agent_sdk/_bundled/claude
2026-04-13 13:20:44 ERROR [flush] Fatal error in message reader: Command failed with exit code 1
2026-04-13 13:20:44 ERROR [flush] Agent SDK query failed: Command failed with exit code 1
```

flush.py **сам падает** при вызове Claude Agent SDK с exit code 1. Это **отдельный, второй баг**,
требующий собственного расследования. **НЕ пытайся его чинить в этой задаче.**

В отчёте этой задачи добавь раздел `Bug G evidence` с дословными свежими записями из
`flush.log` (после твоего фикса) — это войдёт как input для следующего fix-task'а.

**Важно**: даже после твоего фикса BrokenPipe **запись в daily log не появится**, потому что
упадёт следующий слой (flush.py → Agent SDK). Не считай это регрессом своего фикса.

## Files to modify (whitelist — ТОЛЬКО ЭТОТ ФАЙЛ)

**Только**: `hooks/codex/stop.py`

Не трогать **ничего другого** — ни `hook_utils.py`, ни template, ни flush.py, ни doctor.py,
ни тесты. Если возникает соблазн "заодно поправить" — записать в `Out-of-scope-temptations`
и не трогать.

## Изменения (минимально, две функции)

### Изменение 1 — `_emit_ok()` глотает pipe ошибки

**Где**: `hooks/codex/stop.py` (текущая `_emit_ok` функция, около строки 52-56).

**Как**: обернуть `print` в try/except, ловить `BrokenPipeError` и `OSError`. Silently swallow.

```python
def _emit_ok(message: str | None = None) -> None:
    """Emit valid Stop hook JSON output, defensive against closed stdout.

    Codex may close stdout before this runs (e.g. if hook exceeded local
    timeout or Codex is shutting down). BrokenPipeError at this point is
    non-fatal: capture has already been spawned in the success path, and
    in failure paths there's nothing useful to report anyway.

    Reference: developers.openai.com/codex/hooks — Stop expects JSON on
    stdout when it exits 0. We honor the contract on best-effort basis;
    if the pipe is closed we cannot do anything about it.
    """
    payload: dict[str, str] = {}
    if message:
        payload["systemMessage"] = message
    try:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    except (BrokenPipeError, OSError):
        # Codex closed stdout. Capture already handled where applicable.
        pass
```

**Acceptance**: после правки в коде нет `print(...)` без обёртки try/except.

### Изменение 2 — Outer wrapper не падает на BrokenPipeError

**Где**: `hooks/codex/stop.py` строки 176-181.

**Текущий код**:
```python
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Stop hook failed: %s", exc)
        _emit_ok()
```

**Новый**:
```python
if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # Codex closed stdout while hook was still finalizing. Capture state
        # is already what it is — see `Spawned flush.py` log line if present.
        # Silently exit 0 to avoid surfacing as "Stop failed" in Codex UI.
        pass
    except Exception as exc:
        logging.exception("Stop hook failed: %s", exc)
        _emit_ok()
```

**Acceptance**: BrokenPipeError на верхнем уровне ловится **отдельно** до общего `except Exception`,
не логируется как "Stop hook failed", выход через нормальный exit 0.

## Что НЕ менять (явный анти-whitelist)

- **Не двигать** `_emit_ok()` placement в `main()` — текущее размещение (в конце success path после `Spawned flush.py` log) корректно.
- **Не оборачивать** `subprocess.Popen` в дополнительный try/except — он уже есть.
- **Не добавлять** `signal.signal(SIGPIPE, SIG_DFL)` — это работает только под Unix, а наш hook бежит в WSL bash под Windows. Try/except покрывает все среды.
- **Не трогать** другие функции `main()`, debounce, threshold checks — они уже работают.
- **Не трогать** `~/.codex/hooks.json` (пользовательский конфиг) — это вне границ кода.
- **Не пытаться** починить Bug G (flush.py Agent SDK exit code 1) — отдельная задача.

## Обязательное использование внешних инструментов

См. предыдущий task `docs/codex-tasks/fix-codex-stop-hook.md` раздел "Обязательное использование
внешних инструментов" — те же требования для этой задачи:

- **LLM Wiki** проекта (релевантные статьи: `wiki/concepts/claude-code-hooks.md`, `wiki/concepts/llm-wiki-architecture.md`, `wiki/concepts/anthropic-context-anxiety-injection.md` — последняя релевантна для Bug G context).
- **Web fetch** официальной страницы `developers.openai.com/codex/hooks` (для перепроверки контракта Stop output).
- **MCP серверы** доступные в окружении (context7, filesystem, git).
- **Skills** доступные в окружении.
- **Repo-local docs**: `AGENTS.md`, `CLAUDE.md`, и **обязательно** прошлый отчёт `docs/codex-tasks/fix-codex-stop-hook-report.md` (как образец структуры).
- **Опционально**: subagent делегирование, линтеры.

В отчёте раздел `Tools used` обязателен — со статусом по каждому пункту.

## Verification (последовательность)

### Pre-flight (заполняется в отчёте до правок кода)

- `python --version` / `uv --version`
- Дословные строки из `scripts/flush.log` с `Broken pipe` (`grep "Broken pipe" scripts/flush.log`)
- Дословный traceback `BrokenPipeError` из лога (`grep -B 2 -A 5 BrokenPipeError scripts/flush.log`)
- Текущее состояние локального `~/.codex/hooks.json`: `grep -n '"timeout"' ~/.codex/hooks.json` — записать дословно (это для информации, не правим)

### 0.6 Doc verification (обязательно до правок)

Открыть `developers.openai.com/codex/hooks` **прямо сейчас** и подтвердить:

| Что план говорит | Что дока говорит сейчас | Совпало? |
|---|---|---|
| `Stop expects JSON on stdout when it exits 0. Plain text output is invalid for this event.` | `<процитировать дословно>` | ✅ / ❌ |
| Поведение при закрытии pipe со стороны Codex **не задокументировано** | `<подтвердить или опровергнуть>` | ✅ / ❌ |
| SIGPIPE / EPIPE handling **не задокументирован** | `<подтвердить или опровергнуть>` | ✅ / ❌ |

Любое ❌ → стоп, в Discrepancies, не правь код вслепую.

### Phase 1 — Unit / smoke (после правки)

**1.1** Synthesized broken pipe smoke (Linux/WSL):
```bash
echo '{"session_id":"test","transcript_path":null,"cwd":".","hook_event_name":"Stop","model":"x","turn_id":"t","stop_hook_active":false,"last_assistant_message":null}' | uv run python hooks/codex/stop.py 2>&1 > /dev/full
echo "EXIT=$?"
```

Ожидание: `EXIT=0`, никаких traceback.

**1.2** Альтернативный smoke на Windows (без `/dev/full`) — Python harness, который явно закрывает stdout pipe со своей стороны:

```bash
uv run python -c "
import subprocess, json, sys
proc = subprocess.Popen(
    ['uv', 'run', 'python', 'hooks/codex/stop.py'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
proc.stdin.write(json.dumps({
    'session_id': 'test_pipe', 'transcript_path': None, 'cwd': '.',
    'hook_event_name': 'Stop', 'model': 'x', 'turn_id': 't',
    'stop_hook_active': False, 'last_assistant_message': None,
}).encode())
proc.stdin.close()
proc.stdout.close()  # КЛЮЧЕВОЕ: закрываем stdout pipe со стороны 'Codex'
out, err = proc.communicate(timeout=30)
print(f'exit={proc.returncode}')
print(f'stderr_tail={err.decode(errors=\"replace\")[-500:]}')
"
```

Ожидание: `exit=0`, в stderr нет `BrokenPipeError`.

**1.3** Regression smoke от прошлого фикса:
```bash
echo '{"session_id":"test","transcript_path":null,"cwd":".","hook_event_name":"Stop","model":"x","turn_id":"t","stop_hook_active":false,"last_assistant_message":null}' | uv run python hooks/codex/stop.py
echo "EXIT=$?"
```

Ожидание: stdout=`{}`, exit=0.

**1.4** `doctor --full`:
```bash
uv run python scripts/doctor.py --full
```

Ожидание: hook-specific тесты PASS (`stop_smoke`, `flush_roundtrip`, `path_normalization`).
Repo-wide red остаётся pre-existing (см. прошлый отчёт раздел 6.6 — `structural_lint` issues unrelated).

### Phase 2 — Integration (выполняет ПОЛЬЗОВАТЕЛЬ, поля `[awaits user]`)

- 2.1 Опционально, рекомендуется: пользователь обновляет локальный `~/.codex/hooks.json` Stop timeout 10→60.
- 2.2 Перезапуск Codex.
- 2.3 Реальная content-rich сессия.
- 2.4 `tail -30 scripts/flush.log | grep "[codex-stop]"`: должны быть `Spawned flush.py` без `Broken pipe` и без traceback.
- 2.5 UI Codex: нет `Stop failed` после успешного capture.

### Phase 3 — Bug G evidence (для следующего fix-task'а)

После твоего фикса `flush.log` должен показать `Spawned flush.py` чисто (без BrokenPipe), а **дальше** — упасть на `[flush] Agent SDK query failed`. Дословно зафиксировать в отчёте раздел `Bug G evidence` — это input для следующей задачи. **Не чинить.**

## Acceptance criteria (полный список)

- ✅ Pre-flight заполнен реальными выводами команд
- ✅ Doc verification 0.6 — дословные цитаты из офдоки, все строки таблицы
- ✅ Изменение 1 — `_emit_ok` обёрнут в try/except (BrokenPipeError, OSError)
- ✅ Изменение 2 — outer wrapper ловит BrokenPipeError отдельно ДО `except Exception`
- ✅ Phase 1.1 или 1.2 — synthesized broken pipe smoke → exit 0, no traceback
- ✅ Phase 1.3 — regression smoke → stdout=`{}`, exit 0
- ✅ Phase 1.4 — doctor --full hook-specific тесты PASS
- ✅ Bug G evidence записан (для следующего fix-task'а, не чиним сейчас)
- ✅ Tools used раздел заполнен (вики, офдоки, MCP, repo docs)
- ✅ Self-audit checklist в конце отчёта пройден полностью

## Rollback

```bash
git checkout hooks/codex/stop.py
```

Никаких commit'ов и push'ей до полной верификации Phase 1 + Phase 2 + ревью пользователя.

## Notes для исполнителя (Codex)

- Изменение **минимальное**: одна функция + outer wrapper, в одном файле.
- **Не двигать** `_emit_ok()` placement в `main()`. Оставь в конце success path как есть.
- **Не добавлять** SIGPIPE handler — try/except покрывает Linux + Windows + WSL.
- **Перепроверь офдоку Codex hooks** перед правкой. Если контракт изменился — стоп, в Discrepancies.
- **В отчёт ОБЯЗАТЕЛЬНО добавь раздел `Bug G evidence`** — дословные свежие записи из `flush.log` после твоего фикса. Не чини Bug G.
- **Используй** все обязательные внешние инструменты по образцу прошлого fix-task'а.
- **Никаких git commit/push** — финал работы это заполненный отчёт, ревью у пользователя.
