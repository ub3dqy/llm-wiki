"""Lint: run health checks on the knowledge base."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import REPORTS_DIR, SOURCES_DIR, WIKI_DIR, now_iso, today_iso
from runtime_utils import find_uv, is_wsl
from utils import (
    extract_wikilinks,
    file_hash,
    get_article_word_count,
    list_daily_logs,
    list_wiki_articles,
    load_state,
    parse_frontmatter,
    parse_frontmatter_list,
    read_all_wiki_content,
    save_state,
    wiki_article_exists,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ADVISORY_BANNER = "[ADVISORY] Contradiction check results are non-deterministic and must not be used as a merge gate."

_ARTICLE_LIST_CACHE: list[Path] | None = None
_ARTICLE_TEXT_CACHE: dict[Path, str] = {}
_ARTICLE_FRONTMATTER_CACHE: dict[Path, dict[str, str]] = {}
_ARTICLE_WIKILINKS_CACHE: dict[Path, list[str]] = {}
_ARTICLE_WORD_COUNT_CACHE: dict[Path, int] = {}
_INBOUND_LINK_COUNT_CACHE: dict[str, int] | None = None
_UNSTABLE_URL_PATTERNS = [
    re.compile(r"github\.com/[^/]+/[^/]+/(blob|wiki|tree)/"),
    re.compile(r"github\.com/[^/]+/[^/]+/?$"),
]


def _wiki_articles() -> list[Path]:
    global _ARTICLE_LIST_CACHE
    if _ARTICLE_LIST_CACHE is None:
        _ARTICLE_LIST_CACHE = list_wiki_articles()
    return _ARTICLE_LIST_CACHE


def _article_text(path: Path) -> str:
    text = _ARTICLE_TEXT_CACHE.get(path)
    if text is None:
        text = path.read_text(encoding="utf-8")
        _ARTICLE_TEXT_CACHE[path] = text
    return text


def _article_frontmatter(path: Path) -> dict[str, str]:
    fm = _ARTICLE_FRONTMATTER_CACHE.get(path)
    if fm is None:
        fm = parse_frontmatter(path)
        _ARTICLE_FRONTMATTER_CACHE[path] = fm
    return fm


def _article_wikilinks(path: Path) -> list[str]:
    links = _ARTICLE_WIKILINKS_CACHE.get(path)
    if links is None:
        links = extract_wikilinks(_article_text(path))
        _ARTICLE_WIKILINKS_CACHE[path] = links
    return links


def _article_word_count(path: Path) -> int:
    word_count = _ARTICLE_WORD_COUNT_CACHE.get(path)
    if word_count is None:
        word_count = get_article_word_count(path)
        _ARTICLE_WORD_COUNT_CACHE[path] = word_count
    return word_count


def _inbound_link_counts() -> dict[str, int]:
    global _INBOUND_LINK_COUNT_CACHE
    if _INBOUND_LINK_COUNT_CACHE is None:
        counts: dict[str, int] = {}
        for article in _wiki_articles():
            for link in _article_wikilinks(article):
                if link.startswith("daily/"):
                    continue
                counts[link] = counts.get(link, 0) + 1
        _INBOUND_LINK_COUNT_CACHE = counts
    return _INBOUND_LINK_COUNT_CACHE


def to_windows_path(path: Path) -> str | None:
    """Convert /mnt/<drive>/path to Windows form for subprocess delegation."""
    text = str(path)
    if len(text) >= 7 and text.startswith("/mnt/") and text[6] == "/":
        drive = text[5].upper()
        rest = text[7:].replace("/", "\\")
        return f"{drive}:\\{rest}"
    return None


def decode_windows_output(data: bytes) -> str:
    """Decode subprocess output from Windows tooling as robustly as possible."""
    for encoding in ("utf-8", "cp1251", "cp866"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def has_claude_agent_sdk() -> bool:
    return importlib.util.find_spec("claude_agent_sdk") is not None


# ---------------------------------------------------------------------------
# Structural checks (no API calls)
# ---------------------------------------------------------------------------


def check_broken_links() -> list[dict]:
    """Check for [[wikilinks]] that point to non-existent articles."""
    issues: list[dict] = []
    for article in _wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        for link in _article_wikilinks(article):
            if link.startswith("daily/"):
                continue
            if not wiki_article_exists(link):
                issues.append(
                    {
                        "severity": "error",
                        "check": "broken_link",
                        "file": str(rel),
                        "detail": f"Broken link: [[{link}]] — target does not exist",
                    }
                )
    return issues


def check_orphan_pages() -> list[dict]:
    """Check for articles with zero inbound links."""
    issues: list[dict] = []
    inbound_counts = _inbound_link_counts()
    for article in _wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        link_target = str(rel).replace(".md", "").replace("\\", "/")
        inbound = inbound_counts.get(link_target, 0)
        if inbound == 0:
            issues.append(
                {
                    "severity": "warning",
                    "check": "orphan_page",
                    "file": str(rel),
                    "detail": f"Orphan page: no other articles link to [[{link_target}]]",
                }
            )
    return issues


def check_orphan_sources() -> list[dict]:
    """Check for daily logs that haven't been compiled yet."""
    state = load_state()
    ingested = state.get("ingested", {})
    issues: list[dict] = []
    for log_path in list_daily_logs():
        if log_path.name not in ingested:
            issues.append(
                {
                    "severity": "warning",
                    "check": "orphan_source",
                    "file": f"daily/{log_path.name}",
                    "detail": f"Uncompiled daily log: {log_path.name} has not been ingested",
                }
            )
    return issues


