from __future__ import annotations

from typing import TYPE_CHECKING

from revibe.core.llm.backend.generic import GenericBackend

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class CerebrasBackend(GenericBackend):
    def __init__(self, provider: ProviderConfigUnion, timeout: float = 720.0) -> None:
        super().__init__(provider=provider, timeout=timeout)
