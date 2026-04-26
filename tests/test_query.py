"""Regression tests for scripts/query.py frontmatter handling."""

from __future__ import annotations

from pathlib import Path

import query as query_module


def test_score_query_candidate_normalizes_list_form_project(
    tmp_path: Path, monkeypatch
) -> None:
    fake_wiki_dir = tmp_path / "wiki"
    article = fake_wiki_dir / "concepts" / "foo.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\n"
        "title: Foo\n"
        "type: concept\n"
        "project: [alpha, workflow, beta]\n"
        "---\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(query_module, "WIKI_DIR", fake_wiki_dir)

    score, _ = query_module._score_query_candidate_with_frontmatter(article, {"workflow"})
    assert score > 0


