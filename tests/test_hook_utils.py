"""Tests for hooks/hook_utils.py pure path/payload functions.

Scope per docs/codex-tasks/tier4.1-test-coverage-rebuild-index-and-hook-utils.md:
- 5 pure functions, ~26 parametrized test cases
- String + dict transforms; no filesystem or subprocess

Deferred to later tier:
- infer_project_name_from_cwd (PROJECT_ALIASES config dependency, needs fixture)
- _extract_claude_code_format / _extract_codex_format / _detect_format (private format parsers)
- check_debounce / update_debounce (file I/O)
- parse_hook_stdin (stdin mock)
- extract_conversation_context (filesystem + format detection)
"""

from __future__ import annotations

import pytest
from hook_utils import (
    canonical_project_key,
    get_prompt,
    get_transcript_path,
    normalize_cwd,
    path_tail_parts,
)


@pytest.mark.parametrize(
    "cwd,expected",
    [
        pytest.param("E:\\project\\foo", "E:/project/foo", id="windows-backslash"),
        pytest.param("E:/project/foo", "E:/project/foo", id="windows-forward"),
        pytest.param("/mnt/e/project/foo", "E:/project/foo", id="wsl-mnt"),
        pytest.param("/e/project/foo", "E:/project/foo", id="git-bash"),
        pytest.param("/usr/local/bin", "/usr/local/bin", id="posix-no-drive"),
        pytest.param("", "", id="empty"),
        pytest.param('"E:\\project\\foo"', "E:/project/foo", id="quoted-double"),
        pytest.param("E:\\\\project\\\\foo", "E:/project/foo", id="double-separators-collapsed"),
    ],
)
def test_normalize_cwd(cwd: str, expected: str) -> None:
    assert normalize_cwd(cwd) == expected


def test_normalize_cwd_non_string() -> None:
    assert normalize_cwd(None) == ""  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "cwd,expected",
    [
        pytest.param("E:\\project\\memory", ["project", "memory"], id="windows-two-parts"),
        pytest.param("/mnt/e/project/memory", ["project", "memory"], id="wsl-same"),
        pytest.param("/usr/local/bin", ["usr", "local", "bin"], id="posix-full"),
        pytest.param("", [], id="empty"),
        pytest.param("E:\\", [], id="root-only"),
    ],
)
def test_path_tail_parts(cwd: str, expected: list[str]) -> None:
    assert path_tail_parts(cwd) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        pytest.param("LLM Wiki", "llm-wiki", id="spaces-lowercased"),
        pytest.param("memory_claude", "memory-claude", id="underscore-to-hyphen"),
        pytest.param("memory claude", "memory-claude", id="space-to-hyphen"),
        pytest.param("  Padded  ", "padded", id="strip-then-lower"),
        pytest.param("AlReAdY-KeBaB", "already-kebab", id="mixed-case"),
        pytest.param("", "", id="empty"),
    ],
)
def test_canonical_project_key(name: str, expected: str) -> None:
    assert canonical_project_key(name) == expected


def test_get_transcript_path_present() -> None:
    assert get_transcript_path({"transcript_path": "/tmp/foo.jsonl"}) == "/tmp/foo.jsonl"


def test_get_transcript_path_missing() -> None:
    assert get_transcript_path({}) == ""


def test_get_transcript_path_non_string() -> None:
    assert get_transcript_path({"transcript_path": 42}) == ""


def test_get_prompt_present() -> None:
    assert get_prompt({"prompt": "hello"}) == "hello"


def test_get_prompt_missing() -> None:
    assert get_prompt({}) == ""


def test_get_prompt_non_string() -> None:
    assert get_prompt({"prompt": {"nested": "x"}}) == ""
