# [SUPERSEDED 2026-04-13 22:40] — see `remove-dead-debug-stderr-instrumentation.md`

> **Этот план отменён.** Гипотеза "diagnostic IS Bug H" опровергнута Codex'овским pre-fix repro в 22:33:23: тот же патч, тот же Windows venv, схожий контекст → success. Bug H остаётся **интермиттентным** (~30-50% rate), root cause неизвестен, и `debug_stderr=debug_fh` его не вызывает.
>
> Следующая задача — **`docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md`** — переформулирует ту же правку как cleanup dead code (канал ничего не пишет, deprecated в офдоке), без претензий на fix Bug H.
>
> Этот файл сохраняется как историческая запись неудачной гипотезы.

---

# [ORIGINAL] Task — Revert Bug H diagnostic instrumentation (it IS Bug H)

> **Роль**: исполнитель — Codex. Code-fix task. Откатить диагностический патч в `flush.py`, который сам по себе вызывает Bug H.
>
> **Иерархия источников правды**:
> 1. Официальная документация Claude Agent SDK Python (`code.claude.com/docs/en/agent-sdk/python`) — primary
> 2. Реальное состояние кода и логов — secondary
> 3. Этот план — derived artifact, может ошибаться
>
> Расхождение план vs дока → побеждает дока, фиксируй в `Discrepancies`.

---

## TL;DR

Параметр `debug_stderr=debug_fh` в `ClaudeAgentOptions(...)` под Windows host **детерминированно** ломает flush.py через `claude_agent_sdk` с `Fatal error in message reader: Command failed with exit code 1`. Stream messages приходят успешно (`SystemMessage × N`, `AssistantMessage`, `RateLimitEvent`, `ResultMessage`), а **затем** на cleanup phase child process возвращает exit 1 и SDK выбрасывает `ProcessError`. Файл `flush-debug-stderr.log` при этом остаётся 0 байт — диагностический канал ничего не пишет даже на подтверждённой репродукции.

**Фикс**: убрать только то что добавил предыдущий "investigate Bug H" патч — `debug_stderr=debug_fh`, обёртку `with open(DEBUG_STDERR_FILE, ...)`, и константу `DEBUG_STDERR_FILE`. Stderr callback `_log_cli_stderr` и его проводку в `stderr=...` НЕ ТРОГАТЬ — это работает.

---

## Bisection evidence (выполнено в живой сессии 2026-04-13 22:24-22:26)

Все три теста запускались из `<repo-root>` через `.venv/Scripts/python.exe`, на Windows host, с тем же bundled `claude.exe`.

**Тест 1 — flush.py с реальным контекстом 12571 chars** (через CLI `flush.py <ctx> <session> <project>`):
```
22:24:50 INFO  [flush] Starting flush for session bug-h-repro-direct-1 (12571 chars)
22:24:52 INFO  [flush] Using bundled Claude Code CLI: E:\...\claude.exe
22:25:08 ERROR [flush] Fatal error in message reader: Command failed with exit code 1
22:25:08 ERROR [flush] Agent SDK query failed: Command failed with exit code 1
```
`scripts/flush-debug-stderr.log` после fail = **0 байт**.

**Тест 2 — изолированный `claude_agent_sdk.query()` БЕЗ `debug_stderr`**, prompt 13060 chars, max_turns=2, `extra_args={'strict-mcp-config': None}`, stderr callback:
```
MSG: SystemMessage × 4
MSG: AssistantMessage
MSG: RateLimitEvent
MSG: ResultMessage
EXIT=0
```
Чисто.

**Тест 3 — то же что Тест 2, единственное отличие: добавлен `debug_stderr=debug_fh`** (Path `E:/tmp/bug-h-debug-test.log`):
```
MSG: SystemMessage × 3
MSG: AssistantMessage
MSG: RateLimitEvent
MSG: ResultMessage
EXCEPTION: Exception Command failed with exit code 1
Error output: Check stderr output for details
EXIT=0  (Python wrapper caught the exception)
```
`E:/tmp/bug-h-debug-test.log` = **0 байт**.

**Бисекция чистая**: единственное отличие между ✅ и ❌ — параметр `debug_stderr=debug_fh`. Все остальные слои (binary, subprocess, sdk pipe wiring, MCP, prompt size, max_turns, concurrent claude.exe processes под одним user) исключены отдельными прогонами в той же сессии — все ✅.

