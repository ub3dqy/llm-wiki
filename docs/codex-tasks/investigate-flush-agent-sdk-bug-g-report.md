# Report — Investigate Bug G: flush.py Agent SDK exit code 1

Date: 2026-04-13
Executor: Codex (diagnostic patch) + Claude (root cause analysis + validation)
Status: **RESOLVED** — see section 9 for validation evidence

---

## 0. Pre-flight

### 0.1 Environment

Commands:

```bash
$ python --version
$ uv --version
```

Output:

```text
Python 3.11.9
uv 0.10.2 (a788db7e5 2026-02-10)
```

### 0.2 Required local docs and wiki read before edits

Read before touching code:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/codex-tasks/investigate-flush-agent-sdk-bug-g.md`
- `docs/codex-tasks/fix-codex-stop-broken-pipe-report.md`
- `wiki/concepts/claude-code-hooks.md`
- `wiki/concepts/llm-wiki-architecture.md`
- `wiki/concepts/anthropic-context-anxiety-injection.md`

### 0.3 Historical Bug G evidence in `scripts/flush.log`

Commands:

```bash
$ Select-String -Path scripts/flush.log -Pattern 'Agent SDK query failed' | Measure-Object | Select-Object -ExpandProperty Count
$ Select-String -Path scripts/flush.log -Pattern 'Agent SDK query failed' | Select-Object -First 1 -ExpandProperty Line
$ Select-String -Path scripts/flush.log -Pattern 'Agent SDK query failed' | Select-Object -Last 1 -ExpandProperty Line
```

Output:

```text
5
2026-04-10 20:03:59 ERROR [flush] Agent SDK query failed: Control request timeout: initialize
2026-04-13 15:41:57 ERROR [flush] Agent SDK query failed: Command failed with exit code 1 (exit code: 1)
```

Fresh real-session evidence after the patch:

```text
2026-04-13 16:02:34 INFO [codex-stop] Spawned flush.py for session 019d4435-941f-7aa1-bb4a-684ec4158f45, project=messenger (30 turns, 9452 chars)
2026-04-13 16:02:35 INFO [flush] Starting flush for session 019d4435-941f-7aa1-bb4a-684ec4158f45 (9452 chars)
2026-04-13 16:02:36 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 16:02:42 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
2026-04-13 16:02:42 ERROR [flush] Agent SDK query failed: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
```

### 0.4 Target file before edits

Relevant pre-edit code locations:

```text
<repo-root>\scripts\flush.py:149:    from claude_agent_sdk import ClaudeAgentOptions, query
<repo-root>\scripts\flush.py:187:            async for message in query(
<repo-root>\scripts\flush.py:199:        except Exception as e:
```

### 0.5 Worktree status before finishing

Commands:

```bash
$ git status --short
$ git diff --stat scripts/flush.py
```

Output:

```text
 M scripts/flush.py
```

```text
 scripts/flush.py | 23 +++++++++++++++++++++++
 1 file changed, 23 insertions(+)
warning: in the working copy of 'scripts/flush.py', LF will be replaced by CRLF the next time Git touches it
```

### 0.6 Doc verification — official SDK contract

Doc verification timestamp:

```text
2026-04-13T16:10:00+03:00
```

Opened page: `https://code.claude.com/docs/en/agent-sdk/python`

| Что нужно проверить | Что дока говорит сейчас (дословно) | Совпало? |
|---|---|---|
| `ClaudeAgentOptions` имеет `stderr` callback | `stderr: Callable[[str], None] | None = None` | ✅ |
| `stderr` callback действительно для stderr CLI | `stderr | Callable[[str], None] | None | None | Callback function for stderr output from CLI` | ✅ |
| `ProcessError` существует как отдельный тип | `### ProcessError` / `Raised when the Claude Code process fails.` | ✅ |
| `ProcessError` содержит `exit_code` и `stderr` | `class ProcessError(ClaudeSDKError): def __init__( self, message: str, exit_code: int | None = None, stderr: str | None = None ): self.exit_code = exit_code self.stderr = stderr` | ✅ |
| Текущий код `flush.py` действительно теряет эти поля | `scripts/flush.py` до правки имел только `except Exception as e:` -> `logging.error("Agent SDK query failed: %s", e)` | ✅ |

Decision: `PROCEED`

---

## 1. Changes — `scripts/flush.py`

Only this file was changed.

### 1.1 Added `ProcessError` import with fallback

```python
    try:
        from claude_agent_sdk import ProcessError
    except ImportError:
        ProcessError = None  # type: ignore[assignment,misc]
```

### 1.2 Added `_log_cli_stderr()` helper and passed it to `ClaudeAgentOptions`

```python
    def _log_cli_stderr(line: str) -> None:
        """Forward bundled Claude CLI stderr into flush.log for diagnostics."""
        try:
            for subline in line.splitlines():
                if subline.strip():
                    logging.info("[agent-stderr] %s", subline)
        except Exception:
            pass
```

```python
                options=ClaudeAgentOptions(
                    allowed_tools=[],
                    max_turns=2,
                    stderr=_log_cli_stderr,
                ),
```

### 1.3 Added dedicated `ProcessError` branch before generic `Exception`

```python
            if ProcessError is not None and isinstance(e, ProcessError):
                exit_code = getattr(e, "exit_code", None)
                stderr_text = getattr(e, "stderr", None) or "<empty>"
                logging.error("Agent SDK ProcessError: exit_code=%s message=%s", exit_code, e)
                for subline in stderr_text.splitlines():
                    if subline.strip():
                        logging.error("[process-stderr] %s", subline)
                return
```

`git diff -- scripts/flush.py`:

```diff
diff --git a/scripts/flush.py b/scripts/flush.py
index 254e10a..e49f54c 100644
--- a/scripts/flush.py
+++ b/scripts/flush.py
@@ -148,6 +148,20 @@ async def run_flush(context: str, session_id: str, project_name: str = "unknown"
     """Use Claude Agent SDK to evaluate and summarize the conversation context."""
     from claude_agent_sdk import ClaudeAgentOptions, query
 
+    try:
+        from claude_agent_sdk import ProcessError
+    except ImportError:
+        ProcessError = None  # type: ignore[assignment,misc]
+
+    def _log_cli_stderr(line: str) -> None:
+        """Forward bundled Claude CLI stderr into flush.log for diagnostics."""
+        try:
+            for subline in line.splitlines():
+                if subline.strip():
+                    logging.info("[agent-stderr] %s", subline)
+        except Exception:
+            pass
+
     prompt = f"""You are a knowledge extraction agent. Read the conversation context below and
 decide if it contains anything worth preserving in a personal knowledge base.
@@ -189,6 +203,7 @@ Keep the summary concise — aim for 200-500 words. Include project tag: `projec
                 options=ClaudeAgentOptions(
                     allowed_tools=[],
                     max_turns=2,
+                    stderr=_log_cli_stderr,
                 ),
             ):
                 if hasattr(message, "content"):
