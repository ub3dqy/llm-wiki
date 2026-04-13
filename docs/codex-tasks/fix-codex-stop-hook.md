# Task — Fix Codex Stop Hook Reliability

> **Роль**: исполнитель — Codex. Этот файл — **derived plan**, написанный Claude'ом
> на основе чтения официальной документации. Это **не** primary source of truth.
>
> ## Иерархия источников правды (от высшей к низшей)
>
> 1. **Официальная документация** — primary source of truth.
>    - `developers.openai.com/codex/hooks`
>    - `developers.openai.com/codex/config-advanced`
>    - `code.claude.com/docs/en/hooks`
> 2. **Реальное состояние кода и файлов проекта** — secondary source.
> 3. **Этот план** — derived artifact, может содержать ошибки выписывания или быть
>    устаревшим относительно официальной доки.
>
> **Правило двойной проверки**: перед каждым ключевым шагом (новая функция, изменение
> контракта, новый формат данных) **сверься с официальной докой**. Если план и дока
> расходятся — приоритет у **доки**, и зафиксируй разночтение в отчёте,
> раздел `Discrepancies`. План **не пересиливает** документацию.
>
> Параллельно с правками заполняй отчёт `docs/codex-tasks/fix-codex-stop-hook-report.md`.
> Каждый шаг ниже **обязателен**, ничего не пропускай, ничего не оптимизируй
> "по своему усмотрению", ничего не добавляй сверх описанного. Если что-то непонятно —
> оставь поле в отчёте пустым с пометкой `BLOCKED: <причина>`, не выдумывай.

## Источники, на которые опирается план

Каждое утверждение в плане помечено источником. **Перед началом работы** перечитай
официальные страницы и сверь с метками ниже — если хоть что-то не совпадает (поля
изменились, контракт другой, default другой), **остановись**, заполни в отчёте
раздел `Discrepancies`, и **не правь код вслепую**.

- `[OFFICIAL-CODEX]` — `developers.openai.com/codex/hooks` (input schema, output контракт, timeout default)
- `[OFFICIAL-CODEX-CFG]` — `developers.openai.com/codex/config-advanced` (где живут transcripts, формат — не задокументирован)
- `[OFFICIAL-CC]` — `code.claude.com/docs/en/hooks` (Claude Code transcript schema для regression check)
- `[EMPIRICAL]` — наблюдается в реальном файле проекта или на диске пользователя
- `[PROJECT]` — собственное архитектурное решение проекта

**Critical reminder**: для разделов помеченных `[OFFICIAL-*]` ты обязан **открыть
официальную страницу сам** и подтвердить что план сходится с тем, что там написано
**сейчас**. Не верь на слово этому файлу.

## Обязательное использование внешних инструментов

Ты **не работаешь в вакууме**. У тебя есть набор внешних инструментов, и в этой
задаче использование как минимум следующих — **обязательно**, не опционально.
Игнорирование инструмента — это халтура, не "оптимизация".

### Обязательно к использованию

1. **LLM Wiki проекта** (`<repo-root>/wiki/`)
   - Перед началом работы прочитай как минимум:
     - `wiki/concepts/llm-wiki-architecture.md` — общая архитектура capture pipeline.
     - `wiki/concepts/claude-code-hooks.md` — концепт хуков.
     - `wiki/analyses/llm-wiki-improvement-research-2026-04-12.md` — последний аудит, в нём раздел про Codex hooks reliability.
     - Любую другую статью из `wiki/index.md`, которая выглядит релевантной для этой задачи (transcript parsing, capture pipeline, observability).
   - В отчёте перечисли, какие статьи прочитал, и что из них использовал.

2. **Web fetch / web search для официальной документации**
   - Раздел `0.6 Doc verification` в отчёте требует физически открыть три страницы:
     - `developers.openai.com/codex/hooks`
     - `developers.openai.com/codex/config-advanced`
     - `code.claude.com/docs/en/hooks`
   - Не доверяй memory cache — открой реально сейчас.

