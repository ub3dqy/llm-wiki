"""Lint: run health checks on the knowledge base."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import REPORTS_DIR, WIKI_DIR, now_iso, today_iso
from runtime_utils import find_uv, is_wsl
from utils import (
    extract_wikilinks,
    file_hash,
    frontmatter_sources_include_prefix,
    get_article_word_count,
    list_daily_logs,
    list_wiki_articles,
    load_state,
    parse_frontmatter,
    read_all_wiki_content,
    save_state,
    wiki_article_exists,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ADVISORY_BANNER = (
    "[ADVISORY] Contradiction check results are non-deterministic and must not be used as a merge gate."
)

_ARTICLE_LIST_CACHE: list[Path] | None = None
_ARTICLE_TEXT_CACHE: dict[Path, str] = {}
_ARTICLE_FRONTMATTER_CACHE: dict[Path, dict[str, str]] = {}
_ARTICLE_WIKILINKS_CACHE: dict[Path, list[str]] = {}
_ARTICLE_WORD_COUNT_CACHE: dict[Path, int] = {}
_INBOUND_LINK_COUNT_CACHE: dict[str, int] | None = None


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
                issues.append({
                    "severity": "error",
                    "check": "broken_link",
                    "file": str(rel),
                    "detail": f"Broken link: [[{link}]] — target does not exist",
                })
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
            issues.append({
                "severity": "warning",
                "check": "orphan_page",
                "file": str(rel),
                "detail": f"Orphan page: no other articles link to [[{link_target}]]",
            })
    return issues


def check_orphan_sources() -> list[dict]:
    """Check for daily logs that haven't been compiled yet."""
    state = load_state()
    ingested = state.get("ingested", {})
    issues: list[dict] = []
    for log_path in list_daily_logs():
        if log_path.name not in ingested:
            issues.append({
                "severity": "warning",
                "check": "orphan_source",
                "file": f"daily/{log_path.name}",
                "detail": f"Uncompiled daily log: {log_path.name} has not been ingested",
            })
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
                issues.append({
                    "severity": "warning",
                    "check": "stale_article",
                    "file": f"daily/{rel}",
                    "detail": f"Stale: {rel} has changed since last compilation",
                })
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
            issues.append({
                "severity": "warning",
                "check": "freshness_superseded_without_link",
                "file": rel_str,
                "detail": f"{rel_str}: status=superseded but no superseded_by wikilink",
            })
            continue

        reviewed_str = fm.get("reviewed", "")
        max_age = source_max_age if rel_str.startswith("sources/") else concept_max_age

        if not reviewed_str:
            issues.append({
                "severity": "suggestion",
                "check": "freshness_never_reviewed",
                "file": rel_str,
                "detail": f"{rel_str}: no 'reviewed' field — consider adding review date",
            })
            continue

        try:
            reviewed_date = date.fromisoformat(str(reviewed_str))
        except (TypeError, ValueError):
            issues.append({
                "severity": "warning",
                "check": "freshness_malformed_reviewed",
                "file": rel_str,
                "detail": f"{rel_str}: 'reviewed' field not valid ISO date (got {reviewed_str!r})",
            })
            continue

        age = (today - reviewed_date).days
        if today - reviewed_date > timedelta(days=max_age):
            issues.append({
                "severity": "suggestion",
                "check": "freshness_review_overdue",
                "file": rel_str,
                "detail": f"{rel_str}: last reviewed {age} days ago (max {max_age} for {rel.parts[0]}/)",
            })

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
                    issues.append({
                        "severity": "suggestion",
                        "check": "missing_backlink",
                        "file": str(rel),
                        "detail": f"[[{source_link}]] links to [[{link}]] but not vice versa",
                        "auto_fixable": True,
                    })
    return issues


def check_sparse_articles() -> list[dict]:
    """Check for articles with fewer than 200 words."""
    issues: list[dict] = []
    for article in _wiki_articles():
        word_count = _article_word_count(article)
        if word_count < 200:
            rel = article.relative_to(WIKI_DIR)
            issues.append({
                "severity": "suggestion",
                "check": "sparse_article",
                "file": str(rel),
                "detail": f"Sparse article: {word_count} words (minimum recommended: 200)",
            })
    return issues


