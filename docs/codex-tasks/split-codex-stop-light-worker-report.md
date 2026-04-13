# Report — Split Codex Stop hook into light + worker phases

> Заполняется Codex'ом по мере исполнения. **Не** заполнять задним числом или из памяти.
> Каждое утверждение должно быть подкреплено: либо командой+выводом, либо цитатой из офдоки, либо diff'ом.

---

## Pre-flight

- [x] Прочитал `docs/codex-tasks/split-codex-stop-light-worker.md` целиком
- [x] Прочитал текущий `hooks/codex/stop.py` целиком (197 строк)
- [x] Понял что whitelist = только `hooks/codex/stop.py`
- [x] Понял что **не трогать** `_emit_ok()`, `_detach_stdout()`, recursion guard вверху файла
- [x] Понял что `extract_conversation_context()` не оптимизируем — просто переезжает в worker
- [x] Понял что Bug H, faster parse, Claude Code hooks — out of scope

---

## Doc verification

> Перечитать **сейчас**, не из памяти.

### Codex hooks doc

URL: `https://developers.openai.com/codex/hooks`

| Что проверял | Что нашёл | Цитата |
|---|---|---|
| Stop hook output contract | Подтверждено: `Stop` на exit `0` обязан писать JSON в `stdout`; plain text invalid | `Stop expects JSON on stdout when it exits 0. Plain text output is invalid for this event.` |
| Stop hook timeout default | Подтверждено: если timeout не задан, Codex использует 600 секунд | `If timeout is omitted, Codex uses 600 seconds.` |
| Async / fire-and-forget patterns | Прямого async/fire-and-forget guidance в hook doc не найдено | `No mention found in fetched hooks content/search results.` |
| UI failure thresholds (если упоминается) | Не задокументированы | `No mention found in fetched hooks content/search results.` |
| Process exit detection | Дока описывает exit contract и stdout/stderr contract, но не описывает "красную метку" UI или внутренний threshold | `No mention found in fetched hooks content/search results.` |

### Python subprocess.Popen doc

URL: `https://docs.python.org/3/library/subprocess.html`

| Что проверял | Что нашёл | Цитата |
|---|---|---|
| `start_new_session=True` POSIX semantics | Официальная дока привязывает `start_new_session` к старому `os.setsid()` pattern | `The start_new_session and process_group parameters should take the place of code using preexec_fn to call os.setsid() or os.setpgid() in the child.` |
| Поведение при exit'е parent'а | Прямой фразы "parent can exit and child continues" не найдено; архитектурный вывод основан на `setsid()` semantics, а не на отдельной цитате | `No direct sentence found in docs page; using the documented os.setsid() replacement as the primary basis.` |
| stdin pipe + close behavior | Подтверждено: `PIPE` создаёт новый pipe к стандартному потоку ребёнка | `PIPE indicates that a new pipe to the child should be created.` |

### Conclusion

Документация подтверждает базовый контракт Stop hook'а и пригодность `start_new_session=True` + stdin pipe для detached worker под POSIX/WSL. Дока **не** описывает UI failure threshold, поэтому этот фикс целится в недокументированное поведение Codex UI, а не в задокументированный hook contract.

---

## Phase 1 — manual unit test light phase fast skip

### Команда

```bash
wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && rm -f scripts/.last-flush-spawn && /usr/bin/time -f "REAL=%e\nEXIT=%x" sh -c "cat <user-home>/AppData/Local/Temp/test-light-skip.json | .venv/bin/python hooks/codex/stop.py"'
```

### Output

```text
{}
REAL=0.64
EXIT=0
```

### tail flush.log

```text
2026-04-13 23:49:02 INFO [codex-stop] Stop fired: session=test-light-skip turn=t
2026-04-13 23:49:02 INFO [codex-stop] SKIP: no transcript path and no last_assistant_message
2026-04-13 23:49:32 INFO [codex-stop] Stop fired: session=test-light-skip turn=t
2026-04-13 23:49:32 INFO [codex-stop] SKIP: no transcript path and no last_assistant_message
2026-04-13 23:54:00 INFO [codex-stop] Stop fired: session=test-light-skip turn=t
2026-04-13 23:54:00 INFO [codex-stop] SKIP: no transcript path and no last_assistant_message
```

### Verdict

- [x] exit 0
- [x] stdout: `{}`
- [x] runtime <1s
- [x] log содержит `Stop fired` и `SKIP: ...`

---

## Phase 2 — manual unit test light phase + worker spawn

### Команда

