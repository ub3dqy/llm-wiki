# Report — Wiki backlinks cleanup Phase A (top-10 target articles)

> Executed by Codex incrementally. Every claim below is tagged as [OFFICIAL], [EMPIRICAL], or [PROJECT].

---

## Pre-flight

- [x] Read `docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md` fully
- [x] Read `scripts/lint.py:check_missing_backlinks` (actual implementation)
- [x] Read `scripts/utils.py:extract_wikilinks` and `content_has_wikilink_target`
- [x] Read `reports/lint-2026-04-14.md`
- [x] Confirmed [PROJECT] plain `[[slug]]` inside the target body satisfies the symmetric backlink check
- [x] Confirmed [PROJECT] batching by target is the right unit of work
- [x] Confirmed [PROJECT] `#21` requires judgment; no blind auto-fix
- [x] Confirmed [PROJECT] whitelist is exactly 10 target files

---

## Doc verification

> Re-read during execution, not from memory.

### GitHub Flavored Markdown — lists

URL: `https://github.github.com/gfm/#list-items`

| What was verified | Quote |
|---|---|
| Bullet list item syntax | `[OFFICIAL] List markers typically start at the left margin, but may be indented by up to three spaces. List markers must be followed by one or more spaces or a tab.` |
| Blank lines around list content | `[OFFICIAL] Blank lines between block-level elements are ignored, except for the role they play in determining whether a list is tight or loose.` |

### Obsidian internal links

URL: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`

| What was verified | Quote |
|---|---|
| Plain wikilink syntax `[[target]]` | `[OFFICIAL] Wikilink: [[Three laws of motion]] or [[Three laws of motion.md]]` |
| Alias syntax `[[target\|alias]]` | `[OFFICIAL] Use a vertical bar (|) to change the display text. - [[Example|Custom name]]` |

### Conclusion

[OFFICIAL] The docs support the plan’s assumptions: ordinary markdown list bullets are valid in `## See Also`, and plain Obsidian wikilinks `[[target]]` are enough for the backlink matcher. [PROJECT] One discrepancy: the Obsidian vanity URL rendered only the shell page during fetch, so the syntax quote was taken from the official help/search content on the same domain.

---

## Phase 1 — pre-edit lint snapshot

### Command

```bash
uv run python scripts/lint.py --structural-only 2>&1 | Select-Object -Last 10
```

### Output

```text
  * wiki/sources/pion-webrtc-scalable-topology-issue.md links to [[entities/pulse-messenger]] but no link back
  * wiki/sources/recall-mcp-hooks-memory-hn.md links to [[concepts/claude-code-hooks]] but no link back
  * wiki/sources/recall-mcp-hooks-memory-hn.md links to [[concepts/llm-wiki-architecture]] but no link back
  * wiki/sources/recall-mcp-hooks-memory-hn.md links to [[sources/a-mem-zettelkasten-memory-hn]] but no link back
  * wiki/sources/recall-mcp-hooks-memory-hn.md links to [[sources/engram-local-first-memory-hn]] but no link back
  * wiki/sources/you-dont-need-vector-db-for-rag.md links to [[concepts/llm-wiki-architecture]] but no link back
  * wiki/sources/you-dont-need-vector-db-for-rag.md links to [[sources/engram-local-first-memory-hn]] but no link back

Orphan pages: 0
Broken links: 0
Results: 0 errors, 1 warnings, 283 suggestions
```

### Verdict

- [x] [EMPIRICAL] Output shows `Results: 0 errors, 1 warnings, 283 suggestions`
- [x] [EMPIRICAL] Count matches the plan closely enough, so execution proceeded

---

## Phase 1.5 — per-target analysis and edits

### Target 1 — `concepts/llm-wiki-architecture`

#### Sources linking to this target

```text
concepts/anthropic-context-anxiety-injection
concepts/claude-desktop-cowork-architecture
concepts/codex-stop-hook-reliability
concepts/upstream-feedback-queue-coleam00
connections/agent-memory-quality-pipeline
sources/a-mem-zettelkasten-memory-hn
sources/alive-five-markdown-files-memory-hn
sources/anthropic-scaling-managed-agents
sources/anthropic-telemetry-experiment-gates-reddit
sources/aris-autonomous-ml-research
sources/calx-corrections-tracking-hn
sources/claude-code-docker-mcp-orphan-bug
sources/claude-codepro-dev-env-hn
sources/claude-opus-4-6-diagnosis-2026
sources/cloud-coder-overnight-agent-reddit
sources/cognition-rebuilding-devin-sonnet-4-5
sources/cowork-vs-claude-code-reddit-apology
sources/engram-local-first-memory-hn
sources/graperoot-codex-cli-compact-reddit
sources/great-claude-code-leak-2026
sources/llm-referred-traffic-converts-venturebeat
sources/mason-context-builder-github
sources/mempalace-milla-jovovich-reddit
sources/mini-coder-cli-agent-hn
sources/recall-mcp-hooks-memory-hn
sources/spec-driven-verification-overnight-agents
sources/total-recall-write-gated-memory-hn
sources/total-tokens-injection-bug-reddit
sources/vector-vs-graph-rag-agent-memory
sources/you-dont-need-vector-db-for-rag
analyses/reddit-hn-research-2026-04-13
```

