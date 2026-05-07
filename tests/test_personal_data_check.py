from __future__ import annotations

from personal_data_check import scan_text


def _rule_ids(text: str) -> set[str]:
    return {finding.rule_id for finding in scan_text("example.md", text)}


def test_bare_windows_users_reference_is_not_flagged() -> None:
    assert _rule_ids(r"Use C:\Users as a generic documentation example.") == set()


def test_windows_user_home_paths_are_flagged() -> None:
    backslash_path = "C:" + r"\Users\alice\repo"
    slash_path = "C:" + "/" + "Users/alice/repo"

    assert "windows_user_home" in _rule_ids(backslash_path)
    assert "windows_user_home" in _rule_ids(slash_path)


def test_wsl_user_home_path_is_flagged() -> None:
    wsl_path = "/mnt/" + "c/Users/alice/repo"

    assert "wsl_user_home" in _rule_ids(wsl_path)


def test_posix_user_home_paths_are_flagged() -> None:
    linux_path = "/home/" + "alice/repo"
    mac_path = "/" + "Users/alice/repo"

    assert "posix_user_home" in _rule_ids(linux_path)
    assert "posix_user_home" in _rule_ids(mac_path)


def test_local_workspace_roots_are_flagged() -> None:
    windows_path = "E:" + r"\Project\memory claude"
    wsl_path = "/mnt/" + "e/Project/memory-claude"

    assert "windows_absolute_local_path" in _rule_ids(windows_path)
    assert "wsl_absolute_local_path" in _rule_ids(wsl_path)


def test_common_system_roots_and_placeholders_are_ignored() -> None:
    text = "\n".join(
        [
            r"C:\Windows\System32",
            r"C:\Program Files\App",
            r"C:\Users\<USER>\repo",
            r"C:\Users\${USER}\repo",
            "/home/${USER}/repo",
            "/Users/<USER>/repo",
            "/mnt/c/Windows/System32",
            "/mnt/c/Users/${USER}/repo",
        ]
    )

    assert _rule_ids(text) == set()


def test_inline_allow_marker_suppresses_single_fixture_line() -> None:
    path = "C:" + r"\Users\alice\fixture"

    assert _rule_ids(path + "  # personal-data-check: allow") == set()