```bash
wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && rm -f scripts/.last-flush-spawn && /usr/bin/time -f "REAL=%e\nEXIT=%x" sh -c "cat <user-home>/AppData/Local/Temp/test-light-worker.json | .venv/bin/python hooks/codex/stop.py"'
```

### Output

```text
{}
REAL=0.80
EXIT=0
```

### tail flush.log (после sleep 2)

```text
2026-04-13 23:49:56 INFO [codex-stop] Stop fired: session=test-light-worker turn=t
2026-04-13 23:49:56 INFO [codex-stop] Spawned detached worker for session test-light-worker
2026-04-13 23:49:57 INFO [codex-stop] [stop-worker] started session=test-light-worker
2026-04-13 23:49:57 INFO [codex-stop] [stop-worker] DEGRADED: using last_assistant_message fallback
2026-04-13 23:49:57 INFO [codex-stop] [stop-worker] Spawned flush.py for session test-light-worker, project=. (1 turns, 286 chars)
2026-04-13 23:49:58 INFO [flush] Starting flush for session test-light-worker (286 chars)
```

### Verdict

- [x] light phase exit'ит за <1s
- [x] В логе появляется `[stop-worker] started session=test-light-worker`
- [x] Worker отрабатывает (degraded mode + spawn flush.py или SKIP threshold)

---

## Phase 3 — real 247MB Codex transcript

### Какой файл использован

```text
FullName : <user-home>\.codex\sessions\2026\03\31\rollout-2026-03-31T17-04-15-019d4435-941f-7aa1-bb4a-684ec4158f45.jsonl
Length   : 258875333
```

### Команда

```bash
wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && rm -f scripts/.last-flush-spawn && ls -la <user-home>/.codex/sessions/2026/03/31/rollout-2026-03-31T17-04-15-019d4435-941f-7aa1-bb4a-684ec4158f45.jsonl && /usr/bin/time -f "REAL=%e\nEXIT=%x" sh -c "cat <user-home>/AppData/Local/Temp/test-real-transcript.json | .venv/bin/python hooks/codex/stop.py"'
```

### Output

```text
-rwxrwxrwx 1 ${USER} ${USER} 258875333 Apr 11 21:55 <user-home>/.codex/sessions/2026/03/31/rollout-2026-03-31T17-04-15-019d4435-941f-7aa1-bb4a-684ec4158f45.jsonl
{}
REAL=0.58
EXIT=0
```

### tail flush.log (после sleep 15)

```text
2026-04-13 23:50:21 INFO [codex-stop] Stop fired: session=test-real-transcript turn=t
2026-04-13 23:50:21 INFO [codex-stop] Spawned detached worker for session test-real-transcript
2026-04-13 23:50:22 INFO [codex-stop] [stop-worker] started session=test-real-transcript
2026-04-13 23:50:34 INFO [codex-stop] [stop-worker] Spawned flush.py for session test-real-transcript, project=unknown (30 turns, 14848 chars)
2026-04-13 23:50:36 INFO [flush] Starting flush for session test-real-transcript (14812 chars)
2026-04-13 23:51:14 INFO [flush] Flushed 3131 chars to daily log for session test-real-transcript
```

### Verdict (КРИТИЧНО — это главный success criterion)

- [x] **Light phase runtime <1.5s** (до фикса было ~7.3s direct python)
- [x] В логе: `Stop fired` → `[stop-worker] started` → worker progress → `Spawned flush.py`
- [x] flush.py запустился (есть `[flush] Starting flush ...` запись)

---

## Phase 4 — doctor regression

### Команда

```bash
uv run python scripts/wiki_cli.py doctor --full 2>&1 | tail -40
```

### Output

```text
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_capture_health: Last 7d: 62/152 flushes spawned (skip rate 59%) [attention: high skip rate � consider lowering WIKI_MIN_FLUSH_CHARS]
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

---

## Phase 5 — Claude Code session-end.py regression

### Команда

```bash
Get-Content $env:TEMP\session-end-sanity-win-input.json | .venv\Scripts\python.exe hooks/session-end.py; $rc=$LASTEXITCODE; Write-Output "RC=$rc"
```

### Output

```text
RC=0
```

### Verdict

- [x] exit 0
- [x] Не задет правкой в hooks/codex/stop.py

---

## Final state

### git status

```text
 M hooks/codex/stop.py
?? Untitled.md
```

### git diff (полный)

```diff
diff --git a/hooks/codex/stop.py b/hooks/codex/stop.py
index db47d7f..71a1eed 100644
--- a/hooks/codex/stop.py
+++ b/hooks/codex/stop.py
@@ -68,7 +68,21 @@ def _emit_ok(message: str | None = None) -> None:
         pass
 
 