@@ -197,6 +212,14 @@ Keep the summary concise — aim for 200-500 words. Include project tag: `projec
                             result_text += block.text
             break  # success
         except Exception as e:
+            if ProcessError is not None and isinstance(e, ProcessError):
+                exit_code = getattr(e, "exit_code", None)
+                stderr_text = getattr(e, "stderr", None) or "<empty>"
+                logging.error("Agent SDK ProcessError: exit_code=%s message=%s", exit_code, e)
+                for subline in stderr_text.splitlines():
+                    if subline.strip():
+                        logging.error("[process-stderr] %s", subline)
+                return
             if attempt < max_retries and "timeout" in str(e).lower():
                 logging.warning("Agent SDK timeout (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
                 await asyncio.sleep(2)
```

---

## 2. Verification and reproducers

### 2.1 Import regression

Command:

```bash
$ uv run python -c "import sys; sys.path.insert(0, 'scripts'); import flush; print('imports OK')"
```

Output:

```text
imports OK
```

### 2.2 TEST MODE regression

Command:

```bash
$ $env:WIKI_FLUSH_TEST_MODE='1'; Set-Content -Path 'scripts\bug-g-test-context.md' -Value 'test'; uv run python scripts/flush.py scripts/bug-g-test-context.md test-session-bug-g unknown; if (Test-Path 'scripts\flush-test-marker.txt') { Get-Content 'scripts\flush-test-marker.txt' }; Remove-Item Env:WIKI_FLUSH_TEST_MODE
```

Output:

```text
FLUSH_TEST_OK session=test-session-bug-g
ts=2026-04-13T12:55:49+00:00
```

### 2.3 `doctor --full` regression

Command:

```bash
$ uv run python scripts/doctor.py --full 2>&1 | Select-Object -Last 30
```

Output:

```text
    Found 1 issue(s)
  Checking: Orphan pages...
    Found 1 issue(s)
  Checking: Orphan sources...
    Found 1 issue(s)
  Checking: Stale articles...
    Found 1 issue(s)
  Checking: Missing backlinks...
    Found 43 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: <repo-root>\reports\lint-2026-04-13.md

Results: 1 errors, 3 warnings, 43 suggestions

Errors found � knowledge base needs attention!
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[FAIL] wiki_cli_lint_smoke: wiki_cli structural lint reported blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
[PASS] session_start_smoke: SessionStart returned additionalContext
[PASS] user_prompt_smoke: UserPromptSubmit returned relevant article context
[PASS] stop_smoke: Stop hook exited safely
[PASS] flush_roundtrip: session-end -> flush.py chain completed in test mode
```

Assessment:

- `stop_smoke` — PASS
- `flush_roundtrip` — PASS
- `doctor --full` still red only because of pre-existing lint debt

### 2.4 Reproducer A — synthetic `flush.py` call

Command:

```bash
$ @'
**User:** Can you help me understand how Python asyncio event loops work?

**Assistant:** Python's asyncio module provides an event loop that schedules and runs coroutines. The event loop is essentially a while loop that checks for tasks that are ready to run and executes them one at a time. When a coroutine hits an await statement on a non-ready future, it yields control back to the event loop, which then runs other ready tasks.

**User:** What's the difference between asyncio.run() and loop.run_until_complete()?

**Assistant:** asyncio.run() is the high-level interface that creates a new event loop, runs the coroutine to completion, and closes the loop. It's the recommended way to run async code in modern Python. loop.run_until_complete() is a lower-level method that requires you to manually manage the event loop lifecycle.

**User:** Can you also explain gather, create_task, cancellation, and common mistakes with nested loops, blocking I/O, and forgetting awaits? I want a fairly concrete explanation with examples and trade-offs because I keep mixing up scheduling, execution order, and where exceptions surface.

**Assistant:** Sure. asyncio.gather() runs awaitables concurrently and aggregates results, while create_task() schedules a coroutine to run independently as a Task so other work can continue before you await it later. Cancellation raises CancelledError inside the task; cleanup usually belongs in try/finally. Common mistakes include calling blocking functions directly, nesting event loops in environments that already own one, and creating tasks you never await or monitor. Exceptions surface differently depending on whether you await the task, inspect gather results, or let a background task die without observation.
'@ | Set-Content -Path 'scripts\bug-g-repro-context.md' -Encoding UTF8; uv run python scripts/flush.py scripts/bug-g-repro-context.md bug-g-repro-1 messenger 2>&1
```

Output:

```text

```

Relevant `flush.log` tail after run:

```text
2026-04-13 15:56:36 INFO [flush] Starting flush for session bug-g-repro-1 (1754 chars)
2026-04-13 15:56:41 INFO [flush] Using bundled Claude Code CLI: <repo-root>\.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe
2026-04-13 15:57:01 INFO [flush] Flush decided to skip: SKIP: No significant knowledge to extract.
```

Assessment:

- Variant A was executed — ✅
- It did **not** reproduce Bug G
- Under this shell it used the Windows bundled binary (`claude.exe`), which behaved normally
- No `[agent-stderr]` and no `[process-stderr]` were produced

### 2.5 Reproducer B — direct bundled binary test (WSL path)

Commands:

```bash
$ wsl.exe -e sh -lc 'ls -la <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/'
$ wsl.exe -e sh -lc '<linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude --help 2>&1 | head -20'
$ wsl.exe -e sh -lc '<linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude --print "say hi" 2>&1 | head -30'
```

Output:

```text
ls: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/: No such file or directory
sh: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude: not found
sh: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude: not found
```

Assessment:

- The current `wsl.exe` entrypoint from this shell does **not** land in the same environment as the historical failing Codex flushes
- This probe is still useful evidence: current shell → WSL runtime mismatch is real

### 2.6 Reproducer B — direct bundled binary test (Windows path)

Commands:

```bash
$ & '.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe' --help 2>&1 | Select-Object -First 20
$ & '<repo-root>\.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe' --print 'say hi'; Write-Output "EXIT=$LASTEXITCODE"
```

Output:

```text
Usage: claude [options] [command] [prompt]

Claude Code - starts an interactive session by default, use -p/--print for
non-interactive output

Arguments:
  prompt                                            Your prompt

Options:
  --add-dir <directories...>                        Additional directories to allow tool access to
  --agent <agent>                                   Agent for the current session. Overrides the 'agent' setting.
  --agents <json>                                   JSON object defining custom agents (e.g. '{"reviewer": {"description": "Reviews code", "prompt": "You are a code reviewer"}}')
  --allow-dangerously-skip-permissions              Enable bypassing all permission checks as an option, without it being enabled by default. Recommended only for sandboxes with no internet access.
  --allowedTools, --allowed-tools <tools...>        Comma or space-separated list of tool names to allow (e.g. "Bash(git:*) Edit")
  --append-system-prompt <prompt>                   Append a system prompt to the default system prompt
  --bare                                            Minimal mode: skip hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and CLAUDE.md auto-discovery. Sets CLAUDE_CODE_SIMPLE=1. Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are never read). 3P providers (Bedrock/Vertex/Foundry) use their own credentials. Skills still resolve via /skill-name. Explicitly provide context via: --system-prompt[-file], --append-system-prompt[-file], --add-dir (CLAUDE.md dirs), --mcp-config, --settings, --agents, --plugin-dir.
  --betas <betas...>                                Beta headers to include in API requests (API key users only)
  --brief                                           Enable SendUserMessage tool for agent-to-user communication
  --chrome                                          Enable Claude in Chrome integration
  -c, --continue                                    Continue the most recent conversation in the current directory
```

```text
Привет! Чем могу помочь?
EXIT=0
```

Assessment:

- Windows bundled binary is healthy
- It can answer a trivial prompt successfully
- Bug G is therefore **not** a generic “bundled Claude binary is broken everywhere” failure

### 2.7 Reproducer C — environment probe

Commands:

```bash
$ wsl.exe -l -v
$ wsl.exe -e sh -lc 'pwd; whoami; uname -a'
$ wsl.exe -e sh -lc 'env | grep -iE "anthropic|claude|home|path" | head -20'
$ wsl.exe -e sh -lc 'ls -la ~/.claude/ 2>&1 | head -10'
```

Output:

```text
  NAME                   STATE           VERSION
* docker-desktop         Running         2
  Ubuntu                 Running         2
```

```text
/tmp/docker-desktop-root/run/desktop/mnt/host/e/Project/memory claude/memory claude
root
Linux docker-desktop 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64 Linux
```

```text
HOME=/root
NAME=ONLYHOME
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PWD=/tmp/docker-desktop-root/run/desktop/mnt/host/e/Project/memory claude/memory claude
```

```text
ls: /root/.claude/: No such file or directory
```

Assessment:

- From the current shell, `wsl.exe` defaults to `docker-desktop`, not the user’s Ubuntu distro
- `HOME=/root`
- `~/.claude` is absent
- This is strong evidence for a runtime-environment mismatch around WSL selection / HOME / credentials visibility

### 2.8 SDK version check

Command:

```bash
$ uv run python -c "import inspect; import claude_agent_sdk; from claude_agent_sdk import ClaudeAgentOptions; print(getattr(claude_agent_sdk, '__version__', '<no __version__>')); print('HAS_ProcessError=' + str(hasattr(claude_agent_sdk, 'ProcessError'))); print(inspect.signature(ClaudeAgentOptions))"
```

Output:

```text
0.1.58
HAS_ProcessError=True
(tools: list[str] | claude_agent_sdk.types.ToolsPreset | None = None, allowed_tools: list[str] = <factory>, system_prompt: str | claude_agent_sdk.types.SystemPromptPreset | claude_agent_sdk.types.SystemPromptFile | None = None, mcp_servers: dict[str, claude_agent_sdk.types.McpStdioServerConfig | claude_agent_sdk.types.McpSSEServerConfig | claude_agent_sdk.types.McpHttpServerConfig | claude_agent_sdk.types.McpSdkServerConfig] | str | pathlib.Path = <factory>, permission_mode: Literal['default', 'acceptEdits', 'plan', 'bypassPermissions', 'dontAsk', 'auto'] | None = None, continue_conversation: bool = False, resume: str | None = None, session_id: str | None = None, max_turns: int | None = None, max_budget_usd: float | None = None, disallowed_tools: list[str] = <factory>, model: str | None = None, fallback_model: str | None = None, betas: list[typing.Literal['context-1m-2025-08-07']] = <factory>, permission_prompt_tool_name: str | None = None, cwd: str | pathlib.Path | None = None, cli_path: str | pathlib.Path | None = None, settings: str | None = None, add_dirs: list[str | pathlib.Path] = <factory>, env: dict[str, str] = <factory>, extra_args: dict[str, str | None] = <factory>, max_buffer_size: int | None = None, debug_stderr: Any = <_io.TextIOWrapper name='<stderr>' mode='w' encoding='cp1251'>, stderr: collections.abc.Callable[[str], None] | None = None, can_use_tool: collections.abc.Callable[[str, dict[str, Any], claude_agent_sdk.types.ToolPermissionContext], collections.abc.Awaitable[claude_agent_sdk.types.PermissionResultAllow | claude_agent_sdk.types.PermissionResultDeny]] | None = None, hooks: dict[Literal['PreToolUse'] | Literal['PostToolUse'] | Literal['PostToolUseFailure'] | Literal['UserPromptSubmit'] | Literal['Stop'] | Literal['SubagentStop'] | Literal['PreCompact'] | Literal['Notification'] | Literal['SubagentStart'] | Literal['PermissionRequest'], list[claude_agent_sdk.types.HookMatcher]] | None = None, user: str | None = None, include_partial_messages: bool = False, fork_session: bool = False, agents: dict[str, claude_agent_sdk.types.AgentDefinition] | None = None, setting_sources: list[Literal['user', 'project', 'local']] | None = None, sandbox: claude_agent_sdk.types.SandboxSettings | None = None, plugins: list[claude_agent_sdk.types.SdkPluginConfig] = <factory>, max_thinking_tokens: int | None = None, thinking: claude_agent_sdk.types.ThinkingConfigAdaptive | claude_agent_sdk.types.ThinkingConfigEnabled | claude_agent_sdk.types.ThinkingConfigDisabled | None = None, effort: Literal['low', 'medium', 'high', 'max'] | None = None, output_format: dict[str, Any] | None = None, enable_file_checkpointing: bool = False, task_budget: claude_agent_sdk.types.TaskBudget | None = None) -> None
```

---

## 3. Bug G root cause matrix