3. **MCP серверы**
   - Если у тебя в окружении есть MCP сервер `context7` (или аналог) — используй
     его для повторной проверки spec'а Claude Agent SDK / Codex hooks. Это даёт
     независимую от web fetch верификацию.
   - Если есть `filesystem` MCP — можно использовать для безопасного чтения файлов
     вне рабочего каталога (например `~/.codex/sessions/...`).
   - Если есть `git` MCP — используй для diff staging и просмотра истории
     коммитов вокруг capture pipeline (последние ~20 коммитов).
   - Если есть другие MCP, релевантные задаче — используй и опиши в отчёте.

4. **Skills / repo-local skills**
   - Если у тебя в `.agents/skills/` или аналогичном месте есть skill `wiki-query`,
     `wiki-save`, `wiki-health` или похожий — используй его для запросов в wiki
     и для финальной фиксации знаний.

5. **Repo-local docs**
   - `AGENTS.md` в корне проекта — обязательно прочитай.
   - `CLAUDE.md` в корне проекта — обязательно прочитай.
   - `docs/codex-integration-plan.md` — контекст почему Codex hooks вообще существуют.

### Опционально, но рекомендуется

- Если в окружении есть `Plan` / `Explore` / `code-architect` / `code-reviewer` / `silent-failure-hunter` агенты — можешь делегировать им узкие подзадачи (например, проверить полноту defensive checks в новом парсере). Если делегируешь — запиши в отчёте, какому агенту, что попросил, что получил.
- Если есть линтер, статический анализ, type-checker — прогонять после правок.

### Что писать в отчёт

В отчёт раздел `Tools used` должен содержать **полный** список того, чем
пользовался: какие wiki статьи прочитал, какие URL'ы fetched, какие MCP вызовы
сделал, каких subagent'ов запускал. Если пункт обязательного списка не
использован — `BLOCKED: <причина>`. Прочерк недопустим.

## Контракты, которые **нельзя** нарушить

> ⚠ Версии полей и значения ниже — выписаны из официальной доки на момент написания
> этого плана. **Перед использованием** перечитай ссылки и сверь, что они всё ещё
> актуальны. Если расхождение — план не главный, дока главная.


**[OFFICIAL-CODEX]** Stop hook input на stdin (полные поля):
```jsonc
{
  "session_id":            "string",
  "transcript_path":       "string | null",
  "cwd":                   "string",
  "hook_event_name":       "Stop",
  "model":                 "string",
  "turn_id":               "string",
  "stop_hook_active":      "boolean",
  "last_assistant_message":"string | null"
}
```

**[OFFICIAL-CODEX]** Stop hook output контракт:
> "Stop expects JSON on stdout when it exits 0. Plain text output is invalid for this event."

Поддерживаемые поля output: `continue`, `stopReason`, `systemMessage`.

**[OFFICIAL-CODEX]** Default Stop timeout = **600 секунд**, настраивается через `timeout` или `timeoutSec`.

**[OFFICIAL-CODEX]** В Codex нет SessionEnd. Stop — единственный after-turn event. Работа после **каждого** ответа — это **архитектурное ограничение Codex**, не баг. Aggressive debounce 60s — правильный workaround, не трогай его.

**[OFFICIAL-CODEX-CFG]** Codex transcript schema **не задокументирована публично**. Все парсеры обязаны быть defensive: unknown type → skip, missing field → skip, malformed entry → continue. Никаких raise/throw на неожиданный entry.

## Bugs (5 штук, фиксить ВСЕ в одной волне)

### Bug A — `timeout: 10` в `codex-hooks.template.json`

**[EMPIRICAL]** `codex-hooks.template.json:23` стоит `"timeout": 10`.
**[OFFICIAL-CODEX]** Default = 600s. Мы зажали себя в 60 раз меньше дефолта.

**Действие**: в `codex-hooks.template.json` для `Stop` hook заменить `"timeout": 10` на `"timeout": 60`. Только Stop, остальные хуки не трогать.

**Также**: явно сообщить пользователю в отчёте, что **локальный** `~/.codex/hooks.json` тоже надо обновить — template применяется только при reinstall.

### Bug B — Output контракт нарушен

