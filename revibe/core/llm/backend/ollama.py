from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from revibe.core.llm.backend.openai import OpenAIBackend

HTTP_OK = 200

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class OllamaBackend(OpenAIBackend):
    """Backend for interacting with Ollama's API, extending OpenAI's backend."""

    def __init__(self, provider: ProviderConfigUnion, timeout: float = 720.0) -> None:
        """Initialize the Ollama backend with the given provider and timeout.

        Args:
            provider: Configuration for the provider.
            timeout: Timeout for API requests in seconds. Defaults to 720.0.
        """
        super().__init__(provider=provider, timeout=timeout)

    async def list_models(self) -> list[str]:
        """Fetch models from Ollama's native /api/tags endpoint.

        Returns:
            A list of model names available from the Ollama API.

        Raises:
            Exception: If an error occurs during the API request, it is silently caught and the method falls back to the OpenAI-compatible endpoint.
        """
        try:
            # Try native Ollama API first as it's more reliable for internal listing
            base_url = self._provider.api_base.replace("/v1", "").rstrip("/")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response: httpx.Response = await client.get(f"{base_url}/api/tags")
                if response.status_code == HTTP_OK:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass

        # Fallback to OpenAI-compatible endpoint
        return await super().list_models()
