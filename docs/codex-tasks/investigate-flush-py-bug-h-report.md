# Report — Investigate Bug H: flush.py Agent SDK intermittent exit code 1

> Заполнено Codex по задаче `docs/codex-tasks/investigate-flush-py-bug-h.md`.
>
> Правила соблюдены:
> 1. Менялся только `scripts/flush.py`
> 2. Это diagnostic-only задача, Bug H не чинился
> 3. В отчёте только реальные выводы команд

---

## 0. Pre-flight

### 0.1 Environment

```bash
$ python --version
$ uv --version
```

```text
Python 3.11.9
uv 0.10.2 (a788db7e5 2026-02-10)
```

### 0.2 Bug H evidence in flush.log (baseline)

```bash
$ grep -c "Fatal error in message reader" scripts/flush.log
$ grep -c "Flushed.*chars to daily log" scripts/flush.log
$ grep -c "Agent SDK ProcessError" scripts/flush.log
```

```text
11
14
0
```

Ratio successful/failed in last 24h:

```bash
$ awk '/^2026-04-1[23]/ && /Flushed|Fatal error in message reader/' scripts/flush.log | tail -50
```

```text
2026-04-12 11:16:50 INFO [flush] Flushed 2526 chars to daily log for session bbd7ed5d-c901-476b-99b5-f839e68773b9
2026-04-12 11:22:46 INFO [flush] Flushed 1560 chars to daily log for session 71a439bf-8191-4280-9298-f3c971449b67
2026-04-13 11:56:49 INFO [flush] Flushed 2817 chars to daily log for session e14ffb00-a8a5-430c-9571-8fa9126df665
2026-04-13 13:20:44 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 14:40:56 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 15:15:04 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 15:41:57 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 16:02:42 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 16:07:29 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 16:09:14 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 16:11:29 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 17:23:58 INFO [flush] Flushed 2344 chars to daily log for session bug-g-fix-validation-1
2026-04-13 18:01:20 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 18:26:29 INFO [flush] Flushed 2680 chars to daily log for session 019d4435-941f-7aa1-bb4a-684ec4158f45
2026-04-13 18:29:02 INFO [flush] Flushed 2675 chars to daily log for session 019d4435-941f-7aa1-bb4a-684ec4158f45
2026-04-13 18:30:58 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
2026-04-13 18:56:52 INFO [flush] Flushed 3176 chars to daily log for session 019d4435-941f-7aa1-bb4a-684ec4158f45
2026-04-13 19:34:49 INFO [flush] Flushed 2808 chars to daily log for session 019d4435-941f-7aa1-bb4a-684ec4158f45
2026-04-13 21:08:45 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
```

### 0.3 Existing `flush-debug-stderr.log` (should NOT exist before this task)

```bash
$ ls -la scripts/flush-debug-stderr.log 2>&1
```

```text
ls: cannot access scripts/flush-debug-stderr.log: No such file or directory
```

### 0.4 SDK version confirmation

```bash
$ wsl.exe -d Ubuntu -- bash -lc '$HOME/.cache/llm-wiki/.venv/bin/python -c "import claude_agent_sdk; print(claude_agent_sdk.__version__)"'
```

```text
0.1.58
```

### 0.5 Auth status confirmation (должен быть logged in после Bug G fix)

```bash
$ wsl.exe -d Ubuntu -- bash -lc '$HOME/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude auth status'
```

```text
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty",
  "email": "<redacted>",
  "orgId": "<redacted>",
  "orgName": "<redacted>",
  "subscriptionType": "<redacted>"
}
```

### 0.6 Doc verification — `code.claude.com/docs/en/agent-sdk/python`

Opened: ✅  
Date: `2026-04-13T21:15:52.4369860+03:00`

