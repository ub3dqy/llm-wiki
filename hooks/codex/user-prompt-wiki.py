"""Codex UserPromptSubmit: reuse shared wiki search logic."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared_wiki_search import find_and_inject_articles

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "hook-errors.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [codex-user-prompt] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    try:
        find_and_inject_articles()
    except Exception as exc:
        logging.exception("UserPromptSubmit hook failed: %s", exc)
