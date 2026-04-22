"""Profiler for UserPromptSubmit hook retrieval hot path.

HYBRID design:
- Outer: inline-replicate find_relevant_articles skeleton with timers for
  article discovery, keyword extraction, phrase extraction, scoring loop,
  and sort/format.
- Inner: call the real score_article with monkey-patched internals
  (parse_frontmatter, Path.read_text, _strip_frontmatter) to time nested
  phases on the real production call path.

No production behavior changes. Measurement only.
"""

from __future__ import annotations

import functools
import sys
import time
from collections import defaultdict
from pathlib import Path as _Path

ROOT = _Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(ROOT / "scripts"))

import hook_utils  # noqa: E402
import shared_wiki_search  # noqa: E402

_timings: dict[str, float] = defaultdict(float)
_counts: dict[str, int] = defaultdict(int)
_bytes_read: list[int] = []


def _wrap(phase_name: str, func):
    """Wrap callable with cumulative timing accumulator."""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        _timings[phase_name] += time.perf_counter() - t0
        _counts[phase_name] += 1
        return result

    return wrapped


def _make_timed_read_text(original_read_text):
    """Wrapped Path.read_text that also accumulates bytes."""

    def wrapped(self, *args, **kwargs):
        t0 = time.perf_counter()
        result = original_read_text(self, *args, **kwargs)
        _timings["path_read_text"] += time.perf_counter() - t0
        _counts["path_read_text"] += 1
        try:
            _bytes_read.append(len(result.encode("utf-8")))
        except Exception:
            pass
        return result

    return wrapped


def profile_single_run(prompt: str) -> dict:
    """Hybrid profile: inline outer skeleton + real score_article."""
    _timings.clear()
    _counts.clear()
    _bytes_read.clear()

    orig_read = _Path.read_text
    orig_parse = hook_utils.parse_frontmatter
    orig_parse_sw = shared_wiki_search.parse_frontmatter
    orig_strip = shared_wiki_search._strip_frontmatter
    orig_score = shared_wiki_search.score_article

    _Path.read_text = _make_timed_read_text(orig_read)  # type: ignore[method-assign]
    hook_utils.parse_frontmatter = _wrap("parse_frontmatter", orig_parse)
    shared_wiki_search.parse_frontmatter = hook_utils.parse_frontmatter
    shared_wiki_search._strip_frontmatter = _wrap("strip_frontmatter", orig_strip)
    shared_wiki_search.score_article = _wrap("score_article", orig_score)

    try:
        t_total_start = time.perf_counter()

        t0 = time.perf_counter()
        article_paths = list(shared_wiki_search.WIKI_DIR.rglob("*.md"))
        _timings["article_discovery"] = time.perf_counter() - t0
        _counts["articles_scanned"] = len(article_paths)

        t0 = time.perf_counter()
        keywords = shared_wiki_search.extract_keywords(prompt)
        _timings["extract_keywords"] = time.perf_counter() - t0
        _counts["keyword_count"] = len(keywords)

        t0 = time.perf_counter()
        phrases = shared_wiki_search.build_search_phrases(prompt)
        _timings["build_search_phrases"] = time.perf_counter() - t0
        _counts["phrase_count"] = len(phrases)

        t0 = time.perf_counter()
        scored: list[tuple[_Path, int]] = []
        if keywords:
            for article in article_paths:
                score = shared_wiki_search.score_article(
                    article, keywords, phrases, project_name=None
                )
                if score > 0:
                    scored.append((article, score))
        _timings["scoring_loop"] = time.perf_counter() - t0
        _counts["articles_scored_positive"] = len(scored)

        t0 = time.perf_counter()
        scored.sort(key=lambda x: (x[1], str(x[0]).lower()), reverse=True)
        top_n = scored[: shared_wiki_search.MAX_ARTICLES]
        _timings["sort_format"] = time.perf_counter() - t0

        total_sec = time.perf_counter() - t_total_start
    finally:
        _Path.read_text = orig_read  # type: ignore[method-assign]
        hook_utils.parse_frontmatter = orig_parse
        shared_wiki_search.parse_frontmatter = orig_parse_sw
        shared_wiki_search._strip_frontmatter = orig_strip
        shared_wiki_search.score_article = orig_score

    return {
        "timings_sec": dict(_timings),
        "counts": dict(_counts),
        "total_sec": total_sec,
        "total_bytes_read": sum(_bytes_read),
        "matches": [(str(p), s) for p, s in top_n],
    }