def check_stale_articles() -> list[dict]:
    """Check if source daily logs have changed since compilation."""
    state = load_state()
    ingested = state.get("ingested", {})
    issues: list[dict] = []
    for log_path in list_daily_logs():
        rel = log_path.name
        if rel in ingested:
            stored_hash = ingested[rel].get("hash", "")
            current_hash = file_hash(log_path)
            if stored_hash != current_hash:
                issues.append(
                    {
                        "severity": "warning",
                        "check": "stale_article",
                        "file": f"daily/{rel}",
                        "detail": f"Stale: {rel} has changed since last compilation",
                    }
                )
    return issues


def check_freshness_review_debt() -> list[dict]:
    """Advisory: flag concept/source pages overdue for human review."""
    from datetime import date, timedelta

    today = date.today()
    concept_max_age = 180
    source_max_age = 60

    issues: list[dict] = []
    for article in _wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        rel_str = str(rel).replace("\\", "/")
        if not (rel_str.startswith("concepts/") or rel_str.startswith("sources/")):
            continue

        fm = _article_frontmatter(article)
        status = (fm.get("status", "active") or "active").lower()
        if status == "archived":
            continue

        if status == "superseded" and not fm.get("superseded_by"):
            issues.append(
                {
                    "severity": "warning",
                    "check": "freshness_superseded_without_link",
                    "file": rel_str,
                    "detail": f"{rel_str}: status=superseded but no superseded_by wikilink",
                }
            )
            continue

        reviewed_str = fm.get("reviewed", "")
        max_age = source_max_age if rel_str.startswith("sources/") else concept_max_age

        if not reviewed_str:
            issues.append(
                {
                    "severity": "suggestion",
                    "check": "freshness_never_reviewed",
                    "file": rel_str,
                    "detail": f"{rel_str}: no 'reviewed' field — consider adding review date",
                }
            )
            continue

        try:
            reviewed_date = date.fromisoformat(str(reviewed_str))
        except (TypeError, ValueError):
            issues.append(
                {
                    "severity": "warning",
                    "check": "freshness_malformed_reviewed",
                    "file": rel_str,
                    "detail": f"{rel_str}: 'reviewed' field not valid ISO date (got {reviewed_str!r})",
                }
            )
            continue

        age = (today - reviewed_date).days
        if today - reviewed_date > timedelta(days=max_age):
            issues.append(
                {
                    "severity": "suggestion",
                    "check": "freshness_review_overdue",
                    "file": rel_str,
                    "detail": f"{rel_str}: last reviewed {age} days ago (max {max_age} for {rel.parts[0]}/)",
                }
            )

    return issues


def _extract_source_urls(article: Path) -> list[str]:
    """Extract HTTP source URLs from frontmatter.

    Supports both inline `sources: [a, b]` and multiline YAML list form.
    """
    text = _article_text(article)
    if not text.startswith("---"):
        return []

    lines = text.splitlines()
    urls: list[str] = []
    idx = 1

    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---":
            break

        if line.startswith("sources:"):
            raw_value = line.split(":", 1)[1].strip()
            if raw_value:
                candidates = parse_frontmatter_list(raw_value)
                return [item for item in candidates if item.startswith(("http://", "https://"))]

            idx += 1
            while idx < len(lines):
                subline = lines[idx]
                if subline.strip() == "---":
                    break
                if not subline.startswith("  - "):
                    break
                item = subline[4:].strip().strip("'\"")
                if item.startswith(("http://", "https://")):
                    urls.append(item)
                idx += 1
            return urls

        idx += 1

    return []


