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
- Questions, usage examples, and feedback: use GitHub Discussions when enabled

## Pull request guidelines

Please keep pull requests focused and include:

1. A short summary of the change
2. Why the change is needed
3. What you tested
4. Any docs or wiki updates that were included

## Local data and privacy

Do not commit:

- personal paths
- user-specific `.local.json` files
- cloned wiki content under `wiki/`, `daily/`, `raw/`, or `reports/`
- edits to global files like `~/.claude/settings.json` or `~/.codex/hooks.json`

Use the tracked `.example` and `.template` files as the public version of local config.

## Quality gates

Required local gate before proposing a merge:

- `python scripts/doctor.py --quick`
- `python scripts/wiki_cli.py lint`

Recommended manual pre-merge check:

- `python scripts/doctor.py --full`

Advisory knowledge review:

- `python scripts/wiki_cli.py lint --full`

The contradiction review in `lint --full` is non-deterministic and must not be used as a merge gate.