**[EMPIRICAL]** `hooks/codex/stop.py::main()` нигде не пишет в stdout, везде делает `return`.
**[OFFICIAL-CODEX]** Stop требует JSON на stdout при exit 0.

**Действие**:
1. Добавить функцию `_emit_ok(message: str | None = None) -> None`, которая печатает минимальный валидный JSON `{}` (или с `systemMessage`, если передан message). Использовать `json.dumps(...)` + `print(..., flush=True)`.
2. Импортировать `json` если ещё не импортирован.
3. Вызвать `_emit_ok()` **во всех** точках выхода `main()`:
   - перед каждым `return` в SKIP-ветках
   - в `except` блоках (после логирования)
   - в самом конце успешного пути (после `subprocess.Popen` и `update_debounce`)
4. **Не использовать** `_emit_ok()` для блокировки stop'а через `decision: "block"` — мы хотим, чтобы Stop проходил нормально, флаш просто запускается в фоне.

**Acceptance для Bug B (вписывается в отчёт)**: список всех точек return из `main()` и подтверждение, что в каждой вызван `_emit_ok()`.

### Bug C — Codex format mismatch в `extract_conversation_context`

**[EMPIRICAL via inspection]** Реальный Codex jsonl на диске пользователя:
`<user-home>\.codex\sessions\2026\04\11\rollout-2026-04-11T18-26-40-019d7d26-fd6b-7712-b49a-2db94684e0dc.jsonl` (~49KB).

Структура entry:
```jsonc
{
  "timestamp": "...",
  "type":      "response_item",
  "payload": {
    "type":    "message",
    "role":    "user" | "assistant" | "developer",
    "content": [{ "type": "input_text" | "output_text", "text": "..." }]
  }
}
```

**[EMPIRICAL]** `hooks/hook_utils.py::extract_conversation_context` (строки 164-233) парсит только Claude Code format. Mismatch:
- ищет `entry.message.role` или `entry.role`, у Codex — `entry.payload.role`
- ищет `block.type == "text"`, у Codex — `block.type == "input_text"` или `"output_text"`
- ищет `entry.message.content`, у Codex — `entry.payload.content`

**Действие**:

1. **Сначала** — открой реальный jsonl-файл и проверь сам:
   - Прочитай первые 20 строк и оцени структуру.
   - Сделай grep на `"type":"unknown"` (статистика плана говорит про 1788 таких entries) — посмотри как минимум один **полный** entry такого типа, чтобы понять, нужно ли его обрабатывать. Скорее всего — **нет**, defensive skip достаточен. Зафиксируй своё решение в отчёте.
   - Запиши в отчёт реальные счётчики (`grep -c '"role":"user"'`, `grep -c '"role":"assistant"'`, `grep -c '"type":"input_text"'`, `grep -c '"type":"output_text"'`, `grep -c '"type":"unknown"'`) — это твоя ground truth, не цифры из этого плана.

2. Рефактор `extract_conversation_context` в `hooks/hook_utils.py`:
   - Вынеси текущую логику в `_extract_claude_code_format(entries)` без изменений.
   - Добавь `_extract_codex_format(entries)` по схеме выше.
   - Добавь `_detect_format(entries)` — смотрит на первые ~10 entries, ищет `entry.get("type") == "response_item"`. Если нашёл — `"codex"`, иначе — `"claude_code"`. **Не** на первый entry — первый Codex entry это `session_meta`.
   - Главная функция вызывает `_detect_format`, потом нужный парсер.

3. **Defensive**: оба парсера должны игнорировать malformed entries без exception. Любой неожиданный тип/поле — skip.

4. **Diagnostic logging**: если результат пустой — залогируй `entries_total / parsed_user / parsed_assistant / format_detected`. Это поможет ловить будущие format shifts.

**Acceptance для Bug C**:
- Вывод команды парсера на реальном Codex jsonl должен показать `n > 0` и `chars > 0`.
- Парсер на Claude Code jsonl должен **по-прежнему** работать (regression test).

### Bug D — Нет fallback на `last_assistant_message`

**[OFFICIAL-CODEX]** В Stop input есть поле `last_assistant_message: string | null`.
**[EMPIRICAL]** `hooks/codex/stop.py:69-71` немедленно скипает при `transcript_path == null`, не используя `last_assistant_message`.