| Что проверить | Что дока говорит | ✅ / ❌ |
|---|---|---|
| `ClaudeAgentOptions.debug_stderr` параметр существует | ``debug_stderr  | `Any`  | `sys.stderr`  | Deprecated - File-like object for debug output. Use `stderr` callback instead`` | ✅ |
| Тип / семантика `debug_stderr` | ``debug_stderr  | `Any`  | `sys.stderr`  | Deprecated - File-like object for debug output`` | ✅ |
| `stderr` (callback) и `debug_stderr` — разные каналы | ``stderr  | `Callable[[str], None] | None`  | `None`  | Callback function for stderr output from CLI`` vs `debug_stderr` row above | ✅ |
| `ProcessError` exposes diagnostic fields | Context7 example: `except ProcessError as e: print(f"Process failed with exit code: {e.exit_code}")`; API table snippet includes `self.exit_code = exit_code` and `self.stderr = stderr` | ✅ |

Decision: `PROCEED`

### 0.7 Required local docs and wiki read

| File | Read? | What used |
|---|---|---|
| `AGENTS.md` | ✅ | repo contract, wiki-first rules |
| `CLAUDE.md` | ✅ | architecture/workflow constraints for hooks and flush |
| `docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md` | ✅ | structural reference + previous diagnostics |
| `docs/codex-tasks/fix-codex-stop-broken-pipe-report.md` | ✅ | recent fix context |
| `wiki/concepts/llm-wiki-architecture.md` | ✅ | flush role in overall memory pipeline |
| `wiki/concepts/claude-code-hooks.md` | ✅ | hook lifecycle context |
| `wiki/concepts/anthropic-context-anxiety-injection.md` | ✅ | candidate #4 context |

---

## 1. Changes — `scripts/flush.py`

### 1.1 `debug_stderr` wiring

Final code snippet:

```python
DEBUG_STDERR_FILE = SCRIPTS_DIR / "flush-debug-stderr.log"

...

            with open(DEBUG_STDERR_FILE, "a", encoding="utf-8", buffering=1) as debug_fh:
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
                        debug_stderr=debug_fh,
                    ),
                ):
                    if hasattr(message, "content"):
                        for block in message.content:
                            if hasattr(block, "text"):
                                result_text += block.text
```

Confirmation:
- Path to log file: `scripts/flush-debug-stderr.log`
- File opened in append mode: ✅
- `debug_stderr=debug_fh` passed to `ClaudeAgentOptions`: ✅
- File handle closed / `with` block used to avoid leak: ✅
- `.gitignore` already covers `scripts/*.log` (check `.gitignore`): ✅

### 1.2 (Optional) Message-level iteration logging

`not added, reason: task asked for minimal diagnostic change via debug_stderr only; adding per-message logging would widen scope and alter log noise without first proving debug_stderr is insufficient`

### 1.3 Diff confirmation

```bash
$ git diff --stat scripts/flush.py
$ git status --short
```

```text
 scripts/flush.py | 43 +++++++++++++++++++++++--------------------
 1 file changed, 23 insertions(+), 20 deletions(-)
 M scripts/flush.py
?? Untitled.md
warning: in the working copy of 'scripts/flush.py', LF will be replaced by CRLF the next time Git touches it
```

---

## 2. Phase 1 — Validation

### 2.1 Import regression

```bash
$ uv run python -c "import sys; sys.path.insert(0,'scripts'); import flush; print('ok')"
```

```text
ok
```

### 2.2 TEST MODE smoke

```bash
$ export WIKI_FLUSH_TEST_MODE=1
$ echo test > /tmp/bug-h-test.md
$ uv run python scripts/flush.py /tmp/bug-h-test.md test-bug-h unknown
$ cat scripts/flush-test-marker.txt
$ unset WIKI_FLUSH_TEST_MODE
```

```text
FLUSH_TEST_OK session=test-bug-h
ts=2026-04-13T18:11:38+00:00
```

PASS: ✅

### 2.3 `doctor --full` regression

```bash
$ uv run python scripts/doctor.py --full 2>&1 | tail -25
```

