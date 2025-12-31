"""Gemini CLI provider types and constants.

Based on Google Gemini CLI implementation:
https://github.com/google-gemini/gemini-cli
And KiloCode's Gemini CLI provider:
https://github.com/Kilo-Org/kilocode/blob/main/src/api/providers/gemini-cli.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# OAuth2 Configuration
GEMINI_OAUTH_REDIRECT_URI = "http://localhost:45289"
GEMINI_OAUTH_BASE_URL = "https://accounts.google.com"
GEMINI_OAUTH_TOKEN_ENDPOINT = f"{GEMINI_OAUTH_BASE_URL}/o/oauth2/token"
GEMINI_OAUTH_AUTH_ENDPOINT = f"{GEMINI_OAUTH_BASE_URL}/o/oauth2/v2/auth"

# OAuth Client credentials for Gemini Code Assist
# These are the official Google OAuth client credentials for Gemini CLI
# See: https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/oauth2.ts
GEMINI_OAUTH_CLIENT_ID = (
    "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
)
GEMINI_OAUTH_CLIENT_SECRET = "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"

# OAuth scopes required for Cloud Code API access
# These scopes grant access to Google Cloud and Gemini Code Assist APIs
# Based on official gemini-cli implementation:
# https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/oauth2.ts
GEMINI_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Code Assist API Configuration
GEMINI_CODE_ASSIST_ENDPOINT = "https://cloudcode-pa.googleapis.com"
GEMINI_CODE_ASSIST_API_VERSION = "v1internal"

# Credential storage
GEMINI_DIR = ".gemini"
GEMINI_CREDENTIAL_FILENAME = "oauth_creds.json"
GEMINI_ENV_FILENAME = ".env"

# Default settings
GEMINI_DEFAULT_TEMPERATURE = 0.7
GEMINI_DEFAULT_MAX_TOKENS = 8192

# Token refresh buffer (5 minutes)
TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000


@dataclass
class GeminiOAuthCredentials:
    """OAuth credentials for Gemini CLI."""

    access_token: str
    refresh_token: str
    token_type: str
    expiry_date: int  # Timestamp in milliseconds


@dataclass
class GeminiModelInfo:
    """Model information for Gemini CLI models."""

    id: str
    name: str
    context_window: int = 1_048_576  # 1M tokens for gemini-2.x
    max_output: int = 32_768  # 32K output tokens
    input_price: float = 0.0  # Free tier
    output_price: float = 0.0  # Free tier
    supports_native_tools: bool = True
    supports_thinking: bool = True


# Available Gemini CLI models (from gemini-cli repo)
GEMINI_CLI_MODELS: dict[str, GeminiModelInfo] = {
    # Gemini 2.5 series (default)
    "gemini-2.5-pro": GeminiModelInfo(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        context_window=1_048_576,
        max_output=65_536,
        supports_thinking=True,
    ),
    "gemini-2.5-flash": GeminiModelInfo(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        context_window=1_048_576,
        max_output=65_536,
        supports_thinking=True,
    ),
    "gemini-2.5-flash-lite": GeminiModelInfo(
        id="gemini-2.5-flash-lite",
        name="Gemini 2.5 Flash Lite",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=False,
    ),
    # Gemini 3 series (preview)
    "gemini-3-pro-preview": GeminiModelInfo(
        id="gemini-3-pro-preview",
        name="Gemini 3 Pro Preview",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=True,
    ),
    "gemini-3-flash-preview": GeminiModelInfo(
        id="gemini-3-flash-preview",
        name="Gemini 3 Flash Preview",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=True,
    ),
    # Gemini 1.5 series
    "gemini-1.5-pro": GeminiModelInfo(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        context_window=2_097_152,
        max_output=8_192,
        supports_thinking=True,
    ),
    "gemini-1.5-flash": GeminiModelInfo(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=False,
    ),
    # Gemini 2.0 series
    "gemini-2.0-flash": GeminiModelInfo(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        context_window=1_048_576,
        max_output=32_768,
        supports_thinking=True,
    ),
}


def get_geminicli_credential_path(custom_path: str | None = None) -> Path:
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
    return Path.home() / GEMINI_DIR / GEMINI_CREDENTIAL_FILENAME


def get_geminicli_env_path(custom_path: str | None = None) -> Path:
    """Get the path to the .env file for project ID lookup.

    Args:
        custom_path: Optional custom path to the credentials file.

    Returns:
        Path to the .env file.
    """
    if custom_path:
        return Path(custom_path).parent / GEMINI_ENV_FILENAME
    return Path.home() / GEMINI_DIR / GEMINI_ENV_FILENAME
