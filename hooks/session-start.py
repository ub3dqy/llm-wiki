"""SessionStart hook: inject wiki context into every Claude Code session."""
from __future__ import annotations

from shared_context import build_context_and_output


if __name__ == "__main__":
    build_context_and_output()
