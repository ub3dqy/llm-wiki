"""Lint: run health checks on the knowledge base."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import ipaddress
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import REPORTS_DIR, SOURCES_DIR, WIKI_DIR, now_iso, today_iso
from runtime_utils import find_uv, is_wsl
from utils import (
    daily_log_has_compile_signal,
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
SOURCE_DRIFT_REVIEW_LEDGER = ROOT_DIR / "docs" / "codex-tasks" / "source-drift-review-ledger.md"
ADVISORY_BANNER = "[ADVISORY] Contradiction check results are non-deterministic and must not be used as a merge gate."
_WIKI_ROOT = WIKI_DIR.resolve()

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
_LAST_SOURCE_DRIFT_SNAPSHOT: list[dict[str, str]] = []


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
        if not daily_log_has_compile_signal(log_path):
            continue
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
        if not daily_log_has_compile_signal(log_path):
            continue
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


def _normalize_domain_filter(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip().lower()
    if not raw:
        return ""
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    host = parsed.hostname or raw.split("/", 1)[0].split(":", 1)[0]
    return host.rstrip(".")


def _matches_domain_filter(url: str, domain_filter: str) -> bool:
    if not domain_filter:
        return True
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host == domain_filter


def _source_article_filter_label(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip().replace("\\", "/")
    if raw.startswith("wiki/"):
        raw = raw.removeprefix("wiki/")
    if raw.startswith("sources/"):
        raw = raw.removeprefix("sources/")
    if raw.endswith(".md"):
        raw = raw.removesuffix(".md")
    return raw.strip("/")


def _resolve_source_article_filter(value: str | None) -> Path | None:
    label = _source_article_filter_label(value)
    if not label:
        return None

    candidate = (SOURCES_DIR / f"{label}.md").resolve()
    sources_root = SOURCES_DIR.resolve()
    if not candidate.is_relative_to(sources_root):
        raise ValueError(f"source article is outside wiki/sources: {value!r}")
    if not candidate.exists():
        raise ValueError(f"source article not found: sources/{label}.md")
    return candidate


def _is_unstable_url(url: str) -> bool:
    return any(pattern.search(url) for pattern in _UNSTABLE_URL_PATTERNS)


_SSRF_REFUSED_DETAIL = "SSRF guard: target resolves to private/loopback/link-local/reserved IP"


def _is_ssrf_target(url: str) -> tuple[bool, str]:
    """Return whether a URL resolves to a non-public network target."""
    parsed = urlsplit(url)
    host = parsed.hostname
    if not host:
        return True, "invalid URL (no host)"

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True, _SSRF_REFUSED_DETAIL
        return False, ""

    try:
        addrinfo = socket.getaddrinfo(host, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False, ""

    for _family, _socktype, _proto, _canonname, sockaddr in addrinfo:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True, _SSRF_REFUSED_DETAIL
    return False, ""


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

    blocked, reason = _is_ssrf_target(url)
    if blocked:
        entry["last_status"] = "refused"
        return "refused", reason, entry

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


def check_source_drift(
    timeout: float = 10.0,
    delay: float = 2.0,
    *,
    domain: str | None = None,
    source_article: str | None = None,
    save: bool = True,
    progress: Callable[[dict[str, str], int], None] | None = None,
) -> list[dict]:
    """Advisory: check wiki/sources/ HTTP URLs for upstream changes.

    Uses HEAD requests with RFC 9110 conditional validators. First run captures
    baseline validators; subsequent runs report only drift and rot.
    """
    global _LAST_SOURCE_DRIFT_SNAPSHOT

    state = load_state()
    cache = state.get("source_drift_validators", {})
    if not isinstance(cache, dict):
        cache = {}

    issues: list[dict] = []
    snapshot_rows: list[dict[str, str]] = []
    per_domain_last_request: dict[str, float] = defaultdict(float)
    checked_urls: dict[str, tuple[str, str, dict[str, str]]] = {}
    domain_filter = _normalize_domain_filter(domain)
    source_article_filter = _resolve_source_article_filter(source_article)

    for article in sorted(SOURCES_DIR.glob("*.md")):
        if source_article_filter and article.resolve() != source_article_filter:
            continue

        rel = article.relative_to(WIKI_DIR)
        article_urls = _extract_source_urls(article)
        if not article_urls:
            continue

        for url in article_urls:
            if not _matches_domain_filter(url, domain_filter):
                continue

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

            row = {
                "file": str(rel).replace("\\", "/"),
                "url": url,
                "domain": _domain_key(url),
                "status": classification,
                "detail": detail,
            }
            snapshot_rows.append(row)
            if progress:
                progress(row, len(snapshot_rows))

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
            elif classification == "refused":
                issues.append(
                    {
                        "severity": "warning",
                        "check": "source_ssrf_refused",
                        "file": str(rel).replace("\\", "/"),
                        "detail": f"refused: {url} — {detail}",
                    }
                )

    _LAST_SOURCE_DRIFT_SNAPSHOT = snapshot_rows
    if save:
        state["source_drift_validators"] = cache
        save_state(state)
    return issues


def _markdown_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", r"\|")


def _source_drift_status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.get("status", "unknown")] += 1
    return counts


def write_source_drift_snapshot(
    rows: list[dict[str, str]],
    *,
    domain: str | None = None,
    source_article: str | None = None,
    export_only: bool = False,
) -> Path:
    """Write a durable source-drift snapshot report for review batching."""
    domain_filter = _normalize_domain_filter(domain)
    source_article_filter = _source_article_filter_label(source_article)
    label = "-".join(part for part in (domain_filter, source_article_filter) if part) or "all"
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "all"
    timestamp = now_iso().replace(":", "-")
    report_path = REPORTS_DIR / f"source-drift-{timestamp}-{safe_label}.md"

    counts = _source_drift_status_counts(rows)

    lines = [
        f"# Source Drift Snapshot — {now_iso()}",
        "",
        f"- Mode: {'export-only (validator state not saved)' if export_only else 'state-updating'}",
        f"- Domain filter: {domain_filter or 'all'}",
        f"- Source article filter: {source_article_filter or 'all'}",
        f"- Checked URL references: {len(rows)}",
        "",
        "## Status Counts",
        "",
    ]

    if counts:
        for status, count in sorted(counts.items()):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none: 0")

    lines.extend(
        [
            "",
            "## URLs",
            "",
            "| Status | Source | URL | Detail |",
            "|---|---|---|---|",
        ]
    )

    for row in rows:
        lines.append(
            "| "
            f"{_markdown_cell(row.get('status', ''))} | "
            f"{_markdown_cell(row.get('file', ''))} | "
            f"{_markdown_cell(row.get('url', ''))} | "
            f"{_markdown_cell(row.get('detail', ''))} |"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def write_source_drift_ledger_entry(
    rows: list[dict[str, str]],
    *,
    issues: list[dict] | None = None,
    domain: str | None = None,
    source_article: str | None = None,
    export_only: bool = False,
    ledger_path: Path | None = None,
) -> Path:
    """Append a durable source-drift review ledger entry with pending decisions."""
    ledger_path = ledger_path or SOURCE_DRIFT_REVIEW_LEDGER
    timestamp = now_iso()
    domain_filter = _normalize_domain_filter(domain)
    source_article_filter = _source_article_filter_label(source_article)
    counts = _source_drift_status_counts(rows)
    lint_issue_count = len(issues or [])
    actionable_rows = [row for row in rows if row.get("status") in {"drift", "rot", "refused"}]

    if ledger_path.exists():
        text = ledger_path.read_text(encoding="utf-8")
        lines = [text.rstrip(), ""]
    else:
        lines = [
            "# Source Drift Review Ledger",
            "",
            "Durable ledger for explicit source-drift maintenance runs.",
            "Entries created by tooling are pending manual review until a human records a decision.",
            "Do not use this ledger as automatic evidence for `reviewed:` frontmatter.",
            "",
        ]

    lines.extend(
        [
            f"## {timestamp} — scan pending review",
            "",
            f"- Mode: {'export-only (validator state not saved)' if export_only else 'state-updating'}",
            f"- Domain filter: {domain_filter or 'all'}",
            f"- Source article filter: {source_article_filter or 'all'}",
            f"- Checked URL references: {len(rows)}",
            f"- Lint issue rows: {lint_issue_count}",
            f"- Actionable review rows: {len(actionable_rows)}",
            "- Review state: pending manual review",
            "",
            "### Status Counts",
            "",
        ]
    )

    if counts:
        for status, count in sorted(counts.items()):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none: 0")

    lines.extend(["", "### Review Queue", ""])
    if actionable_rows:
        lines.extend(
            [
                "| Status | Source | URL | Detail | Review decision |",
                "|---|---|---|---|---|",
            ]
        )
        for row in actionable_rows:
            lines.append(
                "| "
                f"{_markdown_cell(row.get('status', ''))} | "
                f"{_markdown_cell(row.get('file', ''))} | "
                f"{_markdown_cell(row.get('url', ''))} | "
                f"{_markdown_cell(row.get('detail', ''))} | "
                "pending |"
            )
    else:
        lines.append("No drift, rot, or refused rows in this scan.")

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return ledger_path


def check_missing_backlinks() -> list[dict]:
    """Check for asymmetric links: A→B but B doesn't link back to A."""
    issues: list[dict] = []
    for article in _wiki_articles():
        rel = article.relative_to(WIKI_DIR)
        source_link = str(rel).replace(".md", "").replace("\\", "/")

        for link in _article_wikilinks(article):
            if link.startswith("daily/"):
                continue
            target_path = (WIKI_DIR / f"{link}.md").resolve()
            if target_path.is_relative_to(_WIKI_ROOT) and target_path.exists():
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


