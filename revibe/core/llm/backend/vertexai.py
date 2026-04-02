from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx

from revibe.core.config import ProviderConfig
from revibe.core.llm.backend.openai import OpenAIBackend
from revibe.core.types import LLMChunk, LLMMessage, StrToolChoice

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig


class VertexAIBackend(OpenAIBackend):
    """Google Vertex AI backend using OpenAI-compatible API.

    Supports enterprise Google Cloud environments with automatic
    credential caching and ADC (Application Default Credentials).
    """

    supported_formats: list[str] = ["openai"]

    def __init__(self, provider: ProviderConfig, timeout: float = 720.0) -> None:
        super().__init__(provider=provider, timeout=timeout)
        self._cached_token: str | None = None
        self._project_id: str | None = None
        self._location: str | None = None

    def _get_adc_credentials(self) -> dict[str, str] | None:
        """Get Application Default Credentials from environment."""
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.isfile(cred_path):
            import json

            try:
                with open(cred_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _get_access_token(self) -> str | None:
        """Get cached or fresh access token."""
        if self._cached_token:
            return self._cached_token

        creds = self._get_adc_credentials()
        if not creds:
            return None

        try:
            import google.auth.transport.requests
            import google.oauth2.service_account

            credentials = (
                google.oauth2.service_account.Credentials.from_service_account_info(
                    creds, scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            )
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            self._cached_token = credentials.token
            return self._cached_token
        except ImportError:
            pass
        except Exception:
            pass

        return None

    async def _build_headers(self) -> dict[str, str]:
        """Build headers with Vertex AI authentication."""
        headers = await super()._build_headers()

        token = self._get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        project_id = os.environ.get("VERTEX_AI_PROJECT_ID") or os.environ.get(
            "GOOGLE_CLOUD_PROJECT"
        )
        if project_id:
            self._project_id = project_id
            headers["X-Goog-User-Project"] = project_id

        location = os.environ.get("VERTEX_AI_LOCATION", "us-central1")
        self._location = location

        return headers

    def _get_api_base(self, model: ModelConfig) -> str:
        """Construct Vertex AI API base URL."""
        project = self._project_id or os.environ.get(
            "VERTEX_AI_PROJECT_ID", "your-project"
        )
        location = self._location or os.environ.get("VERTEX_AI_LOCATION", "us-central1")
        model_id = model.name.split("/")[-1] if "/" in model.name else model.name

        if self.provider.api_base:
            return self.provider.api_base

        return (
            f"https://{location}-aiplatform.googleapis.com/v1"
            f"/projects/{project}/locations/{location}"
            f"/publishers/google/models/{model_id}"
        )

    async def complete(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[Any] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | Any | None,
        extra_headers: dict[str, str] | None,
    ) -> LLMChunk:
        """Complete using Vertex AI endpoint."""
        await self._build_headers()
        return await super().complete(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )

    async def complete_streaming(
        self,
        *,
        model: ModelConfig,
        messages: list[LLMMessage],
        temperature: float,
        tools: list[Any] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | Any | None,
        extra_headers: dict[str, str] | None,
    ) -> Any:
        """Stream using Vertex AI endpoint."""
        await self._build_headers()
        async for chunk in super().complete_streaming(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        ):
            yield chunk