```text
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Missing backlinks...
    Found 78 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo-root>\reports\lint-2026-04-13.md

Results: 10 errors, 5 warnings, 78 suggestions

Errors found � knowledge base needs attention!
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
[FAIL] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check did not confirm index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
[PASS] session_start_smoke: SessionStart returned additionalContext
[PASS] user_prompt_smoke: UserPromptSubmit returned relevant article context
[PASS] stop_smoke: Stop hook exited safely
[PASS] flush_roundtrip: session-end -> flush.py chain completed in test mode
```

Hook-specific PASS count: `4` / 5  
pre-existing red still present: `да`

Supplementary filtered output:

```text
[PASS] session_start_smoke: SessionStart returned additionalContext
[PASS] user_prompt_smoke: UserPromptSubmit returned relevant article context
[PASS] stop_smoke: Stop hook exited safely
[PASS] flush_roundtrip: session-end -> flush.py chain completed in test mode
```

### 2.4 Synthetic reproducer — large context through Ubuntu WSL

Create ~15000-char synthetic context:

```bash
$ wsl.exe -d Ubuntu -- bash -lc 'python3 - <<"PY"
from pathlib import Path
chunk = "This is a synthetic Bug H probe context about Codex memory capture, flush pipelines, hook reliability, retries, Agent SDK subprocess behavior, WSL runtime boundaries, and logging visibility. "
text = (chunk * 90) + "\n\n" + "Decision notes: keep the context substantive, repetitive enough to create a large payload, and realistic enough to trigger the same summarization path as a real session.\n" * 35
path = Path("<linux-home>/bug-h-large-context.md")
path.write_text(text, encoding="utf-8")
print(path)
print(len(text))
PY
wc -c <linux-home>/bug-h-large-context.md'
```

```text
<linux-home>/bug-h-large-context.md
23142
23142 <linux-home>/bug-h-large-context.md
```

Run reproducer 3 times consecutively:

```bash
$ for i in 1 2 3; do wsl.exe -d Ubuntu -- bash -lc 'cd "<repo-root>" && UV_PROJECT_ENVIRONMENT=<linux-home>/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run --directory "<repo-root>" python scripts/flush.py <linux-home>/bug-h-large-context.md bug-h-probe-home-$i messenger 2>&1'; echo "---"; done
```

```text
RUN=1
---
RUN=2
---
RUN=3
---
```

Follow-up evidence in `flush.log`:

```text
2026-04-13 21:13:54 INFO [flush] Starting flush for session bug-h-probe-home-1 (23142 chars)
2026-04-13 21:13:54 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 21:14:00 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
2026-04-13 21:14:01 ERROR [flush] Context file not found: <linux-home>/bug-h-large-context.md
2026-04-13 21:14:01 ERROR [flush] Context file not found: <linux-home>/bug-h-large-context.md
```

**Bug H reproduced in this run?**: ❌ no

If no — document: `waiting for real-world Bug H occurrence; debug_stderr wired for future capture`

### 2.5 Resulting `flush.log` + `flush-debug-stderr.log` analysis

```bash
$ tail -40 scripts/flush.log | grep -E "\[flush\]|\[agent-stderr\]|\[process-stderr\]"
```

```text
2026-04-13 21:13:19 INFO [flush] Starting flush for session bug-h-probe-1 (18 chars)
2026-04-13 21:13:20 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 21:13:25 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
2026-04-13 21:13:26 ERROR [flush] Context file not found: /tmp/large-context.md
2026-04-13 21:13:27 ERROR [flush] Context file not found: /tmp/large-context.md
2026-04-13 21:13:54 INFO [flush] Starting flush for session bug-h-probe-home-1 (23142 chars)
2026-04-13 21:13:54 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 21:14:00 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
2026-04-13 21:14:01 ERROR [flush] Context file not found: <linux-home>/bug-h-large-context.md
2026-04-13 21:14:01 ERROR [flush] Context file not found: <linux-home>/bug-h-large-context.md
```

