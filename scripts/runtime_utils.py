from __future__ import annotations

import os
import shutil
from pathlib import Path


def is_wsl() -> bool:
    return bool(os.environ.get("WSL_DISTRO_NAME"))


def find_uv() -> str | None:
    env_uv = os.environ.get("UV_BIN")
    if env_uv and Path(env_uv).exists():
        return env_uv

    found = shutil.which("uv")
    if found:
        return found

    home = Path.home()
    for candidate in (home / ".local" / "bin" / "uv", home / ".cargo" / "bin" / "uv"):
        if candidate.exists():
            return str(candidate)
    return None


def build_uv_python_cmd(
    script_path: Path,
    extra_args: list[str] | None = None,
    project_dir: Path | None = None,
) -> tuple[list[str], dict[str, str]]:
    uv_bin = find_uv()
    if not uv_bin:
        raise FileNotFoundError("uv not found in PATH or common install locations")

    root = project_dir or script_path.resolve().parent.parent
    cmd = [uv_bin, "run", "--directory", str(root), "python", str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    if is_wsl():
        env.setdefault("UV_PROJECT_ENVIRONMENT", str(Path.home() / ".cache" / "llm-wiki" / ".venv"))
        env.setdefault("UV_LINK_MODE", "copy")
    return cmd, env