**Действие**: в `hooks/codex/stop.py` заменить блок 69-71 на ветку, которая:
1. Если `transcript_path` отсутствует — пробует `hook_input.get("last_assistant_message")`.
2. Если оно строка не пустая — синтезирует degraded context: `f"**Assistant (degraded, last-message-only):** {last_msg.strip()}\n"`, ставит `turn_count = 1`, и продолжает к debounce + spawn.
3. Файл degraded entry должен иметь явный маркер в имени: `session-flush-DEGRADED-{session_id}-{timestamp}.md`.
4. Если ни transcript_path, ни last_assistant_message нет — `_emit_ok()` и `return`.

**Решение по порогу**: degraded entry короткий и может не пройти `WIKI_MIN_FLUSH_CHARS`. Используй для degraded path **отдельный** минимум: `degraded_min = max(50, WIKI_MIN_FLUSH_CHARS // 4)`. Если degraded context короче — `_emit_ok()` и `return` с логом `SKIP: degraded too short`.

**Не путать** debounce: degraded entries **должны** проходить через тот же debounce, что и обычные — иначе Stop fires after every response создадут шторм маленьких файлов.

### Bug E — Legacy `MIN_TURNS_TO_FLUSH = 6`

**[EMPIRICAL]** `hooks/codex/stop.py:47`.
**[PROJECT]** Это технический долг после миграции `session-end.py` и `pre-compact.py` на `WIKI_MIN_FLUSH_CHARS`.

**Действие**:
1. Добавить импорт `WIKI_MIN_FLUSH_CHARS` из `config` (он уже есть в `session-end.py:24`, скопируй паттерн).
2. Удалить константу `MIN_TURNS_TO_FLUSH = 6`.
3. Заменить блок 88-94:
   ```python
   if not context.strip():
       logging.info("SKIP: empty context")
       return
   if turn_count < MIN_TURNS_TO_FLUSH:
       logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_TO_FLUSH)
       return
   ```
   На (точно по образцу `session-end.py:88-94`):
   ```python
   content_len = len(context.strip())
   if content_len == 0:
       logging.info("SKIP: empty context (entries=%d)", turn_count)
       _emit_ok()
       return
   if content_len < WIKI_MIN_FLUSH_CHARS:
       logging.info("SKIP: only %d chars (min %d)", content_len, WIKI_MIN_FLUSH_CHARS)
       _emit_ok()
       return
   ```

**Не**:
- Не используй `MIN_TURNS_TO_FLUSH` нигде в новом коде.
- Не меняй `WIKI_MIN_FLUSH_CHARS` отдельно для Codex — один порог на все хуки.
- Не трогай другие хуки (`session-end.py`, `pre-compact.py`, `hook_utils.py` вне `extract_conversation_context`) — они уже мигрированы.

## Файлы, которые можно менять

**Только эти три**:
1. `hooks/hook_utils.py` — добавить два парсера + детектор формата + diagnostic log
2. `hooks/codex/stop.py` — Bug B + D + E
3. `codex-hooks.template.json` — Bug A

Ничего больше не трогай. Ни `scripts/doctor.py`, ни тесты, ни README, ни docs.

## Файлы, которые НЕЛЬЗЯ трогать (явный whitelist выше)

Если возникает соблазн "заодно подправить" — **не делай этого**. Заполни в отчёте `Out-of-scope-temptations` и опиши, что хотелось сделать и почему отказался.

## Verification (последовательность)

### Pre-flight (заполняется в отчёте до правок кода)

- `python --version` / `uv --version`
- `ls -la "<user-home>\.codex\sessions\2026\04\11\rollout-2026-04-11T18-26-40-019d7d26-fd6b-7712-b49a-2db94684e0dc.jsonl"` — убедись что файл существует, запиши размер
- `wc -l <jsonl>` — реальное число строк
- grep статистика по jsonl (см. Bug C, шаг 1)
- `tail -50 scripts/flush.log | grep "[codex-stop]"` — снимок текущего состояния перед фиксом

### Phase 1 — Unit tests (после правок)

