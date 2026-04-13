# Task — Investigate Bug H: flush.py Agent SDK intermittent exit code 1

> **Роль**: исполнитель — Codex. Diagnostic-only task. НЕ чини Bug H, только собери evidence.
>
> **Иерархия источников правды**:
> 1. Официальная документация Claude Agent SDK Python (`code.claude.com/docs/en/agent-sdk/python`) — primary
> 2. Реальное состояние кода и логов — secondary
> 3. Этот план — derived artifact, может ошибаться
>
> Расхождение план vs дока → побеждает дока, фиксируй в `Discrepancies`.

---

## Context

После Bug G закрытия (PR #14 + PR #15, merged 2026-04-13) real Codex sessions большинство flush'ей проходят успешно. **Но ~33% flush'ей всё ещё падают** на той же ошибке `"Fatal error in message reader: Command failed with exit code 1"` — уже **не** из-за Bug G (auth / MCP). Это новый баг с другими характеристиками.

Issue: [#16](https://github.com/ub3dqy/llm-wiki/issues/16) (Bug H)
Parent: [#5](https://github.com/ub3dqy/llm-wiki/issues/5)

## Evidence (dostup в `scripts/flush.log`)

Три подряд real flushes в session `019d4435-...` на 2026-04-13 после 18:25:

| # | Timestamp | Chars | Query time | Result |
|---|---|---|---|---|
| 1 | 18:26:02 → 18:26:29 | 12981 | **25 сек** | ✅ `Flushed 2680 chars` |
| 2 | 18:28:23 → 18:29:02 | 12842 | **24 сек** | ✅ `Flushed 2675 chars` |
| 3 | 18:29:55 → 18:30:58 | 14601 | **51 сек** | ❌ `Fatal error in message reader` |

Третий fail имеет два характерных отличия от predecesors:
- Контекст **больший** (14601 vs 12842/12981)
- Query time **вдвое больше** (51 vs 25) и падение вместо успеха
- Произошёл после быстрой последовательности (5 flush calls за 17 минут)

## Hypotheses

1. **Rate limit** — SDK-level rate limit от Anthropic backend surfacing as exit-1
2. **Large context timeout** — Agent SDK internal timeout scales non-linearly с размером контекста
3. **Transient backend error** — network blip / 5xx
4. **`<total_tokens>` injection (#8)** — intermittent A/B flag
5. **`debug_stderr` missing diagnostics** — SDK пишет внутренние diagnostics в `debug_stderr` (default `sys.stderr`), но мы его не захватываем

## Diagnostic approach

PR #14 wired `stderr` callback + `ProcessError` handler. Bug H **не** срабатывает через них (как и Bug G слой 3 — error на stdout/message-reader слое до того как SDK стабильно wraps в ProcessError). Значит нужен **новый** канал видимости.

### Finding из SDK signature

Из `ClaudeAgentOptions` signature (зафиксировано в отчёте Bug G 2.8):

```python
debug_stderr: Any = <_io.TextIOWrapper name='<stderr>' mode='w' encoding='cp1251'>,
```

Этот параметр — **отдельный** от `stderr` callback. По умолчанию SDK пишет debug info в `sys.stderr` напрямую. Мы этот вывод теряем, потому что `flush.py` spawn'ится с `stderr=subprocess.DEVNULL` (в codex/stop.py и session-end.py).

**Fix для diagnostic**: redirect `debug_stderr` в файл в `flush.py`:

```python
# At top of run_flush or module level:
DEBUG_STDERR_FILE = SCRIPTS_DIR / "flush-debug-stderr.log"

# Inside run_flush, open file and pass to options:
with open(DEBUG_STDERR_FILE, "a", encoding="utf-8", buffering=1) as debug_fh:
    options = ClaudeAgentOptions(
        allowed_tools=[],
        max_turns=2,
        stderr=_log_cli_stderr,
        extra_args={"strict-mcp-config": None},
        debug_stderr=debug_fh,  # NEW
    )
    async for message in query(prompt=prompt, options=options):
        ...
```

Это даст **весь** SDK debug output в `flush-debug-stderr.log`. Когда Bug H снова проявится, в этом файле будет **реальная** причина (либо rate limit error, либо timeout trace, либо HTTP error from backend).

### Alternative / additional: verbose iteration logging

Обернуть `async for message in query(...)` loop с logging каждого message event:

```python
message_count = 0
async for message in query(prompt=prompt, options=options):
    message_count += 1
    logging.info("[flush-msg-%d] type=%s", message_count, type(message).__name__)
    if hasattr(message, "content"):
        ...
```

Это покажет **сколько** сообщений дошло до crash, что может намекнуть на точку падения внутри reader loop.

## Files to modify (whitelist)

**Только**: `scripts/flush.py`

Никаких других файлов — ни `hooks/`, ни `pyproject.toml`, ни tests.

## Doc verification (обязательно до правок)

Открой `code.claude.com/docs/en/agent-sdk/python` сейчас и подтверди:

| Что | Expectation |
|---|---|
| `ClaudeAgentOptions.debug_stderr` существует как параметр | ✅ / ❌ |
| `debug_stderr` принимает `Any` (file-like object) | ✅ / ❌ |
| Default = `sys.stderr` | ✅ / ❌ |
| Semantics задокументирована | `<записать цитату или "not documented">` |

Если `debug_stderr` больше не существует или изменил семантику — стоп, в `Discrepancies`.

## Verification steps

### Phase 1 — code patch validation (synthetic)

1. **Import regression**: `uv run python -c "import sys; sys.path.insert(0,'scripts'); import flush; print('ok')"`
2. **TEST MODE smoke**: `WIKI_FLUSH_TEST_MODE=1 uv run python scripts/flush.py /tmp/test.md test-session unknown` → `FLUSH_TEST_OK`
3. **`doctor --full` regression**: hook-specific тесты PASS, никаких регрессий
4. **Synthetic reproducer через Ubuntu WSL** (same path as real Codex):
   ```bash
   wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run --directory "<repo-root>" python scripts/flush.py /tmp/large-context.md bug-h-probe-1 messenger'
   ```
   С большим synthetic context (~15000 chars). Прогнать 3-5 раз подряд чтобы попытаться воспроизвести Bug H.
5. **Проверить `flush-debug-stderr.log`** — должен быть создан и содержать SDK debug output. Показать tail в отчёте.

### Phase 2 — wait for real-world occurrence

Bug H intermittent. Если synthetic reproducer не triggers — ждать real Codex session у пользователя. Каждая real fail теперь будет давать evidence в **новый** `flush-debug-stderr.log` **вместе** с traditional `flush.log`.

### Phase 3 — analysis

Когда первый real Bug H fail случится после этого patch:
1. Найти соответствующий timestamp в `flush-debug-stderr.log`
2. Процитировать **дословно** 50-100 lines вокруг ошибки
3. Классифицировать root cause по гипотезам 1-5
4. Записать в отчёт раздел "Bug H root cause analysis" (аналогично Bug G report раздел 9)
5. Если root cause ясен — предложить **отдельный fix task**

## Out of scope

- **Не** пытайся починить Bug H в этой задаче. Только diagnostic.
- **Не** меняй retry logic, prompt, locking, deduplication.
- **Не** трогай другие файлы.
- **Не** добавляй rate-limit backoff без evidence что это rate limit.
- **Не** меняй `ClaudeAgentOptions` параметры кроме `debug_stderr` + (опционально) message-level logging.

## Acceptance

- ✅ Doc verification пройден
- ✅ `debug_stderr` wired to file
- ✅ Import/TEST MODE/doctor регрессии PASS
- ✅ Synthetic reproducer запущен (минимум 3 попытки); если Bug H воспроизведён — дословно зафиксирован в отчёте
- ✅ `flush-debug-stderr.log` существует, non-empty, показывает SDK diagnostics
- ✅ `Bug H root cause analysis` раздел заполнен (либо root cause identified, либо "waiting for real-world occurrence" с next steps)

## Rollback

```bash
git checkout scripts/flush.py
```

Никаких commit'ов до верификации и ревью пользователем.

## Notes для исполнителя

- **Это diagnostic-only**. Не чини.
- **`debug_stderr` может быть недокументирован** — semantics могут измениться. Перепроверь офдоку.
- **Используй `wsl.exe -d Ubuntu -- ...`** для reproducer, не default `wsl.exe`, иначе попадёшь в docker-desktop distro и не сможешь воспроизвести (lesson из Bug G investigation).
- **При записи в report**: user identity fields (email, orgId, subscriptionType) **редакти**, personal data не публикуется.
- **В отчёт ОБЯЗАТЕЛЬНО добавь раздел `Tools used`** (wiki статьи, офдоки, MCP, repo docs, subagents, линтеры).
- **Изменение минимальное**: одна-две строки в `run_flush`. Не рефактори.