def _parse_http_datetime(value: str) -> object | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _domain_key(url: str) -> str:
    parts = urlsplit(url)
    return (parts.netloc or parts.path).lower()


def _is_unstable_url(url: str) -> bool:
    return any(pattern.search(url) for pattern in _UNSTABLE_URL_PATTERNS)


def _is_newer_last_modified(stored_value: str, current_value: str) -> bool:
    stored_dt = _parse_http_datetime(stored_value)
    current_dt = _parse_http_datetime(current_value)
    if stored_dt is None or current_dt is None:
        return bool(current_value and stored_value and current_value != stored_value)
    return current_dt > stored_dt


def _classify_head_200(
    stored: dict[str, str], new_etag: str, new_last_modified: str
) -> tuple[str, str]:
    stored_etag = str(stored.get("etag", "") or "")
    stored_last_modified = str(stored.get("last_modified", "") or "")

    if stored_etag and new_etag:
        if new_etag != stored_etag:
            return "drift", f"ETag changed (stored: {stored_etag!r}, current: {new_etag!r})"
        return "no_drift", "ETag unchanged"

    if stored_last_modified and new_last_modified:
        if _is_newer_last_modified(stored_last_modified, new_last_modified):
            return (
                "drift",
                f"Last-Modified changed (stored: {stored_last_modified!r}, current: {new_last_modified!r})",
            )
        return "no_drift", "Last-Modified unchanged"

    if new_etag or new_last_modified:
        return "unverifiable", "validators available but no stored baseline to compare"

    return "unverifiable", "response omitted ETag and Last-Modified"


def _check_source_url(
    url: str,
    stored: dict[str, str],
    *,
    timeout: float,
) -> tuple[str, str, dict[str, str]]:
    """Check one URL using HEAD + conditional validators.

    Returns (classification, detail, updated_state_entry).
    """
    headers = {"User-Agent": "llm-wiki-source-drift/1.0"}
    if stored.get("etag"):
        headers["If-None-Match"] = str(stored["etag"])
    if stored.get("last_modified"):
        headers["If-Modified-Since"] = str(stored["last_modified"])

    request = urllib.request.Request(url, method="HEAD", headers=headers)
    entry = {
        "etag": str(stored.get("etag", "") or ""),
        "last_modified": str(stored.get("last_modified", "") or ""),
        "last_checked": today_iso(),
        "last_status": str(stored.get("last_status", "") or ""),
    }

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            new_etag = str(response.headers.get("ETag", "") or "")
            new_last_modified = str(response.headers.get("Last-Modified", "") or "")

        if _is_unstable_url(url):
            entry["last_status"] = "unverifiable"
            return "unverifiable", "GitHub HTML page (validator-unstable)", entry

        if not entry["etag"] and not entry["last_modified"]:
            entry["etag"] = new_etag
            entry["last_modified"] = new_last_modified
            entry["last_status"] = (
                "baseline_captured" if (new_etag or new_last_modified) else "unverifiable"
            )
            detail = (
                "captured baseline validators"
                if (new_etag or new_last_modified)
                else "no validators exposed"
            )
            return entry["last_status"], detail, entry

        classification, detail = _classify_head_200(stored, new_etag, new_last_modified)
        if new_etag:
            entry["etag"] = new_etag
        if new_last_modified:
            entry["last_modified"] = new_last_modified
        entry["last_status"] = classification
        return classification, detail, entry
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            if _is_unstable_url(url):
                entry["last_status"] = "unverifiable"
                return "unverifiable", "304 Not Modified on validator-unstable URL", entry
            entry["last_status"] = "no_drift"
            return "no_drift", "304 Not Modified", entry
        if exc.code in (404, 410):
            entry["last_status"] = "rot"
            return "rot", f"HTTP {exc.code}", entry
        if exc.code == 403:
            entry["last_status"] = "access_denied"
            return "access_denied", "HTTP 403", entry
        if exc.code == 429:
            entry["last_status"] = "rate_limited"
            return "rate_limited", "HTTP 429", entry
        if 500 <= exc.code < 600:
            entry["last_status"] = "server_error"
            return "server_error", f"HTTP {exc.code}", entry
        entry["last_status"] = "network_error"
        return "network_error", f"HTTP {exc.code}", entry
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        entry["last_status"] = "network_error"
        return "network_error", str(exc), entry


