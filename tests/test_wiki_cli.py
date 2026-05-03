from __future__ import annotations

from pathlib import Path

from utils import file_hash
from wiki_cli import build_daily_log_status


def _write_log(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_build_daily_log_status_uses_compile_signal_rules(tmp_path: Path) -> None:
    low_signal = _write_log(
        tmp_path / "2026-05-03.md",
        "# Daily Log\n\n"
        "## [2026-05-03T13:12:58+00:00] tool-capture\n\n"
        "- **Build**: `uv run pytest`\n",
    )
    new_log = _write_log(
        tmp_path / "2026-04-27.md",
        "# Daily Log\n\n"
        "## [2026-04-27T06:53:02+00:00]\n\n"
        "- **Q: What changed?** A: Channels became the primary wake-up path.\n",
    )
    changed_log = _write_log(
        tmp_path / "2026-04-26.md",
        "# Daily Log\n\n"
        "## [2026-04-26T00:01:27+00:00]\n\n"
        "- **Q: What changed?** A: Mailbox isolation rules were clarified.\n",
    )
    current_log = _write_log(
        tmp_path / "2026-04-25.md",
        "# Daily Log\n\n"
        "## [2026-04-25T00:01:27+00:00]\n\n"
        "- **Q: What changed?** A: Existing compiled log stayed current.\n",
    )

    status = build_daily_log_status(
        [current_log, changed_log, new_log, low_signal],
        {
            "ingested": {
                changed_log.name: {"hash": "old"},
                current_log.name: {"hash": file_hash(current_log)},
            }
        },
    )

    assert status == {
        "total": 4,
        "compile_worthy": 3,
        "low_signal": 1,
        "pending": ["2026-04-26.md (changed)", "2026-04-27.md (new)"],
    }
