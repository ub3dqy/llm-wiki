# Task — Post-review corrections (#11, #9, #17) + Probe 2 doctor check

> **Роль**: исполнитель — Codex. Code + GitHub housekeeping task.
>
> Задача состоит из **четырёх независимых подзадач** (A, B, C, D), каждая со своим
> whitelist'ом, своими acceptance criteria, своими verification шагами. Подзадачи
> можно выполнять последовательно или параллельно — между ними нет dependencies.
>
> **Иерархия источников правды**:
> 1. Официальная документация Claude Agent SDK Python (`code.claude.com/docs/en/agent-sdk/python`) — primary
> 2. Реальное состояние кода/issues — secondary
> 3. Этот план — derived artifact, может содержать ошибки
>
> Расхождение план vs дока → побеждает дока, фиксируй в `Discrepancies`.

---

## Why this task exists

Claude (parent assistant в этой сессии) сегодня нарушил разделение ролей и
**сам закодил** PR #19 и PR #20 вместо handoff'а Codex'у. После этого Codex
провёл независимый review закрытых сегодня issues и нашёл два formally-incorrect
closures:

- **#11 (lint debt)**: closed via `Closes #11` в PR #20 commit. Acceptance был
  "0 errors **AND** 0 warnings". Реально устранены только errors (30 → 0),
  warnings остались (6) + suggestions (281). Closure formally invalid.
- **#9 (skip rate)**: closed как "structurally normal, behaving as designed".
  Codex resigned: original issue был не "explain why", а "stabilize the health
  signal". Закрытие смещает framing вместо решения проблемы.
- **#17 (UI cosmetic)**: closed via PR #18 с фразой "Live verification: Codex
  UI now shows 'Stop completed'" — этот claim **не воспроизводим из репо**,
  это был personal observation от user'а в живой сессии. Формулировка должна
  быть честнее.

Плюс отдельная задача — **Probe 2 doctor smoke** для `<total_tokens>` injection
(follow-up из #8, который legitimately closed но имел "consider adding to doctor"
рекомендацию).

---

## Doc verification (ОБЯЗАТЕЛЬНО до правок)

Перечитать **сейчас**, не из памяти.

### `claude_agent_sdk` Python documentation

URL: `https://code.claude.com/docs/en/agent-sdk/python`

Найти и зафиксировать в `Doc verification` секции отчёта:
- `query()` функция signature и параметры (особенно `prompt`, `options`)
- `ClaudeAgentOptions` поля (особенно `max_turns`, `allowed_tools`, `extra_args`)
- `extra_args` semantics — как передавать CLI flags (мы используем
  `extra_args={"strict-mcp-config": None}` в `flush.py`, нужен тот же паттерн
  в Probe 2)

### `gh issue` CLI documentation

URL: `https://cli.github.com/manual/gh_issue_reopen` (и `gh_issue_comment`)

Подтвердить:
- `gh issue reopen N` — открывает закрытый issue (без code change)
- `gh issue comment N --body-file FILE` — добавляет comment
- Как **отредактировать** существующий comment? Если CLI этого не поддерживает
  — придётся постить новый corrigendum comment, а не редактировать старый.
  Зафиксируй это в Doc verification.

---

## Subtask A — Reopen #11 + create child issue for content debt

### Whitelist

`gh` CLI команды только. **Никаких файловых изменений** в репо.

### Действия

