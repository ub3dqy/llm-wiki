from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# --- Directory layout (adapted for unified wiki/ structure) ---
DAILY_DIR = ROOT_DIR / "daily"
WIKI_DIR = ROOT_DIR / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
CONNECTIONS_DIR = WIKI_DIR / "connections"
QA_DIR = WIKI_DIR / "qa"
SOURCES_DIR = WIKI_DIR / "sources"
ENTITIES_DIR = WIKI_DIR / "entities"
ANALYSES_DIR = WIKI_DIR / "analyses"
REPORTS_DIR = ROOT_DIR / "reports"
SCRIPTS_DIR = ROOT_DIR / "scripts"
HOOKS_DIR = ROOT_DIR / "hooks"
RAW_DIR = ROOT_DIR / "raw"

# --- Key files ---
SCHEMA_FILE = ROOT_DIR / "CLAUDE.md"
INDEX_FILE = ROOT_DIR / "index.md"
LOG_FILE = ROOT_DIR / "log.md"
STATE_FILE = SCRIPTS_DIR / "state.json"

# --- Auto-compile trigger time (local hour, 24h format) ---
COMPILE_TRIGGER_HOUR = 18


def now_iso() -> str:
    """Current time in ISO 8601 format with local timezone."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
