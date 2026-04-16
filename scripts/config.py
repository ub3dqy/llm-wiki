from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env", override=False)
except ImportError:
    pass

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
            value.strip() for value in values if isinstance(value, str) and value.strip()
        }
        if normalized_values:
            aliases[canonical.strip()] = normalized_values

    return aliases


PROJECT_ALIASES: dict[str, set[str]] = _load_project_aliases()


def _env_int(
    name: str, default: int, *, min_val: int | None = None, max_val: int | None = None
) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"[config] warning: {name}={raw!r} is not an int, using default {default}")
        return default
    if min_val is not None and value < min_val:
        print(f"[config] warning: {name}={value} below {min_val}, using default {default}")
        return default
    if max_val is not None and value > max_val:
        print(f"[config] warning: {name}={value} above {max_val}, using default {default}")
        return default
    return value


def _env_timezone(name: str, default: str) -> ZoneInfo:
    raw = os.environ.get(name, default).strip() or default
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        print(f"[config] warning: {name}={raw!r} is not a valid timezone, using {default}")
        try:
            return ZoneInfo(default)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")


# --- Timezone-aware clock ---
# Default UTC so fresh clones behave deterministically.
WIKI_TIMEZONE: ZoneInfo = _env_timezone("WIKI_TIMEZONE", "UTC")

# --- Runtime thresholds (overridable via .env) ---
WIKI_COMPILE_AFTER_HOUR: int = _env_int("WIKI_COMPILE_AFTER_HOUR", 18, min_val=0, max_val=23)
WIKI_MAX_TURNS: int = _env_int("WIKI_MAX_TURNS", 30, min_val=1)
WIKI_MAX_CONTEXT_CHARS: int = _env_int("WIKI_MAX_CONTEXT_CHARS", 15_000, min_val=500)
WIKI_DEBOUNCE_SEC: int = _env_int("WIKI_DEBOUNCE_SEC", 10, min_val=0)
WIKI_MIN_FLUSH_CHARS: int = _env_int("WIKI_MIN_FLUSH_CHARS", 500, min_val=0)


def now_iso() -> str:
    """Current time in ISO 8601 format with configured timezone."""
    return datetime.now(WIKI_TIMEZONE).isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in YYYY-MM-DD format."""
    return datetime.now(WIKI_TIMEZONE).strftime("%Y-%m-%d")
