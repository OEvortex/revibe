from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from revibe.core.llm.backend.openai import OpenAIBackend

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class OllamaBackend(OpenAIBackend):
    def __init__(self, provider: ProviderConfigUnion, timeout: float = 720.0) -> None:
        super().__init__(provider, timeout)

    async def list_models(self) -> list[str]:
        """Fetch models from Ollama's native /api/tags endpoint."""
        try:
            # Try native Ollama API first as it's more reliable for internal listing
            base_url = self._provider.api_base.replace("/v1", "").rstrip("/")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass

        # Fallback to OpenAI-compatible endpoint
        return await super().list_models()
