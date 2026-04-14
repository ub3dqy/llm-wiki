---
task: Narrow flush_pipeline_correctness FAIL window from 7d to 24h
plan: docs/codex-tasks/doctor-pipeline-correctness-24h-window.md
executor: Codex
status: completed-with-discrepancies
---

# Report — Narrow `flush_pipeline_correctness` FAIL window to 24 hours

## 0. Pre-flight

### 0.1 Environment snapshot

```text
Linux ONLYHOME 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
whoami: ${USER}
HOME: <user-home>
uv: uv 0.11.6 (x86_64-unknown-linux-gnu)
python: /bin/bash: line 1: python: command not found
```

### 0.2 Git status before changes

```text
 M .github/workflows/wiki-lint.yml
 M .gitignore
 M CLAUDE.md
 M README.md
 M codex-hooks.template.json
 M docs/codex-integration-plan.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe-report.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe.md
 M docs/codex-tasks/fix-codex-stop-hook-report.md
 M docs/codex-tasks/fix-codex-stop-hook.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g.md
 M docs/codex-tasks/investigate-flush-py-bug-h-report.md
 M docs/codex-tasks/investigate-flush-py-bug-h.md
 M docs/codex-tasks/post-review-corrections-and-probe-2-report.md
 M docs/codex-tasks/post-review-corrections-and-probe-2.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation-report.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation-report.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation.md
 M docs/codex-tasks/split-codex-stop-light-worker-report.md
 M docs/codex-tasks/split-codex-stop-light-worker.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md
 M docs/codex-tasks/wiki-lint-cleanup-d1-continuation.md
 M hooks/codex/stop.py
 M hooks/hook_utils.py
 M index.example.md
 M scripts/doctor.py
 M scripts/flush.py
 M scripts/lint.py
 M scripts/rebuild_index.py
 M scripts/utils.py
?? Untitled.md
?? docs/codex-tasks/doctor-pipeline-correctness-24h-window-report.md
?? docs/codex-tasks/doctor-pipeline-correctness-24h-window.md
?? docs/codex-tasks/split-doctor-flush-capture-health-report.md
?? docs/codex-tasks/split-doctor-flush-capture-health.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-c-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-c.md
1b45593c87526bd9125d7366648700df1ea7f933
```

### 0.3 Read current `scripts/doctor.py` snapshot

Подтверждение, что `_parse_flush_log_events` и `check_flush_pipeline_correctness` существуют в ожидаемом месте: [EMPIRICAL]

```text
101:def _parse_flush_log_events() -> dict[str, object]:
162:        stats = _parse_flush_log_events()
206:        stats = _parse_flush_log_events()
240:def check_flush_pipeline_correctness() -> CheckResult:
249:        stats = _parse_flush_log_events()
773:        check_flush_pipeline_correctness(),
793:        check_flush_pipeline_correctness(),
```

### 0.4 Baseline `doctor --quick` output (до правок)

```text
BLOCKED: pre-change stdout was not preserved verbatim before the code edit. During the original pre-edit verification, the command was blocked by a pre-existing WSL verification problem outside this task. A current rerun would no longer be a true baseline because scripts/doctor.py has already changed. See section 7.
```

Exit code: `BLOCKED`

### 0.5 Count of Fatal events in last 24h vs 7d (baseline)

[EMPIRICAL] Baseline counters were captured before the patch while the 24h window still included both 2026-04-14 fatal entries.

```text
Fatal events last 7d: 16
Fatal events last 24h: 5
Tail:
2026-04-13 16:09:14 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 16:11:29 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 18:01:20 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 18:30:58 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 21:08:45 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 22:04:02 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 22:25:08 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 23:26:20 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-14 15:19:14 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-14 15:21:06 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
```

Fatal events last 7d: `16`  
Fatal events last 24h: `5`

### 0.6 Doc verification (ОБЯЗАТЕЛЬНО ДО ПРАВОК)

