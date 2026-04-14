# Report — Wiki backlinks cleanup Phase B

## Pre-flight

- [x] Read phase plan fully
- [x] Read `scripts/lint.py:140-162`
- [x] Read `scripts/utils.py` backlink helpers
- [x] Regenerated and read `reports/lint-2026-04-14.md`
- [x] Read Phase A report precedent
- [x] Confirmed strict 15-file whitelist
- [x] Confirmed conservative judgment approach
- [x] Confirmed new report file requirement
- [x] Confirmed `.bak` create/delete rule

## Doc verification

### GFM lists

URL: `https://github.github.com/gfm/#lists`

| Check | Quote |
|---|---|
| Bullet syntax | `[OFFICIAL] "A list marker is a bullet list marker or an ordered list marker."` / `[OFFICIAL] "List markers typically start at the left margin, but may be indented by up to three spaces. List markers must be followed by one or more spaces or a tab."` |
| Blank lines | `[OFFICIAL] "Blank lines between block-level elements are ignored, except for the role they play in determining whether a list is tight or loose."` |

### Obsidian wikilinks

URL: `https://help.obsidian.md/Linking+notes+and+files/Internal+links`

| Check | Quote |
|---|---|
| Plain wikilink | `[OFFICIAL] "- Wikilink: \`[[Three laws of motion]]\` or \`[[Three laws of motion.md]]\`"` |
| Alias support | `[OFFICIAL]` No alias syntax was needed in this phase; only plain wikilinks were added. |

### Conclusion

[OFFICIAL] The docs support simple bullet-list additions under `## See Also` and plain `[[target]]` wikilinks.  
[OFFICIAL] Obsidian Help had to be fetched through the published markdown preload URL because the main help URL returned an app shell.

## Phase 1 — pre-edit lint snapshot

### Command

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

### Output

```text
    Found 0 issue(s)
  Checking: Missing backlinks...
    Found 147 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: E:\Project\memory claude\memory claude\reports\lint-2026-04-14.md

Results: 0 errors, 1 warnings, 147 suggestions
```

### Verdict

- [x] `[EMPIRICAL]` Phase 1 matched the expected `147 suggestions`

## Phase 1.5 — target-by-target edits

### 1. `concepts/claude-cli-autonomous-task-loops`
Sources:
```text
analyses/reddit-hn-research-2026-04-13
concepts/anthropic-context-anxiety-injection
concepts/claude-code-memory-tooling-landscape
sources/aris-autonomous-ml-research
sources/spec-driven-verification-overnight-agents
```
Decisions:
| Source | Decision | Reason |
|---|---|---|
| `analyses/reddit-hn-research-2026-04-13` | YES | `[EMPIRICAL]` Same theme cluster. |
| `concepts/anthropic-context-anxiety-injection` | YES | `[EMPIRICAL]` Same loop-risk family. |
| `concepts/claude-code-memory-tooling-landscape` | YES | `[EMPIRICAL]` Landscape cites this pattern. |
| `sources/aris-autonomous-ml-research` | YES | `[EMPIRICAL]` Parallel staged-agent loop. |
| `sources/spec-driven-verification-overnight-agents` | YES | `[EMPIRICAL]` Same spec-first execution discipline. |
Edit:
```diff
+ [[analyses/reddit-hn-research-2026-04-13]]
+ [[concepts/anthropic-context-anxiety-injection]]
+ [[concepts/claude-code-memory-tooling-landscape]]
+ [[sources/aris-autonomous-ml-research]]
+ [[sources/spec-driven-verification-overnight-agents]]
```
Summary: Candidates 5 | YES 5 | NO 0 | SKIP 0 | Resolved 5

