"""Regression tests for scripts/lint.py advisory checks."""

from __future__ import annotations

from pathlib import Path

import lint as lint_module


def test_check_project_frontmatter_shape_flags_list_form_project(
    tmp_path: Path, monkeypatch
) -> None:
    article = tmp_path / "wiki" / "concepts" / "foo.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\n"
        "title: Foo\n"
        "type: concept\n"
        "project: [alpha, beta]\n"
        "---\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(lint_module, "_ARTICLE_LIST_CACHE", [article])
    monkeypatch.setattr(lint_module, "_ARTICLE_FRONTMATTER_CACHE", {})
    monkeypatch.setattr(lint_module, "WIKI_DIR", tmp_path / "wiki")

    issues = lint_module.check_project_frontmatter_shape()

    assert len(issues) == 1
    assert issues[0]["check"] == "project_frontmatter_shape"
    assert issues[0]["severity"] == "suggestion"
