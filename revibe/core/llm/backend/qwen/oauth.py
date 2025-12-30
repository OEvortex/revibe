"""OAuth authentication for Qwen Code API.

Based on Roo-Code qwen-code.ts implementation:
https://github.com/RooCodeInc/Roo-Code/blob/main/src/api/providers/qwen-code.ts

This module handles OAuth2 token management for Qwen Code API access.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import time

import httpx

from revibe.core.llm.backend.qwen.types import (
    HTTP_OK,
    QWEN_CREDENTIAL_FILENAME,
    QWEN_DEFAULT_BASE_URL,
    QWEN_DIR,
    QWEN_OAUTH_CLIENT_ID,
    QWEN_OAUTH_TOKEN_ENDPOINT,
    TOKEN_REFRESH_BUFFER_MS,
    QwenOAuthCredentials,
)


def get_qwen_cached_credential_path(custom_path: str | None = None) -> Path:
    """Get the path to the cached OAuth credentials file.

    Args:
        custom_path: Optional custom path to the credentials file.
                    Supports paths starting with ~/ for home directory.

    Returns:
        Path to the credentials file.
    """
    if custom_path:
        if custom_path.startswith("~/"):
            return Path.home() / custom_path[2:]
        return Path(custom_path).resolve()
    return Path.home() / QWEN_DIR / QWEN_CREDENTIAL_FILENAME


def object_to_url_encoded(data: dict[str, str]) -> str:
    """Convert a dictionary to URL-encoded form data."""
    from urllib.parse import quote

    return "&".join(f"{quote(k)}={quote(v)}" for k, v in data.items())


class QwenOAuthManager:
    """Manages OAuth authentication for Qwen Code API."""

    def __init__(self, oauth_path: str | None = None) -> None:
        """Initialize the OAuth manager.

        Args:
            oauth_path: Optional custom path to the OAuth credentials file.
        """
        self._oauth_path = oauth_path
        self._credentials: QwenOAuthCredentials | None = None
        self._refresh_lock = False

    def _load_cached_credentials(self) -> QwenOAuthCredentials:
        """Load OAuth credentials from the cached file.

        Returns:
            The loaded credentials.

        Raises:
            FileNotFoundError: If the credentials file doesn't exist.
            ValueError: If the credentials file is invalid.
        """
        key_file = get_qwen_cached_credential_path(self._oauth_path)

        try:
            with open(key_file, encoding="utf-8") as f:
                data = json.load(f)

            return QwenOAuthCredentials(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_type=data.get("token_type", "Bearer"),
                expiry_date=data["expiry_date"],
                resource_url=data.get("resource_url"),
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Qwen OAuth credentials not found at {key_file}. "
                "Please login using the Qwen Code CLI first: qwen-code auth login"
            ) from None
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid Qwen OAuth credentials file: {e}") from e

    async def _refresh_access_token(
        self, credentials: QwenOAuthCredentials
    ) -> QwenOAuthCredentials:
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
                "client_id": QWEN_OAUTH_CLIENT_ID,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    QWEN_OAUTH_TOKEN_ENDPOINT,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    },
                    content=object_to_url_encoded(body_data),
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

            new_credentials = QwenOAuthCredentials(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=token_data.get("refresh_token", credentials.refresh_token),
                expiry_date=int(time.time() * 1000) + token_data["expires_in"] * 1000,
                resource_url=credentials.resource_url,
            )

            # Save refreshed credentials
            self._save_credentials(new_credentials)
            self._credentials = new_credentials

            return new_credentials

        finally:
            self._refresh_lock = False

    def _save_credentials(self, credentials: QwenOAuthCredentials) -> None:
        """Save credentials to the cache file."""
        file_path = get_qwen_cached_credential_path(self._oauth_path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "access_token": credentials.access_token,
                        "refresh_token": credentials.refresh_token,
                        "token_type": credentials.token_type,
                        "expiry_date": credentials.expiry_date,
                        "resource_url": credentials.resource_url,
                    },
                    f,
                    indent=2,
                )
        except OSError as e:
            # Continue with refreshed token in memory even if file write fails
            print(f"Warning: Failed to save refreshed credentials: {e}")

    def _is_token_valid(self, credentials: QwenOAuthCredentials) -> bool:
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

    async def ensure_authenticated(self, force_refresh: bool = False) -> tuple[str, str]:
        """Ensure we have valid authentication credentials.

        Args:
            force_refresh: If True, forces a token refresh regardless of expiry.

        Returns:
            Tuple of (access_token, base_url).

        Raises:
            FileNotFoundError: If no cached credentials exist.
            ValueError: If credentials are invalid.
            httpx.HTTPStatusError: If token refresh fails.
        """
        # Always reload credentials from file to pick up external updates (e.g., from Qwen CLI)
        self._credentials = self._load_cached_credentials()

        if force_refresh or not self._is_token_valid(self._credentials):
            self._credentials = await self._refresh_access_token(self._credentials)

        return self._credentials.access_token, self._get_base_url(self._credentials)

    def _get_base_url(self, credentials: QwenOAuthCredentials) -> str:
        """Get the API base URL from credentials.

        Args:
            credentials: The credentials containing optional resource_url.

        Returns:
            The API base URL.

        Note:
            For OAuth authentication, the resource_url (e.g., 'portal.qwen.ai') IS the API endpoint.
            OAuth tokens only work with this endpoint, not with dashscope.aliyuncs.com.
        """
        base_url = credentials.resource_url or QWEN_DEFAULT_BASE_URL

        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"

        # Remove trailing slashes and add /v1 if not present
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        return base_url

    async def get_credentials(self) -> QwenOAuthCredentials:
        """Get the current credentials, refreshing if needed.

        Returns:
            Valid credentials.
        """
        await self.ensure_authenticated()
        assert self._credentials is not None
        return self._credentials