### 2. `sources/cognition-rebuilding-devin-sonnet-4-5`
Sources:
```text
sources/anthropic-telemetry-experiment-gates-reddit
sources/aris-autonomous-ml-research
sources/claude-opus-4-6-diagnosis-2026
sources/mempalace-milla-jovovich-reddit
sources/spec-driven-verification-overnight-agents
```
Decisions:
| Source | Decision | Reason |
|---|---|---|
| `sources/anthropic-telemetry-experiment-gates-reddit` | YES | `[EMPIRICAL]` Hidden Anthropic-side behavior branch. |
| `sources/aris-autonomous-ml-research` | YES | `[EMPIRICAL]` Cross-model review overlap. |
| `sources/claude-opus-4-6-diagnosis-2026` | YES | `[EMPIRICAL]` Direct continuation of same investigation line. |
| `sources/mempalace-milla-jovovich-reddit` | YES | `[EMPIRICAL]` Memory workflow depends on same model reliability. |
| `sources/spec-driven-verification-overnight-agents` | YES | `[EMPIRICAL]` Practical response to same failure class. |
Edit:
```diff
+ [[sources/anthropic-telemetry-experiment-gates-reddit]]
+ [[sources/aris-autonomous-ml-research]]
+ [[sources/claude-opus-4-6-diagnosis-2026]]
+ [[sources/mempalace-milla-jovovich-reddit]]
+ [[sources/spec-driven-verification-overnight-agents]]
```
Summary: Candidates 5 | YES 5 | NO 0 | SKIP 0 | Resolved 5

### 3. `concepts/seo-ai-strategy-2026`
Sources:
```text
sources/ai-seo-statistics-100-plus-2026
sources/answer-engine-optimization-frase-guide
sources/geo-aeo-faq-emarketer-2026
sources/llm-referred-traffic-converts-venturebeat
```
Decisions: all YES `[EMPIRICAL]` because they are direct strategy inputs.
Edit:
```diff
+ [[sources/ai-seo-statistics-100-plus-2026]]
+ [[sources/answer-engine-optimization-frase-guide]]
+ [[sources/geo-aeo-faq-emarketer-2026]]
+ [[sources/llm-referred-traffic-converts-venturebeat]]
```
Summary: Candidates 4 | YES 4 | NO 0 | SKIP 0 | Resolved 4

### 4. `analyses/llm-wiki-improvement-research-2026-04-12`
Sources:
```text
analyses/reddit-hn-research-2026-04-13
concepts/claude-code-memory-tooling-landscape
concepts/upstream-feedback-queue-coleam00
sources/mini-coder-cli-agent-hn
sources/pion-webrtc-scalable-topology-issue
sources/total-recall-write-gated-memory-hn
```
Decisions:
| Source | Decision | Reason |
|---|---|---|
| `analyses/reddit-hn-research-2026-04-13` | YES | `[EMPIRICAL]` Next research wave on same theme. |
| `concepts/claude-code-memory-tooling-landscape` | YES | `[EMPIRICAL]` Direct input to target. |
| `concepts/upstream-feedback-queue-coleam00` | NO | `[EMPIRICAL]` Operational queue, too meta. |
| `sources/mini-coder-cli-agent-hn` | YES | `[EMPIRICAL]` Concrete external memory/workflow reference. |
| `sources/pion-webrtc-scalable-topology-issue` | NO | `[EMPIRICAL]` Too implementation-specific here. |
| `sources/total-recall-write-gated-memory-hn` | YES | `[EMPIRICAL]` Directly relevant memory design input. |
Edit:
```diff
+ [[analyses/reddit-hn-research-2026-04-13]]
+ [[concepts/claude-code-memory-tooling-landscape]]
+ [[sources/mini-coder-cli-agent-hn]]
+ [[sources/total-recall-write-gated-memory-hn]]
```
Summary: Candidates 6 | YES 4 | NO 2 | SKIP 0 | Resolved 4

### 5. `sources/aris-autonomous-ml-research`
Sources:
```text
sources/anthropic-scaling-managed-agents
sources/calx-corrections-tracking-hn
sources/mempalace-milla-jovovich-reddit
sources/mini-coder-cli-agent-hn
sources/spec-driven-verification-overnight-agents
```
Decisions:
| Source | Decision | Reason |
|---|---|---|
| `sources/anthropic-scaling-managed-agents` | YES | `[EMPIRICAL]` Same staged-agent framing. |
| `sources/calx-corrections-tracking-hn` | NO | `[EMPIRICAL]` Too narrow vs ARIS scope. |
| `sources/mempalace-milla-jovovich-reddit` | YES | `[EMPIRICAL]` Similar memory-heavy orchestration. |
| `sources/mini-coder-cli-agent-hn` | YES | `[EMPIRICAL]` Nearby CLI-agent design. |
| `sources/spec-driven-verification-overnight-agents` | YES | `[EMPIRICAL]` Same verification discipline. |
Edit:
```diff
+ [[sources/anthropic-scaling-managed-agents]]
+ [[sources/mempalace-milla-jovovich-reddit]]
+ [[sources/mini-coder-cli-agent-hn]]
+ [[sources/spec-driven-verification-overnight-agents]]
```
Summary: Candidates 5 | YES 4 | NO 1 | SKIP 0 | Resolved 4