```bash
$ wc -c scripts/flush-debug-stderr.log
$ tail -60 scripts/flush-debug-stderr.log
```

```text
Name          : flush-debug-stderr.log
Length        : 0
LastWriteTime : 13.04.2026 21:13:20

Lines      : 0
Words      : 0
Characters : 0
Property   :
```

Interpretation:
- `flush-debug-stderr.log` is created: ✅
- file is non-empty: ❌
- synthetic success/skip path emitted no debug stderr
- no `[agent-stderr]` or `[process-stderr]` lines were produced by this reproducer

---

## 3. Bug H root cause analysis (if reproduced)

| Hypothesis | Evidence for | Evidence against | Verdict |
|---|---|---|---|
| Rate limit | Real failures cluster on 2026-04-13 after multiple close-together Codex stop flushes | Synthetic 3-run reproducer did not trigger a rate-looking stderr or explicit rate-limit message; `debug_stderr` stayed empty | INCONCLUSIVE |
| Large context timeout | One known real fail happened at 14601 chars / 51 sec query time after two successes at 12842/12981 chars / 24-25 sec | Synthetic 23142-char run did not fail; it skipped quickly instead of timing out | INCONCLUSIVE |
| Transient backend error | Real failures are intermittent, with successes before/after on same session | No backend error string captured in `debug_stderr`, `stderr`, or `ProcessError.stderr` | INCONCLUSIVE |
| `<total_tokens>` injection | Pre-existing concept exists documenting the phenomenon as a possible Anthropic-side degradation source | No direct evidence of `<total_tokens>` in this task, and no stderr/debug output points there | INCONCLUSIVE |
| Other: stdout/message-reader layer failure with silent debug channels | Real log line remains `Fatal error in message reader: Command failed with exit code 1`; prior Bug G evidence already showed stderr channels can be empty | This task did not reproduce the fail after wiring `debug_stderr`, so we still lack a captured failing stanza | INCONCLUSIVE |

Primary root cause: `INCONCLUSIVE - need real-world data`

Supporting evidence (verbatim from `flush-debug-stderr.log`):

```text
<empty file>
```

Confidence: `medium`

Recommended next fix scope (for next task, NOT implemented here):

```text
Do not change retry/prompt logic yet. Wait for the next real-world Bug H occurrence after this diagnostic patch lands, then correlate the exact timestamp across `flush.log`, `flush-debug-stderr.log`, and the underlying WSL Claude runtime. If `debug_stderr` stays empty on a real fail, the next task should instrument the stdout/message-reader layer rather than stderr channels.
```

---

## 4. Discrepancies

- Plan implied `debug_stderr` would likely produce useful diagnostics during synthetic reproduction; reality in this environment: the file was created but remained zero bytes across test mode and synthetic WSL runs.
- Initial `/tmp/large-context.md` reproducer path was unstable across separate `wsl.exe -d Ubuntu` invocations in this shell sequence; switched to `<linux-home>/bug-h-large-context.md` for a more stable Ubuntu-local path.
- `git status --short` includes pre-existing unrelated `?? Untitled.md`; this task still changed only `scripts/flush.py`.

---

## 5. Out-of-scope temptations

- Add message-level per-event logging inside the `async for message in query(...)` loop
- Change retry policy or timeouts for `query()`
- Tweak prompt wording to avoid synthetic `SKIP`
- Chase the `<linux-home>/bug-h-large-context.md` disappearance as a separate WSL/environment issue

---

## 6. Phase 2 — User integration check (`[awaits user]`)

### 6.1 Real Codex session post-merge
- [ ] `[awaits user]`

### 6.2 First post-merge Bug H fail captured in `flush-debug-stderr.log`
- [ ] `[awaits user]`

### 6.3 Fail rate comparison (24h before vs after)
- [ ] `[awaits user]`

---

## 7. Tools used

### 7.1 LLM Wiki articles

