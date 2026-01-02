"""Utility functions for detecting installation type and providing update guidance."""
from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any


def is_editable_installation(package_name: str = "revibe") -> bool:
    """Check if the package is installed as an editable installation.

    Args:
        package_name: Name of the package to check

    Returns:
        True if the package is installed as editable, False otherwise
    """
    try:
        dist = importlib.metadata.distribution(package_name)

        # Method 1: Check for direct_url.json which indicates editable installation
        if hasattr(dist, '_path'):
            dist_path = getattr(dist, '_path', None)
            if isinstance(dist_path, (str, Path)):
                dist_info = Path(dist_path)
                direct_url_file = dist_info / 'direct_url.json'
                if direct_url_file.exists():
                    return True

        # Method 2: Check if the package location points to a source directory
        if hasattr(dist, '_path'):
            dist_path = getattr(dist, '_path', None)
            if isinstance(dist_path, (str, Path)):
                package_path = Path(dist_path).parent
                # Look for pyproject.toml or setup.py in parent directories
                for parent in [package_path, package_path.parent, package_path.parent.parent]:
                    if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
                        return True

        # Method 3: Check the metadata for editable indicators
        if hasattr(dist, 'metadata'):
            origin = dist.metadata.get('Origin', '')
            if 'editable' in origin.lower():
                return True

    except Exception:
        # Fallback: try to import the package and check if we're running from source
        try:
            import revibe
            revibe_file = getattr(revibe, '__file__', None)
            if revibe_file and isinstance(revibe_file, str):
                source_dir = Path(revibe_file).parent
                pyproject_toml = source_dir.parent / 'pyproject.toml'
                if pyproject_toml.exists():
                    return True
        except Exception:
            pass

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