| План говорит | Офдока говорит **сейчас** | Совпало? |
|---|---|---|
| `timedelta(hours=24)` даёт 24-часовую дельту | [OFFICIAL] `class datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)`; [OFFICIAL] `An hour is converted to 3600 seconds.` | ✅ |
| `datetime.now() - timedelta(hours=24)` даёт cutoff timestamp | [OFFICIAL] `Return the current local date and time.`; [OFFICIAL] `If optional argument tz is None or not specified, this is like today()` | ✅ |
| `functools.lru_cache(maxsize=1)` безопасен для function без аргументов | [OFFICIAL] `The cache is threadsafe so that the wrapped function can be used in multiple threads.`; [OFFICIAL] `Since a dictionary is used to cache results, the positional and keyword arguments to the function must be hashable.`; [PROJECT] для функции без аргументов аргументный ключ один и `maxsize=1` не создаёт конкурирующих cache entries | ✅ |

## 1. Implementation

### 1.1 Changes to `_parse_flush_log_events`

Дословный diff:

```diff
--- scripts/doctor.py (pre-task)
+++ scripts/doctor.py (current)
@@ -99,13 +99,16 @@
 
 @lru_cache(maxsize=1)
 def _parse_flush_log_events() -> dict[str, object]:
-    cutoff = datetime.now() - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
+    now = datetime.now()
+    cutoff = now - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
+    cutoff_24h = now - timedelta(hours=24)
     stats: dict[str, object] = {
         "fired": 0,
         "spawned": 0,
         "spawned_chars": 0,
         "skip_only_chars": 0,
         "fatal_errors": 0,
+        "fatal_errors_24h": 0,
         "latest_fatal_ts": None,
     }
 
@@ -137,7 +140,10 @@
             stats["spawned_chars"] = int(stats["spawned_chars"]) + int(spawn_match.group(2))
 
         if "Fatal error in message reader" in tail:
-            stats["fatal_errors"] = int(stats["fatal_errors"]) + 1            latest = stats["latest_fatal_ts"]
+            stats["fatal_errors"] = int(stats["fatal_errors"]) + 1
+            if ts >= cutoff_24h:
+                stats["fatal_errors_24h"] = int(stats["fatal_errors_24h"]) + 1
+            latest = stats["latest_fatal_ts"]
             if latest is None or ts > latest:
                 stats["latest_fatal_ts"] = ts
 ```

Контрольные точки:
- [x] Добавлено поле `fatal_errors_24h: 0` в `stats` dict init
- [x] Добавлен `cutoff_24h = datetime.now() - timedelta(hours=24)` после существующего `cutoff`
- [x] В if-блоке "Fatal error in message reader" добавлен conditional increment `fatal_errors_24h`
- [x] `latest_fatal_ts` tracking не изменён

### 1.2 Changes to `check_flush_pipeline_correctness`

Дословный diff:

```diff
--- scripts/doctor.py (pre-task)
+++ scripts/doctor.py (current)
@@ -244,9 +250,10 @@
     except OSError as exc:
         return CheckResult("flush_pipeline_correctness", False, f"Could not read flush.log: {exc}")
 
-    fatal_errors = int(stats["fatal_errors"])
+    fatal_errors_7d = int(stats["fatal_errors"])
+    fatal_errors_24h = int(stats["fatal_errors_24h"])
     latest_fatal_ts = stats["latest_fatal_ts"]
-    if fatal_errors == 0:
+    if fatal_errors_7d == 0:
         return CheckResult(
             "flush_pipeline_correctness",
             True,
@@ -258,12 +265,20 @@
         if isinstance(latest_fatal_ts, datetime)
         else "unknown"
     )
+    if fatal_errors_24h == 0:
+        return CheckResult(
+            "flush_pipeline_correctness",
+            True,
+            f"No 'Fatal error in message reader' events in last 24h "
+            f"(historical: {fatal_errors_7d} in last {CAPTURE_HEALTH_WINDOW_DAYS}d, "
+            f"most recent {latest_detail}, tracked in issue #16)",
+        )
 
     return CheckResult(
         "flush_pipeline_correctness",
         False,
-        f"Last {CAPTURE_HEALTH_WINDOW_DAYS}d: {fatal_errors} 'Fatal error in message reader' events "
-        f"(most recent {latest_detail}) "
+        f"Last 24h: {fatal_errors_24h} 'Fatal error in message reader' events "
+        f"(7d total: {fatal_errors_7d}, most recent {latest_detail}) "
         f"— active Bug H regression, investigate issue #16",
     )
 ```

