from __future__ import annotations

from pathlib import Path
import tomllib

VIBE_ROOT = Path(__file__).parent

# Read version dynamically from pyproject.toml
try:
    pyproject_path = VIBE_ROOT.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)
    __version__ = pyproject_data["project"]["version"]
except Exception:
    # Fallback to hardcoded version if reading fails
    __version__ = "1.4.0"