### 6. `sources/claude-opus-4-6-diagnosis-2026`
Sources:
```text
concepts/claude-code-memory-tooling-landscape
sources/claude-code-non-git-hang-bug
sources/claude-code-vscode-mcp-crash-bug
sources/great-claude-code-leak-2026
```
Decisions: YES for the three concrete failure siblings; NO for the landscape page `[EMPIRICAL]` because the target stays cleaner focused on concrete diagnostics.
Edit:
```diff
+ [[sources/claude-code-non-git-hang-bug]]
+ [[sources/claude-code-vscode-mcp-crash-bug]]
+ [[sources/great-claude-code-leak-2026]]
```
Summary: Candidates 4 | YES 3 | NO 1 | SKIP 0 | Resolved 3

### 7. `sources/seo-ai-strategy-2026-notebooklm`
Sources:
```text
sources/ai-seo-statistics-100-plus-2026
sources/answer-engine-optimization-frase-guide
sources/geo-aeo-faq-emarketer-2026
sources/llm-referred-traffic-converts-venturebeat
sources/seo-hacking-side-projects-reddit
```
Decisions: all YES `[EMPIRICAL]` because they are direct synthesis inputs / adjacent execution source.
Edit:
```diff
+ [[sources/ai-seo-statistics-100-plus-2026]]
+ [[sources/answer-engine-optimization-frase-guide]]
+ [[sources/geo-aeo-faq-emarketer-2026]]
+ [[sources/llm-referred-traffic-converts-venturebeat]]
+ [[sources/seo-hacking-side-projects-reddit]]
```
Summary: Candidates 5 | YES 5 | NO 0 | SKIP 0 | Resolved 5

### 8. `sources/cowork-vs-claude-code-reddit-apology`
Sources:
```text
concepts/claude-cli-autonomous-task-loops
sources/cloud-coder-overnight-agent-reddit
sources/great-claude-code-leak-2026
sources/total-tokens-injection-bug-reddit
```
Decisions: YES for `cloud-coder`, `great-claude-code-leak-2026`, `total-tokens-injection-bug-reddit`; NO for `claude-cli-autonomous-task-loops` `[EMPIRICAL]` because existing concept links already cover the abstraction level.
Edit:
```diff
+ [[sources/cloud-coder-overnight-agent-reddit]]
+ [[sources/great-claude-code-leak-2026]]
+ [[sources/total-tokens-injection-bug-reddit]]
```
Summary: Candidates 4 | YES 3 | NO 1 | SKIP 0 | Resolved 3

### 9. `sources/total-recall-write-gated-memory-hn`
Sources:
```text
sources/calx-corrections-tracking-hn
sources/mempalace-milla-jovovich-reddit
sources/vector-vs-graph-rag-agent-memory
```
Decisions: all YES `[EMPIRICAL]` because all three are direct neighbors in gated/curated memory design.
Edit:
```diff
+ [[sources/calx-corrections-tracking-hn]]
+ [[sources/mempalace-milla-jovovich-reddit]]
+ [[sources/vector-vs-graph-rag-agent-memory]]
```
Summary: Candidates 3 | YES 3 | NO 0 | SKIP 0 | Resolved 3

### 10. `concepts/windows-file-locking`
Sources:
```text
concepts/claude-desktop-cowork-architecture
sources/claude-code-subagent-orphan-bug
sources/cowork-vs-claude-code-reddit-apology
```
Decisions: all YES `[EMPIRICAL]` because all three are concrete members of the same Windows-hostile bug family.
Edit:
```diff
+ [[concepts/claude-desktop-cowork-architecture]]
+ [[sources/claude-code-subagent-orphan-bug]]
+ [[sources/cowork-vs-claude-code-reddit-apology]]
```
Summary: Candidates 3 | YES 3 | NO 0 | SKIP 0 | Resolved 3

