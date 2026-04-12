# Contributing to LLM Wiki

Thanks for helping improve LLM Wiki.

## Before you open an issue

Please check these in order:

1. Read the relevant section in [README.md](README.md).
2. Run the bootstrap and quick checks locally:
   - `uv run python scripts/setup.py`
   - `uv run python scripts/doctor.py --quick`
3. Search existing issues and discussions to avoid duplicates.

## Where to ask what

- Bug or broken behavior: open a bug report issue
- Installation or onboarding problem: open an installation issue
- New idea or improvement: open a feature request
- Questions, usage examples, and feedback: use GitHub Discussions
  (or the "use case" issue form if Discussions are not active in this repo)

## Pull request guidelines

Please keep pull requests focused and include:

1. A short summary of the change
2. Why the change is needed
3. What you tested
4. Any docs or wiki updates that were included

## Local data and privacy

Do not commit:

- personal paths
- user-specific `.local.json` files (e.g. `scripts/project_aliases.local.json`)
- `.env` (local configuration overrides — use `.env.example` as the public template)
- cloned wiki content under `wiki/`, `daily/`, `raw/`, or `reports/`
- edits to your own `~/.claude/settings.json` or `~/.codex/hooks.json`
  (those are per-machine and must not be pushed upstream)

Use the tracked `.example` and `.template` files as the public version of local config.

## Quality gates

Required local gate before proposing a merge:

- `uv run python scripts/doctor.py --quick`
- `uv run python scripts/wiki_cli.py lint`

Recommended manual pre-merge check:

- `uv run python scripts/doctor.py --full` — includes the end-to-end
  `flush_roundtrip` check that simulates SessionEnd with a dummy transcript
  and verifies the full `session-end -> flush.py` chain runs in test mode.

Advisory knowledge review:

- `uv run python scripts/wiki_cli.py lint --full`

The contradiction review in `lint --full` is non-deterministic and must not be used as a merge gate.

## Related documents

- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community expectations
- [SECURITY.md](SECURITY.md) — how to report vulnerabilities privately
- [SUPPORT.md](SUPPORT.md) — where to get help
