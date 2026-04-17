"""Tests for scripts/utils.py pure functions."""

from __future__ import annotations

from pathlib import Path

import pytest
from utils import (
    content_has_wikilink_target,
    extract_wikilinks,
    frontmatter_sources_include_prefix,
    get_article_word_count,
    parse_frontmatter,
    parse_frontmatter_list,
    slugify,
    wiki_article_exists,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param("Hello World", "hello-world", id="basic-space"),
        pytest.param("Test  Multiple   Spaces", "test-multiple-spaces", id="collapse-spaces"),
        pytest.param("UPPERCASE", "uppercase", id="lowercase"),
        pytest.param(
            "with-hyphens_and_underscores", "with-hyphens-and-underscores", id="non-alpha"
        ),
        pytest.param("!!! Special @#$ Chars !!!", "special-chars", id="strip-leading-trailing"),
        pytest.param("", "", id="empty"),
        pytest.param("a" * 200, "a" * 80, id="truncate-80"),
    ],
)
def test_slugify(text: str, expected: str) -> None:
    assert slugify(text) == expected


@pytest.mark.parametrize(
    "content,expected",
    [
        pytest.param("See [[concepts/foo]]", ["concepts/foo"], id="single-plain"),
        pytest.param("[[a]] and [[b]] and [[c]]", ["a", "b", "c"], id="multiple"),
        pytest.param("[[target|display]]", ["target"], id="alias-strip-display"),
        pytest.param("[[target\\|escaped]]", ["target"], id="markdown-table-escape"),
        pytest.param("`[[inline-code-wikilink]]`", [], id="inline-code-excluded"),
        pytest.param(
            "```python\n[[code-block-wikilink]]\n```\n[[real]]",
            ["real"],
            id="code-block-excluded",
        ),
        pytest.param("", [], id="empty"),
    ],
)
def test_extract_wikilinks(content: str, expected: list[str]) -> None:
    assert extract_wikilinks(content) == expected


@pytest.mark.parametrize(
    "content,target,expected",
    [
        pytest.param("[[concepts/foo]]", "concepts/foo", True, id="exact-match"),
        pytest.param("[[concepts/foo|Foo]]", "concepts/foo", True, id="alias-match"),
        pytest.param("[[concepts/bar]]", "concepts/foo", False, id="no-match"),
        pytest.param("", "concepts/foo", False, id="empty-content"),
    ],
)
def test_content_has_wikilink_target(content: str, target: str, expected: bool) -> None:
    assert content_has_wikilink_target(content, target) is expected


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
    "raw,prefix,expected",
    [
        pytest.param("[daily/2026-04-17.md, raw/foo.md]", "daily/", True, id="prefix-match"),
        pytest.param("[raw/foo.md]", "daily/", False, id="no-match"),
        pytest.param("", "daily/", False, id="empty"),
        pytest.param("[daily/x.md]", "", False, id="empty-prefix"),
    ],
)
def test_frontmatter_sources_include_prefix(raw: str, prefix: str, expected: bool) -> None:
    assert frontmatter_sources_include_prefix(raw, prefix) is expected


def test_parse_frontmatter_valid(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text(
        "---\ntitle: Test\ntype: concept\ntags: [a, b]\n---\n\n# Body\n",
        encoding="utf-8",
    )

    assert parse_frontmatter(article) == {"title": "Test", "type": "concept", "tags": "[a, b]"}


def test_parse_frontmatter_no_delimiter(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text("# Just a body, no frontmatter\n", encoding="utf-8")

    assert parse_frontmatter(article) == {}


def test_parse_frontmatter_unclosed(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text("---\ntitle: Unclosed\n", encoding="utf-8")

    assert parse_frontmatter(article) == {}


def test_parse_frontmatter_hyphenated_key(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text(
        "---\nsuperseded-by: other\nreviewed: 2026-04-17\n---\n",
        encoding="utf-8",
    )
    frontmatter = parse_frontmatter(article)

    assert frontmatter.get("superseded-by") == "other"
    assert frontmatter.get("reviewed") == "2026-04-17"


def test_get_article_word_count_with_frontmatter(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text(
        "---\ntitle: Test\n---\n\nOne two three four.\n",
        encoding="utf-8",
    )

    assert get_article_word_count(article) == 4


def test_get_article_word_count_no_frontmatter(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text("Just six words in this body.\n", encoding="utf-8")

    assert get_article_word_count(article) == 6


def test_get_article_word_count_empty(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text("", encoding="utf-8")

    assert get_article_word_count(article) == 0


@pytest.fixture
def fake_wiki(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch utils WIKI_DIR and cached resolved paths to a temporary tree."""
    import utils

    fake_root = tmp_path / "fake_repo"
    fake_wiki_dir = fake_root / "wiki"
    (fake_wiki_dir / "concepts").mkdir(parents=True)
    (fake_wiki_dir / "concepts" / "real.md").write_text("# real", encoding="utf-8")
    (fake_root / "index.md").write_text("# root index", encoding="utf-8")

    monkeypatch.setattr(utils, "WIKI_DIR", fake_wiki_dir)
    monkeypatch.setattr(utils, "_WIKI_ROOT", fake_wiki_dir.resolve())
    monkeypatch.setattr(utils, "_WIKI_PARENT", fake_root.resolve())

    return fake_wiki_dir


def test_wiki_article_exists_valid(fake_wiki: Path) -> None:
    assert wiki_article_exists("concepts/real") is True


def test_wiki_article_exists_nonexistent(fake_wiki: Path) -> None:
    assert wiki_article_exists("concepts/does-not-exist") is False


def test_wiki_article_exists_traversal_rejected(fake_wiki: Path) -> None:
    assert wiki_article_exists("../../../etc/passwd") is False


def test_wiki_article_exists_parent_index(fake_wiki: Path) -> None:
    assert wiki_article_exists("index") is True
