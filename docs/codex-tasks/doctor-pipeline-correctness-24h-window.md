---
task: Narrow flush_pipeline_correctness FAIL window from 7d to 24h
executor: Codex
whitelist: [scripts/doctor.py]
parent: docs/codex-tasks/split-doctor-flush-capture-health.md
---

# Plan — Narrow `flush_pipeline_correctness` FAIL window to 24 hours

## Иерархия источников правды

1. **Официальная документация** (Python stdlib — см. Doc verification ниже) — primary source of truth.
2. **Реальное состояние кода и файлов проекта** — secondary (`scripts/doctor.py` на момент чтения).
3. **Этот план** — derived artifact, написан Claude'ом, может содержать ошибки. Если план и дока/код расходятся — приоритет у доки и кода, не у плана.

## Context

После merge #22 (split `check_flush_capture_health` → throughput / quality_coverage / pipeline_correctness) `doctor --quick` стабильно красный из-за `pipeline_correctness`: 16 "Fatal error in message reader" events за последние 7 дней (Bug H, issue #16).

**[EMPIRICAL]** Текущий live output:
```
[PASS] flush_throughput: 70/167 spawned (skip rate 58%)
[PASS] flush_quality_coverage: 1476572/1479121 chars (coverage 99.8%)
[FAIL] flush_pipeline_correctness: 16 'Fatal error in message reader' events
```

**[PROJECT]** `quality_coverage=99.8%` доказывает, что Bug H затрагивает ~0.2% объёма контента. Постоянно красный doctor теряет сигнал — нужно ловить **активные** регрессии, а не исторический долг. Решение: FAIL условие использует 24-часовое окно, детализация (количество + latest) остаётся по 7d окну для контекста.

## Doc verification

- **[OFFICIAL]** Python `datetime.timedelta(hours=24)` — https://docs.python.org/3/library/datetime.html#datetime.timedelta (уже используется в родительском parse через `timedelta(days=...)`).

## Mandatory external tools

| Tool | Purpose | Why |
|---|---|---|
| Wiki read | `wiki/concepts/codex-stop-hook-reliability.md` | Контекст надёжности capture pipeline |
| Repo read | `docs/codex-tasks/split-doctor-flush-capture-health.md` + `-report.md` | Предыдущая итерация, на которой строится этот фикс |
| `uv run python scripts/wiki_cli.py doctor --quick` | Verify PASS/FAIL flip | Acceptance |

## Root cause

**[EMPIRICAL]** `_parse_flush_log_events()` (scripts/doctor.py:100) уже считает `fatal_errors` в 7d окне и трекает `latest_fatal_ts`. Нет отдельного счётчика для 24h подмножества. `check_flush_pipeline_correctness` (line 235) сейчас флагает FAIL если `fatal_errors > 0` за все 7 дней.

## Files to modify (whitelist)

**Только**: `scripts/doctor.py`

## Fix design

### Изменение 1 — `_parse_flush_log_events` трекает 24h счётчик

**Где**: `scripts/doctor.py:100-145`

Добавить к `stats` поле `fatal_errors_24h` и параллельный подсчёт:

```python
@lru_cache(maxsize=1)
def _parse_flush_log_events() -> dict[str, object]:
    cutoff = datetime.now() - timedelta(days=CAPTURE_HEALTH_WINDOW_DAYS)
    cutoff_24h = datetime.now() - timedelta(hours=24)
    stats: dict[str, object] = {
        "fired": 0,
        "spawned": 0,
        "spawned_chars": 0,
        "skip_only_chars": 0,
        "fatal_errors": 0,
        "fatal_errors_24h": 0,
        "latest_fatal_ts": None,
    }
    ...
    # existing loop body unchanged, only the fatal-error branch extended:
    if "Fatal error in message reader" in tail:
        stats["fatal_errors"] = int(stats["fatal_errors"]) + 1
        if ts >= cutoff_24h:
            stats["fatal_errors_24h"] = int(stats["fatal_errors_24h"]) + 1
        latest = stats["latest_fatal_ts"]
        if latest is None or ts > latest:
            stats["latest_fatal_ts"] = ts
```

### Изменение 2 — `check_flush_pipeline_correctness` использует 24h для FAIL

**Где**: `scripts/doctor.py:235-267`