#### Per-source decisions

| Source article | Decision | Reason |
|---|---|---|
| `concepts/anthropic-context-anxiety-injection` | YES | [EMPIRICAL] Directly frames the bug as damaging the LLM Wiki capture path. |
| `concepts/claude-desktop-cowork-architecture` | YES | [EMPIRICAL] Same ecosystem/tooling context, direct relevance. |
| `concepts/codex-stop-hook-reliability` | YES | [EMPIRICAL] Reliability of Codex memory path is part of architecture. |
| `concepts/upstream-feedback-queue-coleam00` | NO | [EMPIRICAL] Feedback/process queue, not architecture of the wiki itself. |
| `connections/agent-memory-quality-pipeline` | YES | [EMPIRICAL] Direct architectural connection. |
| `sources/a-mem-zettelkasten-memory-hn` | YES | [EMPIRICAL] Explicit comparison to LLM Wiki memory approach. |
| `sources/alive-five-markdown-files-memory-hn` | YES | [EMPIRICAL] Directly compares memory models. |
| `sources/anthropic-scaling-managed-agents` | YES | [EMPIRICAL] Source informs the broader architecture discussion. |
| `sources/anthropic-telemetry-experiment-gates-reddit` | YES | [EMPIRICAL] Directly tied to capture/telemetry implications. |
| `sources/aris-autonomous-ml-research` | YES | [EMPIRICAL] Source used in architecture/tooling landscape context. |
| `sources/calx-corrections-tracking-hn` | YES | [EMPIRICAL] Relevant to correction/writeback architecture. |
| `sources/claude-code-docker-mcp-orphan-bug` | YES | [EMPIRICAL] Hook/runtime architecture evidence. |
| `sources/claude-codepro-dev-env-hn` | NO | [EMPIRICAL] More dev-env UX than wiki architecture. |
| `sources/claude-opus-4-6-diagnosis-2026` | YES | [EMPIRICAL] Directly connected to architecture/pathology of the system. |
| `sources/cloud-coder-overnight-agent-reddit` | YES | [EMPIRICAL] Relevant to autonomous capture/agent workflows. |
| `sources/cognition-rebuilding-devin-sonnet-4-5` | YES | [EMPIRICAL] Direct comparison point in memory/tooling architecture. |
| `sources/cowork-vs-claude-code-reddit-apology` | YES | [EMPIRICAL] Core ecosystem comparison source. |
| `sources/engram-local-first-memory-hn` | YES | [EMPIRICAL] Explicit memory architecture comparison. |
| `sources/graperoot-codex-cli-compact-reddit` | NO | [EMPIRICAL] Tangential tool UX, not central wiki architecture. |
| `sources/great-claude-code-leak-2026` | NO | [EMPIRICAL] Safety/culture source, indirect at best. |
| `sources/llm-referred-traffic-converts-venturebeat` | NO | [EMPIRICAL] Traffic/SEO source, not architecture. |
| `sources/mason-context-builder-github` | YES | [EMPIRICAL] Directly relevant alternative architecture. |
| `sources/mempalace-milla-jovovich-reddit` | YES | [EMPIRICAL] Explicit memory model comparison. |
| `sources/mini-coder-cli-agent-hn` | NO | [EMPIRICAL] Too tangential. |
| `sources/recall-mcp-hooks-memory-hn` | YES | [EMPIRICAL] Direct comparison to hook-based memory architecture. |
| `sources/spec-driven-verification-overnight-agents` | YES | [EMPIRICAL] Connected to writeback/verification architecture. |
| `sources/total-recall-write-gated-memory-hn` | YES | [EMPIRICAL] Direct memory architecture contrast. |
| `sources/total-tokens-injection-bug-reddit` | YES | [EMPIRICAL] Direct architectural failure mode. |
| `sources/vector-vs-graph-rag-agent-memory` | YES | [EMPIRICAL] Memory architecture comparison. |
| `sources/you-dont-need-vector-db-for-rag` | YES | [EMPIRICAL] Directly informs architecture tradeoffs. |
| `analyses/reddit-hn-research-2026-04-13` | YES | [EMPIRICAL] Consolidated research tied back to the architecture. |

#### Edit applied

