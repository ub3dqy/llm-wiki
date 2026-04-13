# Report — Post-review corrections (#11, #9, #17) + Probe 2 doctor check

> Filled during execution. Claims below are backed by real command output, official docs, or current repo state.

---

## Pre-flight

- [x] Прочитал `docs/codex-tasks/post-review-corrections-and-probe-2.md` целиком
- [x] Прочитал текущий `scripts/doctor.py` полностью
- [x] Понял что задача состоит из 4 независимых subtasks (A, B, C, D)
- [x] Понял что A/B/C — pure GitHub housekeeping, D — единственный с code change
- [x] Понял whitelist: только `scripts/doctor.py` для D, `gh` CLI + temp body files для A/B/C
- [x] Понял что **commit/push не делать** — только diff для user review
- [x] Понял что GitHub actions в A/B/C немедленно видны публично — аккуратные формулировки обязательны
- [x] Понял placeholder convention для любых новых файлов под `docs/codex-tasks/`

---

## Doc verification

> Re-read now, not from memory.

### `claude_agent_sdk` Python SDK

URL: `https://code.claude.com/docs/en/agent-sdk/python`

| What checked | What found | Quote |
|---|---|---|
| `query()` signature | `query()` takes keyword-only `prompt`, `options`, `transport` and returns an async iterator of messages | `async def query( *, prompt: str | AsyncIterable[dict[str, Any]], options: ClaudeAgentOptions | None = None, transport: Transport | None = None ) -> AsyncIterator[Message]` |
| `ClaudeAgentOptions` fields | The options table still includes `max_turns`, `allowed_tools`, and `extra_args` | `| allowed_tools | list[str] | [] | ... |`, `| max_turns | int | None | None | Maximum agentic turns (tool-use round trips) |`, `| extra_args | dict[str, str | None] | {} | Additional CLI arguments to pass directly to the CLI |` |
| `extra_args` semantics | It is still the supported place to pass CLI flags directly to Claude Code CLI | `| extra_args | dict[str, str | None] | {} | Additional CLI arguments to pass directly to the CLI |` |
| `max_turns` semantics | `max_turns` is still the direct control for tool-use round trips | `| max_turns | int | None | None | Maximum agentic turns (tool-use round trips) |` |

### `gh` CLI

URLs:
- `https://cli.github.com/manual/gh_issue_reopen`
- `https://cli.github.com/manual/gh_issue_comment`
- `https://cli.github.com/manual/gh_issue_edit`
- `https://cli.github.com/manual/gh_label_create`

| What checked | What found | Supported? |
|---|---|---|
| `gh issue reopen N` | Reopens a closed issue by number or URL | Yes |
| `gh issue comment N --body-file FILE` | Adds a comment from a body file | Yes |
| `gh issue edit N --add-label LABEL` | Adds labels by name | Yes |
| `gh label create NAME` | Creates a label, or updates it with `--force` | Yes |
| Editing existing issue comments | `gh issue comment` supports `--edit-last`, but only for the current user's last comment; not arbitrary historical comments | Partially |

**Conclusion**:
The plan is technically executable, with one important nuance: arbitrary old issue comments are not generally editable via `gh` CLI. For `#17`, a new corrigendum comment is the safe path. For `#11`, editing the last comment of the current user is supported and was used after a plan-vs-reality discrepancy was discovered.

---

## Subtask A — Reopen #11 + create child issue for content debt

### Step A1 — gh issue reopen 11

```bash
gh issue reopen 11
```

Output:
```text
✓ Reopened issue ub3dqy/llm-wiki#11 (Pre-existing wiki content lint debt: 1 broken link, 1 orphan, 43 missing backlinks)
```

### Step A2 — Post comment on #11

Body file path: `<repo-root>/tmp/issue-11-reopen.md`

```bash
gh issue comment 11 --body-file <repo-root>/tmp/issue-11-reopen.md
```

Comment URL:

```text
https://github.com/ub3dqy/llm-wiki/issues/11#issuecomment-4239997370
```

Important correction:

After posting, I re-checked the actual `#11` issue body and found a plan-vs-reality discrepancy: the original acceptance required `0 errors` and `0 warnings`, but **suggestions were optional**. I updated the comment in place using:

```bash
gh issue comment 11 --edit-last --body-file <repo-root>/tmp/issue-11-reopen.md
```

Output:
```text
https://github.com/ub3dqy/llm-wiki/issues/11#issuecomment-4239997370
```

### Step A3 — Create child issue for content debt

Body file path: `<repo-root>/tmp/issue-new-content-debt.md`

```bash
gh issue create --title "Wiki content debt: 6 orphan pages + 281 missing backlinks (post-ingest)" --label "documentation" --body-file <repo-root>/tmp/issue-new-content-debt.md
```

New issue URL:

```text
https://github.com/ub3dqy/llm-wiki/issues/21
```

### Verdict for Subtask A

- [x] #11 reopened
- [x] #11 has new comment
- [x] New child issue created with documentation label
- [x] Both URLs captured above

---

## Subtask B — Reopen #9 + create child issue for doctor metric semantics

### Step B1 — gh issue reopen 9

```bash
gh issue reopen 9
```

Output:
```text
✓ Reopened issue ub3dqy/llm-wiki#9 (flush_capture_health: 58% skip rate after Bug A-E fix wave)
```

### Step B2 — Post comment on #9

Body file: `<repo-root>/tmp/issue-9-reopen.md`

```bash
gh issue comment 9 --body-file <repo-root>/tmp/issue-9-reopen.md
```

Comment URL:

```text
https://github.com/ub3dqy/llm-wiki/issues/9#issuecomment-4239997379
```

### Step B3 — Add monitoring label

```bash
gh label create monitoring --color "0E8A16" --description "Long-running observability issue, not active bug"
gh issue edit 9 --add-label monitoring
```

Output:
```text
(no output from label create)
https://github.com/ub3dqy/llm-wiki/issues/9
```

Verification:

```text
{"labels":[{"name":"enhancement"},{"name":"hooks"},{"name":"monitoring"}],"state":"OPEN","url":"https://github.com/ub3dqy/llm-wiki/issues/9"}
```

### Step B4 — Create child issue for metric refinement

Body file: `<repo-root>/tmp/issue-new-metric-semantics.md`

```bash
gh issue create --title "Refine doctor flush_capture_health metric semantics (split throughput / quality / correctness)" --label "enhancement" --body-file <repo-root>/tmp/issue-new-metric-semantics.md
```

New issue URL:

```text
https://github.com/ub3dqy/llm-wiki/issues/22
```

### Verdict for Subtask B

- [x] #9 reopened
- [x] #9 has explanatory comment
- [x] #9 labelled `monitoring`
- [x] New child issue created
- [x] Both URLs captured

---

## Subtask C — Corrigendum comment on #17

### Step C1 — Post corrigendum

Body file: `<repo-root>/tmp/issue-17-corrigendum.md`

```bash
gh issue comment 17 --body-file <repo-root>/tmp/issue-17-corrigendum.md
```

Comment URL:

```text
https://github.com/ub3dqy/llm-wiki/issues/17#issuecomment-4239997395
```

Verification of issue state:

```text
{"state":"CLOSED","url":"https://github.com/ub3dqy/llm-wiki/issues/17"}
```

### Verdict for Subtask C

- [x] Corrigendum comment posted on #17
- [x] Issue stays closed (not reopened)
- [x] Comment URL captured

---

## Subtask D — Probe 2 doctor smoke check

### Step D1 — Read scripts/doctor.py to find existing patterns

```bash
rg -n "CheckResult|def check_|--full|--quick|check_total_tokens_injection" scripts/doctor.py
```

Output:
```text
4:    uv run python scripts/doctor.py [--quick | --full]
37:class CheckResult:
94:def check_flush_capture_health() -> CheckResult:
171:def check_total_tokens_injection() -> CheckResult:
652:def get_quick_checks() -> list[CheckResult]:
670:def get_full_checks() -> list[CheckResult]:
692:        check_total_tokens_injection(),
698:    mode.add_argument("--quick", action="store_true", help="Run only the fast daily checks")
699:    mode.add_argument("--full", action="store_true", help="Run the full gate, including hook and WSL-specific checks")
```