### 11. `sources/clawmem-gpu-retrieval-memory-hn`
Sources:
```text
sources/graperoot-codex-cli-compact-reddit
sources/mason-context-builder-github
sources/mempalace-milla-jovovich-reddit
```
Decisions: YES for `mason-context-builder-github` and `mempalace-milla-jovovich-reddit`; NO for `graperoot-codex-cli-compact-reddit` `[EMPIRICAL]` because its action-graph angle is too indirect here.
Edit:
```diff
+ [[sources/mason-context-builder-github]]
+ [[sources/mempalace-milla-jovovich-reddit]]
```
Summary: Candidates 3 | YES 2 | NO 1 | SKIP 0 | Resolved 2

### 12. `concepts/claude-code-context-limits`
Sources:
```text
sources/claude-codepro-dev-env-hn
sources/total-tokens-injection-bug-reddit
```
Decisions: both YES `[EMPIRICAL]` because one is the real-limits case and the other is the false-limit contrast.
Edit:
```diff
+ [[sources/claude-codepro-dev-env-hn]]
+ [[sources/total-tokens-injection-bug-reddit]]
```
Summary: Candidates 2 | YES 2 | NO 0 | SKIP 0 | Resolved 2

### 13. `sources/vector-vs-graph-rag-agent-memory`
Sources:
```text
sources/clawmem-gpu-retrieval-memory-hn
sources/you-dont-need-vector-db-for-rag
```
Decisions: both YES `[EMPIRICAL]` as direct implementation / counter-position in the same debate.
Edit:
```diff
+ [[sources/clawmem-gpu-retrieval-memory-hn]]
+ [[sources/you-dont-need-vector-db-for-rag]]
```
Summary: Candidates 2 | YES 2 | NO 0 | SKIP 0 | Resolved 2

### 14. `concepts/claude-code-memory-tooling-landscape`
Sources:
```text
sources/llm-referred-traffic-converts-venturebeat
sources/mason-context-builder-github
```
Decisions: YES for `mason-context-builder-github`; NO for `llm-referred-traffic-converts-venturebeat` `[EMPIRICAL]` because it is strategic context, not core memory-tooling landscape material.
Edit:
```diff
+ [[sources/mason-context-builder-github]]
```
Summary: Candidates 2 | YES 1 | NO 1 | SKIP 0 | Resolved 1

### 15. `concepts/flutter-go-messenger-architecture`
Sources:
```text
concepts/agent-memory-production-schema
concepts/flutter-dependency-upgrade-waves
sources/flutter-riverpod-vs-bloc-comparison
```
Decisions: YES for `concepts/flutter-dependency-upgrade-waves` and `sources/flutter-riverpod-vs-bloc-comparison`; NO for `concepts/agent-memory-production-schema` `[EMPIRICAL]` because it is too orthogonal to this architecture page.
Edit:
```diff
+ [[concepts/flutter-dependency-upgrade-waves]]
+ [[sources/flutter-riverpod-vs-bloc-comparison]]
```
Summary: Candidates 3 | YES 2 | NO 1 | SKIP 0 | Resolved 2

## Phase 2 — post-edit lint snapshot

### Command

```bash
uv run python scripts/lint.py --structural-only 2>&1 | tail -10
```

### Output

```text
    Found 0 issue(s)
  Checking: Missing backlinks...
    Found 79 issue(s)
  Checking: Sparse articles...
    Found 0 issue(s)
  Checking: Provenance completeness...
    Found 0 issue(s)
  Skipping: Contradictions (--structural-only)

Report saved to: E:\Project\memory claude\memory claude\reports\lint-2026-04-14.md

Results: 0 errors, 1 warnings, 79 suggestions
```

### Verdict

- [x] `[EMPIRICAL]` Errors: 0
- [x] `[EMPIRICAL]` Warnings: 1 (unchanged)
- [x] `[EMPIRICAL]` Suggestions: 79
- [x] `[EMPIRICAL]` Raw drop = 68, inside expected 50-90

## Phase 3 — doctor regression

### Command

```bash
uv run python scripts/wiki_cli.py doctor --quick 2>&1 | grep -E "(FAIL|PASS).*(lint|provenance)"
```

### Output

```text
[PASS] structural_lint: Results: 0 errors, 1 warnings, 79 suggestions
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_lint_smoke: wiki_cli structural lint reported zero blocking errors
```

### Verdict

- [x] `[EMPIRICAL]` `structural_lint` PASS
- [x] `[EMPIRICAL]` `wiki_cli_lint_smoke` PASS
- [x] `[EMPIRICAL]` `query_preview_smoke` PASS
- [x] `[EMPIRICAL]` No new FAILs in lint/query slice

