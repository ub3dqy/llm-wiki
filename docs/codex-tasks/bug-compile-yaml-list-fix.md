# Bug fix — compile list-form `project:` frontmatter breaks rebuild_index idempotency

**Version**: v5 (2026-04-23; v4 → v5 Codex execution-round-1 discovered blocker F9: PDC baseline was wrong. Plan claimed `test ! -s /tmp/pdc_post.txt` (empty), but `docs/codex-tasks/wiki-freshness-phase1.md` line 556 genuinely contains an illustrative bullet with `C:\Users` inside a bulletpoint about what NOT to store — a documentation artifact, not a real data leak. CI workflow `.github/workflows/personal-data-check.yml:21` uses PCRE `grep -lP 'C:\\\\Users'` (matches literal `C:\Users`) and also matches this file. My planning-audit Round 1 and Round 2 Windows-grep was silently falling back to BRE/ERE where `\\Users` semantics differ, so I got empty and codified the wrong baseline. v5 restores the v1 expected-hit baseline (allowlist of that single pre-existing file) AND switches the plan command to PCRE (`-lP`) to match CI exactly. All v4-applied changes (Change 1 in utils.py, Change 2 + 3 tests) are already on disk per Codex execution-round-1 report, so this revision is plan-level only; Codex will re-verify PDC with the corrected command.)
**Planning audit**: `bug-compile-yaml-list-fix-planning-audit.md` (sibling)
**Report template**: `bug-compile-yaml-list-fix-report.md` (sibling)
**Background memo**: `bug-compile-yaml-list-project-frontmatter.md` (sibling) — incident record from iter-5 P1 execution.
**Governing contract**: `docs/claude-system-operating-contract.md`
**Executor**: Codex
**Predecessor**: master HEAD (P1 wiki-health closed)

---

## §1 — Why this plan exists

During P1 wiki-health iter-5 execution, `scripts/compile.py` (via Claude Agent SDK) produced `wiki/connections/tool-enforcement-dual-failure.md` with YAML-list frontmatter:

```yaml
project: [codex-easy-start, site-tiretop, workflow]
```

`scripts/rebuild_index.py` then became non-idempotent: successive rebuilds produced strictly different `index.md` outputs, and `doctor --quick index_health` flipped to FAIL. Codex worked around it by hand-editing the article to scalar form `project: codex-easy-start, site-tiretop, workflow`. This plan fixes the underlying parsing bug so that downstream code tolerates both frontmatter forms.

Evidence trail: planning-audit §3 (code reads), §5 (grep surveys), §6 (empirical reproductions Test 1 and Test 2).

---

## §2 — Hierarchy of truth sources

Per `docs/claude-system-operating-contract.md`:

1. Official docs — N/A this cycle (no external library claim; see planning-audit §4 justification).
2. User's explicit instructions — "продолжай но про кодекса не забывай" + «вперед по очереди».
3. Factual tool/test results — planning-audit §6 Test 1 and Test 2.
4. Agreed project documents — planning-audit sections §3, §5, §7.
5. Project memory files — contextual only.

---

## §3 — Doc Verification

Not applicable this cycle. See planning-audit §4.

---

## §4 — Pre-flight verification (Codex-executed)

### Step P1 — Git baseline (capture snapshot for delta check)

```bash
cd "/mnt/e/Project/memory claude/memory claude"
git rev-parse HEAD
git status --short | sort > /tmp/git_status_pre.txt
cat /tmp/git_status_pre.txt
git diff --ignore-cr-at-eol --stat > /tmp/git_diffstat_pre.txt
cat /tmp/git_diffstat_pre.txt
```

**NOTE (Codex-review-round-1 finding F1)**: The repo on HEAD `bd68edc` already has pre-existing unrelated modifications (e.g., `AGENTS.md`, `CLAUDE.md`, `scripts/rebuild_index.py`, `scripts/wiki_cli.py` as reported by Codex). The Phase 2 whitelist check is a **delta** against `/tmp/git_status_pre.txt`, NOT an absolute check. This means: anything that was modified before P1 stays tolerated; only changes beyond the pre-snapshot count as scope creep.