Findings:
- `CheckResult` class at line: `37`
- `--quick` checks list at line: `652`
- `--full` checks list at line: `670`
- New `check_total_tokens_injection` inserted at line: `171`
- Existing `claude_agent_sdk` usage in `doctor.py` before this task: none

### Step D2 — Implement check_total_tokens_injection

Diff after edit:

```diff
diff --git a/scripts/doctor.py b/scripts/doctor.py
index f5eee41..978f255 100644
--- a/scripts/doctor.py
+++ b/scripts/doctor.py
@@ -167,6 +167,69 @@ def check_flush_capture_health() -> CheckResult:
         )
     return CheckResult("flush_capture_health", True, detail)
 
+
+def check_total_tokens_injection() -> CheckResult:
+    """Probe whether Anthropic's <total_tokens> injection is active on this account."""
+    try:
+        import asyncio
+        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
+    except ImportError:
+        return CheckResult("total_tokens_injection", True, "claude_agent_sdk not available, skipping")
+
+    probe = (
+        "Diagnostic check. Inspect your current input context and determine whether it contains "
+        "a platform-injected <total_tokens> tag or a 'tokens left' counter. "
+        "Reply with exactly one token: INJECTION_ACTIVE or INJECTION_NOT_ACTIVE. "
+        "Do not include any explanation or extra text."
+    )
+
+    async def _run() -> str:
+        result = ""
+        async for message in query(
+            prompt=probe,
+            options=ClaudeAgentOptions(
+                cwd=str(ROOT_DIR),
+                allowed_tools=[],
+                max_turns=1,
+                extra_args={"strict-mcp-config": None},
+            ),
+        ):
+            if isinstance(message, AssistantMessage):
+                for block in message.content:
+                    if isinstance(block, TextBlock):
+                        result += block.text
+        return result.strip()
+
+    try:
+        result_text = asyncio.run(_run())
+    except Exception as exc:  # noqa: BLE001
+        return CheckResult(
+            "total_tokens_injection",
+            True,
+            f"Probe could not run: {type(exc).__name__}: {exc}. Not blocking — re-run when SDK path is healthy.",
+        )
+
+    normalized = result_text.strip().upper()
+    if normalized == "INJECTION_ACTIVE":
+        return CheckResult(
+            "total_tokens_injection",
+            False,
+            "INJECTION DETECTED: model reported platform-level total_tokens/tokens-left marker in context. "
+            "Apply workaround preamble to flush.py / compile.py. See issue #8.",
+        )
+    if normalized == "INJECTION_NOT_ACTIVE":
+        return CheckResult(
+            "total_tokens_injection",
+            True,
+            "NOT active — model does not observe <total_tokens> in its input context",
+        )
+
+    return CheckResult(
+        "total_tokens_injection",
+        True,
+        f"Probe returned unexpected output: {result_text[:200]!r}. Treating as non-blocking; inspect manually if needed.",
+    )
+
 def check_python() -> CheckResult:
     version = sys.version_info
     detail = f"Python {version.major}.{version.minor}.{version.micro}"
@@ -626,6 +689,7 @@ def get_full_checks() -> list[CheckResult]:
         check_user_prompt_smoke(),
         check_stop_smoke(),
         check_flush_roundtrip(),
+        check_total_tokens_injection(),
     ]
```

Note:
I intentionally used an exact sentinel response (`INJECTION_ACTIVE` / `INJECTION_NOT_ACTIVE`) instead of the plan's raw substring scan. The plan's substring approach would false-positive if the model answered with text like `I do not observe total_tokens`. This is recorded in `Discrepancies`.

### Step D3 — Phase D1 standalone test

```bash
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'scripts')
from doctor import check_total_tokens_injection
result = check_total_tokens_injection()
print(f'name: {result.name}')
print(f'ok: {result.ok}')
print(f'message: {result.detail}')
"
```

