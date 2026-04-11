"""Codex UserPromptSubmit: reuse shared wiki search logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared_wiki_search import find_and_inject_articles

if __name__ == "__main__":
    find_and_inject_articles()
