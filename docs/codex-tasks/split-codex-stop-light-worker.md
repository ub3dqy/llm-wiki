# Task — Split Codex Stop hook into light + worker phases (kill UI "Stop failed")

> **Роль**: исполнитель — Codex. Architectural code-fix task. Один файл правки.
>
> **Иерархия источников правды**:
> 1. Официальная документация Codex hooks (`developers.openai.com/codex/hooks`) — primary
> 2. Реальное состояние кода и логов — secondary
> 3. Этот план — derived artifact, может ошибаться
>
> Расхождение план vs дока → побеждает дока, фиксируй в `Discrepancies`.

---

## TL;DR

Codex UI показывает "Stop failed" после **каждого** сообщения: красная метка появляется на 10-й секунде после отправки. По свежим измерениям (Claude parent в живой сессии 2026-04-13 22:30-23:25):

- Полный runtime hook'а в проде: **11-15 секунд**, из них:
  - ~4-6s wsl.exe + bash + uv run cold start (структурный, не оптимизируемый этой задачей)
  - **6.91s** `extract_conversation_context()` парсит **247 MB** Codex jsonl (50 947 строк)
  - <0.5s spawn flush.py + emit + exit
- Hook **технически успешно** завершается: exit 0, валидный JSON `{}` на stdout, `Spawned flush.py` залогирован, capture работает (есть `Flushed N chars to daily log` для тех же сессий)
- **Causal hypothesis**: Codex UI флипает в "failed" по внутреннему ~10s порогу, **не задокументированному** в офдоке. Empty `_emit_ok()` (emit nothing) и timing config 60s → не помогают (проверено экспериментально)

**Архитектурный фикс**: разбить `stop.py` на две фазы в одном файле, single entry point с двумя режимами:

1. **Light phase** (default mode, ~500ms total): parse stdin, минимальные skip checks, **спавнит сам себя** в `--worker` режиме detached, вызывает `_emit_ok()`, exit. Codex видит process exit за <1s, UI индикатор в success.
2. **Worker phase** (`--worker` argv, runs detached): читает payload из stdin, делает `extract_conversation_context()`, threshold checks, write context file, spawn flush.py. Никакого emit — родитель уже отдал JSON Codex'у и отсоединился.

Codex UI больше не видит долгий hook → "Stop failed" исчезает. Capture продолжает работать как раньше.

---

## Doc verification (ОБЯЗАТЕЛЬНО перед правкой)

Перечитать **сейчас**, не из памяти:

1. **Codex hooks doc** — `developers.openai.com/codex/hooks` — раздел Stop hook:
   - Подтвердить: "Exit 0 with no output is treated as success" / "JSON on stdout supports common output fields"
   - Подтвердить: default timeout 600s (мы конфигурируем 60s — это тоже не bottleneck)
   - **Найти любые упоминания UI thresholds, status indicators, async hooks, fire-and-forget patterns**. Если что-то подобное есть — это меняет план, фиксируй в Discrepancies.
   - Если документация **не описывает** UI failed indicator timing — зафиксируй явно: *"docs do not mention UI failure threshold; this fix targets undocumented Codex UI behavior"*.

2. **Python `subprocess.Popen` docs** — раздел `start_new_session`:
   - Подтвердить: на POSIX (Linux, WSL Ubuntu) `start_new_session=True` вызывает `setsid()` в child, отделяя его от process group родителя. Parent может exit без отправки SIGHUP child'у.
   - Это ключевой механизм для detached worker под WSL.
   - На Windows `start_new_session` ignored — но Codex Stop hook **запускается только из WSL Ubuntu** (см. `~/.codex/hooks.json` — все commands начинаются с `wsl.exe -d Ubuntu`), так что Windows path не релевантен.

Зафиксируй цитаты в `Doc verification` секции отчёта.

---

## Files to modify (whitelist — только этот файл)

**Только**: `hooks/codex/stop.py`

