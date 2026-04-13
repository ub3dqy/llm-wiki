# Report — Revert Bug H diagnostic instrumentation

> Заполнено по фактическому исполнению. Откат **не применялся**, потому что обязательная pre-fix репродукция из плана не подтвердилась.

---

## Pre-flight

- [x] Прочитал `docs/codex-tasks/revert-bug-h-diagnostic-instrumentation.md` целиком
- [x] Прочитал текущий `scripts/flush.py` (особенно строки 30-40 и 195-225)
- [x] Понял что whitelist = только `scripts/flush.py`
- [x] Понял что НЕ трогаю: `extra_args`, `_log_cli_stderr`, retry loop, lock logic
- [x] Подтвердил что задача — **revert diagnostic patch**, а не "новый фикс Bug H"

---

## Doc verification

> Источник: `https://code.claude.com/docs/en/agent-sdk/python`

| Что проверял | URL / раздел | Что нашёл | Ссылка/цитата |
|---|---|---|---|
| Параметр `debug_stderr` в `ClaudeAgentOptions` | `code.claude.com/docs/en/agent-sdk/python` | параметр существует | ``debug_stderr  | `Any`  | `sys.stderr`  | Deprecated - File-like object for debug output. Use `stderr` callback instead`` |
| Поддерживаемые типы для `debug_stderr` | `code.claude.com/docs/en/agent-sdk/python` | дока говорит только `Any`, без уточнения про concrete file-handle types | ``debug_stderr  | `Any`  | `sys.stderr`  | Deprecated - File-like object for debug output`` |
| Windows-специфичные ограничения | `code.claude.com/docs/en/agent-sdk/python` | не нашёл | `not documented` |
| Известные issues с file handles | `code.claude.com/docs/en/agent-sdk/python` | не нашёл | `not documented` |

**Conclusion**:
> Документация подтверждает, что `debug_stderr` существует, но не даёт ни Windows-specific ограничений, ни предупреждений про проблемы с Python file handles. Это расхождение docs vs observed behavior пока остаётся открытым.

---

## Phase 1 — pre-fix reproduction

### Команда подготовки контекста

```bash
@'
from pathlib import Path
import random, string
lines = [f'[USER] turn {i}: ' + ' '.join(''.join(random.choices(string.ascii_lowercase, k=6)) for _ in range(20)) for i in range(80)]
Path('E:/tmp/bug-h-precheck.md').parent.mkdir(parents=True, exist_ok=True)
Path('E:/tmp/bug-h-precheck.md').write_text('\n'.join(lines), encoding='utf-8')
print('chars:', sum(len(l)+1 for l in lines))
'@ | .venv/Scripts/python.exe -
```

Output:

```text
chars: 12470
```

### Команда запуска flush.py

```bash
.venv/Scripts/python.exe scripts/flush.py "E:/tmp/bug-h-precheck.md" "bug-h-precheck-pre" "memory-claude" 2>&1
```

### Output (последние 15 строк flush.log)

