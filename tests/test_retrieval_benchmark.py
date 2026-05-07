from __future__ import annotations

import retrieval_benchmark as rb


def test_normalize_slug_accepts_paths_and_wikilinks() -> None:
    assert rb.normalize_slug("[[wiki/concepts/foo.md|Foo]]") == "concepts/foo"
    assert rb.normalize_slug("wiki/concepts/bar.md") == "concepts/bar"
    assert rb.normalize_slug("concepts/baz") == "concepts/baz"


def test_reciprocal_rank_returns_first_expected_match() -> None:
    matches = (("concepts/a", 10), ("concepts/b", 8), ("concepts/c", 6))
    assert rb.reciprocal_rank(matches, ("concepts/b", "concepts/c")) == 0.5
    assert rb.reciprocal_rank(matches, ("concepts/x",)) == 0.0
    assert rb.reciprocal_rank(matches, ()) == 0.0


def test_summarize_results_reports_quality_metrics() -> None:
    results = [
        rb.BenchmarkResult(
            prompt="one",
            expected=("concepts/a",),
            project=None,
            matches=(("concepts/a", 10),),
            latency_ms=10.0,
        ),
        rb.BenchmarkResult(
            prompt="two",
            expected=("concepts/b",),
            project=None,
            matches=(("concepts/x", 9), ("concepts/b", 5)),
            latency_ms=30.0,
        ),
        rb.BenchmarkResult(
            prompt="three",
            expected=(),
            project=None,
            matches=(),
            latency_ms=20.0,
        ),
    ]

    summary = rb.summarize_results(results)

    assert summary["case_count"] == 3
    assert summary["expected_case_count"] == 2
    assert summary["latency_avg_ms"] == 20.0
    assert summary["latency_max_ms"] == 30.0
    assert summary["top1_hits"] == 1
    assert summary["any_hits"] == 2
    assert summary["mrr"] == 0.75