Никаких других файлов. Не трогать `hook_utils.py`, `flush.py`, hooks/, scripts/, конфиги, тесты, doctor.

---

## Architecture — точная схема

### Сейчас (single phase, slow)

```python
def main():
    parse stdin            # ~50ms
    skip checks            # ~10ms
    extract_conversation_context()  # ~6.9s on 247MB jsonl ←←← bottleneck
    threshold checks       # ~5ms
    write context file     # ~30ms
    subprocess.Popen(flush.py, fire-and-forget)  # ~200ms
    _emit_ok()             # <10ms
    # exit at ~7.3s+ (direct python) / 11-15s (with wsl wrapper chain)
```

### После (two phases, fast light + detached worker)

```python
def main_light():
    """Default mode. Runs <500ms total. Codex sees fast exit -> UI happy."""
    parse stdin
    
    # Quick skips that don't need transcript parsing
    if no transcript_path AND no last_assistant_message:
        _emit_ok()
        return
    if stop_hook_active:
        _emit_ok()
        return
    if not check_debounce(...):
        _emit_ok()
        return
    
    # Spawn ourselves in --worker mode, detached
    payload = json.dumps(hook_input)  # full event JSON
    p = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # POSIX detach
    )
    p.stdin.write(payload.encode("utf-8"))
    p.stdin.close()
    
    _emit_ok()
    # exit at ~500ms

def main_worker():
    """--worker mode. Runs detached after light phase exit. Heavy lifting."""
    payload = sys.stdin.read()
    hook_input = json.loads(payload)
    logging.info("[stop-worker] started session=%s", hook_input.get("session_id"))
    
    # All the heavy logic from current main() lines 78-185:
    # - extract_conversation_context (~6.9s, but nobody's waiting now)
    # - threshold checks
    # - write context file
    # - spawn flush.py via uv run
    # - update_debounce
    
    # NO _emit_ok() — we're detached, no listener.

if __name__ == "__main__":
    if "--worker" in sys.argv:
        main_worker()
    else:
        try:
            main_light()
        except BrokenPipeError:
            _detach_stdout()
        except Exception as exc:
            logging.exception("Stop hook failed: %s", exc)
            _emit_ok()
```

### Что переезжает где

| Текущий код (строки) | Куда |
|---|---|
| 72-77 (parse stdin, fail emit) | `main_light` |
| 78-86 (extract fields, log "Stop fired") | `main_light` |
| 88-91 (stop_hook_active check) | `main_light` |
| 93-99 (transcript path / degraded mode check) | `main_light` (fast skip when nothing to do) |
| 101-104 (debounce check) | `main_light` (fast skip) |
| 106-122 (extract_conversation_context, degraded handling) | `main_worker` |
| 124-137 (content len, threshold checks) | `main_worker` |
| 139-159 (project name, write file, build cmd) | `main_worker` |
| 161-183 (subprocess.Popen flush.py + update_debounce) | `main_worker` |
| 185 (final `_emit_ok()`) | `main_light` (called after spawning worker) |

### Ключевые детали

1. **`start_new_session=True`**: POSIX-only. На WSL Ubuntu (где Codex Stop запускается) это работает как `setsid()`. Child становится session leader новой session, не получает SIGHUP когда parent exit'ит.

2. **payload передаётся через stdin pipe**, не через argv: чтобы избежать ограничений длины argv и избегать quoting issues с JSON в bash. Light phase открывает pipe, пишет JSON, закрывает stdin своего ребёнка → ребёнок видит EOF и читает payload через `sys.stdin.read()`.

3. **Worker не вызывает `_emit_ok()`**: к моменту запуска worker'а parent (light phase) уже exit'нул, его stdout pipe Codex закрыл, писать туда некому. Worker логирует в `flush.log` через тот же logging setup.

4. **Single file, single entry point**: проще maintain, никаких новых файлов, тот же import set, та же config initialization (logging, paths) для обеих фаз.

