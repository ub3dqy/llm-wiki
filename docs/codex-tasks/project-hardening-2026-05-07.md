# Project Hardening Pass — 2026-05-07

## Scope

This pass addressed repository hygiene issues found during a deep project review:

- Replaced the shell-only Personal Data Check workflow with `scripts/personal_data_check.py`.
- Added unit coverage for personal-path detection and Codex Stop worker runtime spawning.
- Redacted historical tracked task docs that contained real local repo/home paths, replacing them with `${REPO_ROOT}` or `${HOME}`.
- Aligned `hooks/codex/stop.py` with the shared `runtime_utils.build_uv_python_cmd()` path used by the other capture hooks.
- Broadened CI syntax checks from a hand-maintained Python file list to all tracked `*.py` files.
- Added `tests/` to CI Ruff check/format coverage.
- Stopped ignoring `uv.lock` so dependency resolution can be reviewed and reproduced from the repository.
- Ignored `.pytest-tmp*/` so broken local pytest temp directories do not make `git status` noisy.
- Replaced a non-ASCII profiler output marker with ASCII `~=` to avoid Windows console encoding failures.

## Verification

- `scripts/personal_data_check.py` — PASS, no personal local paths found.
- `ruff check scripts hooks tests` — PASS.
- `ruff format --check scripts hooks tests` — PASS.
- `pytest -q` — PASS, 143 tests.
- `scripts/rebuild_index.py --check` — PASS.
- `scripts/lint.py --structural-only` — PASS, 0 errors / 0 warnings / 933 suggestions.
- `scripts/doctor.py --quick` — PASS.
- `scripts/doctor.py --full` — PASS.
- Dynamic AST syntax check — PASS for all tracked Python files.
- `uv lock --check` — PASS, resolved 40 packages.
- `git diff --check` — PASS.

## Notes

- Some old `.pytest-tmp-codex*` directories can remain physically present and inaccessible on Windows. They are local ignored artifacts and no longer affect `git status`.
- Structural lint still reports advisory freshness/backlink suggestions; they are non-blocking under the current gate contract.
