"""UserPromptSubmit hook: inject relevant wiki articles based on prompt content."""

from __future__ import annotations

from shared_wiki_search import find_and_inject_articles

if __name__ == "__main__":
    try:
        find_and_inject_articles()
    except Exception:
        # Never block user prompt due to hook errors
        pass