```text
2026-04-13 22:26:52 INFO [session-end] SessionEnd fired: session=db7aa938-2dae-4f81-8c95-89a7263ab598
2026-04-13 22:26:52 INFO [session-end] Spawned flush.py for session db7aa938-2dae-4f81-8c95-89a7263ab598, project=unknown (2 turns, 13112 chars)
2026-04-13 22:26:52 INFO [flush] Starting flush for session db7aa938-2dae-4f81-8c95-89a7263ab598 (13112 chars)
2026-04-13 22:26:54 INFO [flush] Using bundled Claude Code CLI: <repo-root>\.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe
2026-04-13 22:27:11 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
2026-04-13 22:29:33 INFO [codex-stop] Stop fired: session=019d4435-941f-7aa1-bb4a-684ec4158f45 turn=019d8851-c3f1-7542-99d3-2ebf363d6776
2026-04-13 22:29:45 INFO [codex-stop] Spawned flush.py for session 019d4435-941f-7aa1-bb4a-684ec4158f45, project=messenger (30 turns, 9947 chars)
2026-04-13 22:29:46 INFO [flush] Starting flush for session 019d4435-941f-7aa1-bb4a-684ec4158f45 (9947 chars)
2026-04-13 22:29:47 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 22:30:12 INFO [flush] Flushed 2650 chars to daily log for session 019d4435-941f-7aa1-bb4a-684ec4158f45
2026-04-13 22:31:12 INFO [codex-stop] Stop fired: session=019d4435-941f-7aa1-bb4a-684ec4158f45 turn=019d8853-402c-7a51-9f22-d74d31ccca8a
2026-04-13 22:31:23 INFO [codex-stop] Spawned flush.py for session 019d4435-941f-7aa1-bb4a-684ec4158f45, project=messenger (30 turns, 10089 chars)
2026-04-13 22:31:24 INFO [flush] Starting flush for session 019d4435-941f-7aa1-bb4a-684ec4158f45 (10089 chars)
2026-04-13 22:31:25 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 22:31:48 INFO [flush] Flushed 2725 chars to daily log for session 019d4435-941f-7aa1-bb4a-684ec4158f45
```

### Verdict

- [ ] `Fatal error in message reader: Command failed with exit code 1` присутствует → репродукция подтверждена, идём дальше
- [x] Fatal error отсутствует → **СТОП**, не применять фикс, эскалация в Discrepancies

---

## Phase 2 — apply fix

### Diff scripts/flush.py

```diff
<not applied — pre-fix reproduction failed, so revert was intentionally not performed>
```

### Проверка whitelist

- [x] `git status` показывает только `scripts/flush.py` как tracked change плюс unrelated untracked noise
- [x] Никаких других tracked файлов не тронуто

```text
 M scripts/flush.py
?? Untitled.md
```

---

## Phase 3 — post-fix verification

```text
Not run. By task contract, post-fix verification is blocked because Phase 1 did not reproduce Bug H on the current state.
```

### Verdict

- [ ] `Fatal error in message reader` отсутствует
- [ ] В логе либо `Flushed N chars to daily log`, либо `Flush decided to skip: SKIP: ...`
- [ ] Exit code = 0

---

## Phase 4 — doctor regression

```text
Not run for this revert task. No code change was applied because pre-fix reproduction failed.
```

### Verdict

- [ ] Hook-specific тесты (`stop_smoke`, `flush_roundtrip`) PASS
- [ ] Нет новых regression'ов (pre-existing red — не блокер, отметь явно какие)

---

## Phase 5 — WSL regression

```text
Not run for this revert task. No revert was applied, so there was no code change to regression-test.
```

### Verdict

- [ ] WSL flush работает (success или SKIP)
- [ ] Нет Fatal error

---

## Final state

### git status

```text
 M scripts/flush.py
?? Untitled.md
```

### git diff (полный)

```diff
diff --git a/scripts/flush.py b/scripts/flush.py
index c31bf3a..3d45cfa 100644
--- a/scripts/flush.py
+++ b/scripts/flush.py
@@ -33,6 +33,7 @@ SCRIPTS_DIR = ROOT_DIR / "scripts"
 STATE_FILE = SCRIPTS_DIR / "state.json"
 LOCK_DIR = SCRIPTS_DIR / "locks"
 TEST_MARKER_FILE = SCRIPTS_DIR / "flush-test-marker.txt"
+DEBUG_STDERR_FILE = SCRIPTS_DIR / "flush-debug-stderr.log"
 MAX_CONCURRENT_FLUSH = 2
 LOCK_TIMEOUT_SEC = 120  # stale lock cleanup after 2 minutes
 
@@ -198,26 +199,28 @@ Keep the summary concise — aim for 200-500 words. Include project tag: `projec
     for attempt in range(max_retries + 1):
         result_text = ""
         try:
-            async for message in query(
-                prompt=prompt,
-                options=ClaudeAgentOptions(
-                    allowed_tools=[],
-                    max_turns=2,
-                    stderr=_log_cli_stderr,
-                    # Disable account-level MCP server discovery for this
-                    # subprocess. The bundled Claude CLI otherwise receives
-                    # claude.ai account MCP claims (e.g. Gmail, Calendar) via
-                    # OAuth and blocks on their interactive auth flow, causing
-                    # "Fatal error in message reader: Command failed with exit
-                    # code 1" in non-interactive subprocess context.
-                    # Ref: docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md
-                    extra_args={"strict-mcp-config": None},
-                ),
-            ):
-                if hasattr(message, "content"):
-                    for block in message.content:
-                        if hasattr(block, "text"):
-                            result_text += block.text
+            with open(DEBUG_STDERR_FILE, "a", encoding="utf-8", buffering=1) as debug_fh:
+                async for message in query(
+                    prompt=prompt,
+                    options=ClaudeAgentOptions(
+                        allowed_tools=[],
+                        max_turns=2,
+                        stderr=_log_cli_stderr,
+                        # Disable account-level MCP server discovery for this
+                        # subprocess. The bundled Claude CLI otherwise receives
+                        # claude.ai account MCP claims (e.g. Gmail, Calendar) via
+                        # OAuth and blocks on their interactive auth flow, causing
+                        # "Fatal error in message reader: Command failed with exit
+                        # code 1" in non-interactive subprocess context.
+                        # Ref: docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md
+                        extra_args={"strict-mcp-config": None},
+                        debug_stderr=debug_fh,
+                    ),
+                ):
+                    if hasattr(message, "content"):
+                        for block in message.content:
+                            if hasattr(block, "text"):
+                                result_text += block.text
             break  # success
         except Exception as e:
             if ProcessError is not None and isinstance(e, ProcessError):
warning: in the working copy of 'scripts/flush.py', LF will be replaced by CRLF the next time Git touches it
```

### Файлы созданные/удалённые на диске

- `scripts/flush.py` — modified
- `scripts/flush-debug-stderr.log` — kept, exists, 0 bytes

---

## Tools used

- [x] WebFetch / web search — для документации claude_agent_sdk
- [x] Read — `scripts/flush.py`, `docs/codex-tasks/revert-bug-h-diagnostic-instrumentation.md`
- [x] Bash/PowerShell — Phase 1 команды
- [ ] Edit — Правки 1-2 в `scripts/flush.py`
- [x] git CLI — diff/status

---

## Discrepancies

- План утверждает, что Bug H с `debug_stderr=debug_fh` должен воспроизводиться детерминированно на Windows host. На реальном текущем состоянии pre-fix reproduction не дал `Fatal error`; `flush.py` завершился веткой `Flush decided to skip: SKIP: No significant knowledge to extract.`
- Из-за отсутствия обязательной pre-fix репродукции task contract сам заблокировал применение отката.
- В worktree есть unrelated `?? Untitled.md`, не относящийся к задаче.

---

## Self-audit

- [x] Применил **только** Phase 1 evidence collection из плана
- [x] Не трогал ничего вне `scripts/flush.py`
- [x] `extra_args={"strict-mcp-config": None}` не трогал
- [x] `_log_cli_stderr` callback и `stderr=...` не трогал
- [ ] Phase 1 (pre-fix repro) подтвердил Bug H ДО фикса
- [ ] Phase 3 (post-fix) подтвердил отсутствие Bug H ПОСЛЕ фикса
- [ ] Phase 5 (WSL) подтвердил что WSL path не сломан
- [x] Doc verification раздел заполнен
- [x] Не делал commit / push
- [x] Не делал opportunistic улучшений

---

## Notes / observations

- На текущем состоянии репо прямой Windows-host запуск `.venv/Scripts/python.exe scripts/flush.py ...` с synthetic context не воспроизвёл claimed deterministic Bug H.
- Это не доказывает, что `debug_stderr` безопасен. Это только означает, что task-план уже устарел относительно текущей реальности, и blind revert сейчас был бы нечестным.
