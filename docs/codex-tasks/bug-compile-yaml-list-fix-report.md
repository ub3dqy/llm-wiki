# Execution Report — bug-compile-yaml-list-fix

**Plan**: `bug-compile-yaml-list-fix.md` (sibling) v5
**Planning audit**: `bug-compile-yaml-list-fix-planning-audit.md` (sibling)
**Executor**: Codex
**Started**: `2026-04-23T20:05:02Z`
**Completed**: `2026-04-23T20:26:30Z`
**Status**: `passed`

---

## §1 — Code-authority reads (verbatim quotes)

### `scripts/utils.py` lines 253-283
```python
def parse_frontmatter_list(raw_value: str) -> list[str]:
    """Parse a loose frontmatter list representation into plain items."""
    text = (raw_value or "").strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    parts = [part.strip().strip("'\"") for part in text.split(",")]
    return [part for part in parts if part]


def frontmatter_sources_include_prefix(raw_sources: str, prefix: str) -> bool:
    """Return True if a parsed frontmatter source entry starts with the prefix."""
    normalized_prefix = prefix.strip()
    if not normalized_prefix:
        return False
    return any(
        source.startswith(normalized_prefix) for source in parse_frontmatter_list(raw_sources)
    )


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

### `scripts/rebuild_index.py` lines 88-126
```python
def strip_existing_annotations(line: str) -> str:
    """Remove previously-added [project] (Nw) or (Nw) suffixes for idempotent rebuilds."""
    line = _ANNOTATION_RE.sub("", line)
    line = _ANNOTATION_WORDCOUNT_ONLY_RE.sub("", line)
    return line


def enrich_index_line(line: str, meta: dict[str, dict]) -> str:
    """Enrich one index.md line with [project] (Nw) annotations.

    Lines without [[wikilinks]] or not starting with '- [[' are returned unchanged.
    """
    stripped = line.rstrip()
    if not stripped.startswith("- [["):
        return line

    # Clean any existing annotations first
    clean = strip_existing_annotations(stripped)

    # Extract slug from wikilink
    m = _WIKILINK_RE.search(clean)
    if not m:
        return line

    slug = m.group(1)
    info = meta.get(slug)
    if not info:
        return line

    # Build annotation
    projects = info.get("projects", [])
    word_count = info.get("word_count", 0)

    suffix = ""
    if projects:
        suffix += f" [{', '.join(projects)}]"
    suffix += f" ({word_count}w)"

    return clean + suffix
```

### `scripts/query.py` (relevant `project` usage)
```python
    fm = parse_frontmatter_from_text(raw)
    rel = path.relative_to(WIKI_DIR)
    slug = str(rel).replace("\\", "/").replace(".md", "")
    title = fm.get("title", "")
    tags = fm.get("tags", "")
    project = fm.get("project", "")
    body = strip_frontmatter(raw)[:1200]

    title_text = title.lower()
    slug_text = slug.replace("-", " ").replace("_", " ").lower()
    meta_text = f"{tags} {project}".lower()
    body_text = body.lower()
```

### `tests/test_utils.py` — where new test is inserted
```python
@pytest.mark.parametrize(
    "raw,expected",
    [
        pytest.param("[foo, bar, baz]", ["foo", "bar", "baz"], id="bracketed"),
        pytest.param("foo, bar", ["foo", "bar"], id="unbracketed"),
        pytest.param("['quoted', 'items']", ["quoted", "items"], id="single-quoted"),
        pytest.param('["double", "quoted"]', ["double", "quoted"], id="double-quoted"),
        pytest.param("", [], id="empty"),
        pytest.param("  ", [], id="whitespace-only"),
    ],
)
def test_parse_frontmatter_list(raw: str, expected: list[str]) -> None:
    assert parse_frontmatter_list(raw) == expected