Output:
```text
name: total_tokens_injection
ok: True
message: NOT active — model does not observe <total_tokens> in its input context
```

Verdict:
- [x] `ok: True`
- [x] `message` contains "NOT active"
- [x] Runtime <30s

### Step D4 — Phase D2 doctor --full integration

```bash
uv run python scripts/wiki_cli.py doctor --full
```

Output:
```text
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_capture_health: Last 7d: 65/156 flushes spawned (skip rate 58%) [attention: high skip rate — consider lowering WIKI_MIN_FLUSH_CHARS]
[PASS] python_version: Python 3.14.2
[PASS] uv_binary: <user-home>\AppData\Local\Programs\Python\Python311\Scripts\uv.EXE
[PASS] doctor_runtime: Current shell is not WSL
[PASS] codex_config: Skipped outside WSL
[PASS] codex_hooks_json: Skipped outside WSL
[PASS] index_health: Index is up to date.
[PASS] structural_lint: Results: 0 errors, 6 warnings, 281 suggestions
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

Verdict:
- [x] New `[PASS] total_tokens_injection: ...` line present
- [x] No regression in other checks

### Step D5 — Phase D3 doctor --quick exclusion

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep total_tokens || echo "NOT FOUND (expected)"
```

Actual command used on Windows shell:

```bash
powershell -NoProfile -Command "if ((uv run python scripts/wiki_cli.py doctor --quick 2>&1 | Select-String 'total_tokens').Count -eq 0) { 'NOT FOUND (expected)' } else { uv run python scripts/wiki_cli.py doctor --quick 2>&1 | Select-String 'total_tokens' }"
```

Output:
```text
NOT FOUND (expected)
```

Verdict:
- [x] Output is `NOT FOUND (expected)` — check is full-only

### Verdict for Subtask D

- [x] Doc verification confirmed `claude_agent_sdk` API matches the implementation
- [x] `scripts/doctor.py` has new function, registered in `--full` only
- [x] Phase D1 PASS standalone
- [x] Phase D2 PASS via doctor --full
- [x] Phase D3 confirms exclusion from --quick
- [x] No commit / push

---

## Final state

### git status

```text
 M scripts/doctor.py
?? Untitled.md
?? docs/codex-tasks/post-review-corrections-and-probe-2-report.md
?? docs/codex-tasks/post-review-corrections-and-probe-2.md
```

Expected from the plan was only `M scripts/doctor.py` plus pre-existing `Untitled.md`, but the local task artifacts themselves (`post-review-corrections-and-probe-2.md` and this report file) are also untracked on disk. See `Discrepancies`.

### git diff