def format_breakdown(run_id: int, result: dict) -> str:
    lines = [f"=== Run {run_id} ==="]
    total = result["total_sec"]
    lines.append(f"TOTAL (find_relevant_articles skeleton end-to-end): {total * 1000:.1f}ms")
    lines.append("")
    lines.append("OUTER phases (top-level; sum ≈ total, plus tiny timer overhead):")
    outer_order = [
        ("article_discovery", "article_discovery (rglob)"),
        ("extract_keywords", "extract_keywords"),
        ("build_search_phrases", "build_search_phrases"),
        ("scoring_loop", "scoring_loop (real score_article called N times)"),
        ("sort_format", "sort_format"),
    ]
    for key, label in outer_order:
        t_sec = result["timings_sec"].get(key, 0)
        pct = (t_sec / total * 100) if total > 0 else 0
        lines.append(f"  {label}: {t_sec * 1000:.1f}ms ({pct:.1f}%)")
    lines.append("")
    lines.append(
        "INNER phases (nested inside scoring_loop -> score_article; children of scoring_loop):"
    )
    inner_order = [
        ("score_article", "score_article (sum of N wrapped invocations)"),
        ("parse_frontmatter", "  parse_frontmatter (child of score_article)"),
        (
            "path_read_text",
            "  path_read_text (child of parse_frontmatter + score_article body read)",
        ),
        ("strip_frontmatter", "  strip_frontmatter (child of score_article)"),
    ]
    scoring_t = result["timings_sec"].get("scoring_loop", 0)
    for key, label in inner_order:
        t_sec = result["timings_sec"].get(key, 0)
        calls = result["counts"].get(key, 0)
        if key == "score_article":
            lines.append(f"  {label}: {t_sec * 1000:.1f}ms — {calls} calls")
        else:
            pct_of_scoring = (t_sec / scoring_t * 100) if scoring_t > 0 else 0
            lines.append(
                f"  {label}: {t_sec * 1000:.1f}ms ({pct_of_scoring:.1f}% of scoring_loop) — {calls} calls"
            )
    lines.append("")
    lines.append("Counts:")
    lines.append(f"  articles_scanned: {result['counts'].get('articles_scanned', 0)}")
    lines.append(f"  keyword_count: {result['counts'].get('keyword_count', 0)}")
    lines.append(f"  phrase_count: {result['counts'].get('phrase_count', 0)}")
    lines.append(
        "  articles_scored_positive (before top-N cap): "
        f"{result['counts'].get('articles_scored_positive', 0)}"
    )
    total_bytes_read = result["total_bytes_read"]
    lines.append(
        f"  total_bytes_read: {total_bytes_read:,} bytes ({total_bytes_read / 1024:.1f} KiB)"
    )
    lines.append(f"  matches_returned (after top-N cap): {len(result['matches'])}")
    lines.append("")
    lines.append("Top matches:")
    for path, score in result["matches"]:
        name = _Path(path).name
        lines.append(f"  {name} | score={score}")
    return "\n".join(lines)


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "wiki freshness plan implementation"
    print(f"Profiling prompt: {prompt!r}")
    print(f"Wiki dir: {shared_wiki_search.WIKI_DIR}")
    print()
    print("Warmup run...")
    profile_single_run(prompt)
    print()

    for i in range(1, 4):
        result = profile_single_run(prompt)
        print(format_breakdown(i, result))
        print()


if __name__ == "__main__":
    main()