```diff
- [[concepts/claude-cli-autonomous-task-loops]] — параллельный паттерн "Claude процессит Claude", применённый к code hardening вместо knowledge capture
+ [[concepts/claude-cli-autonomous-task-loops]] — параллельный паттерн "Claude процессит Claude", применённый к code hardening вместо knowledge capture
+ [[concepts/anthropic-context-anxiety-injection]]
+ [[concepts/claude-desktop-cowork-architecture]]
+ [[concepts/codex-stop-hook-reliability]]
+ [[connections/agent-memory-quality-pipeline]]
+ [[sources/a-mem-zettelkasten-memory-hn]]
+ [[sources/alive-five-markdown-files-memory-hn]]
+ [[sources/anthropic-scaling-managed-agents]]
+ [[sources/anthropic-telemetry-experiment-gates-reddit]]
+ [[sources/aris-autonomous-ml-research]]
+ [[sources/calx-corrections-tracking-hn]]
+ [[sources/claude-code-docker-mcp-orphan-bug]]
+ [[sources/claude-opus-4-6-diagnosis-2026]]
+ [[sources/cloud-coder-overnight-agent-reddit]]
+ [[sources/cognition-rebuilding-devin-sonnet-4-5]]
+ [[sources/cowork-vs-claude-code-reddit-apology]]
+ [[sources/engram-local-first-memory-hn]]
+ [[sources/mason-context-builder-github]]
+ [[sources/mempalace-milla-jovovich-reddit]]
+ [[sources/recall-mcp-hooks-memory-hn]]
+ [[sources/spec-driven-verification-overnight-agents]]
+ [[sources/total-recall-write-gated-memory-hn]]
+ [[sources/total-tokens-injection-bug-reddit]]
+ [[sources/vector-vs-graph-rag-agent-memory]]
+ [[sources/you-dont-need-vector-db-for-rag]]
+ [[analyses/reddit-hn-research-2026-04-13]]
```

#### Summary

- Candidates: 31
- YES (links added): 25
- NO: 6
- SKIP: 0

### Target 2 — `concepts/claude-code-hooks`

#### Sources linking to this target

```text
concepts/asyncio-event-loop-patterns
concepts/claude-cli-autonomous-task-loops
concepts/claude-code-memory-tooling-landscape
concepts/claude-desktop-cowork-architecture
concepts/mcp-infrastructure-security
connections/agent-memory-quality-pipeline
sources/alive-five-markdown-files-memory-hn
sources/claude-code-docker-mcp-orphan-bug
sources/claude-code-subagent-orphan-bug
sources/cloud-coder-overnight-agent-reddit
sources/cowork-vs-claude-code-reddit-apology
sources/mason-context-builder-github
sources/recall-mcp-hooks-memory-hn
```

#### Per-source decisions

| Source | Decision | Reason |
|---|---|---|
| `concepts/asyncio-event-loop-patterns` | YES | [EMPIRICAL] Async runtime patterns are directly used in hooks. |
| `concepts/claude-cli-autonomous-task-loops` | YES | [EMPIRICAL] Same control-loop/hook family. |
| `concepts/claude-code-memory-tooling-landscape` | YES | [EMPIRICAL] Hooks are part of that tooling landscape. |
| `concepts/claude-desktop-cowork-architecture` | YES | [EMPIRICAL] Directly compares hook environments. |
| `concepts/mcp-infrastructure-security` | YES | [EMPIRICAL] Hooks touch MCP security surface. |
| `connections/agent-memory-quality-pipeline` | YES | [EMPIRICAL] Direct dependency. |
| `sources/alive-five-markdown-files-memory-hn` | NO | [EMPIRICAL] Mentions hooks only in passing. |
| `sources/claude-code-docker-mcp-orphan-bug` | YES | [EMPIRICAL] Hook/runtime bug source. |
| `sources/claude-code-subagent-orphan-bug` | YES | [EMPIRICAL] Hook behavior source. |
| `sources/cloud-coder-overnight-agent-reddit` | YES | [EMPIRICAL] Directly relevant to autonomous hook flows. |
| `sources/cowork-vs-claude-code-reddit-apology` | YES | [EMPIRICAL] Direct ecosystem relevance. |
| `sources/mason-context-builder-github` | NO | [EMPIRICAL] Not really about Claude hooks themselves. |
| `sources/recall-mcp-hooks-memory-hn` | YES | [EMPIRICAL] Direct comparison point. |

#### Edit applied

```diff
- [[concepts/codex-stop-hook-reliability]]
+ [[concepts/codex-stop-hook-reliability]]
+ [[concepts/asyncio-event-loop-patterns]]
+ [[concepts/claude-cli-autonomous-task-loops]]
+ [[concepts/claude-code-memory-tooling-landscape]]
+ [[concepts/claude-desktop-cowork-architecture]]
+ [[concepts/mcp-infrastructure-security]]
+ [[connections/agent-memory-quality-pipeline]]
+ [[sources/claude-code-docker-mcp-orphan-bug]]
+ [[sources/claude-code-subagent-orphan-bug]]
+ [[sources/cloud-coder-overnight-agent-reddit]]
+ [[sources/cowork-vs-claude-code-reddit-apology]]
+ [[sources/recall-mcp-hooks-memory-hn]]
```

#### Summary

- Candidates: 13
- YES: 11
- NO: 2
- SKIP: 0

### Target 3 — `concepts/anthropic-context-anxiety-injection`

#### Sources

