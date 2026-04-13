# Task — Remove dead `debug_stderr` instrumentation in flush.py (cleanup, NOT Bug H fix)

> **Роль**: исполнитель — Codex. Code-cleanup task. Удалить неиспользуемый диагностический канал.
>
> **Это НЕ fix для Bug H.** Bug H остаётся открытым и интермиттентным. Эта задача — про удаление dead code, который ничего не ловит.
>
> **Иерархия источников правды**:
> 1. Официальная документация Claude Agent SDK Python (`code.claude.com/docs/en/agent-sdk/python`) — primary
> 2. Реальное состояние кода и логов — secondary
> 3. Этот план — derived artifact, может ошибаться
>
> Расхождение план vs дока → побеждает дока, фиксируй в `Discrepancies`.

---

## Context — почему это cleanup, а не fix

Предыдущий task `investigate-flush-py-bug-h.md` добавил в `flush.py` диагностический параметр `debug_stderr=debug_fh` плюс обёртку `with open(DEBUG_STDERR_FILE, ...)` чтобы поймать stderr реального Bug H failure.

**Что выяснилось за день эксплуатации**:

1. **Канал ничего не пишет.** На всех наблюдаемых Bug H failures (включая реальный PreCompact в 22:03:34 и manual репродукцию в 22:24:50) `scripts/flush-debug-stderr.log` остаётся **0 байт**. Это не "повезло не воспроизвести", это подтверждённые failures с пустым debug файлом.

2. **Канал не блокирует Bug H.** Прецедент: Codex'овский pre-fix repro в 22:33:23 — точно тот же flush.py с этим патчем, точно тот же Windows venv path, схожий размер контекста (12469 chars) — **прошёл успешно за 18 секунд**. Если бы `debug_stderr=debug_fh` был причиной Bug H, этот прогон бы упал. Не упал.

3. **Дока подтверждает что канал deprecated.** Из `code.claude.com/docs/en/agent-sdk/python`:
   > `debug_stderr | Any | sys.stderr | Deprecated - File-like object for debug output. Use stderr callback instead`
   
   Параметр помечен **deprecated**, рекомендованная замена — `stderr` callback. У нас в `ClaudeAgentOptions` уже есть `stderr=_log_cli_stderr` — рабочий callback который на WSL path успешно forwards stderr в `flush.log` через `[agent-stderr]` префикс. Это именно то что дока рекомендует вместо deprecated `debug_stderr`.

4. **Чистая бисекция была ошибкой**. Я (Claude) сделал 3 теста подряд и увидел паттерн `debug_stderr → fail`. Codex'овский четвёртый семпл с теми же условиями опроверг гипотезу. Реальный Bug H остаётся **интермиттентным** (~30-50% rate), root cause не локализован, **этот патч не фиксит Bug H**.

**Вывод**: канал доказанно бесполезен, помечен deprecated, дублирует рабочую функциональность через `stderr=` callback. Удаляем как dead code — независимо от Bug H, который остаётся открытым.

---

## Что НЕ делает эта задача

