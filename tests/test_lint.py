"""Regression tests for scripts/lint.py advisory checks."""

from __future__ import annotations

from pathlib import Path

import lint as lint_module
import pytest


def test_check_project_frontmatter_shape_flags_list_form_project(
    tmp_path: Path, monkeypatch
) -> None:
    article = tmp_path / "wiki" / "concepts" / "foo.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\ntitle: Foo\ntype: concept\nproject: [alpha, beta]\n---\n\nbody\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(lint_module, "_ARTICLE_LIST_CACHE", [article])
    monkeypatch.setattr(lint_module, "_ARTICLE_FRONTMATTER_CACHE", {})
    monkeypatch.setattr(lint_module, "WIKI_DIR", tmp_path / "wiki")

    issues = lint_module.check_project_frontmatter_shape()

    assert len(issues) == 1
    assert issues[0]["check"] == "project_frontmatter_shape"
    assert issues[0]["severity"] == "suggestion"


def test_check_orphan_sources_skips_low_signal_daily_logs(tmp_path: Path, monkeypatch) -> None:
    low_signal = tmp_path / "daily" / "2026-05-03.md"
    valuable = tmp_path / "daily" / "2026-04-27.md"
    low_signal.parent.mkdir()
    low_signal.write_text(
        "# Daily Log\n\n"
        "## [2026-05-03T13:12:58+00:00] tool-capture\n\n"
        "- **Build**: `npm run build`\n",
        encoding="utf-8",
    )
    valuable.write_text(
        "# Daily Log\n\n"
        "## [2026-04-27T06:53:02+00:00]\n\n"
        "- **Q: What changed?** A: Channels replaced monitor-only mailbox delivery.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(lint_module, "list_daily_logs", lambda: [low_signal, valuable])
    monkeypatch.setattr(lint_module, "load_state", lambda: {})

    issues = lint_module.check_orphan_sources()

    assert [issue["file"] for issue in issues] == ["daily/2026-04-27.md"]


def test_check_stale_articles_skips_low_signal_daily_logs(tmp_path: Path, monkeypatch) -> None:
    low_signal = tmp_path / "daily" / "2026-05-03.md"
    valuable = tmp_path / "daily" / "2026-04-27.md"
    low_signal.parent.mkdir()
    low_signal.write_text(
        "# Daily Log\n\n"
        "## [2026-05-03T13:12:58+00:00] tool-capture\n\n"
        "- **Build**: `npm run build`\n",
        encoding="utf-8",
    )
    valuable.write_text(
        "# Daily Log\n\n"
        "## [2026-04-27T06:53:02+00:00]\n\n"
        "- **Q: What changed?** A: Channels replaced monitor-only mailbox delivery.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(lint_module, "list_daily_logs", lambda: [low_signal, valuable])
    monkeypatch.setattr(
        lint_module,
        "load_state",
        lambda: {
            "ingested": {
                low_signal.name: {"hash": "old-low"},
                valuable.name: {"hash": "old-valuable"},
            }
        },
    )

    issues = lint_module.check_stale_articles()

    assert [issue["file"] for issue in issues] == ["daily/2026-04-27.md"]


def test_check_source_drift_domain_filter_limits_checked_hosts(tmp_path: Path, monkeypatch) -> None:
    sources_dir = tmp_path / "wiki" / "sources"
    sources_dir.mkdir(parents=True)
    article = sources_dir / "python-docs.md"
    article.write_text(
        "---\n"
        "title: Python Docs\n"
        "type: source\n"
        "sources: [https://docs.python.org/3/library/pathlib.html, https://example.com/a]\n"
        "---\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )

    checked_urls: list[str] = []

    def fake_check_source_url(url: str, stored: dict[str, str], *, timeout: float):
        checked_urls.append(url)
        return "no_drift", "test detail", {"last_status": "no_drift"}

    saved_states: list[dict] = []

    monkeypatch.setattr(lint_module, "WIKI_DIR", tmp_path / "wiki")
    monkeypatch.setattr(lint_module, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(lint_module, "load_state", lambda: {})
    monkeypatch.setattr(lint_module, "save_state", saved_states.append)
    monkeypatch.setattr(lint_module, "_check_source_url", fake_check_source_url)

    issues = lint_module.check_source_drift(domain="docs.python.org", delay=0)

    assert issues == []
    assert checked_urls == ["https://docs.python.org/3/library/pathlib.html"]
    assert len(saved_states) == 1
    assert lint_module._LAST_SOURCE_DRIFT_SNAPSHOT[0]["status"] == "no_drift"


def test_check_source_drift_source_article_filter_limits_checked_articles(
    tmp_path: Path, monkeypatch
) -> None:
    sources_dir = tmp_path / "wiki" / "sources"
    sources_dir.mkdir(parents=True)
    python_article = sources_dir / "python-docs.md"
    python_article.write_text(
        "---\n"
        "title: Python Docs\n"
        "type: source\n"
        "sources: [https://docs.python.org/3/library/pathlib.html]\n"
        "---\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )
    other_article = sources_dir / "example-docs.md"
    other_article.write_text(
        "---\ntitle: Example Docs\ntype: source\nsources: [https://example.com/a]\n---\n\nbody\n",
        encoding="utf-8",
    )

    checked_urls: list[str] = []

    def fake_check_source_url(url: str, stored: dict[str, str], *, timeout: float):
        checked_urls.append(url)
        return "no_drift", "test detail", {"last_status": "no_drift"}

    monkeypatch.setattr(lint_module, "WIKI_DIR", tmp_path / "wiki")
    monkeypatch.setattr(lint_module, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(lint_module, "load_state", lambda: {})
    monkeypatch.setattr(lint_module, "save_state", lambda state: None)
    monkeypatch.setattr(lint_module, "_check_source_url", fake_check_source_url)

    issues = lint_module.check_source_drift(source_article="sources/python-docs.md", delay=0)

    assert issues == []
    assert checked_urls == ["https://docs.python.org/3/library/pathlib.html"]
    assert lint_module._LAST_SOURCE_DRIFT_SNAPSHOT[0]["file"] == "sources/python-docs.md"


def test_check_source_drift_reports_progress_rows(tmp_path: Path, monkeypatch) -> None:
    sources_dir = tmp_path / "wiki" / "sources"
    sources_dir.mkdir(parents=True)
    article = sources_dir / "python-docs.md"
    article.write_text(
        "---\n"
        "title: Python Docs\n"
        "type: source\n"
        "sources: [https://docs.python.org/3/library/pathlib.html]\n"
        "---\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )

    def fake_check_source_url(url: str, stored: dict[str, str], *, timeout: float):
        return "no_drift", "test detail", {"last_status": "no_drift"}

    progress_events: list[tuple[int, dict[str, str]]] = []

    monkeypatch.setattr(lint_module, "WIKI_DIR", tmp_path / "wiki")
    monkeypatch.setattr(lint_module, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(lint_module, "load_state", lambda: {})
    monkeypatch.setattr(lint_module, "save_state", lambda state: None)
    monkeypatch.setattr(lint_module, "_check_source_url", fake_check_source_url)

    issues = lint_module.check_source_drift(
        delay=0,
        progress=lambda row, count: progress_events.append((count, row.copy())),
    )

    assert issues == []
    assert progress_events == [
        (
            1,
            {
                "file": "sources/python-docs.md",
                "url": "https://docs.python.org/3/library/pathlib.html",
                "domain": "docs.python.org",
                "status": "no_drift",
                "detail": "test detail",
            },
        )
    ]


def test_source_article_filter_rejects_paths_outside_sources(tmp_path: Path, monkeypatch) -> None:
    sources_dir = tmp_path / "wiki" / "sources"
    sources_dir.mkdir(parents=True)
    monkeypatch.setattr(lint_module, "SOURCES_DIR", sources_dir)

    with pytest.raises(ValueError, match="outside wiki/sources"):
        lint_module._resolve_source_article_filter("../concepts/source-drift-detection")


def test_check_source_drift_export_only_does_not_save_state(tmp_path: Path, monkeypatch) -> None:
    sources_dir = tmp_path / "wiki" / "sources"
    sources_dir.mkdir(parents=True)
    article = sources_dir / "python-docs.md"
    article.write_text(
        "---\n"
        "title: Python Docs\n"
        "type: source\n"
        "sources: [https://docs.python.org/3/library/pathlib.html]\n"
        "---\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )

    def fake_check_source_url(url: str, stored: dict[str, str], *, timeout: float):
        return "drift", "changed", {"last_status": "drift"}

    def fail_save_state(state: dict) -> None:
        raise AssertionError("export-only source drift must not save validator state")

    monkeypatch.setattr(lint_module, "WIKI_DIR", tmp_path / "wiki")
    monkeypatch.setattr(lint_module, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(lint_module, "load_state", lambda: {})
    monkeypatch.setattr(lint_module, "save_state", fail_save_state)
    monkeypatch.setattr(lint_module, "_check_source_url", fake_check_source_url)

    issues = lint_module.check_source_drift(delay=0, save=False)

    assert len(issues) == 1
    assert issues[0]["check"] == "source_drift"
    assert lint_module._LAST_SOURCE_DRIFT_SNAPSHOT[0]["detail"] == "changed"


def test_write_source_drift_snapshot_records_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(lint_module, "REPORTS_DIR", tmp_path)

    report_path = lint_module.write_source_drift_snapshot(
        [
            {
                "file": "sources/python-docs.md",
                "url": "https://docs.python.org/3/library/pathlib.html",
                "domain": "docs.python.org",
                "status": "drift",
                "detail": "ETag changed",
            }
        ],
        domain="docs.python.org",
        source_article="sources/python-docs.md",
        export_only=True,
    )

    text = report_path.read_text(encoding="utf-8")
    assert "export-only (validator state not saved)" in text
    assert "Domain filter: docs.python.org" in text
    assert "Source article filter: python-docs" in text
    assert (
        "| drift | sources/python-docs.md | https://docs.python.org/3/library/pathlib.html | ETag changed |"
        in text
    )


def test_write_source_drift_ledger_entry_appends_pending_review_queue(tmp_path: Path) -> None:
    ledger_path = tmp_path / "source-drift-review-ledger.md"

    result_path = lint_module.write_source_drift_ledger_entry(
        [
            {
                "file": "sources/python-docs.md",
                "url": "https://docs.python.org/3/",
                "domain": "docs.python.org",
                "status": "drift",
                "detail": "ETag changed",
            },
            {
                "file": "sources/example-docs.md",
                "url": "https://example.com/",
                "domain": "example.com",
                "status": "no_drift",
                "detail": "304 Not Modified",
            },
        ],
        issues=[{"check": "source_drift"}],
        domain="https://docs.python.org",
        source_article="sources/python-docs.md",
        export_only=True,
        ledger_path=ledger_path,
    )

    text = result_path.read_text(encoding="utf-8")
    assert result_path == ledger_path
    assert "# Source Drift Review Ledger" in text
    assert "Review state: pending manual review" in text
    assert "Domain filter: docs.python.org" in text
    assert "Source article filter: python-docs" in text
    assert "Lint issue rows: 1" in text
    assert "Actionable review rows: 1" in text
    assert "- drift: 1" in text
    assert "- no_drift: 1" in text
    assert (
        "| drift | sources/python-docs.md | https://docs.python.org/3/ | ETag changed | pending |"
        in text
    )
    assert "example-docs.md" not in text
    assert "Do not use this ledger as automatic evidence for `reviewed:` frontmatter." in text


def test_write_source_drift_ledger_entry_appends_to_existing_file(tmp_path: Path) -> None:
    ledger_path = tmp_path / "source-drift-review-ledger.md"
    ledger_path.write_text("# Existing Ledger\n\nold entry\n", encoding="utf-8")

    lint_module.write_source_drift_ledger_entry([], ledger_path=ledger_path)

    text = ledger_path.read_text(encoding="utf-8")
    assert text.startswith("# Existing Ledger\n\nold entry\n\n## ")
    assert "No drift, rot, or refused rows in this scan." in text
