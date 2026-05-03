# Source Drift Policy — 2026-04-27

## Status

Adopted for `memory-claude` maintenance after user authorization on 2026-04-27.

This policy is docs-only. It does not reset `scripts/state.json`, does not mark pages as
`reviewed`, and does not close any source-drift backlog automatically.

## Current Baseline

Current cached validator state in `scripts/state.json`:

```text
total validators: 427
drift: 131
rot: 0
unverifiable: 161
baseline_captured: 102
no_drift: 20
network_error: 8
access_denied: 5
```

Top drift domains:

```text
docs.python.org: 34
peps.python.org: 18
docs.docker.com: 12
developers.openai.com: 10
learn.microsoft.com: 8
git-scm.com: 7
hatch.pypa.io: 5
packaging.python.org: 5
pre-commit.com: 4
socket.io: 4
```

Interpretation: this is an advisory source-review backlog, not evidence of link rot. `rot=0` means
there is no current source-disappearance emergency. `drift=131` means validator metadata changed
since baseline capture and needs review batching.

## Decisions

1. Source-drift remains advisory-only. It must not be part of CI, pre-commit, `doctor --quick`, or
   any blocking merge gate.
2. No automatic baseline reset. A validator change can indicate real upstream changes, CDN
   behaviour, or noisy validators. Resetting without review hides useful signal.
3. No automatic `reviewed` stamping. The `reviewed` field remains human/manual evidence that the
   wiki article was read against the current source.
4. `scripts/state.json` is not durable backlog. The current implementation updates validator values
   as it checks URLs, so the durable evidence is the lint report and this policy, not the mutable
   cache alone.
5. Drift closure requires a human/source-review decision per batch or per URL. A later clean
   validator result is not enough to claim the related wiki page is current.

## Operating Cadence

Run `--source-drift` only when explicitly requested or during scheduled maintenance. Default cadence:

```text
weekly: optional source-drift snapshot if the project is actively maintained
monthly: normal source-review batch
immediate: only for rot, high-stakes official docs, or a user-requested dependency/API update
```

Do not run it as an interactive reflex. The command is network-dependent and can take minutes across
hundreds of URLs.

## Required Snapshot Protocol

Before every new `--source-drift` run:

1. Record current `git status --short`.
2. Record validator status counts from `scripts/state.json`.
3. Run the command only with explicit intent.
4. Preserve the generated `reports/lint-YYYY-MM-DD.md` or copy the source-drift section into a
   dated task note.
5. Record post-run counts and changed top domains.

Rationale: because `scripts/state.json` is mutable and gitignored, a run can overwrite the only
machine-readable evidence unless a report/snapshot is preserved.

When a run should produce durable run evidence, add `--ledger`. This appends a pending-review
entry to `docs/codex-tasks/source-drift-review-ledger.md` with status counts and actionable
`drift`/`rot`/`refused` rows. Ledger entries are not automatic human review evidence and must not
be used to stamp `reviewed:`.

## Triage Rules

`rot`:

Treat as P1. Manually open the URL or a canonical replacement. Update the source article if the URL
is dead or moved. If the source cannot be recovered, mark the article status appropriately and add a
replacement/source note.

`drift`:

Batch by domain and documentation family. Review official docs domains first when they influence
current code or API guidance. Update wiki content only when the upstream change materially affects
claims in the article.

`unverifiable`:

Not backlog. Keep as context only unless the source is high-stakes or the user explicitly asks for
current verification.

`access_denied`:

Not backlog by itself. Use browser/manual verification only when the related article is needed for
a current answer or implementation.

`network_error`:

Retry in a later scheduled run. Do not edit wiki pages from transient network failures.

`baseline_captured`:

No action until the next comparison run.

`no_drift`:

No action.

## Batch Order

1. Official language/runtime docs with many drift hits: `docs.python.org`, `peps.python.org`.
2. Platform/runtime docs used for active project decisions: Docker, Microsoft, OpenAI, Git.
3. Tooling docs used in repo workflows: Hatch, Packaging, pre-commit, Socket.IO.
4. Singletons and low-impact sources.
5. Unverifiable/access-denied/network-error only when needed by a live task.

## Definition Of Done For A Drift Batch

A batch can be marked reviewed only when:

1. Each selected drift URL has been manually checked or intentionally skipped with a reason.
2. Affected wiki/source articles were updated if upstream changes materially changed claims.
3. `reviewed` is updated only when a human/manual review actually happened.
4. A dated note records reviewed URLs, decisions, and any skipped noisy validators.
5. No baseline reset was used as a substitute for review.

## Future Tooling Backlog

These are useful but not required for this policy to be active:

1. Consider domain-specific validator rules only after manual evidence shows repeatable noise.

Implemented on 2026-04-30:

- `scripts/lint.py --source-drift --domain <host>` limits checks to one exact source URL host.
- `scripts/lint.py --source-drift --export-only` writes a dated `reports/source-drift-*.md`
  snapshot without saving updated validator state.
- `scripts/lint.py --source-drift --source-article sources/<slug>.md` limits checks to one
  source article.
- `scripts/lint.py --source-drift` prints per-reference progress lines during network scans.
- `scripts/lint.py --source-drift --ledger` appends a durable pending-review entry to
  `docs/codex-tasks/source-drift-review-ledger.md`.

## Next Action

Do not run a full source-drift scan immediately. The next implementation step should stay small:
use the ledger for a scoped `docs.python.org` review batch, then consider domain-specific validator
rules only if manual evidence shows repeatable noise.