- ❌ **Не фиксит Bug H.** Bug H интермиттентный, root cause неизвестен, требует больше семплов и отдельного investigation. Эта задача его **не трогает** и **не претендует** на fix.
- ❌ **Не требует pre-fix reproduction Bug H.** Bug H невозможно гарантированно воспроизвести (мы пробовали, ~50% rate). Эта задача про cleanup, не про fix, и pre-fix repro Bug H **не нужна**.
- ❌ **Не трогает** `extra_args={"strict-mcp-config": None}` (PR #15 fix для Bug G).
- ❌ **Не трогает** `_log_cli_stderr` callback и `stderr=...` параметр — это рабочая dока-рекомендованная замена deprecated `debug_stderr`, оставляем.

---

## Doc verification (ОБЯЗАТЕЛЬНО перед правкой)

Перечитай **прямо сейчас**, не из памяти и не из этого плана:
- `https://code.claude.com/docs/en/agent-sdk/python` — раздел `ClaudeAgentOptions`
- Найди параметр `debug_stderr`. Подтверди что он помечен **Deprecated** с рекомендацией использовать `stderr` callback.

Если документация **не подтверждает** deprecated статус (например, описание изменилось) — стоп, фиксируй в Discrepancies, спрашивай. Если подтверждает — продолжай.

Зафиксируй точную цитату из доки в `Doc verification` секции отчёта.

---

## Files to modify (whitelist — только этот файл)

**Только**: `scripts/flush.py`

Никаких других файлов. Не трогать `hooks/`, `pyproject.toml`, тесты, doctor, документацию.

---

## Правки — точные

### Правка 1 — удалить константу `DEBUG_STDERR_FILE`

В `scripts/flush.py` около строки 36 удалить:
```python
DEBUG_STDERR_FILE = SCRIPTS_DIR / "flush-debug-stderr.log"
```

### Правка 2 — убрать `with open(...)` обёртку и `debug_stderr=debug_fh`

В функции `run_flush()` (около строк 199-225). Текущий код:
```python
    for attempt in range(max_retries + 1):
        result_text = ""
        try:
            with open(DEBUG_STDERR_FILE, "a", encoding="utf-8", buffering=1) as debug_fh:
                async for message in query(
                    prompt=prompt,
                    options=ClaudeAgentOptions(
                        allowed_tools=[],
                        max_turns=2,
                        stderr=_log_cli_stderr,
                        # Disable account-level MCP server discovery for this
                        # subprocess. ...
                        extra_args={"strict-mcp-config": None},
                        debug_stderr=debug_fh,
                    ),
                ):
                    if hasattr(message, "content"):
                        for block in message.content:
                            if hasattr(block, "text"):
                                result_text += block.text
            break  # success
```

Должно стать:
```python
    for attempt in range(max_retries + 1):
        result_text = ""
        try:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    allowed_tools=[],
                    max_turns=2,
                    stderr=_log_cli_stderr,
                    # Disable account-level MCP server discovery for this
                    # subprocess. The bundled Claude CLI otherwise receives
                    # claude.ai account MCP claims (e.g. Gmail, Calendar) via
                    # OAuth and blocks on their interactive auth flow, causing
                    # "Fatal error in message reader: Command failed with exit
                    # code 1" in non-interactive subprocess context.
                    # Ref: docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md
                    extra_args={"strict-mcp-config": None},
                ),
            ):
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            result_text += block.text
            break  # success
```

Изменения:
- Убрана строка `with open(DEBUG_STDERR_FILE, "a", encoding="utf-8", buffering=1) as debug_fh:`
- Убрано `debug_stderr=debug_fh,`
- `async for` поднимается на один уровень indent выше
- `extra_args={"strict-mcp-config": None}` и комментарии MCP **сохранены**
- `stderr=_log_cli_stderr` **сохранён**

### Правка 3 — удалить файл `scripts/flush-debug-stderr.log` если существует

```bash
rm -f scripts/flush-debug-stderr.log
```

Если файл tracked в git — `git rm scripts/flush-debug-stderr.log`. Если untracked — просто `rm`. Если в `.gitignore` — оставить.

---

## Verification

Bug H интермиттентный, поэтому verification **не** опирается на отсутствие Bug H. Verification опирается на: (a) код после правки синтаксически валиден, (b) flush.py успешно работает на свежем прогоне, (c) doctor regression PASS, (d) WSL path не сломан.

### Phase 1 — apply fix

Внести Правки 1-2 (опционально 3) в `scripts/flush.py`.

```bash
git diff scripts/flush.py
```

Diff должен показать **только** удаление `DEBUG_STDERR_FILE` константы, удаление `with open(...)` обёртки, удаление `debug_stderr=debug_fh,` строки и indent shift внутреннего блока.

### Phase 2 — sanity smoke flush.py (Windows venv)

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
import random, string
lines = [f'[USER] turn {i}: ' + ' '.join(''.join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path('E:/tmp/cleanup-smoke.md').parent.mkdir(parents=True, exist_ok=True)
Path('E:/tmp/cleanup-smoke.md').write_text('\n'.join(lines), encoding='utf-8')
print('chars:', sum(len(l)+1 for l in lines))
"
.venv/Scripts/python.exe scripts/flush.py "E:/tmp/cleanup-smoke.md" "cleanup-smoke-1" "memory-claude" 2>&1 | tail -20
echo "EXIT=$?"
grep "cleanup-smoke-1" scripts/flush.log | tail -5
```

**Ожидание**: либо `Flushed N chars to daily log for session cleanup-smoke-1`, либо `Flush decided to skip: SKIP: ...`. Оба варианта OK — это smoke что код запускается и завершается.

**Если** прогон упадёт с `Fatal error in message reader` → это **не блокер** для cleanup, это известный intermittent Bug H. Зафиксируй в отчёте, повтори ещё 2-3 раза. Если из ~3 попыток хотя бы одна прошла без Fatal error — cleanup можно применять. Если **все** 3 упали — стоп, это новая регрессия от наших правок, спрашивай.

### Phase 3 — doctor regression

```bash
uv run python scripts/wiki_cli.py doctor --full 2>&1 | tail -40
```

Hook-specific тесты (`stop_smoke`, `flush_roundtrip`) должны пройти. Pre-existing red — не блокер, отметь явно какие.

### Phase 4 — WSL regression (важно — этот path и так стабильный, не должны его сломать)

```bash
wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && python3 -c "
from pathlib import Path
import random, string
lines = [f\"[USER] turn {i}: \" + \" \".join(\"\".join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path(\"/tmp/cleanup-smoke-wsl.md\").write_text(\"\n\".join(lines), encoding=\"utf-8\")
" && uv run python scripts/flush.py /tmp/cleanup-smoke-wsl.md cleanup-smoke-wsl-1 memory-claude 2>&1 | tail -20'
grep "cleanup-smoke-wsl-1" scripts/flush.log | tail -5
```

**Ожидание**: success или SKIP, **без** Fatal error. WSL path был стабильный весь день, не должны его сломать.

---

## Acceptance criteria

- ✅ Doc verification: подтверждена deprecated пометка `debug_stderr` в офдоке, цитата в отчёте
- ✅ Phase 1: внесены **только** Правки 1-2 (опционально 3) в `scripts/flush.py`, никаких других файлов
- ✅ Phase 2: Windows smoke flush.py прошёл (success или SKIP), либо если упал — повторяется до получения хотя бы одного успеха в ≤3 попытках
- ✅ Phase 3: `doctor --full` hook-specific тесты PASS
- ✅ Phase 4: WSL smoke прошёл успешно
- ✅ В отчёте явно зафиксировано: **это не fix Bug H**, Bug H остаётся открытым

---

## Out of scope

- **Не** чинить Bug H. Эта задача его не трогает.
- **Не** искать другие диагностические каналы. Если в будущем понадобится — отдельная задача, не сейчас.
- **Не** трогать `extra_args`, `_log_cli_stderr`, retry loop, lock acquisition.
- **Не** делать commit / push. Только локальные изменения + отчёт.
- **Не** трогать предыдущий отчёт `investigate-flush-py-bug-h-report.md` — он остаётся как историческая запись неудачной диагностики.
- **Не** трогать предыдущий план `revert-bug-h-diagnostic-instrumentation.md` — Claude (parent) пометит его как superseded отдельно.

---

## Rollback

```bash
git checkout scripts/flush.py
```

И вернуть `scripts/flush-debug-stderr.log` если был удалён (`touch scripts/flush-debug-stderr.log` — пустой файл, оригинал и так был пустой).

---

## Pending user actions

Никаких. Это полностью автономный code-cleanup task в одном файле.

---

## Notes для исполнителя (Codex)

- **Это не fix Bug H, это cleanup dead code.** Если ты пишешь в отчёте "Bug H fixed" — это неправильный framing. Правильный: *"Removed dead diagnostic channel that never captured anything; Bug H remains open intermittent issue requiring more samples"*.
- **Я (Claude, parent) сделал ошибочную бисекцию** в живой сессии 2026-04-13 22:24-22:26 и заявил что `debug_stderr=debug_fh` детерминированно вызывает Bug H. Твой собственный pre-fix repro в 22:33:23 опроверг это (тот же патч → success). Ты был прав что остановился по task contract предыдущего плана `revert-bug-h-diagnostic-instrumentation.md`. Этот новый план учитывает твоё опровержение и переформулирует задачу честно.
- **Diff минимальный** — только удаление параметра, обёртки, константы. Никаких opportunistic улучшений в flush.py.
- **Phase 2 может flake** — Bug H ~30-50% rate. Это нормально, cleanup всё равно валиден. Просто повтори smoke 2-3 раза если первый раз упадёт. Если **все 3** упали — тогда что-то сломано нашей правкой и нужна эскалация.
- **Doc verification обязателен** — найди и процитируй deprecated пометку. Если в доке `debug_stderr` больше не deprecated — стоп, спрашивай (это значит реальность изменилась с момента написания плана).
- **Создай отчёт** в `docs/codex-tasks/remove-dead-debug-stderr-instrumentation-report.md` по той же структуре что предыдущие task reports.