def check_source_drift(timeout: float = 10.0, delay: float = 2.0) -> list[dict]:
    """Advisory: check wiki/sources/ HTTP URLs for upstream changes.

    Uses HEAD requests with RFC 9110 conditional validators. First run captures
    baseline validators; subsequent runs report only drift and rot.
    """
    state = load_state()
    cache = state.get("source_drift_validators", {})
    if not isinstance(cache, dict):
        cache = {}

    issues: list[dict] = []
    per_domain_last_request: dict[str, float] = defaultdict(float)
    checked_urls: dict[str, tuple[str, str, dict[str, str]]] = {}

    for article in sorted(SOURCES_DIR.glob("*.md")):
        rel = article.relative_to(WIKI_DIR)
        article_urls = _extract_source_urls(article)
        if not article_urls:
            continue

        for url in article_urls:
            if url in checked_urls:
                classification, detail, entry = checked_urls[url]
            else:
                domain = _domain_key(url)
                last_request_at = per_domain_last_request.get(domain, 0.0)
                wait_for = delay - (time.monotonic() - last_request_at)
                if wait_for > 0:
                    time.sleep(wait_for)

                stored = cache.get(url, {})
                if not isinstance(stored, dict):
                    stored = {}

                classification, detail, entry = _check_source_url(url, stored, timeout=timeout)
                per_domain_last_request[domain] = time.monotonic()
                cache[url] = entry
                checked_urls[url] = (classification, detail, entry)

            if classification == "drift":
                issues.append(
                    {
                        "severity": "suggestion",
                        "check": "source_drift",
                        "file": str(rel).replace("\\", "/"),
                        "detail": f"drift: {url} — {detail}",
                    }
                )
            elif classification == "rot":
                issues.append(
                    {
                        "severity": "warning",
                        "check": "source_drift",
                        "file": str(rel).replace("\\", "/"),
                        "detail": f"rot: {url} — {detail}",
                    }
                )

    state["source_drift_validators"] = cache
    save_state(state)
    return issues


def check_missing_backlinks() -> list[dict]:
    """Check for asymmetric links: A→B but B doesn't link back to A."""
    issues: list[dict] = []
    for article in _wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        source_link = str(rel).replace(".md", "").replace("\\", "/")

        for link in _article_wikilinks(article):
            if link.startswith("daily/"):
                continue
            target_path = WIKI_DIR / f"{link}.md"
            if target_path.exists():
                if source_link not in _article_wikilinks(target_path):
                    issues.append(
                        {
                            "severity": "suggestion",
                            "check": "missing_backlink",
                            "file": str(rel),
                            "detail": f"[[{source_link}]] links to [[{link}]] but not vice versa",
                            "auto_fixable": True,
                        }
                    )
    return issues


def check_sparse_articles() -> list[dict]:
    """Check for articles with fewer than 200 words."""
    issues: list[dict] = []
    for article in _wiki_articles():
        word_count = _article_word_count(article)
        if word_count < 200:
            rel = article.relative_to(WIKI_DIR)
            issues.append(
                {
                    "severity": "suggestion",
                    "check": "sparse_article",
                    "file": str(rel),
                    "detail": f"Sparse article: {word_count} words (minimum recommended: 200)",
                }
            )
    return issues


def check_provenance_completeness() -> list[dict]:
    """Check concept/connection articles for confidence and Provenance metadata."""
    allowed_confidence = {"extracted", "inferred", "to-verify"}
    issues: list[dict] = []

    for article in _wiki_articles():
        fm = _article_frontmatter(article)
        page_type = fm.get("type", "").strip()
        if page_type not in {"concept", "connection"}:
            continue

        content = _article_text(article)
        rel = article.relative_to(WIKI_DIR)
        confidence = fm.get("confidence", "").strip()

        if confidence not in allowed_confidence:
            issues.append(
                {
                    "severity": "error",
                    "check": "provenance_completeness",
                    "file": str(rel),
                    "detail": (
                        "Concept/connection article must have confidence: "
                        "extracted | inferred | to-verify"
                    ),
                }
            )

        if "\n## Provenance" not in content:
            issues.append(
                {
                    "severity": "error",
                    "check": "provenance_completeness",
                    "file": str(rel),
                    "detail": "Concept/connection article must include a ## Provenance section",
                }
            )

    return issues


# ---------------------------------------------------------------------------
# LLM-based check (costs API credits)
# ---------------------------------------------------------------------------


