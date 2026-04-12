from __future__ import annotations

import json
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

# --- Project alias normalization ---
# Local override: scripts/project_aliases.local.json (gitignored)
# Template: scripts/project_aliases.example.json
PROJECT_ALIASES_LOCAL_FILE = SCRIPTS_DIR / "project_aliases.local.json"
PROJECT_ALIASES_EXAMPLE_FILE = SCRIPTS_DIR / "project_aliases.example.json"


def _load_project_aliases() -> dict[str, set[str]]:
    """Load local project aliases without committing personal project names."""
    if not PROJECT_ALIASES_LOCAL_FILE.exists():
        return {}

    try:
        raw = json.loads(PROJECT_ALIASES_LOCAL_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    aliases: dict[str, set[str]] = {}
    if not isinstance(raw, dict):
        return aliases

    for canonical, values in raw.items():
        if not isinstance(canonical, str) or not canonical.strip():
            continue
        if not isinstance(values, list):
            continue

        normalized_values = {
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip()
        }
        if normalized_values:
            aliases[canonical.strip()] = normalized_values

    return aliases


PROJECT_ALIASES: dict[str, set[str]] = _load_project_aliases()


def now_iso() -> str:
    """Current time in ISO 8601 format with local timezone."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
