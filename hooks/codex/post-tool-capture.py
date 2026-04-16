"""Codex PostToolUse: capture Bash commands.

NOTE:
- tool_name is "Bash" (NOT "local_shell")
- tool_input.command is a string (NOT an array)
- Codex does NOT support async: true - this hook is SYNC
- Only Bash tools are intercepted (not Write, MCP, WebSearch)
- Same tool_name and tool_input format as Claude Code
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PARENT_SCRIPT = Path(__file__).resolve().parent.parent / "post-tool-capture.py"
SPEC = importlib.util.spec_from_file_location("post_tool_capture_parent", PARENT_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load hook module: {PARENT_SCRIPT}")

POST_TOOL_CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POST_TOOL_CAPTURE)


def main() -> None:
    POST_TOOL_CAPTURE.main()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block tool execution due to hook errors
        pass
