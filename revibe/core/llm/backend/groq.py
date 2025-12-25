from __future__ import annotations

from typing import TYPE_CHECKING

from revibe.core.llm.backend.openai import OpenAIBackend

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class GroqBackend(OpenAIBackend):
    def __init__(self, provider: ProviderConfigUnion, timeout: float = 720.0) -> None:
        super().__init__(provider=provider, timeout=timeout)