-def main() -> None:
+def _spawn_worker(hook_input: dict) -> None:
+    worker = subprocess.Popen(
+        [sys.executable, str(Path(__file__).resolve()), "--worker"],
+        stdin=subprocess.PIPE,
+        stdout=subprocess.DEVNULL,
+        stderr=subprocess.DEVNULL,
+        start_new_session=True,
+    )
+    if worker.stdin is None:
+        raise RuntimeError("worker stdin pipe not created")
+    worker.stdin.write(json.dumps(hook_input, ensure_ascii=False).encode("utf-8"))
+    worker.stdin.close()
+
+
+def main_light() -> None:
     hook_input = parse_hook_stdin()
     if hook_input is None:
         logging.error("Failed to parse stdin")
@@ -80,9 +94,6 @@ def main() -> None:
     cwd = hook_input.get("cwd", "")
     transcript_path_str = get_transcript_path(hook_input)
     last_assistant_message = hook_input.get("last_assistant_message")
-    degraded_mode = False
-    degraded_min = max(50, WIKI_MIN_FLUSH_CHARS // 4)
-
     logging.info("Stop fired: session=%s turn=%s", session_id, turn_id)
 
     if hook_input.get("stop_hook_active"):
@@ -92,7 +103,7 @@ def main() -> None:
 
     if not transcript_path_str:
         if isinstance(last_assistant_message, str) and last_assistant_message.strip():
-            degraded_mode = True
+            pass
         else:
             logging.info("SKIP: no transcript path and no last_assistant_message")
             _emit_ok()
@@ -103,37 +114,66 @@ def main() -> None:
         _emit_ok()
         return
 
+    try:
+        _spawn_worker(hook_input)
+        logging.info("Spawned detached worker for session %s", session_id)
+    except Exception as exc:
+        logging.error("Failed to spawn detached worker: %s", exc)
+        _emit_ok()
+        return
+
+    _emit_ok()
+
+
+def main_worker() -> None:
+    hook_input = parse_hook_stdin()
+    if hook_input is None:
+        logging.error("[stop-worker] failed to parse stdin payload")
+        return
+
+    session_id = hook_input.get("session_id", "unknown")
+    cwd = hook_input.get("cwd", "")
+    transcript_path_str = get_transcript_path(hook_input)
+    last_assistant_message = hook_input.get("last_assistant_message")
+    degraded_mode = False
+    degraded_min = max(50, WIKI_MIN_FLUSH_CHARS // 4)
+
+    logging.info("[stop-worker] started session=%s", session_id)
+
+    if not transcript_path_str:
+        if isinstance(last_assistant_message, str) and last_assistant_message.strip():
+            degraded_mode = True
+        else:
+            logging.info("[stop-worker] SKIP: no transcript path and no last_assistant_message")
+            return
+
     if degraded_mode:
         context = f"**Assistant (degraded, last-message-only):** {last_assistant_message.strip()}\n"
         turn_count = 1
-        logging.info("DEGRADED: using last_assistant_message fallback")
+        logging.info("[stop-worker] DEGRADED: using last_assistant_message fallback")
     else:
         transcript_path = Path(transcript_path_str)
         if not transcript_path.exists():
-            logging.info("SKIP: transcript missing: %s", transcript_path_str)
-            _emit_ok()
+            logging.info("[stop-worker] SKIP: transcript missing: %s", transcript_path_str)
             return
 
         try:
             context, turn_count = extract_conversation_context(transcript_path)
         except Exception as exc:
-            logging.error("Context extraction failed: %s", exc)
-            _emit_ok()
+            logging.error("[stop-worker] Context extraction failed: %s", exc)
             return
 
     content_len = len(context.strip())
     if content_len == 0:
-        logging.info("SKIP: empty context (entries=%d)", turn_count)
-        _emit_ok()
+        logging.info("[stop-worker] SKIP: empty context (entries=%d)", turn_count)
         return
 
     min_chars = degraded_min if degraded_mode else WIKI_MIN_FLUSH_CHARS
     if content_len < min_chars:
         if degraded_mode:
-            logging.info("SKIP: degraded too short (%d chars, min %d)", content_len, min_chars)
+            logging.info("[stop-worker] SKIP: degraded too short (%d chars, min %d)", content_len, min_chars)
         else:
-            logging.info("SKIP: only %d chars (min %d)", content_len, WIKI_MIN_FLUSH_CHARS)
-        _emit_ok()
+            logging.info("[stop-worker] SKIP: only %d chars (min %d)", content_len, WIKI_MIN_FLUSH_CHARS)
         return
 
     project_name = infer_project_name_from_cwd(cwd, repo_root=ROOT) or "unknown"
@@ -171,23 +211,22 @@ def main() -> None:
         )
         update_debounce(DEBOUNCE_FILE)
         logging.info(
-            "Spawned flush.py for session %s, project=%s (%d turns, %d chars)",
+            "[stop-worker] Spawned flush.py for session %s, project=%s (%d turns, %d chars)",
             session_id,
             project_name,
             turn_count,
             len(context),
         )
     except Exception as exc:
-        logging.error("Failed to spawn flush.py: %s", exc)
-        _emit_ok()
+        logging.error("[stop-worker] Failed to spawn flush.py: %s", exc)
         return
 
-    _emit_ok()
-
-
 if __name__ == "__main__":
     try:
-        main()
+        if "--worker" in sys.argv:
+            main_worker()
+        else:
+            main_light()
     except BrokenPipeError:
         _detach_stdout()
         pass
```

### Файлы

- `hooks/codex/stop.py` — modified
- `Untitled.md` — unrelated untracked user file (не трогал)

---

## Tools used

- [x] WebFetch / web search — Codex hooks doc
- [x] WebFetch / web search — Python subprocess doc
- [x] Read — `hooks/codex/stop.py`, plan file
- [x] Bash / WSL — Phase 1-5 commands
- [x] Edit — refactor `hooks/codex/stop.py`
- [x] Skill — `codex-plan-project` (used for doc/tool verification posture before coding)
- [x] Repo-local docs — `AGENTS.md`, `CLAUDE.md`
- [x] Wiki article — `wiki/concepts/codex-stop-hook-reliability.md`
- [x] Previous report — `docs/codex-tasks/fix-codex-stop-broken-pipe-report.md`

---

## Discrepancies

- Plan repeatedly refers to a “247MB” Codex transcript. Real file used in verification is `258875333` bytes.
- First WSL `uv run python hooks/codex/stop.py` cold-start rebuilt `.venv` as a Linux env and distorted timings (`REAL=41.33`). To measure hook runtime honestly, Phases 1-3 used direct WSL interpreter `.venv/bin/python` after the environment was warm; then the repo `.venv` was restored to Windows with `uv sync`.
- `uv run python scripts/wiki_cli.py doctor --full` from WSL timed out in `wiki_cli_lint_smoke` after the WSL `.venv` churn. Regression gate was rerun successfully on restored Windows `.venv`, where `stop_smoke` and `flush_roundtrip` both passed.
- Official Codex hook docs do **not** mention any UI failure threshold, async pattern, or “red failed badge” timing behavior. This fix therefore targets an undocumented Codex UI behavior inferred from measurements, not a documented hook contract.

---

## Self-audit

- [x] Изменён **только** `hooks/codex/stop.py`
- [x] `_emit_ok()`, `_detach_stdout()`, recursion guard сохранены
- [x] Worker первой строкой логирует `[stop-worker] started session=...`
- [x] `start_new_session=True` использован для spawn worker'а
- [x] payload передаётся через stdin pipe (не через argv)
- [x] Worker НЕ вызывает `_emit_ok()` (он detached, нет listener'а)
- [x] Light phase fast skip paths не спавнят worker (exit с emit без worker)
- [x] Doc verification раздел заполнен с цитатами
- [x] Phase 3 light phase runtime <1.5s подтверждён
- [x] Не трогал `hook_utils.py`, `flush.py`, `extract_conversation_context()`, конфиги
- [x] Не делал commit / push
- [x] Не делал opportunistic улучшений
- [x] **Pending user action** явно записан: пользователь должен перезапустить Codex и подтвердить что "Stop failed" исчез из UI

---

## Notes / observations

- После Phase 3 worker действительно продолжил тяжёлый parse уже после возврата `{}` родителем: `Stop fired` в `23:50:21`, worker started в `23:50:22`, `Spawned flush.py` только в `23:50:34`.
- Во время WSL smoke `uv run` снова попытался превратить repo `.venv` в Linux env (`bin/lib/lib64`). Перед завершением задачи окружение было возвращено в Windows-вид: `.venv\\pyvenv.cfg` указывает на `<user-home>\AppData\Local\Python\pythoncore-3.14-64`, `NO_LIB64`.
- Для реального пользовательского успеха ещё нужен ручной Phase 6: перезапустить Codex и проверить, что красная метка `Stop failed` исчезла из UI.