async def check_contradictions() -> list[dict]:
    """Use LLM to detect contradictions across articles."""
    from claude_agent_sdk import ClaudeAgentOptions, query

    wiki_content = read_all_wiki_content()

    prompt = f"""Review this knowledge base for contradictions, inconsistencies, or
conflicting claims across articles.

## Knowledge Base

{wiki_content}

## Instructions

Look for:
- Direct contradictions (article A says X, article B says not-X)
- Inconsistent recommendations (different articles recommend conflicting approaches)
- Outdated information that conflicts with newer entries

For each issue found, output EXACTLY one line in this format:
CONTRADICTION: [file1] vs [file2] - description of the conflict
INCONSISTENCY: [file] - description of the inconsistency

If no issues found, output exactly: NO_ISSUES

Do NOT output anything else — no preamble, no explanation, just the formatted lines."""

    response = ""
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                allowed_tools=[],
                max_turns=2,
            ),
        ):
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        response += block.text
    except Exception as e:
        return [
            {
                "severity": "warning",
                "check": "contradiction",
                "file": "(system)",
                "detail": f"LLM contradiction check unavailable in current runtime: {e}",
            }
        ]

    issues: list[dict] = []
    if "NO_ISSUES" not in response:
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("CONTRADICTION:") or line.startswith("INCONSISTENCY:"):
                issues.append(
                    {
                        "severity": "warning",
                        "check": "contradiction",
                        "file": "(cross-article)",
                        "detail": line,
                    }
                )

    return issues


