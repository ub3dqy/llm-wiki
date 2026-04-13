# Task — Investigate Bug G: flush.py Agent SDK exit code 1

> **Роль**: исполнитель — Codex. Этот файл — **derived plan**, написанный Claude'ом
> на основе чтения официальной документации и анализа реальных логов. Это **не** primary
> source of truth.
>
> **Иерархия источников правды**:
> 1. Официальная документация Claude Agent SDK Python (`code.claude.com/docs/en/agent-sdk/python`) — primary.
> 2. Реальное состояние кода и логов в проекте — secondary.
> 3. Этот план — derived artifact, может содержать ошибки.
>
> Расхождение план vs дока → побеждает дока. Фиксируй в `Discrepancies`.

---

## Важное: это diagnostic-only задача, не fix

**Не пытайся починить Bug G в этой задаче.** Root cause пока неизвестен — у нас есть симптом
(`Agent SDK query failed: Command failed with exit code 1`), но **ни одной реальной причины**
от CLI, потому что текущий `flush.py` глотает stderr от bundled Claude binary.

Цель этой задачи — **добавить видимость**:
- перехватить `stderr` от bundled CLI через SDK callback
- перехватить `ProcessError` отдельно и вытащить из него `exit_code` + `stderr`
- запустить reproducer
- **записать** реальную ошибку в отчёт
- **НЕ чинить** — фикс будет следующей задачей, уже с конкретным root cause на руках

Если у тебя появится соблазн "попутно исправить", когда ты увидишь real error — **стоп**,
фиксируй в `Out-of-scope-temptations`, оставь для следующей задачи.

---

## Context — что уже сделано