Контрольные точки:
- [x] Чтение `fatal_errors_7d` и `fatal_errors_24h` из stats
- [x] Early return PASS когда `fatal_errors_7d == 0` сохранён
- [x] Новая ветка PASS когда `fatal_errors_7d > 0 AND fatal_errors_24h == 0` с historical detail
- [x] FAIL ветка использует `fatal_errors_24h` для пороговой проверки
- [x] Detail message обоих non-zero случаев содержит `issue #16`

### 1.3 Full diff scope check

[EMPIRICAL] Path-filtered diff shows only `scripts/doctor.py` for this task. [EMPIRICAL] Global `git status --short` was already dirty before this task, so the literal “only one modified file in repo” acceptance is not satisfiable without rewriting unrelated history; see section 7.

```text
160	41	scripts/doctor.py

 M .github/workflows/wiki-lint.yml
 M .gitignore
 M CLAUDE.md
 M README.md
 M codex-hooks.template.json
 M docs/codex-integration-plan.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe-report.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe.md
 M docs/codex-tasks/fix-codex-stop-hook-report.md
 M docs/codex-tasks/fix-codex-stop-hook.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g.md
 M docs/codex-tasks/investigate-flush-py-bug-h-report.md
 M docs/codex-tasks/investigate-flush-py-bug-h.md
 M docs/codex-tasks/post-review-corrections-and-probe-2-report.md
 M docs/codex-tasks/post-review-corrections-and-probe-2.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation-report.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation-report.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation.md
 M docs/codex-tasks/split-codex-stop-light-worker-report.md
 M docs/codex-tasks/split-codex-stop-light-worker.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md
 M docs/codex-tasks/wiki-lint-cleanup-d1-continuation.md
 M hooks/codex/stop.py
 M hooks/hook_utils.py
 M index.example.md
 M scripts/doctor.py
 M scripts/flush.py
 M scripts/lint.py
 M scripts/rebuild_index.py
 M scripts/utils.py
?? Untitled.md
?? docs/codex-tasks/doctor-pipeline-correctness-24h-window-report.md
?? docs/codex-tasks/doctor-pipeline-correctness-24h-window.md
?? docs/codex-tasks/split-doctor-flush-capture-health-report.md
?? docs/codex-tasks/split-doctor-flush-capture-health.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-c-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-c.md
```

## 2. Phase 1 — Unit smoke (Codex выполняет сам)

### 2.1 `doctor --quick`

Команда:
```text
UV_PROJECT_ENVIRONMENT=<user-home>/.cache/llm-wiki/.venv uv run python scripts/wiki_cli.py doctor --quick
```

Полный stdout:
```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 74/172 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 1558410/1561277 chars reached flush.py (coverage 99.8%)
[FAIL] flush_pipeline_correctness: Last 24h: 4 'Fatal error in message reader' events (7d total: 16, most recent 2026-04-14 15:21:06) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <user-home>/.local/bin/uv
[PASS] index_health: Index is up to date.
[PASS] structural_lint: Results: 0 errors, 1 warnings, 45 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

Exit code: `0`

Ожидание: `flush_pipeline_correctness` станет PASS, если в последние 24h нет новых Fatal events. [PROJECT]

Факт: ❌ [EMPIRICAL] В последние 24h всё ещё есть 4 реальных Bug H события, поэтому check остался FAIL. Это не regression патча, а корректное срабатывание нового окна.

### 2.2 `doctor --full`

Команда:
```text
UV_PROJECT_ENVIRONMENT=<user-home>/.cache/llm-wiki/.venv uv run python scripts/wiki_cli.py doctor --full
```

Полный stdout (head + tail):
```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 74/172 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 1558410/1561277 chars reached flush.py (coverage 99.8%)
[FAIL] flush_pipeline_correctness: Last 24h: 4 'Fatal error in message reader' events (7d total: 16, most recent 2026-04-14 15:21:06) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: <user-home>/.local/bin/uv
[PASS] doctor_runtime: Doctor is not using repo .venv in WSL
[PASS] codex_config: codex_hooks=true in <user-home>/.codex/config.toml
[PASS] codex_hooks_json: Found expected hooks in <user-home>/.codex/hooks.json
[PASS] index_health: Index is up to date.
[PASS] structural_lint: Results: 0 errors, 1 warnings, 45 suggestions
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
[PASS] total_tokens_injection: NOT active — model does not observe <total_tokens> in its input context
```

Exit code: `0`

### 2.3 Regression check на `throughput` и `quality_coverage`

Из вывода 2.1/2.2:

```text
[PASS] flush_throughput: Last 7d: 74/172 flushes spawned (skip rate 57%)
[PASS] flush_quality_coverage: Last 7d: 1558410/1561277 chars reached flush.py (coverage 99.8%)
```

Ожидание: строки остаются без смысловой regression относительно baseline. [PROJECT]

Факт: ✅ [EMPIRICAL] Оба checks остались PASS, а новая логика затронула только `pipeline_correctness`. [EMPIRICAL] Буквальная строка отличается от раннего baseline, потому что `scripts/flush.log` продолжал расти во время задачи: `73/171` → `74/172`, но skip rate и coverage остались на том же уровне.

### 2.4 Python import sanity

Команда из шаблона:
```text
UV_PROJECT_ENVIRONMENT=<user-home>/.cache/llm-wiki/.venv uv run python -c "from scripts.doctor import _parse_flush_log_events, check_flush_pipeline_correctness; print(_parse_flush_log_events().get('fatal_errors_24h'))"
```

Полный stdout:
```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    from scripts.doctor import _parse_flush_log_events, check_flush_pipeline_correctness; print(_parse_flush_log_events().get('fatal_errors_24h'))
  File "<repo-root>/scripts/doctor.py", line 35, in <module>
    from runtime_utils import find_uv, is_wsl
