# README actuality review — 2026-04-16

## Findings

### 1. README describes the required gate incorrectly after the merged repo-hygiene sequence

The README still says the required blocking gate is:

- `uv run python scripts/doctor.py --quick`
- `uv run python scripts/wiki_cli.py lint`

See [README.md](/mnt/e/project/memory%20claude/memory%20claude/README.md#L322).

That is no longer the actual enforced CI contract. The live workflow now runs:

- `scripts/rebuild_index.py --check`
- `scripts/lint.py --structural-only`
- `ruff check --select I scripts/ hooks/`
- `ruff format --check scripts/ hooks/`
- AST syntax check

See [wiki-lint.yml](/mnt/e/project/memory%20claude/memory%20claude/.github/workflows/wiki-lint.yml#L27).

Impact:

- contributors reading the README get the wrong picture of what CI will actually reject
- the README also omits the new Ruff gates that were the whole point of PRs `#35` and `#38`
- `pre-commit` is mentioned in the heading even though the current enforced gate is CI-only

Recommended fix:

- rewrite the "Gate roles" subsection to match current reality
- separate "actual CI workflow" from "recommended local checks"

### 2. The README misdescribes the Codex Stop hook

The hook flow table still says:

- `Stop` -> "Reminds about `/wiki-save` when architectural decisions detected"

See [README.md](/mnt/e/project/memory%20claude/memory%20claude/README.md#L178).

That is true for the Claude-side `hooks/stop-wiki-reminder.py`, but not for Codex. The Codex Stop hook now does transcript capture and spawns `flush.py` through a detached worker.

See:

- [README.md](/mnt/e/project/memory%20claude/memory%20claude/README.md#L261)
- [stop.py](/mnt/e/project/memory%20claude/memory%20claude/hooks/codex/stop.py#L1)
- [codex-hooks.template.json](/mnt/e/project/memory%20claude/memory%20claude/codex-hooks.template.json)

Impact:

- a reader evaluating Codex support gets a materially wrong model of how capture works
- the README underplays the most important recent change in Codex reliability: Stop is not just a reminder path anymore

Recommended fix:

- either split the hook table into "Claude hooks" and "Codex hooks"
- or add a note that `Stop` differs by runtime: Claude = reminder, Codex = capture worker

### 3. The "Live snapshot" block is stale enough to mislead

The README still presents this as a real active-use snapshot:

- `Articles: 97`
- `sources: 51`
- `Last compile: 2026-04-14...`
- `Total cost: $8.81`

See [README.md](/mnt/e/project/memory%20claude/memory%20claude/README.md#L62).

Current real output is already different:

```text
Wiki Status:
  Articles: 158 (analyses: 3, concepts: 48, connections: 4, entities: 2, sources: 100, top-level: 1)
  Projects: memory-claude (114), messenger (22), office (13), personal (8), untagged (3)
  Daily logs: 7 (today: 21 entries)
  Last compile: 2026-04-15T18:41:06+00:00
  Last lint: 2026-04-16T06:58:23+00:00
  Total cost: $12.87
```

Impact:

- low technical risk
- medium documentation risk, because the section is explicitly framed as a live repo snapshot, not a historical example

Recommended fix:

- either refresh the block with current output
- or relabel it as an example snapshot from an earlier date

### 4. The "What makes this different" table is slightly behind the current architecture

The comparison table says knowledge capture is:

- `SessionEnd + PreCompact + PostToolUse async (real-time)`

See [README.md](/mnt/e/project/memory%20claude/memory%20claude/README.md#L154).

That is incomplete now that Codex has a real `Stop` capture path in addition to reminder-only Stop behavior on the Claude side.

Impact:

- low severity
- mostly a product-positioning/documentation drift issue

Recommended fix:

- update the row so it does not erase the Codex Stop capture path

## Open questions / assumptions

- I treated this as a documentation review, not an edit task.
- I did not audit external comparison claims (`claude-mem`, `coleam00`) against their latest upstream state; this review is only about README vs current local repo state.

## Summary

README is mostly fine at the top-level pitch level, but it is no longer fully current operationally.

The two places worth fixing first are:

1. the gate/CI section
2. the Codex Stop hook description

The live snapshot should also be refreshed or explicitly marked historical.