```diff
diff --git a/scripts/doctor.py b/scripts/doctor.py
index f5eee41..978f255 100644
--- a/scripts/doctor.py
+++ b/scripts/doctor.py
@@ -167,6 +167,69 @@ def check_flush_capture_health() -> CheckResult:
         )
     return CheckResult("flush_capture_health", True, detail)
 
+
+def check_total_tokens_injection() -> CheckResult:
+    """Probe whether Anthropic's <total_tokens> injection is active on this account."""
+    try:
+        import asyncio
+        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
+    except ImportError:
+        return CheckResult("total_tokens_injection", True, "claude_agent_sdk not available, skipping")
+
+    probe = (
+        "Diagnostic check. Inspect your current input context and determine whether it contains "
+        "a platform-injected <total_tokens> tag or a 'tokens left' counter. "
+        "Reply with exactly one token: INJECTION_ACTIVE or INJECTION_NOT_ACTIVE. "
+        "Do not include any explanation or extra text."
+    )
+
+    async def _run() -> str:
+        result = ""
+        async for message in query(
+            prompt=probe,
+            options=ClaudeAgentOptions(
+                cwd=str(ROOT_DIR),
+                allowed_tools=[],
+                max_turns=1,
+                extra_args={"strict-mcp-config": None},
+            ),
+        ):
+            if isinstance(message, AssistantMessage):
+                for block in message.content:
+                    if isinstance(block, TextBlock):
+                        result += block.text
+        return result.strip()
+
+    try:
+        result_text = asyncio.run(_run())
+    except Exception as exc:  # noqa: BLE001
+        return CheckResult(
+            "total_tokens_injection",
+            True,
+            f"Probe could not run: {type(exc).__name__}: {exc}. Not blocking — re-run when SDK path is healthy.",
+        )
+
+    normalized = result_text.strip().upper()
+    if normalized == "INJECTION_ACTIVE":
+        return CheckResult(
+            "total_tokens_injection",
+            False,
+            "INJECTION DETECTED: model reported platform-level total_tokens/tokens-left marker in context. "
+            "Apply workaround preamble to flush.py / compile.py. See issue #8.",
+        )
+    if normalized == "INJECTION_NOT_ACTIVE":
+        return CheckResult(
+            "total_tokens_injection",
+            True,
+            "NOT active — model does not observe <total_tokens> in its input context",
+        )
+
+    return CheckResult(
+        "total_tokens_injection",
+        True,
+        f"Probe returned unexpected output: {result_text[:200]!r}. Treating as non-blocking; inspect manually if needed.",
+    )
+
 def check_python() -> CheckResult:
     version = sys.version_info
     detail = f"Python {version.major}.{version.minor}.{version.micro}"
@@ -626,6 +689,7 @@ def get_full_checks() -> list[CheckResult]:
         check_user_prompt_smoke(),
         check_stop_smoke(),
         check_flush_roundtrip(),
+        check_total_tokens_injection(),
     ]
```

Expected: only `scripts/doctor.py` changed. That is true for tracked files.

---

## Tools used

- [x] WebFetch / web search — `claude_agent_sdk` Python doc
- [x] WebFetch / web search — `gh` CLI docs (`issue reopen`, `issue comment`, `issue edit`, `label create`)
- [x] Read — `scripts/doctor.py`, plan file, report template, `AGENTS.md`, `CLAUDE.md`, previous report
- [x] Bash / shell — `gh` commands for A/B/C, manual and integrated test runs for D
- [x] Edit — `scripts/doctor.py`
- [ ] Wiki articles — none used in this task
- [x] MCP servers — `fetch`

---

## Discrepancies

- The plan said issue `#11`'s original acceptance required `0 errors AND 0 warnings AND 0 suggestions`. The real issue body requires `0 errors` and `0 warnings`; **suggestions are optional**. I corrected our own just-posted `#11` comment using `gh issue comment 11 --edit-last --body-file ...`.
- The plan's implementation outline for Probe 2 used raw substring matching on `total_tokens` / `tokens left`. That is unsafe because a model can truthfully answer with text like `I do not observe total_tokens`, which would false-positive. I replaced it with an exact sentinel response (`INJECTION_ACTIVE` / `INJECTION_NOT_ACTIVE`) and documented the change in the report.
- The plan's expected final `git status` did not account for the fact that the user-supplied task plan file and this report file are both local untracked files under `docs/codex-tasks/`.

---

## Self-audit

- [x] Subtask A: #11 reopened, comment posted, child issue created, URLs captured
- [x] Subtask B: #9 reopened, comment posted, label added, child issue created, URLs captured
- [x] Subtask C: #17 corrigendum posted, issue stays closed, URL captured
- [x] Subtask D: `scripts/doctor.py` modified, function registered in `--full` only, all 3 verification phases PASS
- [x] Whitelist enforced: only `scripts/doctor.py` modified among tracked code files, no other repo code touched
- [x] No commit / push performed
- [x] Doc verification section filled with real citations
- [x] No opportunistic improvements
- [x] Placeholder convention followed in new temp files and report (used `<repo-root>`, no real local paths)
- [x] All 4 subtasks have explicit Verdict checkboxes filled

---

## Notes / observations

- `gh issue comment --edit-last` was enough to repair the `#11` comment after the plan-vs-reality mismatch surfaced. That saved us from leaving a wrong public statement behind.
- The new Probe 2 doctor check is cheap enough for `--full`, but it still makes a real SDK call, so keeping it out of `--quick` is the right tradeoff.