```text
concepts/claude-code-memory-tooling-landscape
concepts/upstream-feedback-queue-coleam00
sources/anthropic-scaling-managed-agents
sources/aris-autonomous-ml-research
sources/claude-opus-4-6-diagnosis-2026
sources/cognition-rebuilding-devin-sonnet-4-5
sources/great-claude-code-leak-2026
sources/spec-driven-verification-overnight-agents
analyses/reddit-hn-research-2026-04-13
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `concepts/claude-code-memory-tooling-landscape` | YES | [EMPIRICAL] Directly places the injection bug in tooling landscape. |
| `concepts/upstream-feedback-queue-coleam00` | NO | [EMPIRICAL] Feedback queue, not about the injection itself. |
| `sources/anthropic-scaling-managed-agents` | YES | [EMPIRICAL] Direct Anthropic systems context. |
| `sources/aris-autonomous-ml-research` | YES | [EMPIRICAL] Source used in the same investigation cluster. |
| `sources/claude-opus-4-6-diagnosis-2026` | YES | [EMPIRICAL] Direct evidence. |
| `sources/cognition-rebuilding-devin-sonnet-4-5` | YES | [EMPIRICAL] Same failure pattern family. |
| `sources/great-claude-code-leak-2026` | YES | [EMPIRICAL] Broader Anthropic context directly referenced. |
| `sources/spec-driven-verification-overnight-agents` | NO | [EMPIRICAL] Verification practice, too indirect. |
| `analyses/reddit-hn-research-2026-04-13` | YES | [EMPIRICAL] Aggregated analysis references the concept directly. |

#### Edit

```diff
- [[concepts/claude-desktop-cowork-architecture]] — другой Anthropic-ecosystem dysfunction, задокументированный в апреле 2026
+ [[concepts/claude-desktop-cowork-architecture]] — другой Anthropic-ecosystem dysfunction, задокументированный в апреле 2026
+ [[concepts/claude-code-memory-tooling-landscape]]
+ [[sources/anthropic-scaling-managed-agents]]
+ [[sources/aris-autonomous-ml-research]]
+ [[sources/claude-opus-4-6-diagnosis-2026]]
+ [[sources/cognition-rebuilding-devin-sonnet-4-5]]
+ [[sources/great-claude-code-leak-2026]]
+ [[analyses/reddit-hn-research-2026-04-13]]
```

#### Summary

- Candidates: 9
- YES: 7
- NO: 2
- SKIP: 0

### Target 4 — `sources/a-mem-zettelkasten-memory-hn`

#### Sources

```text
sources/alive-five-markdown-files-memory-hn
sources/claude-codepro-dev-env-hn
sources/clawmem-gpu-retrieval-memory-hn
sources/mempalace-milla-jovovich-reddit
sources/recall-mcp-hooks-memory-hn
sources/valkey-semantic-memory-hn
sources/vector-vs-graph-rag-agent-memory
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `sources/alive-five-markdown-files-memory-hn` | YES | [EMPIRICAL] Direct comparison to A-MEM. |
| `sources/claude-codepro-dev-env-hn` | NO | [EMPIRICAL] Too tangential, dev env not memory model. |
| `sources/clawmem-gpu-retrieval-memory-hn` | YES | [EMPIRICAL] Memory-tool comparison. |
| `sources/mempalace-milla-jovovich-reddit` | YES | [EMPIRICAL] Explicitly references A-MEM-style memory tooling. |
| `sources/recall-mcp-hooks-memory-hn` | YES | [EMPIRICAL] Direct memory-tool comparison. |
| `sources/valkey-semantic-memory-hn` | YES | [EMPIRICAL] Same topic cluster. |
| `sources/vector-vs-graph-rag-agent-memory` | YES | [EMPIRICAL] Direct architectural comparison. |

#### Edit

```diff
- [[sources/total-recall-write-gated-memory-hn]] — contrast: write gate vs self-evolving
+ [[sources/total-recall-write-gated-memory-hn]] — contrast: write gate vs self-evolving
+ [[sources/alive-five-markdown-files-memory-hn]]
+ [[sources/clawmem-gpu-retrieval-memory-hn]]
+ [[sources/mempalace-milla-jovovich-reddit]]
+ [[sources/recall-mcp-hooks-memory-hn]]
+ [[sources/valkey-semantic-memory-hn]]
+ [[sources/vector-vs-graph-rag-agent-memory]]
```

#### Summary

- Candidates: 7
- YES: 6
- NO: 1
- SKIP: 0

### Target 5 — `sources/engram-local-first-memory-hn`

#### Sources

