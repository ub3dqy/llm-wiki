"""Tests for scripts/rebuild_index.py pure string functions.

Scope per docs/codex-tasks/tier4.1-test-coverage-rebuild-index-and-hook-utils.md:
- 4 pure functions, ~19 parametrized test cases
- All string/dict transforms; no filesystem access
- Private-helper _article_type_from_slug included (stable API within module)

Deferred to later tier:
- populate_empty_section_placeholders (complex list-state machine)
- rebuild_index/rebuild_and_write_index (require INDEX_FILE fixture)
"""

from __future__ import annotations

import pytest
from rebuild_index import (
    _article_type_from_slug,
    build_by_project_section,
    enrich_index_line,
    strip_existing_annotations,
)


@pytest.mark.parametrize(
    "slug,expected",
    [
        pytest.param("overview", "overview", id="overview-special"),
        pytest.param("concepts/foo", "concepts", id="concepts-prefix"),
        pytest.param("entities/bar", "entities", id="entities-prefix"),
        pytest.param("noslash", "", id="no-slash-non-overview"),
        pytest.param("sources/deep/nested", "sources", id="multi-level-first-segment"),
    ],
)
def test_article_type_from_slug(slug: str, expected: str) -> None:
    assert _article_type_from_slug(slug) == expected


@pytest.mark.parametrize(
    "line,expected",
    [
        pytest.param(
            "- [[foo]] — Title [memory-claude] (100w)",
            "- [[foo]] — Title",
            id="project-plus-wordcount",
        ),
        pytest.param(
            "- [[foo]] — Title [a, b, c] (50w)",
            "- [[foo]] — Title",
            id="multi-project-plus-wordcount",
        ),
        pytest.param(
            "- [[foo]] — Title (200w)",
            "- [[foo]] — Title",
            id="wordcount-only",
        ),
        pytest.param(
            "- [[foo]] — Title",
            "- [[foo]] — Title",
            id="no-annotation",
        ),
        pytest.param(
            "- [[foo]] — Title [one]",
            "- [[foo]] — Title",
            id="project-only-no-wordcount",
        ),
    ],
)
def test_strip_existing_annotations(line: str, expected: str) -> None:
    assert strip_existing_annotations(line) == expected


def test_enrich_index_line_non_list_line() -> None:
    assert enrich_index_line("# Section header", {}) == "# Section header"


def test_enrich_index_line_no_meta() -> None:
    line = "- [[concepts/foo]] — Title"
    assert enrich_index_line(line, {}) == line


def test_enrich_index_line_with_meta_projects_and_wc() -> None:
    meta = {"concepts/foo": {"projects": ["memory-claude"], "word_count": 150, "title": "Foo"}}
    result = enrich_index_line("- [[concepts/foo]] — Foo", meta)
    assert result == "- [[concepts/foo]] — Foo [memory-claude] (150w)"


def test_enrich_index_line_strips_existing_annotation_before_rewrite() -> None:
    meta = {"concepts/foo": {"projects": ["new-proj"], "word_count": 99, "title": "Foo"}}
    result = enrich_index_line("- [[concepts/foo]] — Foo [old-proj] (50w)", meta)
    assert result == "- [[concepts/foo]] — Foo [new-proj] (99w)"


def test_enrich_index_line_no_projects_only_wordcount() -> None:
    meta = {"concepts/foo": {"projects": [], "word_count": 42, "title": "Foo"}}
    result = enrich_index_line("- [[concepts/foo]] — Foo", meta)
    assert result == "- [[concepts/foo]] — Foo (42w)"


def test_build_by_project_section_single_project() -> None:
    meta = {"concepts/foo": {"projects": ["proj-a"], "word_count": 100, "title": "Foo"}}
    enriched = ["- [[concepts/foo]] — Foo [proj-a] (100w)"]
    result = build_by_project_section(meta, enriched)
    assert "### proj-a" in result
    assert "- [[concepts/foo]] — Foo [proj-a] (100w)" in result


def test_build_by_project_section_sorts_projects_alphabetically() -> None:
    meta = {
        "concepts/foo": {"projects": ["zeta"], "word_count": 100, "title": "Foo"},
        "concepts/bar": {"projects": ["alpha"], "word_count": 50, "title": "Bar"},
    }
    enriched = [
        "- [[concepts/foo]] — Foo [zeta] (100w)",
        "- [[concepts/bar]] — Bar [alpha] (50w)",
    ]
    result = build_by_project_section(meta, enriched)
    alpha_idx = result.find("### alpha")
    zeta_idx = result.find("### zeta")
    assert 0 <= alpha_idx < zeta_idx


def test_build_by_project_section_untagged_bucket() -> None:
    meta = {"concepts/orphan": {"projects": [], "word_count": 30, "title": "Orphan"}}
    enriched = ["- [[concepts/orphan]] — Orphan (30w)"]
    result = build_by_project_section(meta, enriched)
    assert "### (untagged)" in result
    assert "Orphan" in result


def test_build_by_project_section_compact_after_max_detailed() -> None:
    """Projects 16+ (0-indexed) show compact form with article count."""
    meta = {}
    for i in range(17):
        proj = f"p{i:02d}"
        meta[f"concepts/a{i}"] = {"projects": [proj], "word_count": 10, "title": f"A{i}"}
    enriched = [f"- [[concepts/a{i}]] — A{i} [p{i:02d}] (10w)" for i in range(17)]
    result = build_by_project_section(meta, enriched)
    assert "### p00\n" in result
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