**Ironic origin**: этот параметр был добавлен предыдущим Codex task `investigate-flush-py-bug-h.md` именно для того чтобы поймать stderr реального Bug H. Вместо этого он сам стал Bug H. Скорее всего "исходный" Bug H ~33% intermittent был остаточным Bug G до полной стабилизации PR #15, либо первыми двумя TEST MODE прогонами, и мы с ним конфабулировали.

---

## Doc verification (ОБЯЗАТЕЛЬНО перед правкой)

Перечитай **прямо сейчас**, не из памяти и не из этого плана:
- `https://code.claude.com/docs/en/agent-sdk/python` — раздел `ClaudeAgentOptions` (или эквивалент)
- Найди documentation параметра `debug_stderr`. Что он принимает? Какие платформы поддерживаются? Есть ли known issues с Windows / file handles / async cleanup?

Если документация говорит что `debug_stderr` НЕ принимает Python file objects (или принимает только `TextIO` определённого типа), зафиксируй это в Doc verification разделе отчёта. Если документация говорит что Windows поддерживается с file handles — зафиксируй это тоже, и пометь как **поведенческое расхождение docs vs реальность** в Discrepancies.

Если документация недоступна или раздел пуст — зафиксируй это явно. Не выдумывай.

---

## Files to modify (whitelist — только этот файл)

**Только**: `scripts/flush.py`

Никаких других файлов. Не трогать `hooks/`, `pyproject.toml`, тесты, doctor.

---

## Fix — точные правки

### Правка 1 — удалить константу `DEBUG_STDERR_FILE`

В `scripts/flush.py` около строки 36:
```python
DEBUG_STDERR_FILE = SCRIPTS_DIR / "flush-debug-stderr.log"
```
**Удалить полностью**. Константа использовалась только в одном месте — diagnostic wrapper.

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
- Убрано выравнивание (`async for` поднимается на один уровень indent выше)
- `extra_args` и комментарии MCP **сохранены** — это корректно работающая часть от PR #15

### Правка 3 — почистить уже существующий `scripts/flush-debug-stderr.log` (опционально)

Если файл существует — `git rm --cached scripts/flush-debug-stderr.log` и удалить с диска. Это **не блокер** для фикса, но прибраться полезно. Если файл попал в `.gitignore` — оставить как есть.

### Что НЕ менять