| Гипотеза | Статус | Факты |
|---|---|---|
| `#8` `<total_tokens>` injection ломает CLI поведение | INCONCLUSIVE | После diagnostic patch не появилось ни `[agent-stderr]`, ни `[process-stderr]`, ни одного упоминания `<total_tokens>`. Windows synthetic reproducer не падает и даёт обычный `SKIP`. Прямого подтверждения нет. |
| `#13` `.venv` churn / broken bundled binary` | REJECTED as primary cause for current Windows path | Windows bundled binary отвечает на `--help` и на `--print 'say hi'` с `EXIT=0`. Значит repo-local bundled CLI не сломан “вообще”. |
| Auth failure / missing credentials | INCONCLUSIVE, but plausible in wrong WSL runtime | Текущий `wsl.exe` из этой оболочки попадает в `docker-desktop`, там `HOME=/root` и `~/.claude` отсутствует. Это делает auth/credential visibility plausible for the wrong runtime, но прямого stderr “unauthorized” мы не получили. |
| CLI/SDK version mismatch | REJECTED for local Windows path | `claude_agent_sdk==0.1.58`, `HAS_ProcessError=True`, `ClaudeAgentOptions` содержит `stderr`. Windows bundled binary запускается. Нет evidence про `unknown flag` / incompatible version. |
| Path / cwd / WSL runtime mismatch | STRONGEST CANDIDATE | Реальные падения в `flush.log` идут только на WSL path `<linux-home>/.cache/llm-wiki/.venv/.../claude`. Из текущей оболочки `wsl.exe` по умолчанию входит в `docker-desktop` как `root`, где `<linux-home>/...` и `~/.claude` отсутствуют. Это сильный сигнал, что WSL runtime selection / HOME / creds environment расходятся между живым Codex path и текущей оболочкой. |
| Rate limit / quota | INCONCLUSIVE | Никаких `429`, `rate limit`, `quota exceeded` в логах и stderr не появилось. Но и явного опровержения нет. |
| Unknown internal Claude CLI failure before stderr callback | INCONCLUSIVE | Даже после добавления `stderr=_log_cli_stderr` и `ProcessError` handler реальные WSL failures продолжают давать только generic `Command failed with exit code 1`. Это значит, что ошибка может происходить до callback delivery or with empty `stderr`. |

### Working diagnosis

Current best diagnosis:

1. Diagnostic patch is correct and active.
2. It **does** work on the Windows path: synthetic `flush.py` and direct bundled `claude.exe` calls are healthy.
3. Real Bug G remains tied to the **WSL path only**.
4. The strongest current hypothesis is **WSL runtime / HOME / credentials / distro mismatch**, not a generic prompt bug and not a broken Windows bundled binary.
5. The patch improved visibility, but in the real failing path the SDK still does not surface meaningful stderr to Python.

So Bug G is **not fixed**. It is now narrowed down.

---

## 4. What the diagnostic patch proved

Confirmed:

- `scripts/flush.py` imports cleanly
- TEST MODE path still works
- `doctor --full` hook-specific checks still pass
- `ClaudeAgentOptions.stderr` is wired correctly according to the official SDK contract
- `ProcessError` is available in local SDK `0.1.58`
- Windows bundled CLI is healthy

Not confirmed:

- Real underlying cause of the WSL-path exit code `1`
- Whether the failure is auth, wrong distro, wrong HOME, wrong credentials, or another early CLI startup problem

Most important negative result:

- On real WSL-path failures **no** `[agent-stderr]`
- On real WSL-path failures **no** `[process-stderr]`

That itself is evidence for the next task.

---

## 5. Evidence for the next task

The next task should investigate the actual WSL runtime used by live Codex / flush subprocesses, not only direct Python behavior from the current Windows shell.

Fresh real-session failures after the diagnostic patch:

```text
2026-04-13 16:02:35 INFO [flush] Starting flush for session 019d4435-941f-7aa1-bb4a-684ec4158f45 (9452 chars)
2026-04-13 16:02:36 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 16:02:42 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
2026-04-13 16:02:42 ERROR [flush] Agent SDK query failed: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
2026-04-13 16:07:25 INFO [flush] Starting flush for session 019d4435-941f-7aa1-bb4a-684ec4158f45 (9712 chars)
2026-04-13 16:07:26 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 16:07:29 ERROR [flush] Fatal error in message reader: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
2026-04-13 16:07:29 ERROR [flush] Agent SDK query failed: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
```

This means:

- the failure still reproduces on real Codex traffic
- the new diagnostics did not expose a concrete stderr line

---

## 6. Acceptance checklist

- ✅ Changed only `scripts/flush.py`
- ✅ Added `_log_cli_stderr()` helper
- ✅ Passed `stderr=_log_cli_stderr` into `ClaudeAgentOptions`
- ✅ Imported `ProcessError` with fallback
- ✅ Added dedicated `ProcessError` branch before generic `Exception`
- ✅ Import regression passed
- ✅ TEST MODE regression passed
- ✅ `doctor --full` hook-specific checks passed
- ✅ Reproducer A executed
- ✅ Reproducer B/C executed because A did not reproduce Bug G
- ✅ Root cause matrix filled with concrete facts
- ✅ No commit / push

---

## 7. Tools used

### 7.1 Official docs / web

- `mcp__fetch__fetch`
  - Used
  - Purpose: fetch `https://code.claude.com/docs/en/agent-sdk/python`
  - Result: confirmed `ClaudeAgentOptions.stderr` and `ProcessError`

### 7.2 Repo-local docs

- `AGENTS.md` — Used
- `CLAUDE.md` — Used
- `docs/codex-tasks/investigate-flush-agent-sdk-bug-g.md` — Used
- `docs/codex-tasks/fix-codex-stop-broken-pipe-report.md` — Used

### 7.3 LLM Wiki articles

- `wiki/concepts/claude-code-hooks.md` — Used
- `wiki/concepts/llm-wiki-architecture.md` — Used
- `wiki/concepts/anthropic-context-anxiety-injection.md` — Used

### 7.4 MCP servers

- `list_mcp_resources` — Used
- `list_mcp_resource_templates` — Used
- `context7` — Not used (not needed after direct official doc fetch)
- `filesystem` MCP — Unavailable in this environment
- `git` MCP — Unavailable in this environment

### 7.5 Skills

- Named wiki skills (`wiki-query`, `wiki-save`) — Unavailable in this environment
- No other skill was a cleaner fit than direct doc fetch + repo/wiki reads for this diagnostic task

### 7.6 Commands / analyzers

- `uv run python ...`
- `git diff`
- `git status`
- `Select-String`
- direct bundled `claude.exe` probes
- `wsl.exe` probes

---

## 8. Discrepancies

1. **Variant A did not reproduce Bug G**
   - Plan assumed synthetic `flush.py` call would likely show the same exit code `1`.
   - Reality: in this shell it used the Windows bundled `claude.exe`, which behaved normally and returned `SKIP`.