5. **Все skip paths в light phase эмитят `_emit_ok()` и exit без spawn worker'а** — никакого worker spawn для тривиальных случаев. Heavy worker spawn только когда есть реальная работа.

6. **Recursion guard сверху файла (строки 21-22)** работает как для light, так и для worker — не трогать.

---

## Edge cases — обязательно покрыть

### 1. Worker процесс умирает молча (ImportError, etc.)

Mitigation: первой строкой в `main_worker()` после parsing payload — `logging.info("[stop-worker] started session=%s", session_id)`. Если эта строка появилась в `flush.log`, мы знаем что worker реально стартовал. Если worker упадёт ДО неё — мы хотя бы увидим её отсутствие при следующем grep'е.

### 2. Concurrency: два Stop за 1 секунду

Сейчас: оба пройдут через single phase, debounce check во втором сделает SKIP.

После: оба light phase отработают мгновенно, оба заспавнят worker'ы. Каждый worker проверит debounce независимо. Один пройдёт, второй запишет SKIP debounce.

**Важно**: debounce check в текущем коде (строка 101-104) должен оставаться в **light phase** — он используется как fast skip и предотвращает спавн worker'а вообще. Это OK, дублировать его в worker не нужно. Worker не делает debounce check.

Wait — это меняет семантику. Сейчас debounce check ПЕРЕД extract. После: debounce check в light phase ПЕРЕД spawn worker. Это **то же самое** с точки зрения semantics — если debounce hit, ничего не происходит.

### 3. Logging race между двумя одновременными worker'ами

Python `logging.basicConfig(filename=...)` использует FileHandler, который **не** thread-safe между процессами. Два worker'а могут писать в `flush.log` одновременно → строки могут перемешаться.

Mitigation: **не блокер**. Логи только informational, не парсятся машиной (кроме `grep`-ов). Перемешанные строки разделены по timestamp, читаемые. Если будет реальная проблема — отдельная задача с file lock или syslog handler.

### 4. Worker exit code