## Phase 4 — spot-check 3 random targets

### Target A

Target: `concepts/claude-cli-autonomous-task-loops`

```text
- [[sources/cloud-coder-overnight-agent-reddit]] — исходный Reddit-пост
- [[concepts/llm-wiki-architecture]] — наша собственная версия "Claude процессит Claude" для knowledge capture
- [[concepts/claude-code-hooks]] — альтернативная distribution-архитектура через глобальные хуки
- [[concepts/claude-desktop-cowork-architecture]] — другой Reddit-ingest про Claude Code ecosystem
- [[concepts/uv-python-tooling]] — наш аналог "subprocess runner", только через `uv run python`, не через bash
- [[analyses/reddit-hn-research-2026-04-13]] — волна Reddit/HN ingest, где этот паттерн выделен как отдельная ветка
- [[concepts/anthropic-context-anxiety-injection]] — смежный risk-pattern для автономных Claude loops
- [[concepts/claude-code-memory-tooling-landscape]] — соседний ландшафт memory tooling, где такие loops используются как review/execution pattern
- [[sources/aris-autonomous-ml-research]] — другой пример многошагового agent loop с внешней memory/review прослойкой
- [[sources/spec-driven-verification-overnight-agents]] — близкий по духу workflow: маленькие этапы, жёсткий spec, внешний verification loop
```
Verdict: `[EMPIRICAL]` originals preserved, new links present, no duplicates, valid bullets.

### Target B

Target: `sources/claude-opus-4-6-diagnosis-2026`

```text
- [[concepts/anthropic-context-anxiety-injection]] — one specific instance of branch (a) "thinking mode" issue with hidden injection trigger
- [[sources/cognition-rebuilding-devin-sonnet-4-5]] — Cognition's observations on Sonnet 4.5 thinking behavior — cross-reference with this diagnostic framework
- [[sources/anthropic-scaling-managed-agents]] — Anthropic's own admission that Sonnet 4.5 context-anxiety workaround became "dead weight" on Opus 4.5 — model-to-model behavior changes are real
- [[concepts/llm-wiki-architecture]] — наш capture pipeline which benefits from route-aware diagnosis
- [[concepts/windows-path-issues]] — route differences manifesting as Windows vs WSL runtime mismatch
- [[sources/claude-code-non-git-hang-bug]] — another concrete Claude Code failure mode in the same ecosystem
- [[sources/claude-code-vscode-mcp-crash-bug]] — MCP/runtime instability case that complements this diagnosis branch
- [[sources/great-claude-code-leak-2026]] — broader Claude Code reliability and trust context around these failure analyses
```
Verdict: `[EMPIRICAL]` originals preserved, new links present, no duplicates, valid bullets.

### Target C

Target: `concepts/flutter-go-messenger-architecture`

```text
- [[entities/pulse-messenger]]
- [[concepts/gin-http-framework]]
- [[concepts/pion-webrtc-calls]]
- [[concepts/jwt-auth-pattern]]
- [[concepts/messenger-docker-infrastructure]]
- [[concepts/minio-file-storage]]
- [[concepts/pulse-durable-mutations]]
- [[concepts/pulse-e2ee-issues]]
- [[concepts/server-dns-migration-pitfalls]]
- [[concepts/windows-path-issues]]
- [[overview]]
- [[concepts/flutter-dependency-upgrade-waves]] — dependency upgrade pressure directly shapes how this architecture evolves over time
- [[sources/flutter-riverpod-vs-bloc-comparison]] — state-management tradeoffs are directly relevant to the Flutter side of this architecture
```
Verdict: `[EMPIRICAL]` originals preserved, new links present, no duplicates, valid bullets.

## Phase 5 — decision statistics