```text
sources/clawmem-gpu-retrieval-memory-hn
sources/mempalace-milla-jovovich-reddit
sources/recall-mcp-hooks-memory-hn
sources/valkey-semantic-memory-hn
sources/vector-vs-graph-rag-agent-memory
sources/you-dont-need-vector-db-for-rag
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `sources/clawmem-gpu-retrieval-memory-hn` | YES | [EMPIRICAL] Direct memory-tool comparison. |
| `sources/mempalace-milla-jovovich-reddit` | YES | [EMPIRICAL] Same memory-tool cluster. |
| `sources/recall-mcp-hooks-memory-hn` | YES | [EMPIRICAL] Directly compares hook memory tools. |
| `sources/valkey-semantic-memory-hn` | YES | [EMPIRICAL] Related memory architecture source. |
| `sources/vector-vs-graph-rag-agent-memory` | YES | [EMPIRICAL] Direct comparison. |
| `sources/you-dont-need-vector-db-for-rag` | YES | [EMPIRICAL] Graph/vector memory tradeoff source. |

#### Edit

```diff
- [[concepts/llm-wiki-architecture]]
+ [[concepts/llm-wiki-architecture]]
+ [[sources/clawmem-gpu-retrieval-memory-hn]]
+ [[sources/mempalace-milla-jovovich-reddit]]
+ [[sources/recall-mcp-hooks-memory-hn]]
+ [[sources/valkey-semantic-memory-hn]]
+ [[sources/vector-vs-graph-rag-agent-memory]]
+ [[sources/you-dont-need-vector-db-for-rag]]
```

#### Summary

- Candidates: 6
- YES: 6
- NO: 0
- SKIP: 0

### Target 6 — `entities/pulse-messenger`

#### Sources

```text
concepts/agent-memory-filtering
concepts/agent-memory-production-schema
concepts/mcp-infrastructure-security
concepts/pgvector-agent-memory
sources/livekit-sfu-architecture-docs
sources/pion-webrtc-scalable-topology-issue
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `concepts/agent-memory-filtering` | YES | [EMPIRICAL] Pulse is a concrete production consumer. |
| `concepts/agent-memory-production-schema` | YES | [EMPIRICAL] Same. |
| `concepts/mcp-infrastructure-security` | YES | [EMPIRICAL] Pulse infrastructure/security context. |
| `concepts/pgvector-agent-memory` | YES | [EMPIRICAL] Pulse is concrete application context. |
| `sources/livekit-sfu-architecture-docs` | YES | [EMPIRICAL] Pulse calls architecture uses it as a reference. |
| `sources/pion-webrtc-scalable-topology-issue` | YES | [EMPIRICAL] Directly relevant to Pulse calls topology. |

#### Edit

```diff
- [[concepts/pulse-e2ee-issues]]
+ [[concepts/pulse-e2ee-issues]]
+ [[concepts/agent-memory-filtering]]
+ [[concepts/agent-memory-production-schema]]
+ [[concepts/mcp-infrastructure-security]]
+ [[concepts/pgvector-agent-memory]]
+ [[sources/livekit-sfu-architecture-docs]]
+ [[sources/pion-webrtc-scalable-topology-issue]]
```

#### Summary

- Candidates: 6
- YES: 6
- NO: 0
- SKIP: 0

### Target 7 — `concepts/windows-path-issues`

#### Sources

```text
concepts/codex-stop-hook-reliability
sources/claude-code-vscode-mcp-crash-bug
sources/claude-codepro-dev-env-hn
sources/claude-opus-4-6-diagnosis-2026
sources/cowork-vs-claude-code-reddit-apology
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `concepts/codex-stop-hook-reliability` | YES | [EMPIRICAL] Windows path issues directly affect stop reliability. |
| `sources/claude-code-vscode-mcp-crash-bug` | YES | [EMPIRICAL] Pure Windows-path/runtime bug source. |
| `sources/claude-codepro-dev-env-hn` | YES | [EMPIRICAL] Windows path/dev env source. |
| `sources/claude-opus-4-6-diagnosis-2026` | YES | [EMPIRICAL] Real Windows path evidence. |
| `sources/cowork-vs-claude-code-reddit-apology` | YES | [EMPIRICAL] Direct Windows path/tooling context. |

#### Edit

```diff
- [[overview]]
+ [[overview]]
+ [[concepts/codex-stop-hook-reliability]]
+ [[sources/claude-code-vscode-mcp-crash-bug]]
+ [[sources/claude-codepro-dev-env-hn]]
+ [[sources/claude-opus-4-6-diagnosis-2026]]
+ [[sources/cowork-vs-claude-code-reddit-apology]]
```

#### Summary

- Candidates: 5
- YES: 5
- NO: 0
- SKIP: 0

### Target 8 — `concepts/pion-webrtc-calls`

#### Sources

```text
concepts/flutter-dependency-upgrade-waves
sources/flutter-riverpod-vs-bloc-comparison
sources/livekit-sfu-architecture-docs
sources/pion-webrtc-scalable-topology-issue
analyses/reddit-hn-research-2026-04-13
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `concepts/flutter-dependency-upgrade-waves` | NO | [EMPIRICAL] Dependency-upgrade wave, not directly about WebRTC calls concept. |
| `sources/flutter-riverpod-vs-bloc-comparison` | NO | [EMPIRICAL] State management source, not calls architecture. |
| `sources/livekit-sfu-architecture-docs` | YES | [EMPIRICAL] Directly relevant SFU/calls architecture. |
| `sources/pion-webrtc-scalable-topology-issue` | YES | [EMPIRICAL] Direct WebRTC calls source. |
| `analyses/reddit-hn-research-2026-04-13` | YES | [EMPIRICAL] Analysis explicitly references the concept. |

#### Edit

