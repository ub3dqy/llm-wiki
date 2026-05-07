"""Scan tracked files for local personal path leaks.

This is intentionally narrower than a generic path grep: documentation may mention
placeholder forms like a bare Windows user directory, but tracked files should not
contain machine-specific user names or local workspace roots.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

INLINE_ALLOW_MARKER = "personal-data-check: allow"
EXCLUDED_TRACKED_PATHS: set[str] = set()
IGNORED_USER_SEGMENTS = {
    "%USERNAME%",
    "${USER}",
    "${USERNAME}",
    "<USER>",
    "<USERNAME>",
    "USER",
    "USERNAME",
    "Public",
    "Default",
    "Default User",
    "All Users",
}
IGNORED_USER_SEGMENTS_UPPER = {segment.upper() for segment in IGNORED_USER_SEGMENTS}
IGNORED_DRIVE_ROOTS = {
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "Temp",
    "Tmp",
}
DRIVE_ROOT_PATTERN = (
    r"Program Files \(x86\)|Program Files|ProgramData|Default User|All Users|"
    r"[A-Z][A-Za-z0-9._-]*"
)
WINDOWS_USERS_SEGMENT = "Users"
POSIX_HOME_DIRS = ("home", "Users")


@dataclass(frozen=True)
class Finding:
    path: str
    line_no: int
    rule_id: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]


RULES = (
    Rule(
        "windows_user_home",
        re.compile(
            r"(?i)\b[A-Z]:(?:\\+|/+)"
            rf"{WINDOWS_USERS_SEGMENT}(?:\\+|/+)(?P<user>[^\\/\s`'\"|]+)"
        ),
    ),
    Rule(
        "wsl_user_home",
        re.compile(rf"(?i)(?<![\w-])/mnt/[a-z]/{WINDOWS_USERS_SEGMENT}/(?P<user>[^/\s`'\"|]+)"),
    ),
    Rule(
        "posix_user_home",
        re.compile(rf"(?<![\w-])/(?:{'|'.join(POSIX_HOME_DIRS)})/(?P<user>[^/\s`'\"|]+)"),
    ),
    Rule(
        "windows_absolute_local_path",
        re.compile(
            r"\b(?P<drive>[A-Z]):(?:\\+|/+)"
            rf"(?P<root>{DRIVE_ROOT_PATTERN})(?=$|[\\/])"
        ),
    ),
    Rule(
        "wsl_absolute_local_path",
        re.compile(rf"(?<![\w-])/mnt/[a-z]/(?P<root>{DRIVE_ROOT_PATTERN})(?=$|/)"),
    ),
)


def _is_placeholder(segment: str | None) -> bool:
    if not segment:
        return True
    normalized = segment.strip().strip("\\/")
    return normalized.upper() in IGNORED_USER_SEGMENTS_UPPER


def _is_ignored_drive_root(root: str | None) -> bool:
    if not root:
        return True
    normalized = root.strip().strip("\\/")
    return normalized in IGNORED_DRIVE_ROOTS


def _is_allowed_match(rule: Rule, match: re.Match[str]) -> bool:
    if rule.rule_id in {"windows_user_home", "wsl_user_home", "posix_user_home"}:
        return _is_placeholder(match.groupdict().get("user"))
    if rule.rule_id in {"windows_absolute_local_path", "wsl_absolute_local_path"}:
        root = match.groupdict().get("root")
        if root == "Users":
            # User-home rules decide whether the profile segment is real or a placeholder.
            return True
        return _is_ignored_drive_root(root)
    return False


def scan_text(path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if INLINE_ALLOW_MARKER in line:
            continue
        for rule in RULES:
            for match in rule.pattern.finditer(line):
                if _is_allowed_match(rule, match):
                    continue
                findings.append(Finding(path=path, line_no=line_no, rule_id=rule.rule_id))
    return findings


def _tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [item.decode("utf-8") for item in proc.stdout.split(b"\0") if item]


def _read_text_file(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def scan_tracked_files(root: Path = ROOT_DIR) -> list[Finding]:
    findings: list[Finding] = []
    for rel_path in _tracked_files(root):
        if rel_path in EXCLUDED_TRACKED_PATHS:
            continue
        abs_path = root / rel_path
        if not abs_path.is_file():
            continue
        text = _read_text_file(abs_path)
        if text is None:
            continue
        findings.extend(scan_text(rel_path, text))
    return findings


def main() -> int:
    print("Scanning tracked text files for personal local paths...")
    findings = scan_tracked_files()
    if not findings:
        print("All clear - no personal local paths found.")
        return 0

    print("Personal local paths found:")
    for finding in findings:
        print(f"  {finding.path}:{finding.line_no} {finding.rule_id}")
        print(
            f"::error file={finding.path},line={finding.line_no}::"
            f"Potential personal local path ({finding.rule_id})"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