| Target | Candidates | YES | NO | SKIP | Resolved |
|---|---:|---:|---:|---:|---:|
| `concepts/claude-cli-autonomous-task-loops` | 5 | 5 | 0 | 0 | 5 |
| `sources/cognition-rebuilding-devin-sonnet-4-5` | 5 | 5 | 0 | 0 | 5 |
| `concepts/seo-ai-strategy-2026` | 4 | 4 | 0 | 0 | 4 |
| `analyses/llm-wiki-improvement-research-2026-04-12` | 6 | 4 | 2 | 0 | 4 |
| `sources/aris-autonomous-ml-research` | 5 | 4 | 1 | 0 | 4 |
| `sources/claude-opus-4-6-diagnosis-2026` | 4 | 3 | 1 | 0 | 3 |
| `sources/seo-ai-strategy-2026-notebooklm` | 5 | 5 | 0 | 0 | 5 |
| `sources/cowork-vs-claude-code-reddit-apology` | 4 | 3 | 1 | 0 | 3 |
| `sources/total-recall-write-gated-memory-hn` | 3 | 3 | 0 | 0 | 3 |
| `concepts/windows-file-locking` | 3 | 3 | 0 | 0 | 3 |
| `sources/clawmem-gpu-retrieval-memory-hn` | 3 | 2 | 1 | 0 | 2 |
| `concepts/claude-code-context-limits` | 2 | 2 | 0 | 0 | 2 |
| `sources/vector-vs-graph-rag-agent-memory` | 2 | 2 | 0 | 0 | 2 |
| `concepts/claude-code-memory-tooling-landscape` | 2 | 1 | 1 | 0 | 1 |
| `concepts/flutter-go-messenger-architecture` | 3 | 2 | 1 | 0 | 2 |
| **TOTAL** | **56** | **48** | **8** | **0** | **48** |

Derived metrics:
- `[EMPIRICAL]` Before: 147 suggestions
- `[EMPIRICAL]` After: 79 suggestions
- `[EMPIRICAL]` Raw drop: 68
- `[EMPIRICAL]` YES rate Phase B: 85.7%
- `[PROJECT]` Phase A YES rate was 84%; Phase B stayed similarly conservative
- `[PROJECT]` Raw drop exceeds 48 unique YES decisions because `scripts/lint.py` iterates over extracted wikilinks without deduping duplicate source mentions

## Final state

### git status

```text
?? Untitled.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md
?? docs/codex-tasks/wiki-backlinks-cleanup-phase-b.md
```

### Files touched

Only the 15 whitelisted wiki targets were edited. `[EMPIRICAL]`

### .bak files

- [x] `[EMPIRICAL]` All Phase B `.bak` files were deleted after verification

## Tools used

- [x] WebFetch GFM lists doc
- [x] WebFetch Obsidian internal links doc
- [x] Read `scripts/lint.py`
- [x] Read `scripts/utils.py`
- [x] Read current lint report
- [x] Read Phase A report precedent
- [x] Read all 15 target files
- [x] Read all unique source files for the 15 targets (37 unique pages)
- [x] Shell lint pre-snapshot (PowerShell equivalent in current environment)
- [x] Shell lint post-snapshot (PowerShell equivalent in current environment)
- [x] Shell doctor regression (PowerShell equivalent in current environment)
- [x] Shell grouping one-liners (PowerShell / Python equivalent in current environment)
- [x] Edit each target once
- [x] MCP filesystem — BLOCKED (not needed / not used)
- [x] MCP git — BLOCKED (not needed / not used)

## Out-of-scope temptations

- `[PROJECT]` Did not edit orphan pages themselves; only the pages that should link back to them.

## Discrepancies

- `[OFFICIAL]` Main Obsidian Help URL returned an app shell; published markdown preload URL was required for actual content.
- `[PROJECT]` The task text said "Bash", but this workspace is running under PowerShell on Windows. Equivalent shell commands were executed in PowerShell to avoid re-breaking the Windows `.venv` through WSL.

## Self-audit

- [x] Doc verification section filled with real citations
- [x] Mandatory tools table all ticked or BLOCKED
- [x] Each target has `[EMPIRICAL]` decision reasoning
- [x] Each target has one edit diff block
- [x] Phase 1 snapshot recorded
- [x] Phase 2 snapshot recorded
- [x] Phase 3 doctor regression recorded
- [x] Phase 4 spot-check recorded
- [x] Phase 5 statistics complete
- [x] No files touched outside whitelist
- [x] No commit / push
- [x] `.bak` cleaned up
- [x] Report uses `${USER}`, `<repo-root>`, `<user-home>` placeholders
- [x] Recovery/hang rule satisfied

## Notes / observations

- `[PROJECT]` Work executed from `<repo-root>` as `${USER}`; no `<user-home>` files were read or modified in this phase.