- **Не трогать** `_log_cli_stderr` callback и параметр `stderr=_log_cli_stderr`. Этот канал работает корректно (на Linux flush'и на WSL стабильно проходят), и на Windows он молчит **не из-за поломки**, а потому что claude.exe в этом сценарии в stderr ничего не пишет.
- **Не трогать** `extra_args={"strict-mcp-config": None}` — это PR #15 fix для Bug G, остаётся.
- **Не трогать** `try:`/`except ProcessError`/retry logic — оно правильное, просто было слегка глубже залезено indent'ом.
- **Не трогать** ничего другого в `flush.py`. Никаких opportunistic улучшений.

---

## Verification

### Phase 1 — точная репродукция фикса (выполняет Codex)

Перед фиксом — повторить bisection теста 1, чтобы убедиться что Bug H ещё воспроизводится на текущей правке. Создать context file и запустить flush.py:

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
import random, string
lines = [f'[USER] turn {i}: ' + ' '.join(''.join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path('E:/tmp/bug-h-precheck.md').parent.mkdir(parents=True, exist_ok=True)
Path('E:/tmp/bug-h-precheck.md').write_text('\n'.join(lines), encoding='utf-8')
print('chars:', sum(len(l)+1 for l in lines))
"
.venv/Scripts/python.exe scripts/flush.py "E:/tmp/bug-h-precheck.md" "bug-h-precheck-pre" "memory-claude" 2>&1 | tail -20
tail -10 scripts/flush.log
```

**Ожидание ДО фикса**: `Fatal error in message reader: Command failed with exit code 1` в `flush.log`.

Если репродукция **не** выстреливает (например, сценарий уже изменился между подготовкой плана и исполнением) — стоп, не применяй фикс, зафиксируй в Discrepancies и спроси.

### Phase 2 — применить фикс

Внести Правки 1-2 в `flush.py`. Опционально Правка 3 (cleanup).

### Phase 3 — пост-фикс верификация

Повторить тот же сценарий после фикса:

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
import random, string
lines = [f'[USER] turn {i}: ' + ' '.join(''.join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path('E:/tmp/bug-h-postcheck.md').parent.mkdir(parents=True, exist_ok=True)
Path('E:/tmp/bug-h-postcheck.md').write_text('\n'.join(lines), encoding='utf-8')
"
.venv/Scripts/python.exe scripts/flush.py "E:/tmp/bug-h-postcheck.md" "bug-h-postcheck-post" "memory-claude" 2>&1 | tail -20
tail -10 scripts/flush.log
```

**Ожидание ПОСЛЕ фикса**: `Flushed N chars to daily log for session bug-h-postcheck-post` (либо `Flush decided to skip: SKIP: ...` если модель решит что мусорный контекст не стоит сохранять — это тоже OK, главное что **нет** `Fatal error in message reader`).

### Phase 4 — regression

```bash
uv run python scripts/wiki_cli.py doctor --full 2>&1 | tail -40
```

Hook-specific тесты (`stop_smoke`, `flush_roundtrip`) должны пройти. Repo-wide red остаётся pre-existing — не блокер.

### Phase 5 — WSL regression (важно)

Этот фикс не должен сломать WSL path который и так стабильно работал. Прогнать стандартный WSL smoke:

```bash
wsl.exe -d Ubuntu -- bash -lc 'cd <repo-root> && uv run python scripts/flush.py /tmp/wsl-test.md wsl-postfix-1 memory-claude 2>&1 | tail -20'
```

(Сначала создать `/tmp/wsl-test.md` в WSL аналогично precheck'у.) Ожидание: успешный flush либо SKIP, **без** Fatal error.

---

## Acceptance criteria

- ✅ Phase 1: pre-fix reproduction подтверждена (Fatal error в flush.log)
- ✅ Phase 2: внесены только Правки 1-2 (опционально 3) в `scripts/flush.py`
- ✅ Phase 3: post-fix → нет Fatal error, либо успех либо SKIP
- ✅ Phase 4: doctor --full hook-specific тесты PASS
- ✅ Phase 5: WSL path остался зелёным
- ✅ В отчёте есть Doc verification раздел про `debug_stderr` параметр (что нашлось / что не нашлось в офдоке)

---

## Out of scope

- **Не** чинить sam debug_stderr канал (например, через `os.dup()` или другой механизм). Доступа к диагностике через этот параметр нам не нужно — fix полностью устраняет необходимость в нём.
- **Не** искать alternative диагностические каналы (subprocess wrapper, env var, monkey-patch SDK). Если в будущем понадобится stderr визибильность — сделаем отдельной задачей через `_log_cli_stderr` callback который и так есть.
- **Не** трогать другие хуки, doctor, тесты, документацию. Whitelist — `scripts/flush.py`.
- **Не** делать commit или push без явной команды пользователя. Только локальные изменения + отчёт.

---

## Rollback

```bash
git checkout scripts/flush.py
```

И удалить `scripts/flush-debug-stderr.log` если был создан.

---

## Pending user actions

Никаких. Это полностью code-fix task в одном файле.

---

## Notes для исполнителя (Codex)

- Изменение **минимальное и обратное** к предыдущему "investigate Bug H" патчу. Если ты помнишь тот патч — просто откати его аккуратно, **сохранив** `extra_args={"strict-mcp-config": None}` (это от другого Codex task'а — Bug G layer 3 / PR #15).
- **Не делай opportunistic правок** в flush.py. Не трогай retry loop, lock acquisition, deduplication, debounce — всё это работает.
- **Сначала Phase 1** (pre-fix repro). Если не воспроизводится — **СТОП**, спрашивай. Это значит что за время между планом и исполнением что-то изменилось, и фикс может быть неверным для нового состояния.
- **В отчёте** приведи полные tail'ы `flush.log` ДО и ПОСЛЕ фикса (по 10-15 строк каждый), чтобы можно было визуально сверить что Fatal error действительно ушёл.
- **Doc verification** — обязательно перечитай актуальную документацию `claude_agent_sdk` на момент исполнения. Если найдёшь объяснение почему `debug_stderr` ломается под Windows — зафиксируй. Если не найдёшь — тоже зафиксируй.
- Создай отчёт в `docs/codex-tasks/revert-bug-h-diagnostic-instrumentation-report.md` по той же структуре что предыдущие task reports (Pre-flight → Doc verification → Changes → Verification → Tools used → Self-audit).
