from __future__ import annotations

from pathlib import Path
import sys
import tomllib

VIBE_ROOT = Path(__file__).parent

# Read version dynamically from pyproject.toml
try:
    # Try to read from the source location first (for editable installs)
    pyproject_path = VIBE_ROOT.parent / "pyproject.toml"
    if pyproject_path.exists():
        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)
        __version__ = pyproject_data["project"]["version"]
    else:
        # Fallback for non-editable installs - read from installed metadata
        import importlib.metadata
        __version__ = importlib.metadata.version("revibe")
except Exception:
    # Fallback to hardcoded version if reading fails
    __version__ = "0.0.0"