### Step P2 — Read target files in full (no grep substitute)

- `scripts/utils.py` — lines 1-305 (especially 223, 226-242, 253-261, 274-283)
- `scripts/rebuild_index.py` — lines 1-239 (especially 24, 88-92, 95-126)
- `scripts/query.py` — full (confirm degraded-but-not-broken behaviour per planning-audit §10 Gap-A)
- `scripts/wiki_cli.py` — lines 1-end (identify call sites of `build_article_metadata_map` — transitive consumer at lines 28, 49)
- `tests/test_utils.py` — full (existing `fake_wiki` fixture pattern + parametrize style)
- `tests/test_rebuild_index.py` — full (existing `enrich_index_line` unit tests + style)
- `tests/conftest.py` — full (it is a one-docstring file with no fixtures — confirm rather than assume)
- `pyproject.toml` — full (confirm `pythonpath = ["scripts", "hooks"]`, ruff + mypy config)

### Step P3 — Baseline test + lint state

```bash
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run pytest tests/ --tb=short -q > /tmp/pytest_pre.txt 2>&1
tail -3 /tmp/pytest_pre.txt

UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run ruff check scripts/ tests/ > /tmp/ruff_pre.txt 2>&1
tail -5 /tmp/ruff_pre.txt
```

Record `pre_test_count`, `pre_ruff_issues` in report §2.

**NOTE (Codex-review-round-1 finding F2)**: mypy is intentionally NOT part of this plan's gate. `pyproject.toml:12-16` declares only `ruff` and `pytest` in `[dependency-groups].dev`; `mypy` is not installed in the dev env. Earlier planning-audit claim "mypy 0 errors" came from Claude's Windows host where mypy happens to be available separately — not a reliable signal for Codex's WSL uv env. Installing mypy into dev deps is a separate decision out of this fix's scope. Ruff alone satisfies AGENTS.md "lint" requirement for this patch.

### Step P4 — Confirm bug reproduction (independent check)

```bash
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run python -c "
import sys, tempfile, pathlib
sys.path.insert(0, 'scripts')
from utils import get_article_projects
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / 'a.md'
    p.write_text('---\ntitle: T\ntype: concept\nproject: [a, b, c]\n---\nbody\n', encoding='utf-8')
    print(get_article_projects(p))
"
# Expected PRE: ['[a', 'b', 'c]']   (bug reproduced — bracket chars leak)
```

### Step P5 — Survey wiki for any on-disk list-form articles (Gap-C check)

```bash
grep -rE '^project:\s*\[' wiki/ daily/ 2>/dev/null || true
# Expected: empty or a few known normalised files. If any list-form article is found,
# record its path — it becomes an additional natural test subject for Phase 2.
```

---

## §5 — Whitelist (strict)

### MAY modify

- `scripts/utils.py` — **one function only**: `get_article_projects` (lines 274-283). One-line body change routing through `parse_frontmatter_list`.
- `tests/test_utils.py` — **append** a new parametrized test `test_get_article_projects_handles_list_and_scalar`.
- `tests/test_rebuild_index.py` — **append** two tests (NO monkeypatch, NO importlib.reload, NO sys.path hack — follows existing file style):
  - `test_enrich_index_line_idempotent_only_for_clean_projects` — unit-level on `enrich_index_line` directly (contract for that function).
  - `test_list_form_frontmatter_end_to_end_stays_idempotent` — integration through disk → `get_article_projects` → `enrich_index_line` (this is the one that breaks if `scripts/utils.py:274-283` is reverted — addresses Codex-review-round-1 finding F4).

### MUST NOT modify

- `scripts/compile.py` — prompt/LLM behaviour out-of-scope (planning-audit §10 Gap-B).
- `scripts/rebuild_index.py` — its logic is correct once projects are well-parsed.
- `scripts/wiki_cli.py` — transitive consumer (calls `build_article_metadata_map` via utils); benefits from the fix automatically. No direct edit.
- `scripts/query.py` — degraded-but-functional (Gap-A).
- `scripts/lint.py` — no new check this cycle (Gap-D).
- `wiki/`, `daily/`, `index.md`, `log.md`, `reports/`, `raw/` — gitignored wiki-content layer.
- `CLAUDE.md`, `AGENTS.md`, `docs/` (except the 3 handoff files in `docs/codex-tasks/bug-compile-yaml-list-fix*.md`).
- `pyproject.toml`, `.github/`, `hooks/`, `dashboard/`, `agent-mailbox/`.