@pytest.mark.parametrize(
    "frontmatter_value,expected",
    [
        pytest.param(
            "[codex-easy-start, site-tiretop, workflow]",
            ["codex-easy-start", "site-tiretop", "workflow"],
            id="list-form-unquoted",
        ),
        pytest.param(
            "codex-easy-start, site-tiretop, workflow",
            ["codex-easy-start", "site-tiretop", "workflow"],
            id="scalar-csv",
        ),
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

### `tests/test_rebuild_index.py` — where new tests are inserted
```python
    assert "### p14\n" in result
    assert "### p15 (1 articles)\n" in result
    assert "### p16 (1 articles)\n" in result


def test_enrich_index_line_idempotent_only_for_clean_projects() -> None:
    """Unit-level contract for ``enrich_index_line``.

    Broken projects (stray bracket chars baked into strings) cause
    ``enrich_index_line`` to grow annotations on successive passes, because
    ``strip_existing_annotations`` only peels one `[...]` layer and the
    double-bracket case `[[a, b, c]]` leaves inner brackets behind. Clean
    projects stay idempotent.

    This test pins the function's own contract. It does NOT on its own
    guard the upstream ``get_article_projects`` fix.
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
        "to swallow bracket chars."
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
    """Guard against reverting ``get_article_projects`` back to naive split."""
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

### `tests/conftest.py`
```python
"""Pytest fixtures and configuration for LLM Wiki tests.

Per pyproject.toml [tool.pytest.ini_options] pythonpath = ["scripts"],
test modules can `from utils import X` directly without sys.path hacks.

Fixtures for first PR live inside test_utils.py. Shared fixtures can migrate
here in Tier 4.1 when more test modules are added.
"""
```

---

## §2 — Pre-flight outputs

### Step P1 — Git baseline
```
bd68edc75c900ae4ea63fa2b4626d5f089aa7396
 M .git-blame-ignore-revs
 M .gitignore
 M AGENTS.md
 M CLAUDE.md
 M README.md
 M codex-hooks.template.json
 M docs/claude-plan-creation-procedure.md
 M docs/codex-integration-plan.md
 M docs/codex-tasks/doctor-pipeline-correctness-24h-window.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe-report.md
 M docs/codex-tasks/fix-codex-stop-broken-pipe.md
 M docs/codex-tasks/fix-codex-stop-hook-report.md
 M docs/codex-tasks/fix-codex-stop-hook.md
 M docs/codex-tasks/investigate-flush-agent-sdk-bug-g.md
 M docs/codex-tasks/investigate-flush-py-bug-h-report.md
 M docs/codex-tasks/investigate-flush-py-bug-h.md
 M docs/codex-tasks/post-review-corrections-and-probe-2-report.md
 M docs/codex-tasks/post-review-corrections-and-probe-2.md
 M docs/codex-tasks/readme-actuality-review-2026-04-16.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation-report.md
 M docs/codex-tasks/remove-dead-debug-stderr-instrumentation.md
 M docs/codex-tasks/repo-hygiene-fix-15-baseline-and-broaden-ci-planning-audit.md
 M docs/codex-tasks/repo-hygiene-fix-15-baseline-and-broaden-ci-report.md
 M docs/codex-tasks/repo-hygiene-fix-15-baseline-and-broaden-ci.md
 M docs/codex-tasks/repo-hygiene-opinion-on-claude-proposal.md
 M docs/codex-tasks/repo-hygiene-pr1-dev-extras-report.md
 M docs/codex-tasks/repo-hygiene-pr1-dev-extras.md
 M docs/codex-tasks/repo-hygiene-pr1-discrepancy-optional-deps-vs-dependency-groups.md
 M docs/codex-tasks/repo-hygiene-pr1-v2-blocker-baseline-diff.md
 M docs/codex-tasks/repo-hygiene-pr2-continuation-per-file-ignores.md
 M docs/codex-tasks/repo-hygiene-pr2-continuation-v3-narrow-ignores.md
 M docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort-report.md
 M docs/codex-tasks/repo-hygiene-pr2-ruff-config-isort.md
 M docs/codex-tasks/repo-hygiene-pr3-ci-ruff-check-report.md
 M docs/codex-tasks/repo-hygiene-pr3-ci-ruff-check.md
 M docs/codex-tasks/repo-hygiene-pr4a-ruff-format-style-report.md
 M docs/codex-tasks/repo-hygiene-pr4a-ruff-format-style.md
 M docs/codex-tasks/repo-hygiene-response-to-claude-followup.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation-report.md
 M docs/codex-tasks/revert-bug-h-diagnostic-instrumentation.md
 M docs/codex-tasks/split-codex-stop-light-worker-report.md
 M docs/codex-tasks/split-codex-stop-light-worker.md
 M docs/codex-tasks/split-doctor-flush-capture-health-report.md
 M docs/codex-tasks/split-doctor-flush-capture-health.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-a-report.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-a.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-b-report.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-b.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-c-report.md
 M docs/codex-tasks/wiki-backlinks-cleanup-phase-c.md
 M docs/codex-tasks/wiki-freshness-claude-feedback-review.md
 M docs/codex-tasks/wiki-freshness-phase1-report.md
 M docs/codex-tasks/wiki-freshness-phase1.md
 M docs/codex-tasks/wiki-freshness-phase2-1-stabilization-planning-audit.md
 M docs/codex-tasks/wiki-freshness-phase2-1-stabilization-report.md
 M docs/codex-tasks/wiki-freshness-phase2-1-stabilization.md
 M docs/codex-tasks/wiki-freshness-phase2-1-task-brief-for-claude.md
 M docs/codex-tasks/wiki-freshness-phase2-source-drift-planning-audit.md
 M docs/codex-tasks/wiki-freshness-phase2-source-drift-report.md
 M docs/codex-tasks/wiki-freshness-phase2-source-drift.md
 M docs/codex-tasks/wiki-freshness-phase2-task-brief-for-claude.md
 M docs/codex-tasks/wiki-freshness-preliminary-plan.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline-report.md
 M docs/codex-tasks/wiki-lint-cleanup-and-provenance-discipline.md
 M docs/codex-tasks/wiki-lint-cleanup-d1-continuation.md
 M hooks/codex/post-tool-capture.py
 M hooks/codex/session-start.py
 M hooks/codex/stop.py
 M hooks/codex/user-prompt-wiki.py
 M hooks/hook_utils.py
 M hooks/post-tool-capture.py
 M hooks/pre-compact.py
 M hooks/session-end.py
 M hooks/session-start.py
 M hooks/shared_context.py
 M hooks/stop-wiki-reminder.py
 M hooks/user-prompt-wiki.py
 M index.example.md
 M scripts/compile.py
 M scripts/config.py
 M scripts/flush.py
 M scripts/lint.py
 M scripts/rebuild_index.py
 M scripts/seed.py
 M scripts/setup.py
 M scripts/wiki_cli.py
?? 0
?? codex.tgz
?? docs/claude-system-operating-contract.md
?? docs/codex-tasks/backlog-triage-2026-04-17.md
?? docs/codex-tasks/bug-compile-yaml-list-fix-planning-audit.md
?? docs/codex-tasks/bug-compile-yaml-list-fix-report.md
?? docs/codex-tasks/bug-compile-yaml-list-fix.md
?? docs/codex-tasks/bug-compile-yaml-list-project-frontmatter.md
?? docs/codex-tasks/bug-h-issue-16-tracking-log.md
?? docs/codex-tasks/ci-wiki-lint-trigger-paths-followup-planning-audit.md
?? docs/codex-tasks/ci-wiki-lint-trigger-paths-followup-report.md
?? docs/codex-tasks/ci-wiki-lint-trigger-paths-followup.md
?? docs/codex-tasks/doctor-wiki-cli-subprocess-timeout-tracking.md
?? docs/codex-tasks/tier4.1-test-coverage-rebuild-index-and-hook-utils-planning-audit.md
?? docs/codex-tasks/tier4.1-test-coverage-rebuild-index-and-hook-utils-report.md
?? docs/codex-tasks/tier4.1-test-coverage-rebuild-index-and-hook-utils.md
?? docs/codex-tasks/tier4.2-windows-ci-matrix-planning-audit.md
?? docs/codex-tasks/tier4.2-windows-ci-matrix-report.md
?? docs/codex-tasks/tier4.2-windows-ci-matrix.md
?? docs/codex-tasks/tier4.3-dependabot-actions-planning-audit.md
?? docs/codex-tasks/tier4.3-dependabot-actions-report.md
?? docs/codex-tasks/tier4.3-dependabot-actions.md
?? docs/codex-tasks/tier4.4-doctor-lint-subprocess-timeout-raise-planning-audit.md
?? docs/codex-tasks/tier4.4-doctor-lint-subprocess-timeout-raise-report.md
?? docs/codex-tasks/tier4.4-doctor-lint-subprocess-timeout-raise.md
?? docs/codex-tasks/wiki-agent-tooling-phase-a-consolidated-assessment-2026-04-17.md
?? docs/codex-tasks/wiki-agent-tooling-phase-a-evidence-pack.md
?? docs/codex-tasks/wiki-agent-tooling-plan-memo-2026-04-18.md
?? docs/codex-tasks/wiki-agent-tooling-research-2026-04-17.md
?? docs/codex-tasks/wiki-freshness-phase2-2-observation-window-review.md
?? docs/codex-tasks/wiki-freshness-phase2-2-observation-window.md
?? docs/codex-tasks/wiki-freshness-phase2-2-patterns-report.md
?? docs/codex-tasks/wiki-freshness-phase2-2-patterns.md
?? docs/codex-tasks/wiki-freshness-phase2-2-probe-and-403-report.md
?? docs/codex-tasks/wiki-freshness-phase2-2-probe-and-403.md
?? docs/codex-tasks/wiki-freshness-phase2-2-task-brief-for-claude.md
?? docs/codex-tasks/wiki-health-2026-04-21/
?? docs/codex-tasks/wiki-phase-a0-single-read-refactor-planning-audit.md
?? docs/codex-tasks/wiki-phase-a0-single-read-refactor-report.md
?? docs/codex-tasks/wiki-phase-a0-single-read-refactor.md
?? docs/codex-tasks/wiki-phase-b1-recency-only-fix-planning-audit.md
?? docs/codex-tasks/wiki-phase-b1-recency-only-fix-report.md
?? docs/codex-tasks/wiki-phase-b1-recency-only-fix.md
?? docs/codex-tasks/wiki-phase-b1.5-latency-profile-planning-audit.md
?? docs/codex-tasks/wiki-phase-b1.5-latency-profile-report.md
?? docs/codex-tasks/wiki-phase-b1.5-latency-profile.md
?? docs/codex-tasks/wiki-phase-b2-bm25-body-scoring-planning-audit.md
?? docs/codex-tasks/wiki-phase-b2-bm25-body-scoring-report.md
?? docs/codex-tasks/wiki-phase-b2-bm25-body-scoring.md
?? docs/project-audit-2026-04-16.md
?? docs/workflow-instructions-claude.md
?? docs/workflow-instructions-codex.md
?? docs/workflow-role-distribution.md
 AGENTS.md                              |  27 +++
 CLAUDE.md                              | 393 ++++++++-------------------------
 docs/claude-plan-creation-procedure.md |  75 ++++++-
 3 files changed, 185 insertions(+), 310 deletions(-)
```

### Step P3 — Pytest + ruff baseline
```
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 1.59s
pre_test_count = 84

All checks passed!
pre_ruff_issues = 0
```

### Step P4 — Bug reproduction PRE
```
['[a', 'b', 'c]']
Expected: ['[a', 'b', 'c]']
Observed: ['[a', 'b', 'c]']
Verdict: matches expected
```

### Step P5 — Wiki on-disk list-form articles
```
<empty>
```

### §2.5 — Additional observed list-form articles
- none

---

## §3 — Execution log

### Change 1 — `scripts/utils.py::get_article_projects`

Before/after diff:
```diff
diff --git a/scripts/utils.py b/scripts/utils.py
index af66885..9060e82 100644
--- a/scripts/utils.py
+++ b/scripts/utils.py
@@ -271,16 +271,19 @@ def frontmatter_sources_include_prefix(raw_sources: str, prefix: str) -> bool:
     )


-def get_article_projects(path: Path) -> list[str]:
-    """Return list of project tags from article frontmatter.
-
-    Handles both 'project: foo' and 'project: foo, bar' formats.
-    """
-    fm = parse_frontmatter(path)
-    raw = fm.get("project", "").strip()
-    if not raw:
-        return []
-    return [p.strip() for p in raw.split(",") if p.strip()]
+def get_article_projects(path: Path) -> list[str]:
+    """Return list of project tags from article frontmatter.
+
+    Handles all three frontmatter shapes:
+      - 'project: foo'
+      - 'project: foo, bar'
+      - 'project: [foo, bar]'   (YAML list form, possibly quoted)
+
+    Delegates to ``parse_frontmatter_list`` so bracket/quote stripping
+    stays consistent with other frontmatter-list consumers.
+    """
+    fm = parse_frontmatter(path)
+    return parse_frontmatter_list(fm.get("project", ""))
```

Notes: no deviation from plan beyond preserving the helper-routing change with the docstring wording from the approved v4 target.

### Change 2 — `tests/test_utils.py` new test

Insertion-point rationale:
```
Placed immediately after test_parse_frontmatter_list, because it exercises the same parsing family and keeps the new regression adjacent to the helper coverage it builds on.
```

Full new function block:
```python
@pytest.mark.parametrize(
    "frontmatter_value,expected",
    [
        pytest.param(
            "[codex-easy-start, site-tiretop, workflow]",
            ["codex-easy-start", "site-tiretop", "workflow"],
            id="list-form-unquoted",
        ),
        pytest.param(
            "codex-easy-start, site-tiretop, workflow",
            ["codex-easy-start", "site-tiretop", "workflow"],
            id="scalar-csv",
        ),
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

### Change 3 — `tests/test_rebuild_index.py` two new tests (unit + integration)

No monkeypatch, no importlib.reload, no sys.path hack per plan §6 Change 3.

#### §3.3.a Unit-level test — `test_enrich_index_line_idempotent_only_for_clean_projects`

Pins the contract of `enrich_index_line` itself (broken-in → non-idempotent-out, clean-in → idempotent-out). Does NOT on its own guard the upstream `get_article_projects` fix.

```python
def test_enrich_index_line_idempotent_only_for_clean_projects() -> None:
    """Unit-level contract for ``enrich_index_line``.

    Broken projects (stray bracket chars baked into strings) cause
    ``enrich_index_line`` to grow annotations on successive passes, because
    ``strip_existing_annotations`` only peels one `[...]` layer and the
    double-bracket case `[[a, b, c]]` leaves inner brackets behind. Clean
    projects stay idempotent.

    This test pins the function's own contract. It does NOT on its own
    guard the upstream ``get_article_projects`` fix.
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
        "to swallow bracket chars."
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
```

#### §3.3.b Integration test — `test_list_form_frontmatter_end_to_end_stays_idempotent`

Exercises the full disk → `get_article_projects` → `enrich_index_line` pipeline. A revert of `scripts/utils.py:274-283` makes this test fail on the `projects == ["alpha", "beta", "gamma"]` assert or the `"[[alpha" not in pass1` probe.

```python
def test_list_form_frontmatter_end_to_end_stays_idempotent(tmp_path) -> None:
    """Guard against reverting ``get_article_projects`` back to naive split."""
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

---

## §4 — Post-verification

### §4.1 — Bug reproduction POST
```
['a', 'b', 'c']
Expected: ['a', 'b', 'c']
Observed: ['a', 'b', 'c']
Verdict: pass
```

### §4.2 — Pytest full suite
```
........................................................................ [ 79%]
...................                                                      [100%]
91 passed in 0.76s
post_count = 91, delta = +7 expected: 5 parametrized cases + 2 discrete functions
```

### §4.3 — Focused pytest on new tests
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- /home/dmaka/.cache/llm-wiki/.venv/bin/python3
cachedir: .pytest_cache
rootdir: <repo-root>
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 7 items

tests/test_utils.py::test_get_article_projects_handles_list_and_scalar[list-form-unquoted] PASSED [ 14%]
tests/test_utils.py::test_get_article_projects_handles_list_and_scalar[scalar-csv] PASSED [ 28%]
tests/test_utils.py::test_get_article_projects_handles_list_and_scalar[scalar-single] PASSED [ 42%]
tests/test_utils.py::test_get_article_projects_handles_list_and_scalar[empty] PASSED [ 57%]
tests/test_utils.py::test_get_article_projects_handles_list_and_scalar[list-form-quoted] PASSED [ 71%]
tests/test_rebuild_index.py::test_enrich_index_line_idempotent_only_for_clean_projects PASSED [ 85%]
tests/test_rebuild_index.py::test_list_form_frontmatter_end_to_end_stays_idempotent PASSED [100%]

============================== 7 passed in 0.43s ===============================
```

### §4.4 — Doctor class-level diff (pre vs post)
```
[PASS] wiki_structure: Bootstrap files and directories are present
[PASS] env_settings: timezone=UTC, compile_hour=18
[PASS] flush_throughput: Last 7d: 19/29 flushes spawned (skip rate 34%)
[PASS] flush_quality_coverage: Last 7d: 6852408/6852408 chars reached flush.py (coverage 100.0%)
[FAIL] flush_pipeline_correctness: Last 24h: 2 'Fatal error in message reader' events (7d total: 35, most recent 2026-04-23 21:34:32) — active Bug H regression, investigate issue #16
[PASS] python_version: Python 3.14.4
[PASS] uv_binary: /home/dmaka/.local/bin/uv
[PASS] index_health: Index is up to date.
[FAIL] structural_lint: Running knowledge base lint checks...
[PASS] query_preview_smoke: Query preview returned provenance-aware candidates
[PASS] wiki_cli_query_preview_smoke: wiki_cli query preview returned provenance-aware candidates
[PASS] wiki_cli_status_smoke: wiki_cli status returned expected summary fields
[FAIL] wiki_cli_lint_smoke: wiki_cli structural lint reported blocking errors
[PASS] wiki_cli_rebuild_check_smoke: wiki_cli rebuild --check confirmed index freshness
[PASS] path_normalization: Windows, WSL, Git Bash, and repo-root cwd cases passed
```

Verdict: `index_health` is PASS, and no new FAIL classes were introduced by this patch. The observed FAIL classes are pre-existing known streams:
- `flush_pipeline_correctness` — active Bug H stream, explicitly carved out in the plan
- `structural_lint` / `wiki_cli_lint_smoke` — current wiki-content lint debt, unrelated to the touched files

### §4.4.5 — wiki_cli.py status (transitive consumer smoke)
```
Wiki Status:
  Articles: 304 (analyses: 6, concepts: 121, connections: 12, entities: 2, sources: 162, top-level: 1)
  Projects: codex-easy-start (22), memory-claude (175), messenger (47), montazhstroy-site (2), office (21), personal (8), site-tiretop (3), skolkovo (2), workflow (30), untagged (3)
  Daily logs: 14 (today: 34 entries)
  Last compile: 2026-04-23T18:41:44+00:00
  Last lint: 2026-04-22T22:15:21+00:00
  Total cost: $46.72

exit code: 0
```

### §4.5 — PDC scope-creep detector
```
docs/codex-tasks/wiki-freshness-phase1.md

-- pdc_delta_v5 --
```

Verdict: pass under v5. The detector output matches the corrected expected pre-existing allowlist exactly (`docs/codex-tasks/wiki-freshness-phase1.md` only); `pdc_delta_v5` is empty.

### §4.6 — git status delta (not absolute) vs /tmp/git_status_pre.txt
```
85a86
>  M scripts/utils.py
86a88,89
>  M tests/test_rebuild_index.py
>  M tests/test_utils.py

-- git_delta_paths --
scripts/utils.py
tests/test_rebuild_index.py
tests/test_utils.py

-- git_delta_unexpected --
```

### §4.7 — Ruff post-run
```
All checks passed!
post_ruff_issues = 0; delta vs pre = 0
```

---

## §5 — Discrepancies encountered

- v4 execution-round-1 hit `D8` because the package claimed an empty PDC baseline. Claude corrected that in v5 by switching the command to PCRE (`-lP`) and restoring the single-file expected baseline. Re-run on v5 passed.
- No remaining execution discrepancies in v5.

---

## §6 — Acceptance-criteria matrix

| Gate | Result | Evidence (report §) |
|---|---|---|
| `get_article_projects` returns `['a','b','c']` for list-form | `pass` | §4.1 |
| 5 parametrized test cases pass | `pass` | §4.3 |
| `test_enrich_index_line_idempotent_only_for_clean_projects` passes | `pass` | §4.3 |
| `test_list_form_frontmatter_end_to_end_stays_idempotent` passes | `pass` | §4.3 |
| full suite `pre_test_count + 7` passed, zero regressions | `pass` | §4.2 |
| ruff post_count ≤ pre_ruff_issues | `pass` | §4.7 |
| doctor index_health PASS | `pass` | §4.4 |
| wiki_cli status exits 0 | `pass` | §4.4.5 |
| git status **delta** limited to whitelist (git_delta_unexpected.txt empty) | `pass` | §4.6 |
| PDC detector output matches expected allowlist baseline | `pass` | §4.5 |

Soft gates:
- compile.py unchanged: `yes`
- query.py unchanged: `yes`
- lint.py unchanged: `yes`
- mypy intentionally skipped this cycle (not in dev deps).

---

## §7 — Final summary

- Files edited: `scripts/utils.py`, `tests/test_utils.py`, `tests/test_rebuild_index.py`, `docs/codex-tasks/bug-compile-yaml-list-fix-report.md`
- Files created: `none`
- state.json mutated: `no`
- Cross-env visibility: shared `/mnt/e/` ↔ `E:\` — Claude's Windows env will see changes immediately
- Bug closed? `passed`

The code fix behaved as intended end-to-end:
- reproduction PRE → POST flipped from `['[a', 'b', 'c]']` to `['a', 'b', 'c']`
- targeted tests passed (`7 passed`)
- full suite moved `84 passed` → `91 passed`
- `ruff` stayed clean
- git-status delta stayed inside the whitelist
- corrected PDC check matched the expected single-file baseline exactly
- `doctor --quick` retained `index_health PASS`; observed FAIL classes remained in known out-of-scope streams only

---

## §8 — Notification

Upon completion: send mailbox reply in thread `bug-compile-yaml-list-fix` to Claude with report location + one-line status.

Reply sent: `<pending>`