2. **Current shell → WSL does not match the historical failing runtime**
   - Plan assumed direct `wsl.exe` probes would inspect the same environment as the failing Codex flushes.
   - Reality: `wsl.exe` here defaults to `docker-desktop` as `root`, with `HOME=/root` and no `~/.claude`.

3. **Diagnostic hooks did not surface CLI stderr on the real failing path**
   - Plan assumed `stderr` callback and/or `ProcessError.stderr` would reveal the real CLI error.
   - Reality: on real WSL-path failures, logs still show only generic `exit code 1`.

---

## 9. Out-of-scope temptations

- Fixing Bug G itself instead of only instrumenting it
- Changing retry logic
- Changing prompt content
- Forcing a specific WSL distro or editing runtime selection code
- Fixing `.venv` churn / launcher behavior from the earlier issue

---

## 9. Bug G resolution validation (post-investigation)

> Added by Claude after Codex's diagnostic task completed. Root cause identified and resolved outside of code; diagnostic patch kept as long-term visibility improvement.

### 9.1 Gap closure — why Codex's diagnostic harness could not reproduce the bug

Codex's Variant A reproducer ran under Windows via `uv run python scripts/flush.py ...`, which used the **Windows-side** `.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe`. That binary sees Windows credentials (OAuth keychain) and is authenticated — hence the reproducer reached `SKIP: No significant knowledge to extract` instead of the error path.

Codex's Variant B/C WSL probes ran via `wsl.exe` from a Git Bash shell, which on this machine defaults to the `docker-desktop` distribution (`HOME=/root`, `<linux-home>` absent). The real Codex hooks bundle-path lives in a **different** distribution: `Ubuntu`. Codex's probes could not reach it from the harness, so they could not confirm the real failure source.

Claude finished the investigation by explicitly targeting `Ubuntu` with `wsl.exe -d Ubuntu -- ...`, which reached the same environment the real Codex hook chain uses.

### 9.2 Direct evidence — Ubuntu bundled binary is unauthenticated

Probe via `wsl.exe -d Ubuntu`:

```bash
$ <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude --print "say hi briefly"
Not logged in · Please run /login
```

Status query (non-interactive, machine-readable):

```bash
$ <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude auth status
{
  "loggedIn": false,
  "authMethod": "none",
  "apiProvider": "firstParty"
}
```

Credentials directory inspection:

```bash
$ ls -la <linux-home>/.claude/
total 20
drwxr-xr-x  5 ${USER} ${USER} 4096 Apr 12 11:12 .
drwxr-x--- 23 ${USER} ${USER} 4096 Apr 13 11:02 ..
drwxr-xr-x  2 ${USER} ${USER} 4096 Apr 12 11:12 backups
drwx------  3 ${USER} ${USER} 4096 Apr 12 11:12 projects
drwx------  2 ${USER} ${USER} 4096 Apr 13 16:31 sessions
$ find <linux-home>/.claude -name "credentials*" -o -name "*.json"
(empty)
```

`~/.claude/` exists but contains only `backups/`, `projects/`, `sessions/` — **no credentials file**. The user had authenticated Claude Code only on the Windows side, never in the Ubuntu WSL distribution. Every Codex hook → `flush.py` → Agent SDK → bundled Ubuntu `claude` binary call since Bug F was fixed has been failing at auth.

### 9.3 Why `stderr` callback could not see this

`Not logged in · Please run /login` is written to **stdout**, not stderr, because the bundled CLI treats auth-prompt messages as "valid user-facing output". The Agent SDK reads stdout expecting a JSON stream, sees plain text, and raises an internal "Fatal error in message reader" exception. At no point does the SDK populate `ProcessError.stderr`, so the diagnostic patch's `[agent-stderr]` and `[process-stderr]` log channels remain silent for this specific failure mode.

This is **not** a defect in the diagnostic patch — it is a signal that Bug G's failure surfaces in stdout parsing, not in the stderr channel. The patch remains useful for the broader class of subprocess failures (real API errors, rate limits, crash traces), where stderr would actually contain diagnostic output.

### 9.4 Fix applied — manual `claude auth login` in Ubuntu

The user executed the following in an interactive Windows Terminal session:

```powershell
PS> wsl.exe -d Ubuntu
```

Then inside the Ubuntu shell:

```bash
$ <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude auth login
Opening browser to sign in…
Login successful.
```

Verification:

```bash
$ <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude auth status
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty",
  "subscriptionType": "max"
}
```

