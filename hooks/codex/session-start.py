"""Codex SessionStart: reuse shared context logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared_context import build_context_and_output

if __name__ == "__main__":
    build_context_and_output()
