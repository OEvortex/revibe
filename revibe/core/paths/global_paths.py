from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path

from revibe import VIBE_ROOT


class GlobalPath:
    def __init__(self, resolver: Callable[[], Path]) -> None:
        self._resolver = resolver

    @property
    def path(self) -> Path:
        return self._resolver()


_DEFAULT_REVIBE_HOME = Path.home() / ".revibe"


def _get_revibe_home() -> Path:
    if revibe_home := os.getenv("REVIBE_HOME"):
        return Path(revibe_home).expanduser().resolve()
    return _DEFAULT_REVIBE_HOME


REVIBE_HOME = GlobalPath(_get_revibe_home)
GLOBAL_CONFIG_FILE = GlobalPath(lambda: REVIBE_HOME.path / "config.toml")
GLOBAL_ENV_FILE = GlobalPath(lambda: REVIBE_HOME.path / ".env")
GLOBAL_TOOLS_DIR = GlobalPath(lambda: REVIBE_HOME.path / "tools")
GLOBAL_SKILLS_DIR = GlobalPath(lambda: REVIBE_HOME.path / "skills")
SESSION_LOG_DIR = GlobalPath(lambda: REVIBE_HOME.path / "logs" / "session")
TRUSTED_FOLDERS_FILE = GlobalPath(lambda: REVIBE_HOME.path / "trusted_folders.toml")
LOG_DIR = GlobalPath(lambda: REVIBE_HOME.path / "logs")
LOG_FILE = GlobalPath(lambda: REVIBE_HOME.path / "revibe.log")

DEFAULT_TOOL_DIR = GlobalPath(lambda: VIBE_ROOT / "core" / "tools" / "builtins")