Фикс-волна Bug A-F (PR #12, merged `2026-04-13T12:40:54Z`) закрыла все проблемы на уровне
Codex Stop hook. После merge `flush.log` показывает:

```
2026-04-13 13:20:38 INFO  [codex-stop] Spawned flush.py for session ... (30 turns, 9359 chars)
2026-04-13 13:20:39 INFO  [flush]      Starting flush for session ... (9359 chars)
2026-04-13 13:20:40 INFO  [flush]      Using bundled Claude Code CLI: .../claude_agent_sdk/_bundled/claude
2026-04-13 13:20:44 ERROR [flush]      Fatal error in message reader: Command failed with exit code 1
2026-04-13 13:20:44 ERROR [flush]      Agent SDK query failed: Command failed with exit code 1
```

Stop hook теперь работает чисто — Spawned без Broken pipe. Но следующий слой —
`scripts/flush.py` → Claude Agent SDK → bundled Claude Code CLI — падает на первом сообщении
с exit code 1. **Это последний блокер** для того, чтобы реальные Codex сессии приводили к
записи в `daily/YYYY-MM-DD.md`.

Этот баг наблюдается как **минимум 5 раз подряд** с разными session ID за один день, без
каких-либо variations — это детерминированный баг, не флапающий.

Parent issue: [#5](https://github.com/ub3dqy/llm-wiki/issues/5)
Target issue: [#6](https://github.com/ub3dqy/llm-wiki/issues/6) (Bug G)
Possibly related: [#8](https://github.com/ub3dqy/llm-wiki/issues/8) (`<total_tokens>` injection),
[#13](https://github.com/ub3dqy/llm-wiki/issues/13) (`.venv` churn on Windows)

---

## Critical finding from official SDK docs

**[OFFICIAL-SDK]** Из `code.claude.com/docs/en/agent-sdk/python`:

> The SDK **does capture stderr** via the `stderr` callback parameter:
> ```python
> stderr: Callable[[str], None] | None = None
> ```
> "Callback function for stderr output from CLI"

И:

> `ProcessError` exception has fields:
> ```python
> class ProcessError(ClaudeSDKError):
>     def __init__(self, message: str, exit_code: int | None = None, stderr: str | None = None):
>         self.exit_code = exit_code
>         self.stderr = stderr
> ```
> The error "Command failed with exit code 1" is wrapped in a `ProcessError` with
> `exit_code = 1` and `stderr` containing the actual error from the CLI.

**Прямой вывод**: текущий `flush.py:199-205` делает `except Exception as e` и логирует только
`str(e)` — это **обрезает** `exit_code` и `stderr`. Реальная ошибка от CLI теряется.
Добавление обработки `ProcessError` + `stderr` callback вернёт её в лог.

Это не догадка — это прямо задокументировано SDK.

## Sources table

- `[OFFICIAL-SDK]` — `code.claude.com/docs/en/agent-sdk/python` (perefetched в этой сессии Claude'ом, обязан проверить самостоятельно перед правкой)
- `[OFFICIAL-CODEX]` — `developers.openai.com/codex/hooks` (для контекста, не касается этой задачи)
- `[EMPIRICAL]` — реальные записи в `scripts/flush.log` на диске
- `[STACK-TRACE]` — дословно из логов
- `[PROJECT]` — решения этого проекта

## Target file (whitelist)

**Только**: `scripts/flush.py`

Никакие другие файлы не трогать — ни `hooks/`, ни `compile.py`, ни `doctor.py`, ни тесты.
Если возникнет соблазн "заодно" — `Out-of-scope-temptations`.

## Fix design (diagnostic patch)

### Изменение 1 — Добавить `stderr` callback в ClaudeAgentOptions

**Где**: `scripts/flush.py::run_flush` (строки 147-205). Внутри вызова `query(...)` нужно
передать `ClaudeAgentOptions(stderr=..., allowed_tools=[], max_turns=2)`.

**Как**:

```python
def _log_cli_stderr(line: str) -> None:
    """Forward each stderr line from bundled Claude CLI to flush.log."""
    # line can be multi-char chunk including newline; split defensively.
    for subline in line.splitlines():
        if subline.strip():
            logging.info("[agent-stderr] %s", subline)
```

И в `run_flush`:

```python
async for message in query(
    prompt=prompt,
    options=ClaudeAgentOptions(
        allowed_tools=[],
        max_turns=2,
        stderr=_log_cli_stderr,  # <-- NEW
    ),
):
    ...
```

**Acceptance**: каждая строка stderr от bundled binary теперь попадает в `flush.log` с
префиксом `[agent-stderr]`.

### Изменение 2 — Обработать `ProcessError` отдельно с exit_code и stderr

**Где**: тот же файл, блок retry на строках 199-205:

```python
except Exception as e:
    if attempt < max_retries and "timeout" in str(e).lower():
        logging.warning("Agent SDK timeout (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
        await asyncio.sleep(2)
        continue
    logging.error("Agent SDK query failed: %s", e)
    return
```

**Как**: импортировать `ProcessError` и ловить отдельно до общего `Exception`:

```python
from claude_agent_sdk import ClaudeAgentOptions, query
try:
    from claude_agent_sdk import ProcessError
except ImportError:
    # SDK < 0.1.58 may not export ProcessError; fall back to generic Exception.
    ProcessError = None  # type: ignore[assignment,misc]
```

И в блоке retry:

```python
except Exception as e:
    # Try to extract SDK-specific diagnostics first.
    if ProcessError is not None and isinstance(e, ProcessError):
        exit_code = getattr(e, "exit_code", None)
        stderr_text = getattr(e, "stderr", None) or "<empty>"
        logging.error(
            "Agent SDK ProcessError: exit_code=%s message=%s",
            exit_code,
            e,
        )
        # Split stderr into lines so it's readable in flush.log.
        for subline in stderr_text.splitlines():
            if subline.strip():
                logging.error("[process-stderr] %s", subline)
        return

    if attempt < max_retries and "timeout" in str(e).lower():
        logging.warning("Agent SDK timeout (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
        await asyncio.sleep(2)
        continue
    logging.error("Agent SDK query failed: %s", e)
    return
```

**Acceptance**: если query() падает с `ProcessError`, в `flush.log` теперь видны:
- `exit_code` числом
- полный `stderr` построчно с префиксом `[process-stderr]`

### Что НЕ менять

- **Не** менять логику retry — она корректно обрабатывает timeouts.
- **Не** менять prompt или tool configuration.
- **Не** менять `append_to_daily_log`, deduplication, locking — они не связаны.
- **Не** менять вообще ничего вне `run_flush` и импортов.
- **Не** трогать `scripts/config.py`, `hooks/`, `pyproject.toml`, `AGENTS.md`, `CLAUDE.md`.
- **Не** пытаться чинить root cause после того как увидишь реальную ошибку. **Это следующая задача.**

## Reproducer

После правки нужно **воспроизвести** баг и записать обогащённый лог в отчёт.

### Вариант A — Synthetic reproducer через manual flush.py call

Это самый чистый способ — не требует реальной Codex сессии:

```bash
# Создать synthetic context file с достаточным объёмом
mkdir -p /tmp/bug-g-repro
cat > /tmp/bug-g-repro/context.md <<'EOF'
**User:** Can you help me understand how Python asyncio event loops work?

**Assistant:** Python's asyncio module provides an event loop that schedules
and runs coroutines. The event loop is essentially a while loop that checks
for tasks that are ready to run and executes them one at a time. When a
coroutine hits an `await` statement on a non-ready future, it yields control
back to the event loop, which then runs other ready tasks.

**User:** What's the difference between asyncio.run() and loop.run_until_complete()?

**Assistant:** `asyncio.run()` is the high-level interface that creates a new
event loop, runs the coroutine to completion, and closes the loop. It's the
recommended way to run async code in modern Python. `loop.run_until_complete()`
is a lower-level method that requires you to manually manage the event loop
lifecycle.
EOF

# Вызвать flush.py прямо (как его спавнит Codex Stop hook)
cd "<repo-root>"
uv run python scripts/flush.py /tmp/bug-g-repro/context.md bug-g-repro-1 messenger

# Посмотреть что попало в flush.log
tail -30 scripts/flush.log | grep -E "\[flush\]|\[agent-stderr\]|\[process-stderr\]"
```

### Вариант B — Direct bundled binary test

Если вариант A не покажет stderr (например, если SDK swallows его до callback), можно вызвать
bundled binary напрямую, минуя SDK:

```bash
# Узнать путь bundled Claude CLI из WSL venv
wsl.exe -- bash -lc 'ls -la <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/'

# Попробовать вызвать напрямую с минимальным prompt
wsl.exe -- bash -lc '<linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude --help 2>&1 | head -20'

# Попробовать с простым query
wsl.exe -- bash -lc '<linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude --print "say hi" 2>&1 | head -30'
```

Записать **дословный** вывод в отчёт, раздел `2.3 Direct binary test`.

### Вариант C — Environment probe

Проверить, что видит subprocess:
- `ANTHROPIC_API_KEY` (may or may not be required, docs не обязывают)
- `HOME`, `PATH`, `LANG`
- Наличие creds файлов (`~/.claude/credentials.json` или похожие)

```bash
wsl.exe -- bash -lc 'env | grep -iE "anthropic|claude|home|path" | head -20'
wsl.exe -- bash -lc 'ls -la ~/.claude/ 2>&1 | head -10'
```

### Вариант D — `<total_tokens>` injection probe в SDK subprocess

**Важный контекст**: Claude (Opus 4.6) в **этой** Claude Code CLI сессии самоотчитался,
что `<total_tokens>` injection в его user turn'ах **не активен** на текущем аккаунте.
Но это **negative result только для CLI client**, не гарантирует отсутствие injection
в **Agent SDK subprocess** — SDK использует отдельный auth path через bundled Claude
binary, и A/B test может быть привязан к session/endpoint, а не к аккаунту.

Для **independent** проверки injection в контексте, в котором реально бежит `flush.py`,
нужно задать SDK **прямой probe-вопрос** из того же subprocess chain.

Временно (только на этот repro) изменить `run_flush` prompt на:

```python
probe_prompt = """You are a diagnostic probe. Answer ONLY these two questions, nothing else:

1. Do you see any <system> block attached to this user turn that contains
   a <total_tokens>NNNN tokens left</total_tokens> tag? Answer exactly "YES" or "NO".

2. If YES, quote the exact content of the tag on a new line prefixed with "TAG: ".
   If NO, output the single line "TAG: <none>".

Respond with nothing else. No explanation, no commentary."""
```

И запустить reproducer Вариант A с этим temporary prompt'ом. Ожидаемые outcomes:

- **Response "NO" / "TAG: <none>"** → injection неактивен и в SDK subprocess тоже. Гипотеза #8 REJECTED. Bug G имеет другую причину, сосредоточиться на #13, auth, version.
- **Response "YES" / "TAG: <total_tokens>10000 tokens left</total_tokens>"** → injection активен в SDK subprocess (но не в CLI — что само по себе interesting). Гипотеза #8 CONFIRMED. Next fix: добавить workaround preamble в `flush.py` prompt.
- **ProcessError exit 1 снова** → probe тоже падает, injection гипотезу нельзя ни подтвердить, ни опровергнуть, переходить к Вариантам B/C.

**ВАЖНО**: после probe run **откатить** prompt на оригинальный (git checkout), чтобы не
пойти в merge с probe-версией. Probe — чисто инструмент диагностики, не final code.
Результат probe — в отчёт, не в commit.

---

## Evidence collection checklist (fill in report)

После каждого реза reproducer'а, заполни в отчёте:

1. **Вариант A (synthetic through flush.py)**:
   - полный stdout + stderr от `uv run python scripts/flush.py ...`
   - `tail -30 scripts/flush.log | grep -E "[flush]|[agent-stderr]|[process-stderr]"`
2. **Вариант B (direct binary)**:
   - `--help` output (первые 20 строк)
   - `--print "say hi"` output (первые 30 строк)
3. **Вариант C (env probe)**:
   - env vars
   - creds files
4. **SDK version check**:
   - `<linux-home>/.cache/llm-wiki/.venv/bin/python -c "import claude_agent_sdk; print(claude_agent_sdk.__version__)"`
5. **Historical log grep**:
   - `grep -c "Agent SDK query failed" scripts/flush.log` — сколько раз баг проявлялся
   - Даты первого и последнего вхождения

Из этих данных собрать в отчёт секцию **"Bug G root cause analysis"** с обоснованным
диагнозом — какая из возможных причин подтверждается и какая опровергается.

## Possible root causes to check (matrix в отчёте)

| Гипотеза | Evidence для подтверждения | Evidence для опровержения |
|---|---|---|
| **#8** — `<total_tokens>` injection affects Agent SDK subprocess | Probe Вариант D вернул "YES"; CLI stderr упоминает `<total_tokens>` или context anxiety; error содержит "tokens left" | Probe Вариант D вернул "NO"; CLI падает до любого upstream response. **Note**: Claude в host Claude Code CLI сессии самоотчитался что injection не активен, но это не переносится автоматически на SDK subprocess — probe обязателен. |
| **#13** — `.venv` churn corrupted bundled binary | `.venv/lib/python3.14/...` частично отсутствует; binary не запускается даже с `--help` | binary корректно отвечает на `--help`, чистый `--print` работает |
| **Auth failure** — `ANTHROPIC_API_KEY` missing or wrong | stderr упоминает "authentication", "401", "unauthorized"; `~/.claude/credentials.json` отсутствует | env отдаёт валидный key, credentials.json существует |
| **CLI/SDK version mismatch** | stderr упоминает "unknown flag", "unexpected argument"; `claude --version` показывает pre-release или incompatible | versions совпадают с SDK requirement |
| **Path / cwd issue в subprocess** | binary работает в shell, но падает в subprocess с иной `HOME` / `PWD` | env в subprocess идентичен shell env |
| **Rate limit / quota** | stderr "rate limit", "429", "quota exceeded" | no rate limit keywords |
| **Unknown** — ничего из выше | — | — |

Codex **обязан** заполнить эту матрицу в отчёте конкретными фактами.

## Verification (Phase 1 — diagnostic only)

### 1.1 Regression — flush.py всё ещё импортируется

```bash
uv run python -c "import sys; sys.path.insert(0, 'scripts'); import flush; print('imports OK')"
```

Ожидание: `imports OK`, без traceback.

### 1.2 TEST MODE smoke (не падает до Agent SDK call)

```bash
export WIKI_FLUSH_TEST_MODE=1
echo "test" > /tmp/bug-g-test-context.md
uv run python scripts/flush.py /tmp/bug-g-test-context.md test-session-bug-g unknown
cat scripts/flush-test-marker.txt 2>&1 | head
unset WIKI_FLUSH_TEST_MODE
```

Ожидание: `flush-test-marker.txt` обновлён, никаких traceback. Это проверяет, что diagnostic
patch не сломал TEST MODE path (который используется в `doctor --full` `flush_roundtrip`).

### 1.3 doctor --full regression

```bash
uv run python scripts/doctor.py --full 2>&1 | tail -30
```

Ожидание: `flush_roundtrip` PASS, `stop_smoke` PASS. Pre-existing structural_lint red
остаётся (не связано).

### 1.4 Reproducer run — real Bug G trigger

См. раздел "Reproducer" выше — прогнать Вариант A обязательно, B и C опционально для
диагностики.

Ожидание: в `flush.log` появляются **новые** строки с префиксами `[agent-stderr]` и/или
`[process-stderr]`, содержащие **реальную** ошибку от CLI (не "exit code 1").

---

## Acceptance criteria

Задача считается выполненной когда:

- ✅ Изменение 1 применено: `stderr=_log_cli_stderr` в `ClaudeAgentOptions`
- ✅ Изменение 2 применено: отдельный `ProcessError` handler с `exit_code` и stderr logging
- ✅ `uv run python -c "import flush"` работает (regression)
- ✅ TEST MODE smoke работает (regression)
- ✅ `doctor --full` hook-specific тесты PASS (regression)
- ✅ Reproducer Вариант A запущен, вывод записан в отчёт
- ✅ Минимум одна реальная CLI ошибка попала в `flush.log` с префиксом `[agent-stderr]` или `[process-stderr]`
- ✅ Матрица причин в отчёте заполнена конкретными фактами
- ✅ Root cause analysis в отчёте указывает **обоснованный** диагноз (или честное "inconclusive" если evidence противоречив)
- ✅ Self-audit checklist пройден

## Out of scope

1. **Любой фикс** Bug G — это **следующая задача**. Только diagnostic.
2. **Изменение retry logic** — сейчас она работает для timeouts, не трогаем.
3. **Изменение prompt** — не связано с Bug G.
4. **Bug H / что-то новое** — если найдёшь ещё баги по ходу, в `Out-of-scope-temptations`.
5. **Переход на другой SDK / LLM провайдер** — нет.
6. **Чистка pre-existing lint debt** — unrelated.
7. **`.venv` churn fix** — отдельная задача (#13).

## Rollback

```bash
git checkout scripts/flush.py
```

Никаких commit'ов до верификации и ревью пользователем.

## Notes для исполнителя (Codex)

- Ты **не чинишь** Bug G. Ты добавляешь visibility и собираешь evidence.
- **Обязательно** перепроверь официальную SDK doc (`code.claude.com/docs/en/agent-sdk/python`)
  до правки — контракт `stderr` callback и `ProcessError` структура могли измениться.
- Если при импорте `from claude_agent_sdk import ProcessError` падает — в отчёт Discrepancies,
  используй fallback `ProcessError = None` и полагайся только на `stderr` callback.
- `_log_cli_stderr` должен быть **idempotent** и **safe** — никаких raise, только logging.
- В reproducer **используй один и тот же context file** для нескольких запусков, чтобы удобно
  сравнивать вывод до/после правки.
- Если reproducer Вариант A не триггерит баг (например, короткий synthetic context слишком
  тривиальный для SDK → моментально возвращает `SKIP`), увеличь context до ~2000 символов
  реалистичного кода/диалога.
- **В self-audit отчёта** помеченная секция `Bug G root cause analysis` должна содержать
  не просто "exit code 1", а **конкретный** первопричинный сигнал, например:
  - `"[agent-stderr] Error: ANTHROPIC_API_KEY not set"`
  - `"[process-stderr] Error: Unknown flag --output-format json"`
  - `"[agent-stderr] <total_tokens>10000 tokens left</total_tokens>"` (injection confirmed)
  - и т.п.
- Если **ничего нового** не появилось в логе — это тоже валидный результат, но тогда в
  отчёте раздел `Discrepancies` должен явно сказать: "stderr callback не сработал, возможно
  SDK swallows stderr до callback, нужно investigating SDK source code или direct binary path (Вариант B/C)".
