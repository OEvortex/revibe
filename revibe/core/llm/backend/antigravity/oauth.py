"""OAuth authentication for Antigravity.

This module handles OAuth2 PKCE token management for Antigravity API access.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from revibe.core.llm.backend.antigravity.types import (
    ANTIGRAVITY_API_VERSION,
    ANTIGRAVITY_DEFAULT_ENDPOINT,
    ANTIGRAVITY_DEFAULT_HEADERS,
    ANTIGRAVITY_ENDPOINT_FALLBACKS,
    ANTIGRAVITY_LOAD_ENDPOINTS,
    ANTIGRAVITY_OAUTH_AUTH_ENDPOINT,
    ANTIGRAVITY_OAUTH_CLIENT_ID,
    ANTIGRAVITY_OAUTH_CLIENT_SECRET,
    ANTIGRAVITY_OAUTH_REDIRECT_URI,
    ANTIGRAVITY_OAUTH_SCOPES,
    ANTIGRAVITY_OAUTH_TOKEN_ENDPOINT,
    DEFAULT_PROJECT_ID,
    TOKEN_REFRESH_BUFFER_MS,
    AntigravityOAuthCredentials,
    get_antigravity_credential_path,
)

HTTP_OK = 200


# Global variable for OAuth callback
_oauth_result: dict = {}


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _encode_state(verifier: str, project_id: str = "") -> str:
    """Encode state for OAuth callback."""
    payload = {"verifier": verifier, "projectId": project_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


def _decode_state(state: str) -> tuple[str, str]:
    """Decode OAuth state parameter."""
    normalized = state.replace("-", "+").replace("_", "/")
    padding = 4 - (len(normalized) % 4)
    if padding != 4:
        normalized += "=" * padding
    data = json.loads(base64.b64decode(normalized).decode())
    return data.get("verifier", ""), data.get("projectId", "")


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from Google."""

    def log_message(self, format, *args):
        """Suppress logging."""
        pass

    def do_GET(self):
        global _oauth_result

        parsed = urlparse(self.path)
        if parsed.path == "/oauth-callback":
            query = parse_qs(parsed.query)

            if "code" in query and "state" in query:
                _oauth_result = {
                    "code": query["code"][0],
                    "state": query["state"][0],
                }
                self._send_success()
            elif "error" in query:
                _oauth_result = {"error": query.get("error", ["Unknown error"])[0]}
                self._send_error(query.get("error_description", ["Authorization failed"])[0])
            else:
                _oauth_result = {"error": "Invalid callback"}
                self._send_error("Invalid callback parameters")
        else:
            self.send_response(404)
            self.end_headers()

    def _send_success(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Successful</title>
            <style>
                body { font-family: system-ui, sans-serif; display: flex; justify-content: center;
                       align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .card { background: white; padding: 3rem; border-radius: 1rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
                        text-align: center; max-width: 400px; }
                h1 { color: #22c55e; margin-bottom: 1rem; }
                p { color: #64748b; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>✅ Authorization Successful!</h1>
                <p>You can close this window and return to your application.</p>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_error(self, message: str):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Failed</title>
            <style>
                body {{ font-family: system-ui, sans-serif; display: flex; justify-content: center;
                       align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }}
                .card {{ background: white; padding: 3rem; border-radius: 1rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
                        text-align: center; max-width: 400px; }}
                h1 {{ color: #ef4444; margin-bottom: 1rem; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>❌ Authorization Failed</h1>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())


class AntigravityOAuthManager:
    """Manages OAuth authentication for Antigravity."""

    def __init__(
        self,
        oauth_path: str | None = None,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize the OAuth manager.

        Args:
            oauth_path: Optional custom path to the OAuth credentials file.
            client_id: OAuth client ID. Uses default if not provided.
            client_secret: OAuth client secret. Uses default if not provided.
            endpoint: API endpoint URL. Uses default if not provided.
        """
        self._oauth_path = oauth_path
        self._client_id = client_id or ANTIGRAVITY_OAUTH_CLIENT_ID
        self._client_secret = client_secret or ANTIGRAVITY_OAUTH_CLIENT_SECRET
        self._endpoint = endpoint or ANTIGRAVITY_DEFAULT_ENDPOINT
        self._credentials: AntigravityOAuthCredentials | None = None
        self._refresh_lock = False

    def _load_cached_credentials(self) -> AntigravityOAuthCredentials:
        """Load OAuth credentials from the cached file.

        Returns:
            The loaded credentials.

        Raises:
            FileNotFoundError: If the credentials file doesn't exist.
            ValueError: If the credentials file is invalid.
        """
        key_file = get_antigravity_credential_path(self._oauth_path)

        try:
            with open(key_file, encoding="utf-8") as f:
                data = json.load(f)

            return AntigravityOAuthCredentials(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_type=data.get("token_type", "Bearer"),
                expiry_date=data["expiry_date"],
                project_id=data.get("project_id", ""),
                email=data.get("email", ""),
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Antigravity OAuth credentials not found at {key_file}. "
                "Please authenticate first using revibe --provider antigravity --login"
            ) from None
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid Antigravity OAuth credentials file: {e}") from e

    async def authenticate(self) -> AntigravityOAuthCredentials:
        """Perform OAuth2 PKCE authentication flow.

        Opens a browser for the user to authorize, then exchanges the code for tokens.

        Returns:
            OAuth credentials on success.

        Raises:
            RuntimeError: If authentication fails.
        """
        global _oauth_result
        _oauth_result = {}

        # Generate PKCE values
        verifier, challenge = _generate_pkce()

        # Build authorization URL
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": ANTIGRAVITY_OAUTH_REDIRECT_URI,
            "scope": " ".join(ANTIGRAVITY_OAUTH_SCOPES),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": _encode_state(verifier),
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"{ANTIGRAVITY_OAUTH_AUTH_ENDPOINT}?{urlencode(params)}"

        # Start callback server
        port = int(ANTIGRAVITY_OAUTH_REDIRECT_URI.split(":")[-1].split("/")[0])
        server = HTTPServer(("localhost", port), _OAuthCallbackHandler)
        server_thread = Thread(target=server.handle_request, daemon=True)
        server_thread.start()

        # Open browser
        print("🌐 Opening browser for Antigravity authentication...")
        print(f"   If browser doesn't open, visit: {auth_url[:80]}...")
        webbrowser.open(auth_url)

        # Wait for callback
        server_thread.join(timeout=120)
        server.server_close()

        if "error" in _oauth_result:
            raise RuntimeError(f"Authentication failed: {_oauth_result['error']}")

        if "code" not in _oauth_result:
            raise RuntimeError("Authentication timed out or was cancelled")

        # Exchange code for tokens
        return await self._exchange_code(_oauth_result["code"], _oauth_result["state"])

    async def _exchange_code(self, code: str, state: str) -> AntigravityOAuthCredentials:
        """Exchange authorization code for tokens."""
        verifier, project_id = _decode_state(state)

        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": ANTIGRAVITY_OAUTH_REDIRECT_URI,
            "code_verifier": verifier,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                ANTIGRAVITY_OAUTH_TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != HTTP_OK:
                raise RuntimeError(f"Token exchange failed: {response.text}")

            token_data = response.json()

            # Get user info
            email = ""
            try:
                user_response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"},
                )
                if user_response.status_code == HTTP_OK:
                    email = user_response.json().get("email", "")
            except Exception:
                pass

            # Fetch project ID if not provided
            if not project_id:
                project_id = await self._fetch_project_id(client, token_data["access_token"])

        credentials = AntigravityOAuthCredentials(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expiry_date=int(time.time() * 1000) + token_data.get("expires_in", 3600) * 1000,
            project_id=project_id or DEFAULT_PROJECT_ID,
            email=email,
        )

        self._save_credentials(credentials)
        self._credentials = credentials

        print(f"✅ Authenticated as: {email or 'Unknown'}")
        print(f"   Project ID: {credentials.project_id}")

        return credentials

    async def _fetch_project_id(self, client: httpx.AsyncClient, access_token: str) -> str:
        """Fetch project ID from the API with endpoint fallback."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "google-api-nodejs-client/9.15.1",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
            "Client-Metadata": ANTIGRAVITY_DEFAULT_HEADERS["Client-Metadata"],
        }

        # Combine load endpoints and fallback endpoints, removing duplicates
        all_endpoints = list(dict.fromkeys(ANTIGRAVITY_LOAD_ENDPOINTS + ANTIGRAVITY_ENDPOINT_FALLBACKS))

        for base_endpoint in all_endpoints:
            try:
                response = await client.post(
                    f"{base_endpoint}/{ANTIGRAVITY_API_VERSION}:loadCodeAssist",
                    headers=headers,
                    json={
                        "metadata": {
                            "ideType": "IDE_UNSPECIFIED",
                            "platform": "PLATFORM_UNSPECIFIED",
                            "pluginType": "GEMINI",
                        }
                    },
                    timeout=10.0,
                )

                if response.status_code == HTTP_OK:
                    data = response.json()
                    project = data.get("cloudaicompanionProject", "")
                    if isinstance(project, str) and project:
                        return project
                    if isinstance(project, dict):
                        return project.get("id", "")
            except Exception:
                continue

        return ""

    async def _refresh_access_token(
        self, credentials: AntigravityOAuthCredentials
    ) -> AntigravityOAuthCredentials:
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
                "scope": " ".join(ANTIGRAVITY_OAUTH_SCOPES),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ANTIGRAVITY_OAUTH_TOKEN_ENDPOINT,
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

            new_credentials = AntigravityOAuthCredentials(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=token_data.get("refresh_token", credentials.refresh_token),
                expiry_date=int(time.time() * 1000) + token_data["expires_in"] * 1000,
                project_id=credentials.project_id,
                email=credentials.email,
            )

            # Save refreshed credentials
            self._save_credentials(new_credentials)
            self._credentials = new_credentials

            return new_credentials

        finally:
            self._refresh_lock = False

    def _save_credentials(self, credentials: AntigravityOAuthCredentials) -> None:
        """Save credentials to the cache file."""
        file_path = get_antigravity_credential_path(self._oauth_path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "access_token": credentials.access_token,
                        "refresh_token": credentials.refresh_token,
                        "token_type": credentials.token_type,
                        "expiry_date": credentials.expiry_date,
                        "project_id": credentials.project_id,
                        "email": credentials.email,
                    },
                    f,
                    indent=2,
                )
        except OSError as e:
            # Continue with refreshed token in memory even if file write fails
            print(f"Warning: Failed to save refreshed credentials: {e}")

    def _is_token_valid(self, credentials: AntigravityOAuthCredentials) -> bool:
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

    async def get_credentials(self) -> AntigravityOAuthCredentials:
        """Get the current credentials, refreshing if needed.

        Returns:
            Valid credentials.
        """
        await self.ensure_authenticated()
        assert self._credentials is not None
        return self._credentials

    def get_api_endpoint(self) -> str:
        """Get the API endpoint.

        Returns:
            The API endpoint URL.
        """
        return f"{self._endpoint}/{ANTIGRAVITY_API_VERSION}"

    def get_project_id(self) -> str | None:
        """Get the project ID from cached credentials.

        Returns:
            The project ID if available, None otherwise.
        """
        if self._credentials and self._credentials.project_id:
            return self._credentials.project_id
        return None