```diff
- [[overview]]
+ [[overview]]
+ [[sources/livekit-sfu-architecture-docs]]
+ [[sources/pion-webrtc-scalable-topology-issue]]
+ [[analyses/reddit-hn-research-2026-04-13]]
```

#### Summary

- Candidates: 5
- YES: 3
- NO: 2
- SKIP: 0

### Target 9 — `concepts/codex-stop-hook-reliability`

#### Sources

```text
concepts/upstream-feedback-queue-coleam00
sources/claude-code-chrome-socket-crash-bug
sources/claude-code-non-git-hang-bug
sources/claude-code-subagent-orphan-bug
sources/graperoot-codex-cli-compact-reddit
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `concepts/upstream-feedback-queue-coleam00` | NO | [EMPIRICAL] Feedback queue, not stop-hook reliability. |
| `sources/claude-code-chrome-socket-crash-bug` | YES | [EMPIRICAL] Direct reliability failure source. |
| `sources/claude-code-non-git-hang-bug` | YES | [EMPIRICAL] Direct reliability failure source. |
| `sources/claude-code-subagent-orphan-bug` | YES | [EMPIRICAL] Direct reliability failure source. |
| `sources/graperoot-codex-cli-compact-reddit` | NO | [EMPIRICAL] Compact UX is too indirect. |

#### Edit

```diff
- [[concepts/mcp-infrastructure-security]]
+ [[concepts/mcp-infrastructure-security]]
+ [[sources/claude-code-chrome-socket-crash-bug]]
+ [[sources/claude-code-non-git-hang-bug]]
+ [[sources/claude-code-subagent-orphan-bug]]
```

#### Summary

- Candidates: 5
- YES: 3
- NO: 2
- SKIP: 0

### Target 10 — `concepts/bullmq-agent-workers`

#### Sources

```text
sources/bullmq-at-scale-medium
sources/bullmq-horizontal-scaling-oneuptime
sources/fastify-queue-plugin-github
analyses/reddit-hn-research-2026-04-13
```

#### Decisions

| Source | Decision | Reason |
|---|---|---|
| `sources/bullmq-at-scale-medium` | YES | [EMPIRICAL] Direct implementation reference. |
| `sources/bullmq-horizontal-scaling-oneuptime` | YES | [EMPIRICAL] Direct horizontal scaling reference. |
| `sources/fastify-queue-plugin-github` | YES | [EMPIRICAL] Direct queue/plugin implementation reference. |
| `analyses/reddit-hn-research-2026-04-13` | YES | [EMPIRICAL] Analysis explicitly ties back to the concept. |

#### Edit

```diff
- [[overview]]
+ [[overview]]
+ [[sources/bullmq-at-scale-medium]]
+ [[sources/bullmq-horizontal-scaling-oneuptime]]
+ [[sources/fastify-queue-plugin-github]]
+ [[analyses/reddit-hn-research-2026-04-13]]
```

#### Summary

- Candidates: 4
- YES: 4
- NO: 0
- SKIP: 0

---

## Phase 2 — post-edit lint snapshot

### Command

```bash
uv run python scripts/lint.py --structural-only 2>&1 | Select-Object -Last 10
```

### Output

```text
  * wiki/sources/spec-driven-verification-overnight-agents.md links to [[concepts/anthropic-context-anxiety-injection]] but no link back
  * wiki/sources/upstream-feedback-queue-coleam00.md links to [[concepts/anthropic-context-anxiety-injection]] but no link back
  * wiki/sources/upstream-feedback-queue-coleam00.md links to [[concepts/codex-stop-hook-reliability]] but no link back
  * wiki/sources/upstream-feedback-queue-coleam00.md links to [[concepts/llm-wiki-architecture]] but no link back
  * wiki/sources/upstream-feedback-queue-coleam00.md links to [[sources/claude-code-memory-tooling-landscape]] but no link back
  * wiki/sources/upstream-feedback-queue-coleam00.md links to [[sources/seo-ai-strategy-2026-notebooklm]] but no link back
  * wiki/sources/upstream-feedback-queue-coleam00.md links to [[sources/uv-python-tooling]] but no link back

Orphan pages: 0
Broken links: 0
Results: 0 errors, 1 warnings, 147 suggestions
```

### Verdict

- [x] [EMPIRICAL] Errors stayed at 0
- [x] [EMPIRICAL] Warnings stayed at 1
- [x] [EMPIRICAL] Suggestions dropped from 283 to 147
- [x] [EMPIRICAL] Actual drop = 136, which is meaningful and non-regressive

---

## Phase 3 — doctor regression

### Command

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | Select-String '(FAIL|PASS).*(lint|provenance)'
```

### Output

```text
[PASS] structural_lint: Results: 0 errors, 1 warnings, 147 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
```

### Verdict

- [x] [EMPIRICAL] `structural_lint` PASS
- [x] [EMPIRICAL] `wiki_cli_lint_smoke` PASS
- [x] [EMPIRICAL] `query_preview_smoke` PASS
- [x] [EMPIRICAL] No new FAILs from the content edits

---