def check_provenance_completeness() -> list[dict]:
    """Check concept/connection articles for confidence and Provenance metadata."""
    allowed_confidence = {"extracted", "inferred", "to-verify"}
    issues: list[dict] = []

    for article in _wiki_articles():
        fm = _article_frontmatter(article)
        page_type = fm.get("type", "").strip()
        sources = fm.get("sources", "")
        if page_type not in {"concept", "connection"}:
            continue

        content = _article_text(article)
        rel = article.relative_to(WIKI_DIR)
        confidence = fm.get("confidence", "").strip()

        if confidence not in allowed_confidence:
            issues.append({
                "severity": "error",
                "check": "provenance_completeness",
                "file": str(rel),
                "detail": (
                    "Concept/connection article must have confidence: "
                    "extracted | inferred | to-verify"
                ),
            })

        if "\n## Provenance" not in content:
            issues.append({
                "severity": "error",
                "check": "provenance_completeness",
                "file": str(rel),
                "detail": "Concept/connection article must include a ## Provenance section",
            })

    return issues


# ---------------------------------------------------------------------------
# LLM-based check (costs API credits)
# ---------------------------------------------------------------------------


async def check_contradictions() -> list[dict]:
    """Use LLM to detect contradictions across articles."""
    from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, TextBlock, query

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
        return [{
            "severity": "warning",
            "check": "contradiction",
            "file": "(system)",
            "detail": f"LLM contradiction check unavailable in current runtime: {e}",
        }]

    issues: list[dict] = []
    if "NO_ISSUES" not in response:
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("CONTRADICTION:") or line.startswith("INCONSISTENCY:"):
                issues.append({
                    "severity": "warning",
                    "check": "contradiction",
                    "file": "(cross-article)",
                    "detail": line,
                })

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
            return [{
                "severity": "warning",
                "check": "contradiction",
                "file": "(system)",
                "detail": "claude_agent_sdk unavailable and uv not found for contradiction delegation",
            }]

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
            return [{
                "severity": "warning",
                "check": "contradiction",
                "file": "(system)",
                "detail": f"Contradiction delegation via uv failed: {exc}",
            }]

        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
            return [{
                "severity": "warning",
                "check": "contradiction",
                "file": "(system)",
                "detail": f"Contradiction runtime via uv failed: {detail}",
            }]

        try:
            return json.loads(proc.stdout.strip() or "[]")
        except json.JSONDecodeError as exc:
            return [{
                "severity": "warning",
                "check": "contradiction",
                "file": "(system)",
                "detail": f"Invalid contradiction JSON from uv runtime: {exc}",
            }]

    windows_root = to_windows_path(ROOT_DIR)
    if not windows_root:
        return [{
            "severity": "warning",
            "check": "contradiction",
            "file": "(system)",
            "detail": "WSL contradiction check could not derive a Windows repo path",
        }]

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
        return [{
            "severity": "warning",
            "check": "contradiction",
            "file": "(system)",
            "detail": f"WSL contradiction delegation failed: {exc}",
        }]

    if proc.returncode != 0:
        stderr = decode_windows_output(proc.stderr).strip()
        stdout = decode_windows_output(proc.stdout).strip()
        detail = stderr or stdout or f"exit {proc.returncode}"
        return [{
            "severity": "warning",
            "check": "contradiction",
            "file": "(system)",
            "detail": f"Windows contradiction runtime failed: {detail}",
        }]

    try:
        stdout = decode_windows_output(proc.stdout).strip()
        return json.loads(stdout or "[]")
    except json.JSONDecodeError as exc:
        return [{
            "severity": "warning",
            "check": "contradiction",
            "file": "(system)",
            "detail": f"Invalid contradiction JSON from Windows runtime: {exc}",
        }]


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

    if not args.structural_only:
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
