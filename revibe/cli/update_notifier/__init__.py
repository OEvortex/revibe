from __future__ import annotations

from revibe.cli.update_notifier.adapters.filesystem_update_cache_repository import (
    FileSystemUpdateCacheRepository,
)
from revibe.cli.update_notifier.adapters.github_version_update_gateway import (
    GitHubVersionUpdateGateway,
)
from revibe.cli.update_notifier.adapters.pypi_version_update_gateway import (
    PyPIVersionUpdateGateway,
)
from revibe.cli.update_notifier.ports.update_cache_repository import (
    UpdateCache,
    UpdateCacheRepository,
)
from revibe.cli.update_notifier.ports.version_update_gateway import (
    DEFAULT_GATEWAY_MESSAGES,
    VersionUpdate,
    VersionUpdateGateway,
    VersionUpdateGatewayCause,
    VersionUpdateGatewayError,
)
from revibe.cli.update_notifier.version_update import (
    VersionUpdateAvailability,
    VersionUpdateError,
    get_update_if_available,
)

__all__ = [
    "DEFAULT_GATEWAY_MESSAGES",
    "FileSystemUpdateCacheRepository",
    "GitHubVersionUpdateGateway",
    "PyPIVersionUpdateGateway",
    "UpdateCache",
    "UpdateCacheRepository",
    "VersionUpdate",
    "VersionUpdateAvailability",
    "VersionUpdateError",
    "VersionUpdateGateway",
    "VersionUpdateGatewayCause",
    "VersionUpdateGatewayError",
    "get_update_if_available",
]