Никто не ждёт worker exit. Под Linux orphaned worker continues и завершается нормально, его exit code теряется (init адоптирует и reap'ит). На WSL это нормально работает.

### 5. `sys.executable` под WSL

`sys.executable` в WSL Ubuntu Python будет `<linux-home>/.cache/llm-wiki/.venv/bin/python` (uv-managed venv) или `/usr/bin/python3` (system). Должен быть тот же Python который запустил light phase, чтобы worker имел те же импорты. Это даёт `sys.executable` автоматически — не хардкодить пути.

### 6. `__file__` resolution

`Path(__file__).resolve()` в light phase даёт абсолютный путь к stop.py. Под WSL это будет что-то вроде `<repo-root>/hooks/codex/stop.py`. Передавать как absolute path в Popen.

---

## Verification

### Phase 1 — manual unit test light phase

```bash
cd "<repo-root>"
# Stub stdin: no transcript, no last message → fast skip path
echo '{"session_id":"test-light-skip","transcript_path":null,"cwd":".","hook_event_name":"Stop","model":"x","turn_id":"t","stop_hook_active":false,"last_assistant_message":null}' | time uv run python hooks/codex/stop.py
echo "EXIT=$?"
```

**Ожидание**: 
- exit 0
- stdout: `{}`
- `time` показывает <1s
- В `flush.log` появляется `[codex-stop] Stop fired: session=test-light-skip ...` и `[codex-stop] SKIP: no transcript path and no last_assistant_message`

### Phase 2 — manual unit test light phase + worker spawn

```bash
cd "<repo-root>"
# Stub with last_assistant_message that's long enough → light phase spawns worker
PAYLOAD='{"session_id":"test-light-worker","transcript_path":null,"cwd":".","hook_event_name":"Stop","model":"x","turn_id":"t","stop_hook_active":false,"last_assistant_message":"This is a longer message that exceeds the degraded threshold so the worker actually does the spawn and we can verify the worker phase logs appear after light phase exits. Adding more padding to make sure we are well above 125 chars minimum."}'
echo "$PAYLOAD" | time uv run python hooks/codex/stop.py
echo "EXIT=$?"
sleep 2
tail -20 scripts/flush.log
```

**Ожидание**:
- light phase exit'ит за <1s, exit 0, stdout `{}`
- В `flush.log` сразу после `Stop fired` появляется `[stop-worker] started session=test-light-worker` (через 1-2 секунды)
- Затем `[stop-worker]` лог про degraded mode и spawn flush.py
- Затем (через 5-30s) `[flush] Starting flush ...` от ребёнка-flush.py

### Phase 3 — manual test with real Codex transcript

Find a real Codex transcript file (например `<user-home>/.codex/sessions/2026/03/31/rollout-...019d4435....jsonl` — 247MB):

```bash
cd "<repo-root>"
TRANSCRIPT="<user-home>/.codex/sessions/2026/03/31/rollout-2026-03-31T17-04-15-019d4435-941f-7aa1-bb4a-684ec4158f45.jsonl"
ls -la "$TRANSCRIPT"
PAYLOAD="{\"session_id\":\"test-real-transcript\",\"transcript_path\":\"$TRANSCRIPT\",\"cwd\":\"<repo-root>\",\"hook_event_name\":\"Stop\",\"model\":\"x\",\"turn_id\":\"t\",\"stop_hook_active\":false,\"last_assistant_message\":\"hi\"}"
echo "$PAYLOAD" | time uv run python hooks/codex/stop.py
echo "EXIT=$?"
sleep 15
tail -30 scripts/flush.log
```

**Ожидание**:
- **light phase exit'ит за <1.5s** (это критичный success criterion — раньше было 7-15s)
- В `flush.log`: `Stop fired` → `[stop-worker] started` → `[stop-worker]` extract done (через ~7s) → `Spawned flush.py` → flush.py logs

**Сравнение для цифр**: до фикса direct python invocation на этом же файле занимал 7.3 секунды (см. plan TL;DR). После фикса должно быть <1.5s для light phase, ~7-10s для worker (но он detached).

### Phase 4 — doctor regression

```bash
cd "<repo-root>"
uv run python scripts/wiki_cli.py doctor --full 2>&1 | tail -40
```

Hook-specific тесты должны пройти. Pre-existing red — не блокер.

### Phase 5 — Windows-side regression (Claude Code hooks)

Хотя Codex Stop запускается только из WSL, проверить что **Claude Code SessionEnd / PreCompact** (которые тоже spawn flush.py через `subprocess.Popen` похожим pattern'ом) **не** затронуты этой правкой. Они в **другом файле** (`hooks/session-end.py`, `hooks/pre-compact.py`), их whitelist не разрешает трогать. Просто sanity smoke:

```bash
cd "<repo-root>"
echo '{"session_id":"test-claude-se","transcript_path":null,"cwd":".","hook_event_name":"SessionEnd","reason":"other"}' | .venv/Scripts/python.exe hooks/session-end.py
echo "EXIT=$?"
```

Должно быть exit 0 как раньше.

### Phase 6 — pending real Codex test (выполняет ПОЛЬЗОВАТЕЛЬ, не Codex)

После применения фикса:
1. Перезапустить Codex полностью (close + reopen, hooks не hot-reload'ятся)
2. Отправить тестовое сообщение
3. Дождаться ответа agent'а
4. Проверить UI: индикатор Stop должен показать success, **не failed**
5. Проверить `tail -10 scripts/flush.log` — должны быть `Stop fired`, `[stop-worker] started`, `Spawned flush.py`, `Flushed N chars`

Это **не** часть Codex executor scope — это финальная user-side verification. Codex executor только готовит код и проводит Phase 1-5.

---

## Acceptance criteria

- ✅ Doc verification: подтверждено что Codex Stop hook contract позволяет fast emit + exit; `start_new_session=True` подтверждён в Python docs для POSIX detach; цитаты в отчёте
- ✅ Phase 1: light phase fast skip path работает за <1s
- ✅ Phase 2: light phase + worker spawn path работает; worker лог `[stop-worker] started` появляется в `flush.log`
- ✅ Phase 3: real 247MB transcript test показывает **light phase <1.5s**, worker завершает работу asynchronously
- ✅ Phase 4: `doctor --full` hook-specific тесты PASS
- ✅ Phase 5: Claude Code session-end.py не задет (regression sanity)
- ✅ Whitelist: только `hooks/codex/stop.py` modified, никаких других файлов

---

## Out of scope

- **Bug H** (intermittent `Fatal error in message reader` в flush.py). Сегодня воспроизвёлся под **WSL Linux path** (не только Windows как ранее думали — это инвалидирует прошлую гипотезу). Это **отдельная** проблема, не связана с UI Stop failed. Не чинить в этой задаче.
- **Faster jsonl parse** (Approach B). Можно сделать отдельной задачей если worker phase когда-то станет bottleneck'ом. Сейчас неактуально — worker детачнут, его время никто не ждёт.
- **Concurrent worker logging race**. Логи перемешиваются — не блокер, не чинить.
- **Claude Code hooks** (`hooks/session-end.py`, `hooks/pre-compact.py`). Они **могут** иметь похожую проблему, но они в **другом UI** (Claude Code, не Codex), и пользователь сейчас жалуется только на Codex UI. Если позже выяснится что Claude Code тоже показывает фейл — отдельная задача.
- **Изменения в `hook_utils.py`**, `flush.py`, `extract_conversation_context()`. Trigger будет позже если worker phase сам станет bottleneck.
- **Commit / push**. Только локальные изменения + отчёт.

---

## Rollback

```bash
git checkout hooks/codex/stop.py
```

---

## Pending user actions

После того как Codex закончит и заполнит отчёт, **пользователь** должен:
1. Перезапустить Codex
2. Отправить тестовое сообщение
3. Подтвердить что "Stop failed" в UI исчез
4. Проверить `tail scripts/flush.log` — capture продолжает работать

Если "Stop failed" остался — гипотеза 1 (UI flips by timing) тоже неверна, и это **не** UI threshold, а что-то ещё. Тогда откатываем эту правку и копаем дальше.

---

## Notes для исполнителя (Codex)

- **Архитектурное изменение**, не one-line fix. Будь аккуратен с copy-paste границами между light и worker фазами.
- **Сначала Doc verification** — обязательно перечитай Codex hooks doc и Python subprocess doc. Если что-то противоречит плану — стоп, фиксируй, спрашивай.
- **Не трогать `_emit_ok()`, `_detach_stdout()`, recursion guard вверху файла**. Они работают и нужны для light phase exception handlers.
- **Обязательно prepend** worker phase первой строкой `logging.info("[stop-worker] started session=%s", ...)` — это критично для observability и для Phase 2 verification.
- **`start_new_session=True`** только для worker spawn в light phase. **НЕ** для существующего `subprocess.Popen(flush.py, ...)` который уже есть в коде — он остаётся как есть, переезжает в worker.
- **Не оптимизируй extract_conversation_context** — это out of scope. Just move it to worker.
- **Phase 3 верификация** требует доступ к real Codex transcript. Если не сможешь найти 247MB файл — используй любой реальный jsonl >50 MB из `~/.codex/sessions/`. Главное чтобы это был real Codex transcript, не synthetic.
- **Если debounce check fail'ит в Phase 2/3** — добавь cleanup в начале каждого test'а: `rm -f scripts/.last-flush-spawn`.
- Создай отчёт в `docs/codex-tasks/split-codex-stop-light-worker-report.md` по той же структуре что предыдущие task reports (Pre-flight → Doc verification → Phase 1-5 → Final state → Tools used → Self-audit).
