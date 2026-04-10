"""Query: search the knowledge base and optionally file answers as Q&A articles."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import QA_DIR, INDEX_FILE, LOG_FILE, WIKI_DIR, now_iso
from utils import load_state, read_all_wiki_content, save_state

ROOT_DIR = Path(__file__).resolve().parent.parent


async def run_query(question: str, file_back: bool = False) -> str:
    """Query the knowledge base. Optionally file the answer as a Q&A article."""
    from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock, query

    wiki_content = read_all_wiki_content()

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
3. Update {INDEX_FILE} with a new entry under the Analyses section
4. Append to {LOG_FILE}:
   ## [{timestamp}] query (filed) | question summary
   - Question: {question}
   - Consulted: [[list of articles read]]
   - Filed to: [[qa/article-name]]
"""

    prompt = f"""You are a knowledge base query engine. Answer the user's question by
consulting the knowledge base below.

## How to Answer

1. Read the INDEX section first — it lists every article with a one-line summary
2. Identify relevant articles from the index
3. Read those articles carefully (they're included below)
4. Synthesize a clear, thorough answer
5. Cite sources using [[wikilinks]] (e.g., [[concepts/supabase-auth]])
6. If the knowledge base doesn't contain relevant information, say so honestly

## Knowledge Base

{wiki_content}

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
    args = parser.parse_args()

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    answer = asyncio.run(run_query(args.question, file_back=args.file_back))
    print(answer)

    if args.file_back:
        print("\n" + "-" * 60)
        qa_count = len(list(QA_DIR.glob("*.md"))) if QA_DIR.exists() else 0
        print(f"Answer filed to wiki/qa/ ({qa_count} Q&A articles total)")


if __name__ == "__main__":
    main()