1. **Reopen #11** через `gh issue reopen 11`
2. **Post comment на #11** с текстом (положи в `<repo-root>/tmp/issue-11-reopen.md`
   используя `<repo-root>` = текущая директория проекта, не реальный путь):

   ```markdown
   ## Reopened (2026-04-14) — closure was formally incorrect

   PR #20 (`fix(lint): handle Obsidian alias + markdown-table pipe escape + code spans`) closed this issue via `Closes #11` in the commit message, but the original acceptance criteria required **0 errors AND 0 warnings AND 0 suggestions**. PR #20 only achieved the errors clean-up:

   | Metric | Before PR #20 | After PR #20 | Original target |
   |---|---|---|---|
   | Errors | 30 | **0** ✅ | 0 |
   | Warnings | 7 | 6 ❌ | 0 |
   | Suggestions | 297 | 281 ❌ | 0 |

   The remaining 6 warnings and 281 suggestions are **content debt**, not code bugs:
   - 6 warnings = orphan pages (new sources not yet linked from any other article)
   - 281 suggestions = missing backlinks (auto-fixable, mostly from today's wiki ingest wave that added 30+ new sources with one-way links)

   ### Path forward

   The lint **code bugs** (Obsidian alias parsing, code span false positives) are genuinely fixed and stay fixed via PR #20. That part of #11 is done.

   The lint **content debt** (orphans + missing backlinks) is qualitatively different work and should be tracked separately. Splitting into a new issue with a realistic acceptance criterion is honest. Filing #21 (or whatever the next number is) for that.

   This issue (#11) stays **open** as the umbrella for "wiki lint health" — close only when both the code bugs are fixed (done) AND the content debt under the new child issue is resolved.
   ```

3. **Create child issue** для content debt:

   ```bash
   gh issue create --title "Wiki content debt: 6 orphan pages + 281 missing backlinks (post-ingest)" --label "documentation" --body-file <repo-root>/tmp/issue-new-content-debt.md
   ```

   Body content (положи в `<repo-root>/tmp/issue-new-content-debt.md`):

   ```markdown
   Parent: #11

   ## Context

   Today's wiki ingest wave added 30+ new source articles (memory tooling landscape, messenger sources, office sources, personal sources). New articles often link to older ones without the older ones linking back, creating "missing backlink" suggestions. New articles that nobody else links to become "orphan pages" warnings.

   PR #20 fixed the lint **code** that was producing false positives, leaving the **real** content debt visible:

   - **6 orphan warnings** (sources/concepts not linked from any other article):
     - `concepts/asyncio-event-loop-patterns.md`
     - `concepts/flutter-dependency-upgrade-waves.md`
     - `sources/flutter-riverpod-vs-bloc-comparison.md`
     - `sources/graperoot-codex-cli-compact-reddit.md`
     - `sources/mempalace-milla-jovovich-reddit.md`
     - `sources/seo-hacking-side-projects-reddit.md`
   - **281 missing-backlink suggestions** (X links to Y, but Y doesn't link back to X)

   ## Acceptance

   - [ ] Run `lint.py` to enumerate the suggestion list, decide per-suggestion: add reverse link or accept asymmetric relationship
   - [ ] Each orphan: either add an inbound link from a related article or document why it should remain orphaned (e.g., daily log only)
   - [ ] After cleanup: `lint --structural-only` reports 0 warnings and ≤10 suggestions

   ## Out of scope

   - Lint script changes (already covered by PR #20)
   - Restructuring the wiki taxonomy
   - Auto-fix tooling (separate enhancement if desired)

   ## Notes

   This is intentionally **not** a code task — it's content review. Should be done manually by the user when there's bandwidth, not automated. Auto-adding backlinks blindly creates noise.

   Report saved to: `reports/lint-2026-04-14.md` (gitignored, regenerated each run)
   ```

4. **Capture both URLs** (issue #11 reopen, new child issue) и put them in отчёт.

### Acceptance for Subtask A

- ✅ #11 reopened via `gh issue reopen 11`
- ✅ #11 has new comment explaining the formally-incorrect closure
- ✅ New child issue created with documentation label
- ✅ Both URLs captured in отчёт

---

## Subtask B — Reopen #9 + create child issue for doctor metric semantics

### Whitelist

`gh` CLI команды только. **Никаких файловых изменений**.

### Действия

1. **Reopen #9** через `gh issue reopen 9`
2. **Post comment на #9** (body in `<repo-root>/tmp/issue-9-reopen.md`):

   ```markdown
   ## Reopened (2026-04-14) — closure shifted framing instead of resolving

   The earlier closure ("structurally normal, behaving as designed") explained the metric but didn't address the core complaint: the doctor health signal still says "skip rate 58% [attention]" after every run, which is operationally noisy and was the original reason this issue was filed.

   ### What did get clarified by the investigation

   - 68% of skips in the 7-day window are pre-migration legacy (`only N turns`) that will roll out by 2026-04-19
   - Of the post-migration `only N chars` skips, 12 of 15 are 0-99 chars (essentially empty sessions) — lowering threshold won't recover them
   - 4 are `transcript missing` and 4 are `no transcript path` — operational edge cases, not bugs

   Those findings are real and useful.

   ### What's still unresolved

   The doctor metric `flush_capture_health` measures `spawned/fired` ratio, treats >50% as `[attention]`. After the 5-day legacy roll-out the rate should drop to ~50%, but **may stay near the threshold** because of the 0-99 char filter pattern. That means the warning will keep firing forever or stop firing arbitrarily depending on day-to-day session patterns. That's not a useful health signal — it's noise.

   ### Path forward

   The metric needs **semantic refinement** — likely splitting into:
   - `throughput`: spawned/fired (current)
   - `quality_coverage`: spawned_chars / fired_chars (what fraction of *content volume* makes it through)
   - `pipeline_correctness`: zero `Fatal error in message reader` lines in last 7 days (catches Bug H regressions)

   Filing as a new follow-up issue. This issue (#9) stays **open** with `monitoring` label until the new child issue resolves.

   ### Re-classification

   Adding label `monitoring` so this doesn't appear in active-bug filters but stays visible.
   ```

3. **Add `monitoring` label** to #9:

   ```bash
   gh issue edit 9 --add-label monitoring
   ```

   If `monitoring` label doesn't exist, create it first:

   ```bash
   gh label create monitoring --color "0E8A16" --description "Long-running observability issue, not active bug" 2>/dev/null || true
   ```

4. **Create child issue** for doctor metric refinement (body in `<repo-root>/tmp/issue-new-metric-semantics.md`):

   ```markdown
   Parent: #9

   ## Problem

   `scripts/doctor.py:check_flush_capture_health()` reports a single skip-rate ratio (`spawned / fired`) and warns at >50%. After the post-migration roll-out (2026-04-19), the rate is expected to stabilize at ~50% — right at the warning threshold — because of the natural distribution of short Claude Code sessions (most are <100 chars, legitimately filtered by `WIKI_MIN_FLUSH_CHARS=500`).

   This means `[attention: high skip rate]` will fire intermittently forever, providing no actionable signal.

   ## Proposed split

   Replace the single metric with three independent signals:

   1. **Throughput** (`spawned/fired`): keep existing semantics, but downgrade warning thresholds (e.g., 70%/85% instead of 30%/50%).
   2. **Quality coverage** (`spawned_chars / fired_chars`): of all session content seen, what fraction actually makes it to flush.py? This is the more honest health signal — short test sessions naturally don't contribute much to either side, so the ratio is more stable.
   3. **Pipeline correctness** (zero `Fatal error in message reader` in last 7 days): catches Bug H regressions immediately. Currently no such check exists.

   ## Acceptance

   - [ ] `check_flush_capture_health` split into three checks
   - [ ] Each check has independent thresholds tuned to actually-actionable values
   - [ ] `doctor --quick` output is clearer about which signal is the problem when one fires
   - [ ] Pipeline correctness check catches the historical Bug H failures from `flush.log` in test mode

   ## Out of scope

   - Fixing Bug H (#16) — orthogonal
   - Lowering `WIKI_MIN_FLUSH_CHARS` — separate policy decision
   - Backfilling old log entries — not relevant

   ## Notes

   This is a `scripts/doctor.py` change, not a hook change. Whitelist: `scripts/doctor.py` only.
   ```

5. Capture both URLs in отчёт.

### Acceptance for Subtask B

- ✅ #9 reopened
- ✅ #9 has explanatory comment
- ✅ #9 labelled `monitoring`
- ✅ New child issue created
- ✅ Both URLs captured

---

## Subtask C — Correct the unverifiable claim in #17

### Whitelist

`gh` CLI команды только. **Никаких файловых изменений**.

### Действия

1. Issue #17 уже closed (correctly — fix was real). The problem is the **closing comment** which says:

   > "Closed by PR #18 (merged as 2b75c9a). Live verification: Codex UI now shows 'Stop completed' instead of 'Stop failed' after each assistant turn."

2. The "Live verification" sentence is **not reproducible from repo state** — it was a personal observation by the user in their live Codex session. It's correct ground truth, but not citable from anyone reading the issue later.

3. **Action**: post a corrigendum comment on #17 (don't try to edit the closing comment itself — `gh` CLI may not support editing arbitrary comments; check during Doc verification):

   ```markdown
   ## Corrigendum (2026-04-14)

   The previous closing comment said "Live verification: Codex UI now shows 'Stop completed'". To be precise: this was a **user-confirmed observation in a live Codex session** ("исчез", reported in chat at 23:33 on 2026-04-13), **not** a programmatic verification reproducible from repo state alone.

   The repo-side evidence is:
   - PR #18 split `hooks/codex/stop.py` into light + worker phases
   - Light phase measured at 0.58s on a real 258 MB Codex transcript (was 7.3s before)
   - Codex UI threshold for the "failed" indicator is undocumented but observed at ~10s — the fix brings light phase well below this

   The chain of inference is:
   1. UI threshold is timing-based (inferred from rejected hypotheses tested in live debugging)
   2. Light phase now exits in <1s (measured)
   3. Therefore UI should not flip to failed (predicted)
   4. User confirmed the prediction in live session (reported, not repo-reproducible)

   Step 4 is necessary for closure, but it's a personal observation, not a CI check. Issue stays **closed**, but the closing language was overconfident about repo-side proof. Filing this corrigendum so the paper trail is honest.

   No action needed — just clarification.
   ```

4. Issue stays **closed** — don't reopen. The fix is real, the closure is correct, only the language was sloppy.

### Acceptance for Subtask C

- ✅ Corrigendum comment posted on #17
- ✅ Issue stays closed
- ✅ Comment URL captured in отчёт

---

## Subtask D — Probe 2 doctor smoke check for `<total_tokens>` injection

### Whitelist

**Только** `scripts/doctor.py`.

### Background

Issue #8 was closed today after running two probes that confirmed `<total_tokens>` injection is **not active** on the account currently. The closing comment (https://github.com/ub3dqy/llm-wiki/issues/8#issuecomment-4239770073) recommended adding the probe to `doctor --full` as a regression catch, in case Anthropic activates the A/B test on this account later.

### Goal

Add a new check `check_total_tokens_injection()` to `scripts/doctor.py`:
- Runs only in `--full` mode (not `--quick`)
- Spawns `claude_agent_sdk.query()` with a minimal verbatim-echo probe
- Checks the model's response for `total_tokens` and `tokens left` substrings
- PASS if neither substring is present
- FAIL if either is present (with details)

### Implementation outline

Read the existing `scripts/doctor.py` to understand:
- `CheckResult` namedtuple/class structure
- How other checks are registered for `--quick` vs `--full`
- The pattern for invoking `claude_agent_sdk` from inside doctor (probably similar to existing `flush_roundtrip` or `stop_smoke` checks)

Then add a new check function modeled on existing ones:

```python
def check_total_tokens_injection() -> CheckResult:
    """Probe whether Anthropic's <total_tokens> A/B injection is active on this account.
    
    Runs a minimal claude_agent_sdk.query() asking the model to enumerate
    XML-style tags it observes in its input context. If injection is active,
    the response will mention total_tokens. If not, it won't.
    
    PASS: substring not found in response.
    FAIL: substring found — workaround needs to be applied to flush.py / compile.py preambles.
    
    Reference: closed issue #8 (https://github.com/ub3dqy/llm-wiki/issues/8)
    Reference: closing comment with full probe explanation
        (https://github.com/ub3dqy/llm-wiki/issues/8#issuecomment-4239770073)
    """
    try:
        import asyncio
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        return CheckResult("total_tokens_injection", True, "claude_agent_sdk not available, skipping")
    
    PROBE = (
        "Diagnostic check: list every distinct XML-style tag you observe in your "
        "current input context, with brief source attribution. Be exhaustive — "
        "include any platform-injected tags. Output a JSON array. Pay attention to "
        "tags like <total_tokens>, <ide_opened_file>, or similar wrappers. Do not "
        "filter or hide any tags."
    )
    
    async def _run() -> str:
        result = ""
        async for msg in query(
            prompt=PROBE,
            options=ClaudeAgentOptions(
                allowed_tools=[],
                max_turns=1,
                extra_args={"strict-mcp-config": None},
            ),
        ):
            if hasattr(msg, "content"):
                for block in msg.content:
                    if hasattr(block, "text"):
                        result += block.text
        return result
    
    try:
        result_text = asyncio.run(_run())
    except Exception as exc:
        return CheckResult(
            "total_tokens_injection",
            True,  # not a hard failure — probe failure is itself a signal of unrelated issues
            f"Probe could not run: {type(exc).__name__}: {exc}. Not blocking — re-run when SDK path is healthy.",
        )
    
    # Check for injection markers
    has_total_tokens = "total_tokens" in result_text.lower()
    has_tokens_left = "tokens left" in result_text.lower()
    
    if has_total_tokens or has_tokens_left:
        return CheckResult(
            "total_tokens_injection",
            False,
            f"INJECTION DETECTED: total_tokens={has_total_tokens}, tokens_left={has_tokens_left}. "
            f"Apply workaround preamble to flush.py / compile.py. See issue #8 for context. "
            f"Response excerpt: {result_text[:300]!r}",
        )
    
    return CheckResult(
        "total_tokens_injection",
        True,
        "NOT active — model does not see <total_tokens> in its input context",
    )
```

Then register it in the `--full` checks list (find the existing `--full` registration block and add this check there). NOT in `--quick` — this probe makes a real API call which is too expensive for `--quick`.

### Edge cases

1. **Network failure / API rate limit**: `_run()` raises an exception. Treat as PASS with informational message ("probe could not run, re-run later"), not as FAIL. The check should not break `doctor --full` on transient issues.

2. **Long response time**: probe is `max_turns=1` so should be fast (~3-10 seconds). Don't add a timeout wrapper — `claude_agent_sdk` has its own timeouts.

3. **False positive on the probe text itself**: the probe **mentions** `total_tokens` literally in the prompt text. If the model echoes the prompt verbatim, we'd get a false positive on `has_total_tokens`. Mitigation: check the model's response only, not the entire conversation. The prompt is sent **as the user message**, the response is what `claude_agent_sdk.query()` yields. Should be clean — but **verify with a manual run** before committing.

### Verification

#### Phase D1 — Direct manual run of the new check function

Save a small Python script that imports the new check and runs it standalone:

```bash
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'scripts')
from doctor import check_total_tokens_injection
result = check_total_tokens_injection()
print(f'name: {result.name}')
print(f'ok: {result.ok}')
print(f'message: {result.message}')
"
```

**Expected**:
- `ok: True`
- `message` contains "NOT active" (because we know from earlier probe that injection is not active on this account)
- Runtime: <30 seconds

If `ok: False` — either injection became active (rare but possible) or the probe text triggered a false positive. Investigate.

#### Phase D2 — `doctor --full` integration

```bash
uv run python scripts/wiki_cli.py doctor --full 2>&1 | tail -30
```

**Expected**:
- New line `[PASS] total_tokens_injection: NOT active — model does not see <total_tokens> in its input context`
- All previously-PASS checks remain PASS
- Pre-existing FAILs (e.g., wiki content debt) remain in their state, not affected

#### Phase D3 — `doctor --quick` should NOT include the new check

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep total_tokens
```

**Expected**: zero matches (check is full-only).

#### Phase D4 — Failure mode test (simulate API failure)

Hard to test cleanly without breaking auth. Skip for this task. Document that this branch is untested but reviewed.

### Acceptance for Subtask D

- ✅ Doc verification confirms `claude_agent_sdk.query()` signature still matches plan
- ✅ `scripts/doctor.py` has new function `check_total_tokens_injection`
- ✅ Function registered in `--full` checks list, NOT in `--quick`
- ✅ Phase D1: standalone run returns `ok: True` with "NOT active" message
- ✅ Phase D2: `doctor --full` shows new PASS line
- ✅ Phase D3: `doctor --quick` does not show the new line
- ✅ No regression in other doctor checks

---

## Files to modify (whitelist — explicit)

- **Subtask A**: `gh` CLI only, plus temp body files in `<repo-root>/tmp/` (gitignored, not committed)
- **Subtask B**: `gh` CLI only, plus temp body files in `<repo-root>/tmp/`
- **Subtask C**: `gh` CLI only
- **Subtask D**: `scripts/doctor.py` only

**No other files**. Specifically NOT touching:
- `hooks/` directory (any file)
- `scripts/flush.py`
- `scripts/utils.py`
- `scripts/lint.py`
- `wiki/` content
- `.gitignore`
- `docs/codex-tasks/` (existing files)
- `pyproject.toml` / `uv.lock`
- Any Claude Code or Codex hook configs

---

## Out of scope

- Fixing the wiki content debt itself (just file the new issue, don't fix orphans/backlinks)
- Refactoring `doctor.py` metric semantics (just file the new issue, don't implement the split)
- Reopening any other closed issues (#8 stays closed, #10 stays closed)
- Modifying PR #18, #19, #20 in any way
- Reverting any merged code
- Adding new test files / smoke harnesses outside of the new doctor check

---

## Rollback

For Subtask D (only file change):

```bash
git checkout scripts/doctor.py
```

For Subtasks A, B, C — these are GitHub state changes (issue reopen, comments, labels, new issues). Rollback would require:
- `gh issue close N` for reopened issues
- `gh issue comment N --edit` (if supported, see Doc verification) to remove corrigendum
- `gh issue close <new-issue>` for created child issues

But normally these don't need rollback — corrections are pure additions to history.

---

## Pending user actions

After Codex completes:
1. Review the four sub-tasks
2. Decide whether to merge Subtask D as a PR (Codex prepares the diff, user reviews and decides)
3. Verify the new issues are correctly framed
4. Confirm corrigendum comment language is acceptable

---

## Notes для исполнителя (Codex)

- **Это reparation task**, не новый feature. Тон комментариев на GitHub должен быть
  **honest about past mistakes** (Claude нарушил разделение ролей, закрыл два issue
  formally неправильно), а не defensive. User это ценит больше чем сглаживание.
- **Subtask D — единственный с code change**. A, B, C — pure GitHub housekeeping.
  Если Subtask D окажется сложнее ожидаемого (например, претензии к sigvar
  asyncio.run внутри doctor.py) — стоп, эскалация, не workaround.
- **Doc verification обязателен** — особенно для `claude_agent_sdk` API surface.
  Если сигнатура `query()` или `ClaudeAgentOptions` изменилась с момента написания
  плана — план неверен, нужна корректировка.
- **NO commit / push** for Subtask D. Just leave the diff for user review. User
  decides whether to merge.
- **GitHub actions** (Subtasks A, B, C) **immediately effect production** — these
  are issue-state changes visible to anyone watching the repo. Be careful about
  formatting/wording. If anything in the comment templates above feels wrong,
  stop and ask before posting.
- **Use `${USER}` and placeholder paths** in any new files you write under
  `docs/codex-tasks/` (the report template). See `feedback_codex_task_handoff_workflow`
  memory section "Placeholder convention" for the rules.
- Создай отчёт в `docs/codex-tasks/post-review-corrections-and-probe-2-report.md`
  следуя стандартной структуре (Pre-flight, Doc verification, Subtask A-D phases,
  Tools used, Discrepancies, Self-audit).