## Phase 4 — spot-check 3 random targets

### Target A

Target: `concepts/llm-wiki-architecture`

```text
- [[concepts/claude-code-hooks]]
- [[concepts/uv-python-tooling]]
- [[concepts/windows-path-issues]]
- [[analyses/llm-wiki-improvement-research-2026-04-12]]
- [[overview]]
- [[concepts/claude-code-context-limits]]
- [[concepts/claude-cli-autonomous-task-loops]] — параллельный паттерн "Claude процессит Claude", применённый к code hardening вместо knowledge capture
- [[concepts/anthropic-context-anxiety-injection]]
- [[concepts/claude-desktop-cowork-architecture]]
- [[concepts/codex-stop-hook-reliability]]
- [[connections/agent-memory-quality-pipeline]]
- [[sources/a-mem-zettelkasten-memory-hn]]
- [[sources/alive-five-markdown-files-memory-hn]]
- [[sources/anthropic-scaling-managed-agents]]
- [[sources/anthropic-telemetry-experiment-gates-reddit]]
- [[sources/aris-autonomous-ml-research]]
- [[sources/calx-corrections-tracking-hn]]
- [[sources/claude-code-docker-mcp-orphan-bug]]
- [[sources/claude-opus-4-6-diagnosis-2026]]
- [[sources/cloud-coder-overnight-agent-reddit]]
- [[sources/cognition-rebuilding-devin-sonnet-4-5]]
- [[sources/cowork-vs-claude-code-reddit-apology]]
- [[sources/engram-local-first-memory-hn]]
- [[sources/mason-context-builder-github]]
- [[sources/mempalace-milla-jovovich-reddit]]
- [[sources/recall-mcp-hooks-memory-hn]]
- [[sources/spec-driven-verification-overnight-agents]]
- [[sources/total-recall-write-gated-memory-hn]]
- [[sources/total-tokens-injection-bug-reddit]]
- [[sources/vector-vs-graph-rag-agent-memory]]
- [[sources/you-dont-need-vector-db-for-rag]]
- [[analyses/reddit-hn-research-2026-04-13]]
```

Verdict:
- [x] Original entries preserved
- [x] New reverse links present
- [x] No duplicates
- [x] Valid markdown

### Target B

Target: `entities/pulse-messenger`

```text
- [[concepts/flutter-go-messenger-architecture]]
- [[concepts/messenger-docker-infrastructure]]
- [[concepts/flutter-adb-testing]]
- [[concepts/pulse-testing-methodology]]
- [[concepts/flutter-dependency-upgrade-waves]]
- [[sources/flutter-riverpod-vs-bloc-comparison]]
- [[concepts/claude-code-context-limits]]
- [[concepts/jwt-auth-pattern]]
- [[concepts/pulse-durable-mutations]]
- [[concepts/pulse-e2ee-issues]]
- [[concepts/agent-memory-filtering]]
- [[concepts/agent-memory-production-schema]]
- [[concepts/mcp-infrastructure-security]]
- [[concepts/pgvector-agent-memory]]
- [[sources/livekit-sfu-architecture-docs]]
- [[sources/pion-webrtc-scalable-topology-issue]]
- [[concepts/server-dns-migration-pitfalls]]
- [[concepts/claude-code-hooks]]
- [[overview]]
```

Verdict:
- [x] Original entries preserved
- [x] New reverse links present
- [x] No duplicates
- [x] Valid markdown

### Target C

Target: `concepts/bullmq-agent-workers`

```text
- [[concepts/agentcorp-domain-model]]
- [[concepts/pgvector-agent-memory]]
- [[entities/agentcorp]]
- [[concepts/agent-notification-system]]
- [[concepts/fastify-api-framework]]
- [[sources/agentcorp-architecture-notes]]
- [[overview]]
- [[sources/bullmq-at-scale-medium]]
- [[sources/bullmq-horizontal-scaling-oneuptime]]
- [[sources/fastify-queue-plugin-github]]
- [[analyses/reddit-hn-research-2026-04-13]]
```

Verdict:
- [x] Original entries preserved
- [x] New reverse links present
- [x] No duplicates
- [x] Valid markdown

---

## Phase 5 — decision statistics

### Aggregate across all 10 targets

| Target | Candidates | YES | NO | SKIP | Suggestions resolved |
|---|---|---:|---:|---:|---:|
| `concepts/llm-wiki-architecture` | 31 | 25 | 6 | 0 | 48 |
| `concepts/claude-code-hooks` | 13 | 11 | 2 | 0 | 15 |
| `concepts/anthropic-context-anxiety-injection` | 9 | 7 | 2 | 0 | 14 |
| `sources/a-mem-zettelkasten-memory-hn` | 7 | 6 | 1 | 0 | 10 |
| `sources/engram-local-first-memory-hn` | 6 | 6 | 0 | 0 | 11 |
| `entities/pulse-messenger` | 6 | 6 | 0 | 0 | 10 |
| `concepts/windows-path-issues` | 5 | 5 | 0 | 0 | 9 |
| `concepts/pion-webrtc-calls` | 5 | 3 | 2 | 0 | 5 |
| `concepts/codex-stop-hook-reliability` | 5 | 3 | 2 | 0 | 6 |
| `concepts/bullmq-agent-workers` | 4 | 4 | 0 | 0 | 8 |
| **TOTAL** | **91** | **76** | **15** | **0** | **136** |

