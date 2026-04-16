"""Codex SessionStart: reuse shared context logic."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared_context import build_context_and_output

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"

logging.basicConfig(
    filename=str(SCRIPTS_DIR / "hook-errors.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [codex-session-start] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    try:
        build_context_and_output()
    except Exception as exc:
        logging.exception("SessionStart hook failed: %s", exc)