ModuleNotFoundError: No module named 'runtime_utils'
```

Exit code: `1`

[EMPIRICAL] Шаблонная команда падает из-за существующей import-модели `doctor.py`, а не из-за 24h-патча. Проверка с корректным import path:

```text
PYTHONPATH=scripts UV_PROJECT_ENVIRONMENT=<user-home>/.cache/llm-wiki/.venv uv run python -c "from doctor import _parse_flush_log_events, check_flush_pipeline_correctness; print(_parse_flush_log_events().get('fatal_errors_24h'))"
4
```

Exit code: `0`

Ожидание: число (0 или больше), не `AttributeError`/`KeyError`. [PROJECT]

Факт: ✅ [EMPIRICAL] На корректном `PYTHONPATH` ключ `fatal_errors_24h` существует и возвращает число `4`. [EMPIRICAL] Шаблонная команда не годится для этого репозитория в текущем import layout.

## 3. Phase 2 — Integration `[awaits user]`

### 3.1 Реальное использование doctor --quick через день

`[awaits user]`

### 3.2 Manual Bug H trigger stress test

`[awaits user — optional]`

## 4. Phase 3 — Statistical `[awaits 7-day window]`

### 4.1 24h window sensitivity over 7 days

`[awaits 7-day window]`

## 5. Tools used

| Tool | Status | Details |
|---|---|---|
| Wiki: `wiki/concepts/codex-stop-hook-reliability.md` | ✅ | [PROJECT] Прочитал для контекста: Bug H уже описан как intermittent flush failure, а stop-path reliability отделён от него. |
| Repo docs: `docs/codex-tasks/split-doctor-flush-capture-health.md` | ✅ | [PROJECT] Прочитал родительский план, чтобы не сломать split-metric дизайн и registration slot. |
| Repo docs: `docs/codex-tasks/split-doctor-flush-capture-health-report.md` | ✅ | [PROJECT] Прочитал родительский отчёт, чтобы сохранить naming/verification continuity. |
| Repo read: `scripts/doctor.py` | ✅ | [EMPIRICAL] Прочитал `_parse_flush_log_events` и `check_flush_pipeline_correctness` до правки; snapshot в section 0.3. |
| WebFetch: https://docs.python.org/3/library/datetime.html#datetime.timedelta | ✅ | [OFFICIAL] Использовал официальный Python docs fetch/open; процитированы constructor signature и `An hour is converted to 3600 seconds.` |
| WebFetch: https://docs.python.org/3/library/datetime.html#datetime.datetime.now | ✅ | [OFFICIAL] Использовал официальный Python docs open/find; процитировано `Return the current local date and time.` |
| WebFetch: https://docs.python.org/3/library/functools.html#functools.lru_cache | ✅ | [OFFICIAL] Использовал официальный Python docs open; процитированы `The cache is threadsafe ...` и `Since a dictionary is used ... hashable.` |
| MCP filesystem | not used | [PROJECT] Локального чтения через shell и `apply_patch` хватило; дополнительный filesystem MCP не потребовался. |
| MCP git | not used | [PROJECT] Достаточно было локального `git status` и path-filtered diff без отдельного MCP git. |
| `uv run python scripts/wiki_cli.py doctor --quick` | ✅ | [EMPIRICAL] Выполнен post-change; exit code `0`; показал новый 24h FAIL detail. |
| `uv run python scripts/wiki_cli.py doctor --full` | ✅ | [EMPIRICAL] Выполнен post-change; exit code `0`; full checks остались рабочими. |
| Python direct probe (`_parse_flush_log_events` / `check_*`) | ✅ | [EMPIRICAL] Использовал для сверки live counters и подтверждения `fatal_errors_24h` на реальном `flush.log`. |
| Subagent делегирование | not used | [PROJECT] Задача узкая, последовательная и быстрее делается локально без параллельных subagents. |

## 6. Out-of-scope temptations

- [PROJECT] Хотелось сразу починить шаблонную import-команду `from scripts.doctor ...`, но это уже не whitelist и касается import layout/packaging, а не 24h-window logic.
- [PROJECT] Хотелось одновременно обновить issue `#16` новыми числами `16/7d` и `4/24h`, но это отдельный follow-up после user review.
- [PROJECT] Хотелось вынести `24h` в конфиг/env, но план прямо просил hardcoded simplest approach.