---

## §6 — Change N specs

### Change 1 — `scripts/utils.py::get_article_projects`

**Current** (lines 274-283, verbatim):

```python
def get_article_projects(path: Path) -> list[str]:
    """Return list of project tags from article frontmatter.

    Handles both 'project: foo' and 'project: foo, bar' formats.
    """
    fm = parse_frontmatter(path)
    raw = fm.get("project", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]
```

**Target**:

```python
def get_article_projects(path: Path) -> list[str]:
    """Return list of project tags from article frontmatter.

    Handles all three frontmatter shapes:
      - 'project: foo'
      - 'project: foo, bar'
      - 'project: [foo, bar]'   (YAML list form, possibly quoted)

    Delegates to ``parse_frontmatter_list`` so bracket/quote stripping
    stays consistent with other frontmatter-list consumers.
    """
    fm = parse_frontmatter(path)
    return parse_frontmatter_list(fm.get("project", ""))
```

Rationale:
- `parse_frontmatter_list` (same module, lines 253-261) is the canonical helper and is already parametrized-tested (`tests/test_utils.py::test_parse_frontmatter_list`).
- All three shape cases validated in planning-audit §6 Test 1.
- Scalar-input behaviour identical to current; list-input behaviour newly correct.

### Change 2 — `tests/test_utils.py` — regression test for `get_article_projects`

Append a new function AFTER `test_parse_frontmatter_list` (ends at line 83). Add `get_article_projects` to the `from utils import (...)` block at the top of the file, keeping alphabetical order already used there.

```python
@pytest.mark.parametrize(
    "frontmatter_value, expected",
    [
        pytest.param("[codex-easy-start, site-tiretop, workflow]",
                     ["codex-easy-start", "site-tiretop", "workflow"], id="list-form-unquoted"),
        pytest.param("codex-easy-start, site-tiretop, workflow",
                     ["codex-easy-start", "site-tiretop", "workflow"], id="scalar-csv"),
        pytest.param("memory-claude", ["memory-claude"], id="scalar-single"),
        pytest.param("", [], id="empty"),
        pytest.param('["a", "b"]', ["a", "b"], id="list-form-quoted"),
    ],
)
def test_get_article_projects_handles_list_and_scalar(
    tmp_path: Path, frontmatter_value: str, expected: list[str]
) -> None:
    article = tmp_path / "a.md"
    article.write_text(
        f"---\ntitle: T\ntype: concept\nproject: {frontmatter_value}\n---\nbody\n",
        encoding="utf-8",
    )
    assert get_article_projects(article) == expected
```

Rationale: the 5 cases mirror planning-audit §6 Test 1. Failure re-exposes the bracket-leak regression.

### Change 3 — `tests/test_rebuild_index.py` — idempotency regression at unit level

Append at end of file. Mirror existing style (direct import from `rebuild_index`, no monkeypatch, no importlib.reload, no sys.path hack — the `pyproject.toml` `pythonpath = ["scripts"]` handles imports).

