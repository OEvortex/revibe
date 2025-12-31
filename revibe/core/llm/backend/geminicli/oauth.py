"""OAuth authentication for Gemini CLI.

Based on KiloCode's Gemini CLI implementation:
https://github.com/Kilo-Org/kilocode/blob/main/src/api/providers/gemini-cli.ts

This module handles OAuth2 token management for Gemini Code Assist API access.
"""

from __future__ import annotations

import asyncio
import json
import time
from urllib.parse import urlencode

import httpx

from revibe.core.llm.backend.geminicli.types import (
    GEMINI_CODE_ASSIST_API_VERSION,
    GEMINI_CODE_ASSIST_ENDPOINT,
    GEMINI_OAUTH_AUTH_ENDPOINT,
    GEMINI_OAUTH_CLIENT_ID,
    GEMINI_OAUTH_CLIENT_SECRET,
    GEMINI_OAUTH_REDIRECT_URI,
    GEMINI_OAUTH_SCOPES,
    GEMINI_OAUTH_TOKEN_ENDPOINT,
    TOKEN_REFRESH_BUFFER_MS,
    GeminiOAuthCredentials,
    get_geminicli_credential_path,
)

HTTP_OK = 200


class GeminiOAuthManager:
    """Manages OAuth authentication for Gemini CLI."""

    def __init__(
        self,
        oauth_path: str | None = None,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize the OAuth manager.

        Args:
            oauth_path: Optional custom path to the OAuth credentials file.
            client_id: OAuth client ID. Uses official Gemini CLI client if not provided.
            client_secret: OAuth client secret. Uses official Gemini CLI secret if not provided.
        """
        self._oauth_path = oauth_path
        self._client_id = client_id or GEMINI_OAUTH_CLIENT_ID
        self._client_secret = client_secret or GEMINI_OAUTH_CLIENT_SECRET
        self._credentials: GeminiOAuthCredentials | None = None
        self._refresh_lock = False

    def _load_cached_credentials(self) -> GeminiOAuthCredentials:
        """Load OAuth credentials from the cached file.

        Returns:
            The loaded credentials.

        Raises:
            FileNotFoundError: If the credentials file doesn't exist.
            ValueError: If the credentials file is invalid.
        """
        key_file = get_geminicli_credential_path(self._oauth_path)

        try:
            with open(key_file, encoding="utf-8") as f:
                data = json.load(f)

            return GeminiOAuthCredentials(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_type=data.get("token_type", "Bearer"),
                expiry_date=data["expiry_date"],
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Gemini OAuth credentials not found at {key_file}. "
                "Please login using the Gemini CLI first: gemini auth login"
            ) from None
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid Gemini OAuth credentials file: {e}") from e

    async def _refresh_access_token(
        self, credentials: GeminiOAuthCredentials
    ) -> GeminiOAuthCredentials:
        """Refresh the OAuth access token.

        Args:
            credentials: Current credentials with refresh token.

        Returns:
            New credentials with refreshed access token.

        Raises:
            ValueError: If no refresh token is available.
            httpx.HTTPStatusError: If the token refresh fails.
        """
        if self._refresh_lock:
            # Wait for ongoing refresh
            while self._refresh_lock:
                await asyncio.sleep(0.1)
            return self._credentials or credentials

        self._refresh_lock = True

        try:
            if not credentials.refresh_token:
                raise ValueError("No refresh token available in credentials.")

            body_data = {
                "grant_type": "refresh_token",
                "refresh_token": credentials.refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": " ".join(GEMINI_OAUTH_SCOPES),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GEMINI_OAUTH_TOKEN_ENDPOINT,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                    content=urlencode(body_data),
                )

                if response.status_code != HTTP_OK:
                    error_text = response.text
                    raise httpx.HTTPStatusError(
                        f"Token refresh failed: {response.status_code} {response.reason_phrase}. "
                        f"Response: {error_text}",
                        request=response.request,
                        response=response,
                    )

                try:
                    token_data = response.json()
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Token refresh failed: Invalid JSON response from OAuth endpoint. "
                        f"Response: {response.text[:200]}"
                    ) from e

                if token_data.get("error"):
                    raise ValueError(
                        f"Token refresh failed: {token_data['error']} - "
                        f"{token_data.get('error_description', 'Unknown error')}"
                    )

            new_credentials = GeminiOAuthCredentials(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=token_data.get(
                    "refresh_token", credentials.refresh_token
                ),
                expiry_date=int(time.time() * 1000) + token_data["expires_in"] * 1000,
            )

            # Save refreshed credentials
            self._save_credentials(new_credentials)
            self._credentials = new_credentials

            return new_credentials

        finally:
            self._refresh_lock = False

    def _save_credentials(self, credentials: GeminiOAuthCredentials) -> None:
        """Save credentials to the cache file."""
        file_path = get_geminicli_credential_path(self._oauth_path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "access_token": credentials.access_token,
                        "refresh_token": credentials.refresh_token,
                        "token_type": credentials.token_type,
                        "expiry_date": credentials.expiry_date,
                    },
                    f,
                    indent=2,
                )
        except OSError as e:
            # Continue with refreshed token in memory even if file write fails
            print(f"Warning: Failed to save refreshed credentials: {e}")

    def _is_token_valid(self, credentials: GeminiOAuthCredentials) -> bool:
        """Check if the access token is still valid.

        Args:
            credentials: The credentials to check.

        Returns:
            True if the token is still valid, False otherwise.
        """
        if not credentials.expiry_date:
            return False
        current_time_ms = int(time.time() * 1000)
        return current_time_ms < credentials.expiry_date - TOKEN_REFRESH_BUFFER_MS

    def invalidate_credentials(self) -> None:
        """Invalidate cached credentials to force a refresh on next request.

        Call this when receiving authentication errors (401) from the API.
        """
        self._credentials = None

    async def ensure_authenticated(self, force_refresh: bool = False) -> str:
        """Ensure we have valid authentication credentials.

        Args:
            force_refresh: If True, forces a token refresh regardless of expiry.

        Returns:
            Valid access token.

        Raises:
            FileNotFoundError: If no cached credentials exist.
            ValueError: If credentials are invalid.
            httpx.HTTPStatusError: If token refresh fails.
        """
        # Always reload credentials from file to pick up external updates
        self._credentials = self._load_cached_credentials()

        if force_refresh or not self._is_token_valid(self._credentials):
            self._credentials = await self._refresh_access_token(self._credentials)

        assert self._credentials is not None
        return self._credentials.access_token

    async def get_credentials(self) -> GeminiOAuthCredentials:
        """Get the current credentials, refreshing if needed.

        Returns:
            Valid credentials.
        """
        await self.ensure_authenticated()
        assert self._credentials is not None
        return self._credentials

    def get_api_endpoint(self) -> str:
        """Get the Code Assist API endpoint.

        Returns:
            The API endpoint URL.
        """
        return f"{GEMINI_CODE_ASSIST_ENDPOINT}/{GEMINI_CODE_ASSIST_API_VERSION}"

    def get_project_id(self) -> str | None:
        """Get the Google Cloud project ID from environment variables.

        Checks (in order):
        1. GOOGLE_CLOUD_PROJECT env var
        2. GOOGLE_CLOUD_PROJECT_ID env var

        Note: This matches the official gemini-cli behavior which only reads
        from environment variables, not from .env files.

        Returns:
            The project ID if found, None otherwise.
        """
        import os

        # Check environment variables only (matching gemini-cli behavior)
        return os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GOOGLE_CLOUD_PROJECT_ID"
        )

    def generate_auth_url(self, state: str, code_verifier: str | None = None) -> str:
        """Generate the OAuth authorization URL.

        Args:
            state: Random state string for CSRF protection.
            code_verifier: Optional PKCE code verifier.

        Returns:
            The authorization URL to visit for OAuth consent.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": GEMINI_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(GEMINI_OAUTH_SCOPES),
            "access_type": "offline",
            "state": state,
        }

        if code_verifier:
            params["code_challenge"] = code_verifier
            params["code_challenge_method"] = "S256"

        return f"{GEMINI_OAUTH_AUTH_ENDPOINT}?{urlencode(params)}"