```python
def check_flush_pipeline_correctness() -> CheckResult:
    if not FLUSH_LOG.exists():
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            "No flush.log yet (fresh install). Will populate after first SessionEnd.",
        )

    try:
        stats = _parse_flush_log_events()
    except OSError as exc:
        return CheckResult("flush_pipeline_correctness", False, f"Could not read flush.log: {exc}")

    fatal_errors_7d = int(stats["fatal_errors"])
    fatal_errors_24h = int(stats["fatal_errors_24h"])
    latest_fatal_ts = stats["latest_fatal_ts"]

    if fatal_errors_7d == 0:
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            f"No 'Fatal error in message reader' events in last {CAPTURE_HEALTH_WINDOW_DAYS} days",
        )

    latest_detail = (
        latest_fatal_ts.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(latest_fatal_ts, datetime)
        else "unknown"
    )

    if fatal_errors_24h == 0:
        return CheckResult(
            "flush_pipeline_correctness",
            True,
            f"No 'Fatal error in message reader' events in last 24h "
            f"(historical: {fatal_errors_7d} in last {CAPTURE_HEALTH_WINDOW_DAYS}d, "
            f"most recent {latest_detail}, tracked in issue #16)",
        )

    return CheckResult(
        "flush_pipeline_correctness",
        False,
        f"Last 24h: {fatal_errors_24h} 'Fatal error in message reader' events "
        f"(7d total: {fatal_errors_7d}, most recent {latest_detail}) "
        f"— active Bug H regression, investigate issue #16",
    )
```

### Что НЕ менять

- `check_flush_throughput` и `check_flush_quality_coverage` — не трогать.
- `CAPTURE_HEALTH_WINDOW_DAYS` константу — не менять.
- Регистрацию в `get_quick_checks` / `get_full_checks` — не менять.
- Никакие другие файлы.

## Verification

### Phase 1 — Unit smoke

**1.1** `uv run python scripts/wiki_cli.py doctor --quick` — ожидание: `pipeline_correctness` PASS (если в последние 24h нет Fatal events), detail содержит "historical: N in last 7d" и ссылку на issue #16. Если Bug H стрельнул в последний час — FAIL с "Last 24h: N events".

**1.2** `uv run python scripts/wiki_cli.py doctor --full` — тот же результат для pipeline_correctness + остальные full-only checks работают.

**1.3** Проверить что `throughput` и `quality_coverage` остались без изменений.

### Phase 2 — Git status (Codex выполняет сам)

**2.1** `git diff scripts/doctor.py` — только `_parse_flush_log_events` и `check_flush_pipeline_correctness` затронуты.

**2.2** `git status` — никаких других модифицированных файлов.

### Phase 3 — Integration verification `[awaits user]`

**3.1** Пользователь запускает `doctor --quick` в его реальном окружении через день — проверка что pipeline_correctness остаётся PASS (если не было реальных Bug H events) или корректно детектирует new regression (если Bug H стрельнул).

**3.2** Пользователь вручную триггерит Bug H путь (optional stress test) и проверяет что check корректно переключается в FAIL.

### Phase 4 — Statistical window `[awaits 7-day window]`

**4.1** Через 7 дней: проверить что 24h окно достаточно sensitive — не пропускает реальные регрессии, не слишком шумное.

## Acceptance criteria

- ✅ Phase 1.1: doctor --quick показывает pipeline_correctness как PASS с historical 7d context в detail (при отсутствии Fatal в последние 24h).
- ✅ Phase 1.3: throughput и quality_coverage unchanged.
- ✅ Phase 2.1: diff изолирован в whitelist.
- ✅ `doctor --quick` overall green (если никаких других check не красных).

## Out of scope

1. **Issue #16 update** с новыми данными (16 events/7d, 0.2% content loss) — отдельная задача после merge.
2. **Bug H root cause fix** — это ortogonal work, данный фикс только меняет окно мониторинга.
3. **Конфигурируемый window** через env var — не требуется, 24h hardcoded.

## Rollback

```bash
git checkout scripts/doctor.py
```

## Notes для исполнителя

- **Doc-first**: ПЕРЕД правкой кода открой Python datetime URL из Doc verification и процитируй дословный контракт `timedelta(hours=24)` в `0.6 Doc verification` отчёта. Не пиши по памяти, даже если "знаешь".
- **Минимальный patch**: ~15 строк добавить, 1 функция изменить. Никаких других правок.
- **Не забыть** `@lru_cache` остаётся — при изменении структуры stats dict кэш автоматически пересоберётся в новой сессии.
- **Whitelist строгий** — только `scripts/doctor.py`. Соблазны "по дороге" → секция Out-of-scope-temptations в отчёте, не в коде.
- **Отчёт обязателен**: `docs/codex-tasks/doctor-pipeline-correctness-24h-window-report.md` — шаблон уже создан Claude'ом, заполняй последовательно.
- **Self-audit** перед сдачей — любой ❌ → возвращайся и доделывай.
- **Никаких commit/push** — финал = заполненный отчёт. User ревьюит и коммитит сам.