**1.1** Парсер на реальном Codex jsonl:
```bash
uv run python -c "from hooks.hook_utils import extract_conversation_context; from pathlib import Path; ctx, n = extract_conversation_context(Path(r'<user-home>\.codex\sessions\2026\04\11\rollout-2026-04-11T18-26-40-019d7d26-fd6b-7712-b49a-2db94684e0dc.jsonl')); print(f'turns={n} chars={len(ctx)}')"
```
Записать **полный** stdout вывод в отчёт.

**1.2** Парсер на Claude Code jsonl. Найти любой свежий файл в `~/.claude/projects/E--Project-memory-claude-memory-claude/*.jsonl`, прогнать тот же one-liner с этим путём. Записать stdout в отчёт.

**1.3** `uv run python scripts/doctor.py --full` — записать **полный** вывод (или хотя бы хвост с total PASS/FAIL счётом). Должно быть 20/20 PASS.

**1.4** JSON output контракт. Команда:
```bash
echo '{"session_id":"test","transcript_path":null,"cwd":".","hook_event_name":"Stop","model":"x","turn_id":"t","stop_hook_active":false,"last_assistant_message":null}' | uv run python hooks/codex/stop.py
echo "EXIT=$?"
```
Записать **дословный** stdout (должен быть валидным JSON) и exit code (должен быть 0).

**1.5** Дополнительный smoke на degraded path:
```bash
echo '{"session_id":"test2","transcript_path":null,"cwd":".","hook_event_name":"Stop","model":"x","turn_id":"t2","stop_hook_active":false,"last_assistant_message":"This is a test response that should trigger the degraded path with enough characters to pass the degraded threshold."}' | uv run python hooks/codex/stop.py
echo "EXIT=$?"
```
Записать stdout, exit, и проверить `tail -5 scripts/flush.log` — должна быть запись `DEGRADED:` или `SKIP: degraded too short`. Записать обе проверки.

### Phase 2 — Integration (выполняет ПОЛЬЗОВАТЕЛЬ, не Codex)

В отчёте оставить эти поля **пустыми** с пометкой `[awaits user]`:
- 2.1 Локальный `~/.codex/hooks.json` обновлён
- 2.2 Перезапуск Codex
- 2.3 Реальная сессия → нет `Stop failed` в UI
- 2.4 `tail scripts/flush.log` после сессии
- 2.5 Запись в `daily/2026-04-13.md`

### Phase 3 — Statistical (через несколько дней)

В отчёте оставить пустыми с пометкой `[awaits 7-day window]`:
- 3.1 skip rate < 30%
- 3.2 `check_flush_capture_health` без attention маркера

## Acceptance criteria (полный список)

Отчёт считается завершённым **только** если:

- ✅ Pre-flight заполнен реальными данными
- ✅ Bug A — реальный diff `codex-hooks.template.json` записан
- ✅ Bug B — список всех return-точек `main()`, в каждой `_emit_ok()`
- ✅ Bug C — реальная grep-статистика, реальный код парсера, проверка `"type":"unknown"`
- ✅ Bug D — код degraded ветки, решение по threshold
- ✅ Bug E — diff применён по образцу `session-end.py`
- ✅ Phase 1.1 — `n > 0` на реальном Codex jsonl
- ✅ Phase 1.2 — `n > 0` на Claude Code jsonl (regression OK)
- ✅ Phase 1.3 — `doctor --full` 20/20 PASS, полный вывод записан
- ✅ Phase 1.4 — валидный JSON stdout, exit 0
- ✅ Phase 1.5 — degraded smoke с реальным выводом
- ✅ Self-audit checklist в конце отчёта — все пункты ✅ или явный `BLOCKED: <причина>`

Если хоть один пункт остался пустым или с фейковыми данными — задача не закрыта, **вернись и доделай**.

## Rollback

Все изменения изолированы в трёх файлах. Если что-то идёт не так:
```bash
git checkout hooks/hook_utils.py hooks/codex/stop.py codex-hooks.template.json
```
`wiki/`, `flush.log`, `daily/` — gitignored. Никаких commit'ов до полной верификации и approval пользователем.
