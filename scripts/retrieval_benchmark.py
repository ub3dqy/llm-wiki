"""Benchmark wiki retrieval quality and latency.

This is intentionally dependency-free. It measures the current production
UserPromptSubmit retrieval path before any qmd/BM25/vector replacement is
considered.

Usage:
    uv run python scripts/retrieval_benchmark.py
    uv run python scripts/retrieval_benchmark.py --json
    uv run python scripts/retrieval_benchmark.py --prompt "codex stop hook reliability"
    uv run python scripts/retrieval_benchmark.py --cases-file retrieval-cases.json

Cases file format:
[
  {
    "prompt": "что wiki знает про llm-wiki-architecture",
    "expected": ["concepts/llm-wiki-architecture"],
    "project": "memory-claude"
  }
]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(ROOT / "scripts"))

import shared_wiki_search  # noqa: E402
from config import WIKI_DIR  # noqa: E402


@dataclass(frozen=True)
class BenchmarkCase:
    prompt: str
    expected: tuple[str, ...] = ()
    project: str | None = None


@dataclass(frozen=True)
class BenchmarkResult:
    prompt: str
    expected: tuple[str, ...]
    project: str | None
    matches: tuple[tuple[str, int], ...]
    latency_ms: float


DEFAULT_CASES = (
    BenchmarkCase(
        prompt="что wiki знает про llm-wiki-architecture",
        expected=("concepts/llm-wiki-architecture",),
        project="memory-claude",
    ),
    BenchmarkCase(
        prompt="retrieval quality gaps and BM25 IDF phase",
        expected=("concepts/wiki-retrieval-quality-gaps",),
        project="memory-claude",
    ),
    BenchmarkCase(
        prompt="doctor health metric design",
        expected=("concepts/doctor-health-metric-design",),
        project="memory-claude",
    ),
    BenchmarkCase(
        prompt="codex stop hook reliability",
        expected=("concepts/codex-stop-hook-reliability",),
        project="memory-claude",
    ),
    BenchmarkCase(
        prompt="dependency bump verification workflow",
        expected=("concepts/dependency-bump-verification-workflow",),
        project="memory-claude",
    ),
)


def normalize_slug(value: str) -> str:
    """Normalize wiki slug/path input for benchmark expected values."""
    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("[[") and normalized.endswith("]]"):
        normalized = normalized[2:-2].split("|", 1)[0]
    if normalized.startswith("wiki/"):
        normalized = normalized[len("wiki/") :]
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    return normalized.strip("/")


def load_cases(path: Path) -> list[BenchmarkCase]:
    """Load benchmark cases from a JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("cases file must contain a JSON list")

    cases: list[BenchmarkCase] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"case {idx} must be an object")
        prompt = item.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"case {idx} must include a non-empty prompt")

        expected_raw = item.get("expected", [])
        if isinstance(expected_raw, str):
            expected_raw = [expected_raw]
        if not isinstance(expected_raw, list) or not all(
            isinstance(value, str) for value in expected_raw
        ):
            raise ValueError(f"case {idx} expected must be a string or list of strings")

        project = item.get("project")
        if project is not None and not isinstance(project, str):
            raise ValueError(f"case {idx} project must be a string when provided")

        cases.append(
            BenchmarkCase(
                prompt=prompt.strip(),
                expected=tuple(normalize_slug(value) for value in expected_raw),
                project=project,
            )
        )
    return cases


def _slug_for_match(path: Path) -> str:
    return str(path.relative_to(WIKI_DIR)).replace("\\", "/").replace(".md", "")


def run_case(case: BenchmarkCase) -> BenchmarkResult:
    """Run one benchmark case against production hook retrieval."""
    start = time.perf_counter()
    matches = shared_wiki_search.find_relevant_articles(
        case.prompt,
        wiki_dir=WIKI_DIR,
        project_name=case.project,
    )
    latency_ms = (time.perf_counter() - start) * 1000
    normalized_matches = tuple((_slug_for_match(path), score) for path, score in matches)

    return BenchmarkResult(
        prompt=case.prompt,
        expected=case.expected,
        project=case.project,
        matches=normalized_matches,
        latency_ms=latency_ms,
    )