```python
def test_enrich_index_line_idempotent_only_for_clean_projects() -> None:
    """Unit-level contract for ``enrich_index_line``.

    Broken projects (stray bracket chars baked into strings) cause
    ``enrich_index_line`` to GROW annotations on successive passes, because
    ``strip_existing_annotations`` only peels one `[...]` layer and the
    double-bracket case `[[a, b, c]]` leaves inner brackets behind. Clean
    projects stay idempotent.

    This test pins the function's own contract. It does NOT on its own
    guard the upstream ``get_article_projects`` fix — for that, see
    ``test_list_form_frontmatter_end_to_end_stays_idempotent``.
    """
    original = "- [[concepts/foo]] — Foo"

    broken_projects = ["[a", "b", "c]"]
    meta_broken = {
        "concepts/foo": {"projects": broken_projects, "word_count": 100, "title": "Foo"},
    }
    pass1_broken = enrich_index_line(original, meta_broken)
    pass2_broken = enrich_index_line(pass1_broken, meta_broken)
    assert pass1_broken != pass2_broken, (
        "Broken projects must expose non-idempotency in enrich_index_line. "
        "If pass1 == pass2 for broken input, enrich_index_line has been changed "
        "to swallow bracket chars — the contract fix belongs upstream in "
        "get_article_projects, not here."
    )

    clean_projects = ["a", "b", "c"]
    meta_clean = {
        "concepts/foo": {"projects": clean_projects, "word_count": 100, "title": "Foo"},
    }
    pass1_clean = enrich_index_line(original, meta_clean)
    pass2_clean = enrich_index_line(pass1_clean, meta_clean)
    pass3_clean = enrich_index_line(pass2_clean, meta_clean)
    assert pass1_clean == pass2_clean == pass3_clean, (
        "Clean projects must stabilise after the first enrich pass."
    )


def test_list_form_frontmatter_end_to_end_stays_idempotent(tmp_path) -> None:
    """Integration guard against reverting ``scripts/utils.py::get_article_projects``.

    Flow: on-disk article with ``project: [a, b, c]`` frontmatter
        → ``get_article_projects`` (must strip brackets, returning clean strings)
        → meta dict
        → ``enrich_index_line`` (must stay idempotent since input is clean).

    If someone reverts ``get_article_projects`` back to naive split(","),
    projects come out as ``['[alpha', 'beta', 'gamma]']`` and
    ``enrich_index_line`` starts growing ``[[alpha, beta, gamma]] [[...]] ...``
    — this test fails loudly on both the second-pass inequality AND the
    explicit double-bracket probe.

    Note on import: ``get_article_projects`` is imported inside the function
    body to keep the module-level imports in this test file narrow and
    rebuild_index-focused; pytest's pythonpath configuration
    (``pyproject.toml`` ``pythonpath = ["scripts"]``) makes that import work
    without sys.path manipulation.
    """
    from utils import get_article_projects

    article = tmp_path / "foo.md"
    article.write_text(
        "---\ntitle: Foo\ntype: concept\nproject: [alpha, beta, gamma]\n---\n\nbody\n",
        encoding="utf-8",
    )
    projects = get_article_projects(article)
    assert projects == ["alpha", "beta", "gamma"], (
        f"get_article_projects regressed: expected clean list, got {projects!r}"
    )

    meta = {"concepts/foo": {"projects": projects, "word_count": 10, "title": "Foo"}}
    line = "- [[concepts/foo]] — Foo"
    pass1 = enrich_index_line(line, meta)
    pass2 = enrich_index_line(pass1, meta)
    pass3 = enrich_index_line(pass2, meta)

    assert "[[alpha" not in pass1 and "gamma]]" not in pass1, (
        f"Double-bracket annotation detected in enriched line: {pass1!r}"
    )
    assert pass1 == pass2 == pass3, (
        "End-to-end pipeline must be idempotent for list-form `project:` frontmatter."
    )
```

Rationale:
- **Unit-level test** pins `enrich_index_line`'s contract (broken-in → non-idempotent-out, clean-in → idempotent-out). Does NOT on its own catch a revert of `get_article_projects` — honest framing per Codex-review-round-1 finding F4.
- **Integration test** closes the loop: tempfile with list-form frontmatter → `get_article_projects` → meta → `enrich_index_line`. A revert of `scripts/utils.py:274-283` makes `get_article_projects` return bracket-leaked strings, which then fail either the `["alpha", "beta", "gamma"]` assert or the `"[[alpha" not in pass1` assert (and the second/third pass inequality).
- Mirrors existing file style: direct imports, `tmp_path` fixture already used elsewhere in the suite, no monkeypatch ceremony.

---

## §7 — Verification phases

### Phase 1 — Codex pre-flight (see §4)

Record raw outputs of Steps P1-P5 in report §2 verbatim.

