# Source Drift Review Ledger

Durable ledger for explicit source-drift maintenance runs.
Entries created by tooling are pending manual review until a human records a decision.
Do not use this ledger as automatic evidence for `reviewed:` frontmatter.

## 2026-05-01T04:53:17+00:00 — scan pending review

- Mode: export-only (validator state not saved)
- Domain filter: all
- Source article filter: python-docs
- Checked URL references: 1
- Lint issue rows: 1
- Actionable review rows: 1
- Review state: pending manual review

### Status Counts

- drift: 1

### Review Queue

| Status | Source | URL | Detail | Review decision |
|---|---|---|---|---|
| drift | sources/python-docs.md | https://docs.python.org/3/ | ETag changed (stored: '"69ece5fd-458a"', current: '"69f3d52b-458a"') | checked 2026-05-01: root still identifies as Python 3.14.4; upstream build timestamp changed; no article content update and no `reviewed:` stamp |