def reciprocal_rank(matches: tuple[tuple[str, int], ...], expected: tuple[str, ...]) -> float:
    """Return reciprocal rank for the first expected match, or 0.0."""
    if not expected:
        return 0.0
    expected_set = set(expected)
    for idx, (slug, _score) in enumerate(matches, start=1):
        if slug in expected_set:
            return 1.0 / idx
    return 0.0


def summarize_results(results: list[BenchmarkResult]) -> dict[str, Any]:
    """Summarize latency and quality metrics."""
    latencies = [result.latency_ms for result in results]
    expected_results = [result for result in results if result.expected]
    top1_hits = sum(
        1
        for result in expected_results
        if result.matches and result.matches[0][0] in set(result.expected)
    )
    any_hits = sum(
        1
        for result in expected_results
        if set(result.expected).intersection(slug for slug, _score in result.matches)
    )
    mrr = (
        statistics.fmean(
            reciprocal_rank(result.matches, result.expected) for result in expected_results
        )
        if expected_results
        else 0.0
    )

    return {
        "case_count": len(results),
        "expected_case_count": len(expected_results),
        "latency_avg_ms": statistics.fmean(latencies) if latencies else 0.0,
        "latency_max_ms": max(latencies) if latencies else 0.0,
        "top1_hits": top1_hits,
        "any_hits": any_hits,
        "mrr": mrr,
    }


def result_to_dict(result: BenchmarkResult) -> dict[str, Any]:
    return {
        "prompt": result.prompt,
        "project": result.project,
        "expected": list(result.expected),
        "matches": [{"slug": slug, "score": score} for slug, score in result.matches],
        "latency_ms": result.latency_ms,
        "reciprocal_rank": reciprocal_rank(result.matches, result.expected),
    }


def format_text_report(results: list[BenchmarkResult]) -> str:
    """Format a human-readable benchmark report."""
    summary = summarize_results(results)
    lines = [
        "Retrieval benchmark",
        f"Wiki dir: {WIKI_DIR}",
        f"Cases: {summary['case_count']} ({summary['expected_case_count']} with expected slugs)",
        (f"Latency: avg {summary['latency_avg_ms']:.1f}ms, max {summary['latency_max_ms']:.1f}ms"),
    ]
    if summary["expected_case_count"]:
        lines.append(
            "Quality: "
            f"top1 {summary['top1_hits']}/{summary['expected_case_count']}, "
            f"any {summary['any_hits']}/{summary['expected_case_count']}, "
            f"MRR {summary['mrr']:.3f}"
        )

    lines.append("")
    for idx, result in enumerate(results, start=1):
        lines.append(f"{idx}. {result.prompt}")
        if result.expected:
            lines.append(f"   expected: {', '.join(result.expected)}")
        lines.append(f"   latency: {result.latency_ms:.1f}ms")
        if result.matches:
            for rank, (slug, score) in enumerate(result.matches, start=1):
                marker = "*" if slug in set(result.expected) else " "
                lines.append(f"   {marker} {rank}. [[{slug}]] score={score}")
        else:
            lines.append("     no matches")
    return "\n".join(lines)


def build_cases_from_args(args: argparse.Namespace) -> list[BenchmarkCase]:
    """Build benchmark cases from CLI args."""
    cases: list[BenchmarkCase] = []
    if args.cases_file:
        cases.extend(load_cases(Path(args.cases_file)))
    if args.prompt:
        cases.extend(BenchmarkCase(prompt=prompt, project=args.project) for prompt in args.prompt)
    if not cases:
        cases = list(DEFAULT_CASES)
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark wiki retrieval")
    parser.add_argument(
        "--cases-file",
        help="JSON file with benchmark cases: prompt, expected, optional project",
    )
    parser.add_argument(
        "--prompt",
        action="append",
        help="Prompt to benchmark without expected slug; repeat as needed",
    )
    parser.add_argument("--project", help="Project hint for --prompt cases")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    cases = build_cases_from_args(args)
    results = [run_case(case) for case in cases]

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summarize_results(results),
                    "results": [result_to_dict(result) for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(format_text_report(results))


if __name__ == "__main__":
    main()