### Phase 2 — Post-change verification

```bash
# Bug reproduction POST (must be clean):
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run python -c "
import sys, tempfile, pathlib
sys.path.insert(0, 'scripts')
from utils import get_article_projects
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / 'a.md'
    p.write_text('---\ntitle: T\ntype: concept\nproject: [a, b, c]\n---\nbody\n', encoding='utf-8')
    print(get_article_projects(p))
"
# Expected POST: ['a', 'b', 'c']

# Full pytest:
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run pytest tests/ --tb=short -q > /tmp/pytest_post.txt 2>&1
tail -5 /tmp/pytest_post.txt
# Expected: pre_test_count + 7 passed, 0 failed
# Math: 5 parametrized cases (test_get_article_projects_handles_list_and_scalar) + 2 discrete
# (test_enrich_index_line_idempotent_only_for_clean_projects, test_list_form_frontmatter_end_to_end_stays_idempotent)

# Focused run on new tests (all three — unit + parametrized + integration):
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run pytest tests/test_utils.py::test_get_article_projects_handles_list_and_scalar \
                tests/test_rebuild_index.py::test_enrich_index_line_idempotent_only_for_clean_projects \
                tests/test_rebuild_index.py::test_list_form_frontmatter_end_to_end_stays_idempotent \
                --tb=long -v
# Expected 7 total pytest nodes: 5 parametrized cases + 2 discrete.

# Ruff (AGENTS.md mandatory lint):
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run ruff check scripts/ tests/ > /tmp/ruff_post.txt 2>&1
tail -5 /tmp/ruff_post.txt
# Expected: same or fewer issues vs pre_ruff_issues; 0 new issues

# (mypy intentionally skipped — not in dev deps per pyproject.toml:12-16; see §4 Step P3 note)

# Doctor sanity — must remain unchanged in class-level outcomes:
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run python scripts/wiki_cli.py doctor --quick > /tmp/doctor_post.txt 2>&1
grep -E '^\[(PASS|FAIL)\]' /tmp/doctor_post.txt
# Expected: index_health PASS; structural_lint may remain FAIL only for residual known items;
# flush_pipeline_correctness unchanged (Bug H stream).

# Transitive-consumer smoke (wiki_cli.py also consumes build_article_metadata_map):
UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy \
  uv run python scripts/wiki_cli.py status > /tmp/wiki_cli_status.txt 2>&1
tail -10 /tmp/wiki_cli_status.txt
# Expected: exits 0, summary-style output with article counts.

# PDC detector — MUST use PCRE (-lP) to match CI workflow .github/workflows/personal-data-check.yml:21
# exactly. Note the CI's `C:\\\\Users` double-escape is bash-level; inside the shell string below it
# reaches grep as the PCRE pattern `C:\\Users` which matches the literal `C:\Users`.
git ls-files -z | grep -zv 'personal-data-check.yml' \
  | xargs -0 grep -lP '/mnt/[a-z]/[A-Z]|[A-Z]:/[A-Z]|C:\\\\Users' | sort > /tmp/pdc_post.txt

# Expected baseline: one pre-existing documentation-artifact hit, tolerated:
#   docs/codex-tasks/wiki-freshness-phase1.md   (line 556 illustrates what NOT to store)
# Any other path means new PDC leak.
diff /tmp/pdc_post.txt <(printf '%s\n' "docs/codex-tasks/wiki-freshness-phase1.md") > /tmp/pdc_delta.txt || true
test ! -s /tmp/pdc_delta.txt || { echo "FAIL: PDC set differs from expected baseline"; cat /tmp/pdc_delta.txt; exit 1; }

# Git status delta (absolute-whitelist check would fail on pre-existing unrelated mods; use delta vs pre-snapshot):
git status --short | sort > /tmp/git_status_post.txt
diff /tmp/git_status_pre.txt /tmp/git_status_post.txt > /tmp/git_status_delta.txt || true
cat /tmp/git_status_delta.txt

# Expected delta (lines added in POST but not in PRE) limited to these paths:
#   scripts/utils.py                                    (M — if was clean; or same M that was already there untouched)
#   tests/test_utils.py                                 (M)
#   tests/test_rebuild_index.py                         (M)
#   docs/codex-tasks/bug-compile-yaml-list-fix*.md      (?? or M — already untracked pre-existing; OK if delta shows nothing new for them)
# No other path may appear in the `> ` side of the diff. Any new line prefixed `> ` outside this list = scope creep.
awk '/^> /{sub(/^> ...\s*/,"",$0); print}' /tmp/git_status_delta.txt | sort -u > /tmp/git_delta_paths.txt
grep -vE '^(scripts/utils\.py|tests/test_utils\.py|tests/test_rebuild_index\.py|docs/codex-tasks/bug-compile-yaml-list-fix.*\.md)$' /tmp/git_delta_paths.txt > /tmp/git_delta_unexpected.txt || true
test ! -s /tmp/git_delta_unexpected.txt || { echo "FAIL: unexpected paths in git status delta"; cat /tmp/git_delta_unexpected.txt; exit 1; }
```

