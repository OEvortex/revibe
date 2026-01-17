"""Utility functions for detecting installation type and providing update guidance."""
from __future__ import annotations

import importlib.metadata
from pathlib import Path


def _get_distribution_path(dist: importlib.metadata.Distribution) -> Path | None:
    dist_path = getattr(dist, "_path", None)
    return Path(dist_path) if isinstance(dist_path, (str, Path)) else None


def _has_source_markers(base_path: Path) -> bool:
    for parent in [base_path, base_path.parent, base_path.parent.parent]:
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return True
    return False


def _is_editable_from_source() -> bool:
    try:
        import revibe

        revibe_file = getattr(revibe, "__file__", None)
        if isinstance(revibe_file, str):
            source_dir = Path(revibe_file).parent
            return (source_dir.parent / "pyproject.toml").exists()
    except Exception:
        return False
    return False


def is_editable_installation(package_name: str = "revibe") -> bool:
    """Check if the package is installed as an editable installation.

    Args:
        package_name: Name of the package to check

    Returns:
        True if the package is installed as editable, False otherwise
    """
    try:
        dist = importlib.metadata.distribution(package_name)
    except Exception:
        return _is_editable_from_source()

    if dist_path := _get_distribution_path(dist):
        if (dist_path / "direct_url.json").exists():
            return True
        if _has_source_markers(dist_path.parent):
            return True

    origin = dist.metadata.get("Origin", "")
    if "editable" in origin.lower():
        return True

    return False


def get_update_command(package_name: str = "revibe") -> str:
    """Get the appropriate update command based on installation type.

    Args:
        package_name: Name of the package

    Returns:
        The command to use for updating the package
    """
    if is_editable_installation(package_name):
        return f'cd your-{package_name}-source && git pull && pip install -e .'
    else:
        return f"uv tool upgrade {package_name}"


def get_installation_info(package_name: str = "revibe") -> dict[str, str]:
    """Get detailed installation information.

    Args:
        package_name: Name of the package

    Returns:
        Dictionary with installation details
    """
    info = {
        "package_name": package_name,
        "installation_type": "regular",
        "update_command": get_update_command(package_name),
        "version": "unknown",
        "location": "unknown"
    }

    try:
        dist = importlib.metadata.distribution(package_name)
        info["version"] = dist.version
        dist_path = getattr(dist, '_path', None)
        if isinstance(dist_path, (str, Path)):
            info["location"] = str(dist_path)

        if is_editable_installation(package_name):
            info["installation_type"] = "editable"

    except Exception:
        pass

    return info