## 7. Discrepancies

- [EMPIRICAL] Старое WSL-правило из repo instructions про `UV_PROJECT_ENVIRONMENT=/root/.cache/llm-wiki/.venv` в этом окружении неверно: реальный `${USER}` — не `root`, а рабочий внешний env здесь `<user-home>/.cache/llm-wiki/.venv`. Команды doctor пришлось гонять с этой фактической переменной.
- [EMPIRICAL] План ожидал, что `doctor --quick` может стать PASS после сужения окна. В реальном `scripts/flush.log` на момент финальной проверки всё ещё было `4` Bug H событий в последние 24 часа, поэтому новый check корректно остался FAIL.
- [EMPIRICAL] Ранний pre-edit baseline `doctor --quick` не был сохранён verbatim до патча. Я не стал подменять его текущим rerun и честно отметил section 0.4 как `BLOCKED`.
- [EMPIRICAL] Глобальный `git status --short` был грязным ещё до начала задачи, поэтому acceptance “никаких других modified files” нельзя выполнить буквально на уровне всего repo. Я ограничил кодовые правки whitelist-файлом `scripts/doctor.py` и показал path-filtered diff.
- [EMPIRICAL] Шаблонная import-команда `from scripts.doctor ...` в этом репозитории не работает из-за существующего import layout (`runtime_utils` импортируется как top-level module). Для sanity-check пришлось использовать `PYTHONPATH=scripts`.
- [EMPIRICAL] `flush.log` — живой файл. Пока шла верификация, одно событие выпало из 24h окна, поэтому числа дрейфнули `5 -> 4` за последние 24 часа и `73/171 -> 74/172` по throughput. Это не regression, а ожидаемое следствие live log.

## 8. Self-audit checklist

- [x] 0.1 Environment snapshot заполнен
- [x] 0.2 Git status before заполнен
- [x] 0.3 Snapshot функций заполнен
- [x] 0.4 Baseline doctor --quick output заполнен честным `BLOCKED`
- [x] 0.5 Baseline fatal events counts заполнены
- [x] 0.6 Doc verification таблица заполнена дословными цитатами (не "см. план")
- [x] 1.1 Diff для `_parse_flush_log_events` вставлен, все контрольные точки ✅
- [x] 1.2 Diff для `check_flush_pipeline_correctness` вставлен, все контрольные точки ✅
- [x] 1.3 Scope check выполнен path-filtered diff; глобальная dirty-state объяснена в section 7
- [x] 2.1 doctor --quick post-change output заполнен с exit code
- [x] 2.2 doctor --full post-change output заполнен с exit code
- [x] 2.3 throughput/quality_coverage regression check показывает PASS по смыслу; live-log drift объяснён в section 7
- [x] 2.4 Python import sanity проверен; шаблонная команда упала, рабочий `PYTHONPATH=scripts` probe дал число `4`
- [x] 3.x Phase 2 fields marked `[awaits user]`
- [x] 4.x Phase 3 fields marked `[awaits 7-day window]`
- [x] 5 Tools used таблица полностью заполнена (no dashes)
