"""Regression tests for scripts/query.py frontmatter handling."""

from __future__ import annotations

from pathlib import Path

import pytest
import query as query_module


def test_score_query_candidate_normalizes_list_form_project(tmp_path: Path, monkeypatch) -> None:
    fake_wiki_dir = tmp_path / "wiki"
    article = fake_wiki_dir / "concepts" / "foo.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\ntitle: Foo\ntype: concept\nproject: [alpha, workflow, beta]\n---\n\nbody\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(query_module, "WIKI_DIR", fake_wiki_dir)

    score, _ = query_module._score_query_candidate_with_frontmatter(article, {"workflow"})
    assert score > 0


def test_save_manual_qa_answer_writes_article_log_and_state(tmp_path: Path, monkeypatch) -> None:
    fake_wiki_dir = tmp_path / "wiki"
    fake_qa_dir = fake_wiki_dir / "qa"
    fake_concepts_dir = fake_wiki_dir / "concepts"
    fake_concepts_dir.mkdir(parents=True)
    (fake_concepts_dir / "foo.md").write_text("---\ntitle: Foo\n---\n\n# Foo\n", encoding="utf-8")
    (fake_concepts_dir / "bar.md").write_text("---\ntitle: Bar\n---\n\n# Bar\n", encoding="utf-8")
    fake_log = tmp_path / "log.md"
    rebuild_calls: list[str] = []
    saved_states: list[dict] = []

    import rebuild_index

    monkeypatch.setattr(query_module, "WIKI_DIR", fake_wiki_dir)
    monkeypatch.setattr(query_module, "QA_DIR", fake_qa_dir)
    monkeypatch.setattr(query_module, "LOG_FILE", fake_log)
    monkeypatch.setattr(query_module, "now_iso", lambda: "2026-05-07T12:34:56+00:00")
    monkeypatch.setattr(query_module, "load_state", lambda: {})
    monkeypatch.setattr(query_module, "save_state", lambda state: saved_states.append(state.copy()))
    monkeypatch.setattr(
        rebuild_index, "rebuild_and_write_index", lambda: rebuild_calls.append("yes")
    )

    saved = query_module.save_manual_qa_answer(
        question="How should manual Q&A be filed?",
        answer="Use the local save path and keep consulted articles traceable.",
        consulted_articles=["[[wiki/concepts/foo.md|Foo]]", "concepts/bar"],
        title="Manual Q&A Filing",
        slug="manual-qa-filing",
        project="memory-claude",
    )

    assert saved == fake_qa_dir / "manual-qa-filing.md"
    content = saved.read_text(encoding="utf-8")
    assert 'title: "Manual Q&A Filing"' in content
    assert 'question: "How should manual Q&A be filed?"' in content
    assert 'consulted_articles: ["concepts/foo", "concepts/bar"]' in content
    assert "- [[concepts/foo]]" in content
    assert "- [[concepts/bar]]" in content

    log_content = fake_log.read_text(encoding="utf-8")
    assert "query (manual-filed)" in log_content
    assert "[[qa/manual-qa-filing]]" in log_content
    assert rebuild_calls == ["yes"]
    assert saved_states == [{"manual_qa_file_count": 1}]


def test_save_manual_qa_answer_rejects_existing_explicit_slug(tmp_path: Path, monkeypatch) -> None:
    fake_wiki_dir = tmp_path / "wiki"
    fake_qa_dir = fake_wiki_dir / "qa"
    fake_qa_dir.mkdir(parents=True)
    (fake_qa_dir / "manual-qa-filing.md").write_text("existing", encoding="utf-8")

    monkeypatch.setattr(query_module, "WIKI_DIR", fake_wiki_dir)
    monkeypatch.setattr(query_module, "QA_DIR", fake_qa_dir)

    with pytest.raises(FileExistsError):
        query_module.save_manual_qa_answer(
            question="How should manual Q&A be filed?",
            answer="Use the local save path.",
            slug="manual-qa-filing",
        )


def test_save_manual_qa_answer_rejects_missing_consulted_article(
    tmp_path: Path, monkeypatch
) -> None:
    fake_wiki_dir = tmp_path / "wiki"
    fake_qa_dir = fake_wiki_dir / "qa"

    monkeypatch.setattr(query_module, "WIKI_DIR", fake_wiki_dir)
    monkeypatch.setattr(query_module, "QA_DIR", fake_qa_dir)

    with pytest.raises(FileNotFoundError, match="concepts/missing"):
        query_module.save_manual_qa_answer(
            question="How should manual Q&A be filed?",
            answer="Use the local save path.",
            consulted_articles=["concepts/missing"],
        )