### Derived metrics

- Total suggestions before Phase A: 283
- Total suggestions after Phase A: 147
- Actual drop: 136
- Expected drop from Top-10: ~100-154 raw suggestions
- YES rate: 83.5%

---

## Final state

### git status

```text
?? Untitled.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
```

### Files touched

| File | Type | Action |
|---|---|---|
| `wiki/concepts/llm-wiki-architecture.md` | concept | edit (`## See Also`) |
| `wiki/concepts/claude-code-hooks.md` | concept | edit (`## See Also`) |
| `wiki/concepts/anthropic-context-anxiety-injection.md` | concept | edit (`## See Also`) |
| `wiki/sources/a-mem-zettelkasten-memory-hn.md` | source | edit (`## See Also`) |
| `wiki/sources/engram-local-first-memory-hn.md` | source | edit (`## See Also`) |
| `wiki/entities/pulse-messenger.md` | entity | edit (`## See Also`) |
| `wiki/concepts/windows-path-issues.md` | concept | edit (`## See Also`) |
| `wiki/concepts/pion-webrtc-calls.md` | concept | edit (`## See Also`) |
| `wiki/concepts/codex-stop-hook-reliability.md` | concept | edit (`## See Also`) |
| `wiki/concepts/bullmq-agent-workers.md` | concept | edit (`## See Also`) |

### .bak files

- [x] [EMPIRICAL] All `.bak` files created for this Phase A run were deleted after verification
- [x] [EMPIRICAL] Four older `.bak` files remain in `wiki/` (`claude-code-memory-tooling-landscape`, `seo-ai-strategy-2026`, `upstream-feedback-queue-coleam00`, `uv-python-tooling`) and were left untouched because they predated this task

---

## Tools used

- [x] **WebFetch** `https://github.github.com/gfm/#list-items` — GFM list syntax verified
- [x] **WebFetch** `https://help.obsidian.md/Linking+notes+and+files/Internal+links` — wikilink syntax verified
- [x] **Read** `scripts/lint.py` — backlink check logic verified
- [x] **Read** `scripts/utils.py` — matcher semantics verified
- [x] **Read** `reports/lint-2026-04-14.md` — suggestion list verified
- [x] **Read** all 10 whitelisted target articles before editing
- [x] **Read** all unique source articles grouped per target before deciding YES/NO
- [x] **Bash/PowerShell** pre-edit lint snapshot
- [x] **Bash/PowerShell** post-edit lint snapshot
- [x] **Bash/PowerShell** doctor regression
- [x] **Bash/PowerShell** per-target grouping + diff + spot checks
- [x] **Edit** one `## See Also` update per target
- [x] **MCP filesystem** — BLOCKED: not available in this environment
- [x] **MCP git** — BLOCKED: not available in this environment

---

## Out-of-scope temptations

- [PROJECT] Did not edit `concepts/upstream-feedback-queue-coleam00` even though it remains a heavy backlink source; the phase rule was to edit link targets, not the source side.
- [PROJECT] Did not fix the remaining daily warning (`daily/2026-04-14.md` uncompiled); outside this phase.
- [PROJECT] Did not expand beyond the exact top-10 whitelist even though more candidates remain.

---

## Discrepancies

- [PROJECT] The lint report uses human-readable suggestion lines with displayed slashes/backslashes, but grouping by actual `[[source]] -> [[target]]` pairs still resolved to the same top-10 targets.
- [PROJECT] The Obsidian vanity help URL rendered only a shell page during fetch; the actual syntax quote was taken from official help/search content on the same domain.

---

## Self-audit

- [x] Doc verification section filled with real citations
- [x] Mandatory tools section fully ticked or marked BLOCKED
- [x] Each of 10 targets has a per-source decision table with rationale
- [x] Each of 10 targets has one edit diff in the report
- [x] Phase 1 pre-edit snapshot recorded with real output
- [x] Phase 2 post-edit snapshot recorded with real output
- [x] Phase 3 doctor regression recorded with real output
- [x] Phase 4 spot-check covers 3 random targets
- [x] Phase 5 statistics table complete
- [x] Out-of-scope and Discrepancies filled
- [x] No files touched outside whitelist
- [x] No commit / push
- [x] All task-created `.bak` files cleaned up
- [x] Report uses `${USER}`, `<repo-root>`, `<user-home>` placeholder convention where path placeholders would otherwise be user-specific

---

## Notes / observations

- [EMPIRICAL] This top-10 pass removed 136 raw backlink suggestions in one phase (283 -> 147).
- [EMPIRICAL] The remaining unresolved suggestions for touched targets align with deliberate NO decisions, not missed edits.
- [PROJECT] This phase worked best when treated as “architectural triage,” not “make every symmetric backlink exist.”