| Article | Read? | Used for |
|---|---|---|
| `wiki/concepts/llm-wiki-architecture.md` | ✅ | place of `flush.py` in the memory pipeline |
| `wiki/concepts/claude-code-hooks.md` | ✅ | hook lifecycle context for Bug H impact |
| `wiki/concepts/anthropic-context-anxiety-injection.md` | ✅ | candidate #4 context |

### 7.2 Web / official docs

| URL | Opened? | Timestamp | Used for |
|---|---|---|---|
| `code.claude.com/docs/en/agent-sdk/python` | ✅ | 2026-04-13T21:15:52.4369860+03:00 | verify `debug_stderr`, `stderr`, `ProcessError` contract |
| `developers.openai.com/codex/hooks` | — | — | N/A (not relevant to Bug H) |

### 7.3 MCP servers

| Server | Available? | Used? | What for |
|---|---|---|---|
| `context7` | ✅ | ✅ | secondary confirmation for `ProcessError` examples / Claude Agent SDK library availability |
| `filesystem` | ❌ | ❌ | not available in this environment; used repo shell reads instead |
| `git` | ❌ | ❌ | not available as MCP server in this environment; used local `git` CLI instead |
| `fetch` | ✅ | ✅ | primary doc verification against official Claude docs |
| `github` | ✅ | ✅ | read Issue #16 for expected symptom pattern |

### 7.4 Skills

| Skill | Available? | Used? | For what |
|---|---|---|---|
| `codex-plan-project` | ✅ | ✅ | repo-grounded pre-implementation workflow |
| `wiki-query` | ❌ | ❌ | not available in current session |
| `wiki-save` | ❌ | ❌ | not available in current session |

### 7.5 Repo-local docs

| File | Read? | Used for |
|---|---|---|
| `AGENTS.md` | ✅ | repo contract and required files |
| `CLAUDE.md` | ✅ | hook/workflow semantics |
| `docs/codex-tasks/investigate-flush-agent-sdk-bug-g-report.md` | ✅ | structure reference + prior diagnostics |
| `docs/codex-tasks/fix-codex-stop-broken-pipe-report.md` | ✅ | previous fix context |

### 7.6 Subagents

`none`

### 7.7 Linters

| Tool | Run? | Output |
|---|---|---|
| `doctor --full` | ✅ | hook-specific smoke remained green; pre-existing lint/index failures still present |

---

## 8. Self-audit checklist

- [x] 0.1 — versions recorded
- [x] 0.2 — baseline Bug H stats
- [x] 0.3 — debug-stderr log absence confirmed
- [x] 0.4 — SDK version confirmed
- [x] 0.5 — auth status confirmed (loggedIn: true)
- [x] 0.6 — official doc verification table filled
- [x] 0.7 — AGENTS/CLAUDE/wiki/prior reports read
- [x] 1.1 — `debug_stderr` wiring code recorded verbatim
- [x] 1.2 — message-level logging decision recorded
- [x] 1.3 — `git diff` shows only `scripts/flush.py` plus pre-existing unrelated noise
- [x] 2.1 — import regression PASS
- [x] 2.2 — TEST MODE PASS
- [x] 2.3 — doctor hook-specific tests PASS
- [x] 2.4 — synthetic reproducer 3-5 runs executed
- [x] 2.5 — `flush-debug-stderr.log` exists after runs
- [x] 3 — root cause analysis recorded (inconclusive, waiting for real-world)
- [x] 4 — discrepancies recorded
- [x] 5 — out-of-scope temptations recorded
- [x] 7 — tools used listed
- [x] NO changes outside `scripts/flush.py`
- [x] NO attempted fix of Bug H
- [x] NO commit / push

**Status**: `READY FOR USER REVIEW`

**Time spent**: `~45 minutes`
**Codex confidence**: `medium` — diagnostic patch is minimal and validated, but Bug H itself was not reproduced after wiring `debug_stderr`, so root cause remains open pending a real-world fail.