def check_contradictions_portable() -> list[dict]:
    """Run contradiction check in a deterministic runtime.

    In WSL, delegate the expensive LLM check to the Windows uv runtime so the
    result stays aligned with the primary project environment.
    """
    if not is_wsl():
        if has_claude_agent_sdk():
            return asyncio.run(check_contradictions())

        uv_bin = find_uv()
        if not uv_bin:
            return [
                {
                    "severity": "warning",
                    "check": "contradiction_runtime",
                    "file": "(system)",
                    "detail": "claude_agent_sdk unavailable and uv not found for contradiction delegation",
                }
            ]

        try:
            proc = subprocess.run(
                [
                    uv_bin,
                    "run",
                    "--directory",
                    str(ROOT_DIR),
                    "python",
                    str(Path(__file__).resolve()),
                    "--contradictions-only",
                    "--json",
                    "--internal-contradictions-runtime",
                ],
                text=True,
                capture_output=True,
                cwd=str(ROOT_DIR),
                timeout=240,
            )
        except Exception as exc:  # noqa: BLE001
            return [
                {
                    "severity": "warning",
                    "check": "contradiction_runtime",
                    "file": "(system)",
                    "detail": f"Contradiction delegation via uv failed: {exc}",
                }
            ]

        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
            return [
                {
                    "severity": "warning",
                    "check": "contradiction_runtime",
                    "file": "(system)",
                    "detail": f"Contradiction runtime via uv failed: {detail}",
                }
            ]

        try:
            return json.loads(proc.stdout.strip() or "[]")
        except json.JSONDecodeError as exc:
            return [
                {
                    "severity": "warning",
                    "check": "contradiction_runtime",
                    "file": "(system)",
                    "detail": f"Invalid contradiction JSON from uv runtime: {exc}",
                }
            ]

    windows_root = to_windows_path(ROOT_DIR)
    if not windows_root:
        return [
            {
                "severity": "warning",
                "check": "contradiction_runtime",
                "file": "(system)",
                "detail": "WSL contradiction check could not derive a Windows repo path",
            }
        ]

    ps_script = (
        "$ErrorActionPreference='Stop'; "
        "$env:PYTHONIOENCODING='utf-8'; "
        "$env:PYTHONUTF8='1'; "
        "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"Set-Location -LiteralPath '{windows_root}'; "
        f"uv run --directory '{windows_root}' python 'scripts\\lint.py' --contradictions-only --json"
    )

    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_script],
            text=False,
            capture_output=True,
            cwd=str(ROOT_DIR),
            timeout=240,
        )
    except Exception as exc:  # noqa: BLE001
        return [
            {
                "severity": "warning",
                "check": "contradiction_runtime",
                "file": "(system)",
                "detail": f"WSL contradiction delegation failed: {exc}",
            }
        ]

    if proc.returncode != 0:
        stderr = decode_windows_output(proc.stderr).strip()
        stdout = decode_windows_output(proc.stdout).strip()
        detail = stderr or stdout or f"exit {proc.returncode}"
        return [
            {
                "severity": "warning",
                "check": "contradiction_runtime",
                "file": "(system)",
                "detail": f"Windows contradiction runtime failed: {detail}",
            }
        ]

    try:
        stdout = decode_windows_output(proc.stdout).strip()
        return json.loads(stdout or "[]")
    except json.JSONDecodeError as exc:
        return [
            {
                "severity": "warning",
                "check": "contradiction_runtime",
                "file": "(system)",
                "detail": f"Invalid contradiction JSON from Windows runtime: {exc}",
            }
        ]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(all_issues: list[dict]) -> str:
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    suggestions = [i for i in all_issues if i["severity"] == "suggestion"]

    lines = [
        f"# Lint Report — {today_iso()}",
        "",
        f"**Total issues:** {len(all_issues)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        f"- Suggestions: {len(suggestions)}",
        "",
    ]

    for severity, items, marker in [
        ("Errors", errors, "x"),
        ("Warnings", warnings, "!"),
        ("Suggestions", suggestions, "?"),
    ]:
        if items:
            lines.append(f"## {severity}")
            lines.append("")
            for issue in items:
                fixable = " (auto-fixable)" if issue.get("auto_fixable") else ""
                lines.append(f"- **[{marker}]** `{issue['file']}` — {issue['detail']}{fixable}")
            lines.append("")

    if not all_issues:
        lines.append("All checks passed. Knowledge base is healthy.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint the knowledge base")
    parser.add_argument(
        "--structural-only",
        action="store_true",
        help="Skip LLM-based checks (contradictions) — faster and free",
    )
    parser.add_argument(
        "--contradictions-only",
        action="store_true",
        help="Run only the contradiction check",
    )
    parser.add_argument(
        "--source-drift",
        action="store_true",
        help="Check wiki/sources/ URLs for upstream drift or rot (network I/O)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print contradiction issues as JSON (for internal delegation)",
    )
    parser.add_argument(
        "--internal-contradictions-runtime",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.contradictions_only:
        if args.internal_contradictions_runtime:
            issues = asyncio.run(check_contradictions())
        else:
            issues = check_contradictions_portable()
        if args.json:
            print(json.dumps(issues, ensure_ascii=False))
        else:
            print(ADVISORY_BANNER)
            for issue in issues:
                print(issue["detail"])
        errors = sum(1 for i in issues if i["severity"] == "error")
        return 1 if errors > 0 else 0

    print("Running knowledge base lint checks...")
    all_issues: list[dict] = []

    checks: list[tuple[str, object]] = [
        ("Broken links", check_broken_links),
        ("Orphan pages", check_orphan_pages),
        ("Orphan sources", check_orphan_sources),
        ("Stale articles", check_stale_articles),
        ("Freshness review debt", check_freshness_review_debt),
        ("Missing backlinks", check_missing_backlinks),
        ("Sparse articles", check_sparse_articles),
        ("Provenance completeness", check_provenance_completeness),
    ]

    for name, check_fn in checks:
        print(f"  Checking: {name}...")
        issues = check_fn()
        all_issues.extend(issues)
        print(f"    Found {len(issues)} issue(s)")

    if args.source_drift:
        print("  Checking: Source drift (network)...")
        print(
            "  [ADVISORY] Source drift results are network-dependent and must not be used as a merge gate."
        )
        issues = check_source_drift()
        all_issues.extend(issues)
        print(f"    Found {len(issues)} issue(s)")
        print("  Skipping: Contradictions (--source-drift explicit network check)")
    elif not args.structural_only:
        print("  Checking: Contradictions (LLM)...")
        print(f"  {ADVISORY_BANNER}")
        issues = check_contradictions_portable()
        all_issues.extend(issues)
        print(f"    Found {len(issues)} issue(s)")
    else:
        print("  Skipping: Contradictions (--structural-only)")

    report = generate_report(all_issues)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"lint-{today_iso()}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")

    state = load_state()
    state["last_lint"] = now_iso()
    save_state(state)

    errors = sum(1 for i in all_issues if i["severity"] == "error")
    warnings = sum(1 for i in all_issues if i["severity"] == "warning")
    suggestions = sum(1 for i in all_issues if i["severity"] == "suggestion")
    print(f"\nResults: {errors} errors, {warnings} warnings, {suggestions} suggestions")

    if errors > 0:
        print("\nErrors found — knowledge base needs attention!")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