def check_project_frontmatter_shape() -> list[dict]:
    """Advisory: flag list-form `project:` for consistency and prevention."""
    issues: list[dict] = []
    for article in _wiki_articles():
        fm = _article_frontmatter(article)
        raw_project = str(fm.get("project", "") or "").strip()
        if not raw_project:
            continue
        if raw_project.startswith("[") and raw_project.endswith("]"):
            rel = article.relative_to(WIKI_DIR)
            issues.append(
                {
                    "severity": "suggestion",
                    "check": "project_frontmatter_shape",
                    "file": str(rel),
                    "detail": (
                        "List-form `project:` frontmatter detected; prefer scalar CSV form "
                        "like `project: a, b, c` for consistency and downstream simplicity"
                    ),
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
        "--domain",
        metavar="HOST",
        help="Limit --source-drift to source URLs on one exact host",
    )
    parser.add_argument(
        "--source-article",
        metavar="SLUG_OR_PATH",
        help="Limit --source-drift to one wiki/sources article",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="With --source-drift, write a snapshot without updating validator state",
    )
    parser.add_argument(
        "--ledger",
        action="store_true",
        help="With --source-drift, append a durable review ledger entry",
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

    if args.domain and not args.source_drift:
        parser.error("--domain requires --source-drift")
    if args.source_article and not args.source_drift:
        parser.error("--source-article requires --source-drift")
    if args.export_only and not args.source_drift:
        parser.error("--export-only requires --source-drift")
    if args.ledger and not args.source_drift:
        parser.error("--ledger requires --source-drift")

    source_article_filter: Path | None = None
    if args.source_article:
        try:
            source_article_filter = _resolve_source_article_filter(args.source_article)
        except ValueError as exc:
            parser.error(str(exc))

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
        ("Project frontmatter shape", check_project_frontmatter_shape),
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
        if args.domain:
            print(f"  Domain filter: {_normalize_domain_filter(args.domain)}")
        if source_article_filter:
            rel_source_article = source_article_filter.relative_to(WIKI_DIR)
            rel_source_article_text = str(rel_source_article).replace("\\", "/")
            print(f"  Source article filter: {rel_source_article_text}")
        if args.export_only:
            print("  Export-only mode: validator state will not be saved.")

        def print_source_drift_progress(row: dict[str, str], checked_count: int) -> None:
            print(
                "    "
                f"checked {checked_count}: "
                f"{row.get('status', 'unknown')} "
                f"{row.get('domain', 'unknown')} "
                f"({row.get('file', 'unknown')})"
            )

        issues = check_source_drift(
            domain=args.domain,
            source_article=args.source_article,
            save=not args.export_only,
            progress=print_source_drift_progress,
        )
        all_issues.extend(issues)
        print(f"    Found {len(issues)} issue(s)")
        snapshot_path = write_source_drift_snapshot(
            _LAST_SOURCE_DRIFT_SNAPSHOT,
            domain=args.domain,
            source_article=args.source_article,
            export_only=args.export_only,
        )
        print(f"    Snapshot saved to: {snapshot_path}")
        if args.ledger:
            ledger_path = write_source_drift_ledger_entry(
                _LAST_SOURCE_DRIFT_SNAPSHOT,
                issues=issues,
                domain=args.domain,
                source_article=args.source_article,
                export_only=args.export_only,
            )
            print(f"    Review ledger updated: {ledger_path}")
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
