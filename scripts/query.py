"""Query: search the knowledge base and optionally file answers as Q&A articles."""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INDEX_FILE, LOG_FILE, QA_DIR, WIKI_DIR, now_iso
from utils import list_wiki_articles, load_state, parse_frontmatter, read_wiki_index, save_state

ROOT_DIR = Path(__file__).resolve().parent.parent
MAX_QUERY_CANDIDATES = 8

STOP_WORDS = {
    "and",
    "are",
    "for",
    "how",
    "that",
    "the",
    "this",
    "what",
    "with",
    "где",
    "для",
    "есть",
    "как",
    "или",
    "можно",
    "над",
    "нужно",
    "под",
    "при",
    "про",
    "что",
    "это",
}


def tokenize(text: str) -> set[str]:
    """Extract lightweight search tokens from English/Russian text."""
    words = re.findall(r"[\w-]+", text.lower(), flags=re.UNICODE)
    return {word for word in words if len(word) >= 3 and word not in STOP_WORDS}


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from a markdown article."""
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3 :].lstrip()


def score_query_candidate(path: Path, tokens: set[str]) -> int:
    """Score an article for no-cost query preview and prompt candidates."""
    fm = parse_frontmatter(path)
    rel = path.relative_to(WIKI_DIR)
    slug = str(rel).replace("\\", "/").replace(".md", "")
    title = fm.get("title", "")
    tags = fm.get("tags", "")
    project = fm.get("project", "")
    body = strip_frontmatter(path.read_text(encoding="utf-8"))[:1200]

    title_text = title.lower()
    slug_text = slug.replace("-", " ").replace("_", " ").lower()
    meta_text = f"{tags} {project}".lower()
    body_text = body.lower()

    score = 0
    for token in tokens:
        if token in title_text:
            score += 8
        if token in slug_text:
            score += 6
        if token in meta_text:
            score += 4
        if token in body_text:
            score += 2

    status = (fm.get("status", "active") or "active").lower()
    freshness_factor = {
        "active": 1.0,
        "stale": 0.7,
        "superseded": 0.3,
        "archived": 0.05,
    }.get(status, 1.0)

    return int(score * freshness_factor)


def build_query_candidates(
    question: str, limit: int = MAX_QUERY_CANDIDATES
) -> list[dict[str, str | int]]:
    """Return likely relevant articles with confidence metadata."""
    tokens = tokenize(question)
    if not tokens:
        return []

    candidates: list[dict[str, str | int]] = []
    for article in list_wiki_articles():
        score = score_query_candidate(article, tokens)
        if score <= 0:
            continue
        rel = article.relative_to(WIKI_DIR)
        slug = str(rel).replace("\\", "/").replace(".md", "")
        fm = parse_frontmatter(article)
        candidates.append(
            {
                "slug": slug,
                "title": fm.get("title", slug),
                "score": score,
                "confidence": fm.get("confidence", "unspecified"),
                "sources": fm.get("sources", ""),
            }
        )

    candidates.sort(key=lambda item: (int(item["score"]), str(item["slug"])), reverse=True)
    return candidates[:limit]


def format_query_candidates(candidates: list[dict[str, str | int]]) -> str:
    """Format candidate articles for preview output and LLM prompt context."""
    if not candidates:
        return "(no local candidates found)"
    lines = []
    for item in candidates:
        source_suffix = f", sources: {item['sources']}" if item.get("sources") else ""
        lines.append(
            f"- [[{item['slug']}]] — {item['title']} "
            f"(score: {item['score']}, confidence: {item['confidence']}{source_suffix})"
        )
    return "\n".join(lines)


def preview_query(question: str) -> str:
    """Build a no-cost query preview without starting Agent SDK."""
    candidates = build_query_candidates(question)
    return (
        "Query preview (no Agent SDK call, no state update)\n"
        f"Question: {question}\n\n"
        "Candidate articles:\n"
        f"{format_query_candidates(candidates)}\n\n"
        "Answering guidance:\n"
        "- Read candidate articles before answering.\n"
        "- Use frontmatter `confidence` and `## Provenance` to separate extracted facts from inferred synthesis.\n"
        "- Call out `to-verify` claims explicitly instead of presenting them as settled."
    )


async def run_query(question: str, file_back: bool = False) -> str:
    """Query the knowledge base. Optionally file the answer as a Q&A article."""
    from claude_agent_sdk import ClaudeAgentOptions, query

    wiki_index = read_wiki_index()
    candidate_articles = format_query_candidates(build_query_candidates(question))

    tools = ["Read", "Glob", "Grep"]
    if file_back:
        tools.extend(["Write", "Edit"])

    file_back_instructions = ""
    if file_back:
        timestamp = now_iso()
        file_back_instructions = f"""

## File Back Instructions

After answering, do the following:
1. Create a Q&A article at {QA_DIR}/ with a slugified filename
   (e.g., wiki/qa/how-to-handle-auth-redirects.md)
2. Use YAML frontmatter: title, type: qa, question, consulted_articles, filed: {timestamp[:10]}
3. Update {INDEX_FILE} with a new entry under the Q&A section
4. Append to {LOG_FILE}:
   ## [{timestamp}] query (filed) | question summary
   - Question: {question}
   - Consulted: [[list of articles read]]
   - Filed to: [[qa/article-name]]
"""

    prompt = f"""You are a knowledge base query engine. Answer the user's question by
consulting the knowledge base.

## How to Answer

1. Read the wiki index below — it lists every article with a one-line summary
2. Review the local candidate list below, then identify any additional relevant articles from the index
3. Use the Read tool to read candidate/relevant articles (they are at {WIKI_DIR}/<section>/<slug>.md)
4. Use Grep to search for related terms across the wiki/ directory if needed
5. Inspect each article's frontmatter `confidence` and its `## Provenance` section when present
6. Synthesize a clear, thorough answer
7. Cite sources using [[wikilinks]] (e.g., [[concepts/supabase-auth]])
8. If the knowledge base doesn't contain relevant information, say so honestly

## Provenance Rules

- Treat `confidence: extracted` as directly supported by listed sources
- Treat `confidence: inferred` as synthesized knowledge; useful, but label it as inference when it matters
- Treat `confidence: to-verify` as uncertain and explicitly call out the verification gap
- Do not flatten all wiki content into equal certainty
- If an answer mixes extracted and inferred material, include a short reliability note
- Prefer article `## Provenance` details over your own assumptions

## Local Candidate Articles

{candidate_articles}

## Wiki Index

{wiki_index}

## Question

{question}
{file_back_instructions}"""

    answer = ""
    cost = 0.0

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=tools,
                permission_mode="acceptEdits",
                max_turns=15,
            ),
        ):
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        answer += block.text
            if hasattr(message, "total_cost_usd"):
                cost = message.total_cost_usd or 0.0
    except Exception as e:
        answer = f"Error querying knowledge base: {e}"

    # Update state
    state = load_state()
    state["query_count"] = state.get("query_count", 0) + 1
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the personal knowledge base")
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--file-back",
        action="store_true",
        help="File the answer back as a Q&A article",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show local candidate articles and provenance guidance without starting Agent SDK",
    )
    args = parser.parse_args()

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    if args.preview:
        print(preview_query(args.question))
        return

    answer = asyncio.run(run_query(args.question, file_back=args.file_back))
    print(answer)

    if args.file_back:
        print("\n" + "-" * 60)
        qa_count = len(list(QA_DIR.glob("*.md"))) if QA_DIR.exists() else 0
        print(f"Answer filed to wiki/qa/ ({qa_count} Q&A articles total)")


if __name__ == "__main__":
    main()
