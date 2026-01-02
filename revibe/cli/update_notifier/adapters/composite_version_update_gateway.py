from __future__ import annotations

from packaging.version import Version

from revibe.cli.update_notifier.ports.version_update_gateway import (
    VersionUpdate,
    VersionUpdateGateway,
    VersionUpdateGatewayError,
)


class CompositeVersionUpdateGateway(VersionUpdateGateway):
    def __init__(
        self,
        *gateways: VersionUpdateGateway,
    ) -> None:
        self._gateways = gateways

    async def fetch_update(self) -> VersionUpdate | None:
        latest_update: VersionUpdate | None = None
        latest_version: Version | None = None

        for gateway in self._gateways:
            try:
                update = await gateway.fetch_update()
                if update is None:
                    continue

                try:
                    current_version = Version(update.latest_version)
                    if (
                        latest_version is None
                        or current_version > latest_version
                    ):
                        latest_update = update
                        latest_version = current_version
                except Exception:
                    # Skip invalid version strings
                    continue

            except VersionUpdateGatewayError:
                # Continue to next gateway if one fails
                continue
            except Exception:
                # Continue to next gateway for any other errors
                continue

        return latest_update
