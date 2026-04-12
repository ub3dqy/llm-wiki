# LLM Wiki Project Instructions

This repository is a global knowledge base for Claude Code and Codex.

Start every non-trivial task by reading [CLAUDE.md](CLAUDE.md). It defines:

- wiki schema and page formats
- ingest / compile / query / lint workflows
- hook behavior and scaling strategy

## Wiki-First Rules

1. Before proposing architecture or implementation changes, check whether the wiki already contains a relevant decision or concept.
2. Prefer updating existing wiki pages over creating duplicates.
3. Keep claims traceable to sources.
4. After meaningful changes to hooks, config, or workflows, run verification commands.

## Preferred Commands

Use the repo scripts instead of ad hoc commands where possible:

```bash
uv run python scripts/wiki_cli.py status
uv run python scripts/wiki_cli.py rebuild
uv run python scripts/lint.py --structural-only
python scripts/doctor.py
```

## Codex Notes

- Codex hooks in this repo are designed for WSL.
- If Codex runs inside WSL, verify `codex_hooks = true` in `~/.codex/config.toml`.
- Use `python scripts/doctor.py` to smoke-test SessionStart and UserPromptSubmit before trusting a new setup.

## Important Files

- [CLAUDE.md](CLAUDE.md)
- [README.md](README.md)
- [codex-hooks.template.json](codex-hooks.template.json)
- [docs/codex-integration-plan.md](docs/codex-integration-plan.md)