### Phase 3 — Awaits user (commit/push decision only)

No user action during execution. After successful Phase 2, Codex reports with:
- git diff --stat + git status delta file
- pytest tail
- ruff tail
- PRE/POST reproduction outputs
- doctor class-level diff
- wiki_cli.py status output

Claude reviews + runs local verification (independent Windows env). If clean → surface to user for commit decision. No push without explicit user command.

---

## §8 — Acceptance criteria

Hard gates (all must hold):
- [ ] `get_article_projects` returns `['a', 'b', 'c']` for list-form (Phase 2 reproduction).
- [ ] All 5 parametrized cases in `test_get_article_projects_handles_list_and_scalar` pass.
- [ ] `test_enrich_index_line_idempotent_only_for_clean_projects` passes (both broken-not-idempotent and clean-idempotent branches).
- [ ] `test_list_form_frontmatter_end_to_end_stays_idempotent` passes (integration through `get_article_projects` → `enrich_index_line`).
- [ ] Full pytest: `pre_test_count + 7` passed, 0 failed.
- [ ] `ruff check scripts/ tests/`: 0 new issues vs pre_ruff_issues.
- [ ] `doctor --quick`: `index_health` PASS; no new FAILs.
- [ ] `wiki_cli.py status` exits 0 cleanly.
- [ ] **Git status delta** (`diff /tmp/git_status_pre.txt /tmp/git_status_post.txt`): added lines limited to whitelisted paths only (`/tmp/git_delta_unexpected.txt` is empty).
- [ ] PDC detector output equals the expected pre-existing allowlist (`diff /tmp/pdc_post.txt <(printf '%s\n' "docs/codex-tasks/wiki-freshness-phase1.md")` is empty).

Soft gates (document, do not block):
- compile.py unchanged (Gap-B).
- query.py unchanged (Gap-A).
- lint.py unchanged (Gap-D).

---

## §9 — Out of scope

- `scripts/compile.py` prompt/SDK — parsing-side fix chosen (Gap-B).
- `scripts/query.py` direct `project:` read — degraded-but-functional (Gap-A).
- `scripts/lint.py` `project:` shape check — deferred (Gap-D).
- Wiki content normalization — already done in iter-5 P1.
- Other frontmatter fields (`sources:`, `tags:`) — scoped to `project:` only.
- Bug H / P2 freshness — separate streams.

---

## §10 — Rollback

```bash
git checkout -- scripts/utils.py tests/test_utils.py tests/test_rebuild_index.py
```

No wiki-content mutation — no filesystem-only rollback needed.

---

## §11 — Discrepancy checkpoints (STOP + report)

