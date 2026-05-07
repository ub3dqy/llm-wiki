"""Query: search the knowledge base and optionally file answers as Q&A articles."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INDEX_FILE, LOG_FILE, QA_DIR, WIKI_AGENT_BACKEND, WIKI_DIR, now_iso
from utils import (
    list_wiki_articles,
    load_state,
    parse_frontmatter_from_text,
    parse_frontmatter_list,
    read_wiki_index,
    save_state,
    slugify,
)

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


def _score_query_candidate_with_frontmatter(
    path: Path, tokens: set[str]
) -> tuple[int, dict[str, str]]:
    raw = path.read_text(encoding="utf-8")
    fm = parse_frontmatter_from_text(raw)
    rel = path.relative_to(WIKI_DIR)
    slug = str(rel).replace("\\", "/").replace(".md", "")
    title = fm.get("title", "")
    tags = fm.get("tags", "")
    project = " ".join(parse_frontmatter_list(fm.get("project", "")))
    body = strip_frontmatter(raw)[:1200]

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

    return int(score * freshness_factor), fm


def score_query_candidate(path: Path, tokens: set[str]) -> int:
    """Score an article for no-cost query preview and prompt candidates."""
    score, _ = _score_query_candidate_with_frontmatter(path, tokens)
    return score


def build_query_candidates(
    question: str, limit: int = MAX_QUERY_CANDIDATES
) -> list[dict[str, str | int]]:
    """Return likely relevant articles with confidence metadata."""
    tokens = tokenize(question)
    if not tokens:
        return []

    candidates: list[dict[str, str | int]] = []
    for article in list_wiki_articles():
        score, fm = _score_query_candidate_with_frontmatter(article, tokens)
        if score <= 0:
            continue
        rel = article.relative_to(WIKI_DIR)
        slug = str(rel).replace("\\", "/").replace(".md", "")
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


def _frontmatter_string(value: str) -> str:
    """Return a YAML-safe inline string using JSON quoting rules."""
    return json.dumps(value, ensure_ascii=False)


def _frontmatter_list(values: list[str]) -> str:
    """Return a YAML-safe inline list using JSON string quoting."""
    return "[" + ", ".join(_frontmatter_string(value) for value in values) + "]"


def normalize_article_slug(value: str) -> str:
    """Normalize user-provided wiki article references to index-style slugs."""
    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("[[") and normalized.endswith("]]"):
        normalized = normalized[2:-2]
    normalized = normalized.split("|", 1)[0]
    if normalized.startswith("wiki/"):
        normalized = normalized[len("wiki/") :]
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    return normalized.strip("/")


def _qa_path_for_slug(slug: str, explicit_slug: bool) -> Path:
    """Return a collision-safe path for a new Q&A article."""
    QA_DIR.mkdir(parents=True, exist_ok=True)
    path = QA_DIR / f"{slug}.md"
    if explicit_slug:
        if path.exists():
            raise FileExistsError(f"Q&A article already exists: {path}")
        return path

    candidate = path
    counter = 2
    while candidate.exists():
        candidate = QA_DIR / f"{slug}-{counter}.md"
        counter += 1
    return candidate


def normalize_and_validate_consulted_articles(values: list[str]) -> list[str]:
    """Normalize consulted article refs and ensure they resolve inside wiki/."""
    normalized: list[str] = []
    wiki_root = WIKI_DIR.resolve()
    for value in values:
        slug = normalize_article_slug(value)
        if not slug:
            continue
        candidate = (WIKI_DIR / f"{slug}.md").resolve()
        if not candidate.is_relative_to(wiki_root) or not candidate.exists():
            raise FileNotFoundError(f"consulted article not found: {slug}")
        normalized.append(slug)
    return normalized


def build_manual_qa_article(
    *,
    title: str,
    question: str,
    answer: str,
    consulted_articles: list[str],
    timestamp: str,
    project: str,
) -> str:
    """Build a manual Q&A article body for the markdown wiki."""
    filed_date = timestamp[:10]
    consulted = [normalize_article_slug(item) for item in consulted_articles]
    consulted = [item for item in consulted if item]

    frontmatter = [
        "---",
        f"title: {_frontmatter_string(title)}",
        "type: qa",
        f"question: {_frontmatter_string(question)}",
        f"consulted_articles: {_frontmatter_list(consulted)}",
        f"filed: {filed_date}",
        f"project: {_frontmatter_string(project)}",
        "tags: [qa, manual-file-back]",
        "---",
        "",
    ]

    consulted_section = (
        "\n".join(f"- [[{slug}]]" for slug in consulted) if consulted else "_Not recorded._"
    )

    body = [
        f"# {title}",
        "",
        "## Question",
        "",
        question.strip(),
        "",
        "## Answer",
        "",
        answer.strip(),
        "",
        "## Consulted Articles",
        "",
        consulted_section,
        "",
    ]

    return "\n".join(frontmatter + body)


def save_manual_qa_answer(
    *,
    question: str,
    answer: str,
    consulted_articles: list[str] | None = None,
    title: str | None = None,
    slug: str | None = None,
    project: str = "memory-claude",
) -> Path:
    """Save a manually produced answer into wiki/qa without starting Agent SDK."""
    clean_question = question.strip()
    clean_answer = answer.strip()
    if not clean_question:
        raise ValueError("question must not be empty")
    if not clean_answer:
        raise ValueError("answer must not be empty")

    article_title = (title or clean_question).strip()
    article_slug = slugify(slug or article_title)
    if not article_slug:
        raise ValueError("could not derive a Q&A slug")

    path = _qa_path_for_slug(article_slug, explicit_slug=slug is not None)
    timestamp = now_iso()
    consulted = normalize_and_validate_consulted_articles(consulted_articles or [])

    path.write_text(
        build_manual_qa_article(
            title=article_title,
            question=clean_question,
            answer=clean_answer,
            consulted_articles=consulted,
            timestamp=timestamp,
            project=project,
        ),
        encoding="utf-8",
    )

    from rebuild_index import rebuild_and_write_index

    rebuild_and_write_index()

    rel_slug = str(path.relative_to(WIKI_DIR)).replace("\\", "/").replace(".md", "")
    log_entry = (
        f"\n## [{timestamp}] query (manual-filed) | {article_title}\n"
        f"- Question: {clean_question}\n"
        f"- Consulted: "
        f"{', '.join(f'[[{normalize_article_slug(item)}]]' for item in consulted) or 'not recorded'}\n"
        f"- Filed to: [[{rel_slug}]]\n"
    )
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(log_entry)

    state = load_state()
    state["manual_qa_file_count"] = state.get("manual_qa_file_count", 0) + 1
    save_state(state)

    return path


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
    if WIKI_AGENT_BACKEND != "claude":
        return (
            f"Agent SDK query requires WIKI_AGENT_BACKEND=claude; current backend is "
            f"{WIKI_AGENT_BACKEND!r}. Use --preview, read the candidate articles, and answer "
            "manually."
        )

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
    parser.add_argument(
        "--save-answer-file",
        metavar="PATH",
        help="Save an already-written answer file to wiki/qa/ without starting Agent SDK",
    )
    parser.add_argument(
        "--consulted",
        action="append",
        default=[],
        help="Consulted wiki article slug for --save-answer-file; repeat as needed",
    )
    parser.add_argument("--title", help="Q&A article title for --save-answer-file")
    parser.add_argument("--slug", help="Explicit Q&A article slug for --save-answer-file")
    parser.add_argument(
        "--project",
        default="memory-claude",
        help="Project frontmatter value for --save-answer-file",
    )
    args = parser.parse_args()

    if args.file_back and args.save_answer_file:
        parser.error("--file-back and --save-answer-file are mutually exclusive")

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    if args.save_answer_file:
        answer_path = Path(args.save_answer_file)
        answer = answer_path.read_text(encoding="utf-8")
        saved = save_manual_qa_answer(
            question=args.question,
            answer=answer,
            consulted_articles=args.consulted,
            title=args.title,
            slug=args.slug,
            project=args.project,
        )
        rel = saved.relative_to(ROOT_DIR)
        print(f"Saved manual Q&A answer to {rel}")
        print("Index rebuilt and log.md updated.")
        return

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
