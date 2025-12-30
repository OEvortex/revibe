from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from revibe.core.llm.backend.openai import OpenAIBackend

HTTP_OK = 200

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class LlamaCppBackend(OpenAIBackend):
    def __init__(self, provider: ProviderConfigUnion, timeout: float = 720.0) -> None:
        super().__init__(provider=provider, timeout=timeout)

    async def list_models(self) -> list[str]:
        """Fetch models from llama.cpp. Llama.cpp usually handles one model,
        but we can try to find its name.
        """
        try:
            # Try props endpoint for llama.cpp native info
            base_url = self._provider.api_base.replace("/v1", "").rstrip("/")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/props")
                if response.status_code == HTTP_OK:
                    data = response.json()
                    # Some versions return filename or alias
                    if "default_generation_settings" in data:
                        model_path = data.get("model_path", "local")
                        return [model_path.split("/")[-1]]
        except Exception:
            pass

        # Fallback to OpenAI-compatible endpoint
        return await super().list_models()