- **D1**: Phase 1 Step P3 `pre_test_count` ≠ 84 → record new count, proceed.
- **D2**: Phase 1 Step P4 reproduction does NOT output `['[a', 'b', 'c]']` → STOP; upstream may have fixed independently or env diverges; notify Claude.
- **D3**: Phase 1 Step P5 finds list-form articles in `wiki/` or `daily/` — record path, note as additional natural test subject in report §2.5. Not a blocker.
- **D4**: `test_enrich_index_line_idempotent_only_for_clean_projects` fails on broken-branch assert (`pass1 == pass2` for broken projects) → STOP; someone has changed `enrich_index_line` to swallow bracket chars (test's second message explains).
- **D5**: pytest shows any regression (not just new passes) → STOP with failing test names + stderr.
- **D6**: `doctor --quick` post-fix introduces any new FAIL class → STOP with diff.
- **D7**: `git status` **delta** vs `/tmp/git_status_pre.txt` adds paths outside the whitelist (`/tmp/git_delta_unexpected.txt` non-empty) → STOP, revert. (Pre-existing unrelated modifications stay tolerated — this is a delta check per Codex-review-round-1 finding F1.)
- **D8**: PDC detector set differs from the expected allowlist (single pre-existing path `docs/codex-tasks/wiki-freshness-phase1.md`). Any NEW path = data-leak scope creep → STOP, investigate. Losing the pre-existing path is not a block, but record it in report. Use PCRE `-lP` to mirror CI workflow exactly (ERE/BRE silently differ on backslash semantics — that was the v4 baseline mis-read).
- **D9**: `ruff check` post-count exceeds pre_ruff_issues → STOP, investigate.

---

## §12 — Self-audit checklist

- [x] Plan cites planning-audit rows for every state claim.
- [x] Whitelist strict; explicit MUST NOT list.
- [x] Out-of-scope lists the 4 gaps from planning-audit §10.
- [x] Discrepancy checkpoints: 9 items.
- [x] Acceptance criteria path-scoped AND delta-scoped (file list + test count + lint + mypy).
- [x] Rollback specified.
- [x] No claims from training data. No context7 claim (disconnected this session).
- [x] Commit strategy below.
- [x] audit-round-1 findings applied (Change 3 rewrite, sys.path removal, PDC baseline, ruff, wiki_cli in blast radius, conftest claim correction).
- [x] Codex-review-round-1 findings applied (F1 delta git gate, F2 mypy dropped, F3 sibling v1→v3 sync, F4 integration test added + Change 3 rationale tightened).
- [x] Codex-review-round-2 findings applied (F5 pytest delta +3→+7 everywhere, F6 focused pytest includes integration test, F7 report Change 3 split into two subsections, F8 report §4.4.5 dedicated wiki_cli slot, minor D1-D8→D1-D9).
- [x] Codex-execution-round-1 finding F9 applied (PDC baseline corrected from empty to single pre-existing allowlist; command switched to PCRE `-lP` for CI parity).

---

## §13 — Notes for Codex

- WSL env: `UV_PROJECT_ENVIRONMENT=$HOME/.cache/llm-wiki/.venv UV_LINK_MODE=copy uv run ...`. Claude saw iter-5 discrepancy on `$HOME` vs `/root/.cache` — use whichever resolves on your WSL home; record in report §2 if differs.
- Claude Agent SDK NOT invoked — no API cost.
- Wiki gitignored — do NOT mutate.
- Shared filesystem — cross-env verification trivial.
- After completion, send mailbox reply in a new thread `bug-compile-yaml-list-fix` referencing this plan.

---

## §14 — Commits strategy

Single commit:

```
fix(utils): tolerate list-form project: frontmatter in get_article_projects

Restores rebuild_index.py idempotency when a wiki article has
`project: [a, b, c]` YAML-list frontmatter. The prior naive
.split(",") leaked bracket chars into project names, producing
`[[...]]` double-bracket annotations that strip_existing_annotations
could not fully remove — making successive rebuilds diverge.

Fix routes get_article_projects through the existing
parse_frontmatter_list helper (which already handles list/scalar/
quoted/whitespace cases).

Adds two regression tests:
- test_utils.py::test_get_article_projects_handles_list_and_scalar
- test_rebuild_index.py::test_enrich_index_line_idempotent_only_for_clean_projects

Observed during 2026-04-22 wiki-health P1 iter-5 compile run;
Codex worked around it by manually normalising the offending article.
See docs/codex-tasks/bug-compile-yaml-list-fix.md for plan.
```

No split. No push. Commit only on explicit user command after review.