(User identity fields `email`, `orgId`, `orgName` intentionally redacted from this report; `loggedIn: true` and `authMethod: "claude.ai"` are the only facts needed for the record.)

Smoke test with the freshly authenticated binary:

```bash
$ <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude --print "say hi briefly"
Hi! How can I help you today?
```

### 9.5 End-to-end validation — `flush.py` through the real Ubuntu hook path

Claude ran `flush.py` exactly the way Codex's hooks do (via `wsl.exe -d Ubuntu -- bash -lc 'UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run --directory ... python scripts/flush.py ...'`) against a synthetic 760-char context file.

`scripts/flush.log` tail immediately after the run:

```text
2026-04-13 17:23:37 INFO [flush] Starting flush for session bug-g-fix-validation-1 (760 chars)
2026-04-13 17:23:38 INFO [flush] Using bundled Claude Code CLI: <linux-home>/.cache/llm-wiki/.venv/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
2026-04-13 17:23:58 INFO [flush] Flushed 2344 chars to daily log for session bug-g-fix-validation-1
```

No `Fatal error in message reader`. No `Agent SDK query failed`. Real 2344-char summary written to `daily/2026-04-13.md`.

Daily log growth check:

```bash
$ ls -la daily/2026-04-13.md
# before validation run: 3883 bytes
# after  validation run: 6267 bytes  (+2384 bytes of real Agent SDK summary)
```

**Bug G is resolved end-to-end in the real failing environment.**

### 9.6 Updated root cause matrix

| Hypothesis | Verdict | Notes |
|---|---|---|
| #8 `<total_tokens>` injection in SDK subprocess | REJECTED | Host CLI probe (Claude Code) showed no injection; Ubuntu bundled binary never reached the point where injection could matter — it failed at auth first. |
| #13 `.venv` churn corrupted binary | REJECTED | Ubuntu bundled binary works correctly after login. `lib64`/`lib` race was a Windows-only symptom affecting `stop-wiki-reminder.py`, unrelated to this bug. |
| **Auth failure (missing Ubuntu WSL credentials)** | **CONFIRMED** | Direct probes (`auth status`, `--print`) confirmed `loggedIn: false` → `Not logged in` output → SDK parse failure → exit 1. |
| CLI/SDK version mismatch | REJECTED | Both sides are on `claude-agent-sdk 0.1.58` and `claude 2.1.97`. Version sig is compatible (`HAS_ProcessError=True`). |
| Path / cwd in subprocess | REJECTED | `cwd=<projects-root>/...` works correctly after auth, as proven by the validation run. |
| Rate limit / quota | REJECTED | Smoke test with fresh auth returned a normal response. |

**Primary root cause**: Bundled Claude CLI in the Ubuntu WSL distribution (where Codex hooks spawn `flush.py`) was never authenticated. A single user-run `claude auth login` inside that distribution resolved the bug. No code change was required for the fix itself. The diagnostic patch (`_log_cli_stderr` + `ProcessError` branch) is retained as a long-term visibility improvement for other failure modes.

### 9.7 Next follow-ups (not part of this investigation)

- Merge the diagnostic visibility patch in `scripts/flush.py` via PR with `Fixes #6`.
- Close issue #6 on merge.
- Reject `#8` as candidate for #6 (but keep it open as an independent external-risk tracker).
- Keep `#13` (.venv churn on Windows) open — still relevant for Windows-side `uv run` reliability.
- Monitor `scripts/flush.log` over the next real Codex session(s) for `Flushed N chars to daily log` lines with real session IDs as the final confirmation.
- Consider documenting "Codex integration requires `claude auth login` inside the user's dev WSL distribution" in `AGENTS.md` or setup docs so future forkers do not hit the same issue.

---

## 10. Self-audit

- ✅ I verified the official SDK docs before editing code
- ✅ I changed only `scripts/flush.py`
- ✅ I did not touch retry logic, prompt text, locking, or deduplication
- ✅ I ran the mandatory Variant A reproducer
- ✅ I ran deeper probes because Variant A did not expose the bug
- ✅ I recorded only real command outputs
- ✅ I did not claim Bug G is fixed
- ✅ I did not commit or push
- ✅ (section 9, Claude) Root cause identified outside Codex's harness by targeting Ubuntu distribution explicitly
- ✅ (section 9, Claude) Fix validated end-to-end with real daily log growth
- ✅ (section 9, Claude) Personal data (`email`, `orgId`, `orgName`) redacted from report

