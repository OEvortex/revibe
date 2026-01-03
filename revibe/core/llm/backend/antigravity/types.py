"""Antigravity provider types and constants.

Based on the Antigravity Unified Gateway API which provides access to
multiple models (Claude, Gemini, GPT-OSS) through a unified interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# OAuth2 Configuration
ANTIGRAVITY_OAUTH_REDIRECT_URI = "http://localhost:51121/oauth-callback"
ANTIGRAVITY_OAUTH_BASE_URL = "https://accounts.google.com"
ANTIGRAVITY_OAUTH_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
ANTIGRAVITY_OAUTH_AUTH_ENDPOINT = f"{ANTIGRAVITY_OAUTH_BASE_URL}/o/oauth2/v2/auth"

# OAuth Client credentials for Antigravity
ANTIGRAVITY_OAUTH_CLIENT_ID = (
    "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
)
ANTIGRAVITY_OAUTH_CLIENT_SECRET = "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"

# OAuth scopes required for Antigravity API access
ANTIGRAVITY_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

# API Endpoints
ANTIGRAVITY_ENDPOINT_DAILY = "https://daily-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_AUTOPUSH = "https://autopush-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_PROD = "https://cloudcode-pa.googleapis.com"
ANTIGRAVITY_API_VERSION = "v1internal"

# Endpoint fallback order (daily → autopush → prod)
ANTIGRAVITY_ENDPOINT_FALLBACKS = [
    ANTIGRAVITY_ENDPOINT_DAILY,
    ANTIGRAVITY_ENDPOINT_AUTOPUSH,
    ANTIGRAVITY_ENDPOINT_PROD,
]

# Preferred endpoint order for project discovery (prod first, then fallbacks)
ANTIGRAVITY_LOAD_ENDPOINTS = [
    ANTIGRAVITY_ENDPOINT_PROD,
    ANTIGRAVITY_ENDPOINT_DAILY,
    ANTIGRAVITY_ENDPOINT_AUTOPUSH,
]

# Default to daily endpoint for development
ANTIGRAVITY_DEFAULT_ENDPOINT = ANTIGRAVITY_ENDPOINT_DAILY

# Credential storage
ANTIGRAVITY_DIR = ".antigravity"
ANTIGRAVITY_CREDENTIAL_FILENAME = "oauth_creds.json"

# Default settings
ANTIGRAVITY_DEFAULT_TEMPERATURE = 0.7
ANTIGRAVITY_DEFAULT_MAX_TOKENS = 8192

# Token refresh buffer (5 minutes)
TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000

# Default project ID (fallback when API doesn't return one)
DEFAULT_PROJECT_ID = "rising-fact-p41fc"

# Default headers for API requests
ANTIGRAVITY_DEFAULT_HEADERS = {
    "User-Agent": "antigravity/1.11.5 windows/amd64",
    "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
    "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}',
}


@dataclass
class AntigravityOAuthCredentials:
    """OAuth credentials for Antigravity."""

    access_token: str
    refresh_token: str
    token_type: str
    expiry_date: int  # Timestamp in milliseconds
    project_id: str = ""
    email: str = ""


@dataclass
class AntigravityModelInfo:
    """Model information for Antigravity models."""

    id: str
    name: str
    context_window: int = 128_000
    max_output: int = 8_192
    input_price: float = 0.0
    output_price: float = 0.0
    supports_native_tools: bool = True
    supports_thinking: bool = False


# Available Antigravity models
ANTIGRAVITY_MODELS: dict[str, AntigravityModelInfo] = {
    # Gemini 3 series
    "gemini-3-flash": AntigravityModelInfo(
        id="gemini-3-flash",
        name="Gemini 3 Flash",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=True,
    ),
    "gemini-3-pro-low": AntigravityModelInfo(
        id="gemini-3-pro-low",
        name="Gemini 3 Pro Low",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=True,
    ),
    "gemini-3-pro-high": AntigravityModelInfo(
        id="gemini-3-pro-high",
        name="Gemini 3 Pro High",
        context_window=1_048_576,
        max_output=8_192,
        supports_thinking=True,
    ),
    # Claude Sonnet 4.5 series
    "claude-sonnet-4-5": AntigravityModelInfo(
        id="claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        context_window=200_000,
        max_output=8_192,
        supports_thinking=False,
    ),
    "claude-sonnet-4-5-thinking-low": AntigravityModelInfo(
        id="claude-sonnet-4-5-thinking-low",
        name="Claude Sonnet 4.5 Thinking Low",
        context_window=200_000,
        max_output=16_000,
        supports_thinking=True,
    ),
    "claude-sonnet-4-5-thinking-medium": AntigravityModelInfo(
        id="claude-sonnet-4-5-thinking-medium",
        name="Claude Sonnet 4.5 Thinking Medium",
        context_window=200_000,
        max_output=32_000,
        supports_thinking=True,
    ),
    "claude-sonnet-4-5-thinking-high": AntigravityModelInfo(
        id="claude-sonnet-4-5-thinking-high",
        name="Claude Sonnet 4.5 Thinking High",
        context_window=200_000,
        max_output=64_000,
        supports_thinking=True,
    ),
    # Claude Opus 4.5 series
    "claude-opus-4-5-thinking-low": AntigravityModelInfo(
        id="claude-opus-4-5-thinking-low",
        name="Claude Opus 4.5 Thinking Low",
        context_window=200_000,
        max_output=16_000,
        supports_thinking=True,
    ),
    "claude-opus-4-5-thinking-medium": AntigravityModelInfo(
        id="claude-opus-4-5-thinking-medium",
        name="Claude Opus 4.5 Thinking Medium",
        context_window=200_000,
        max_output=32_000,
        supports_thinking=True,
    ),
    "claude-opus-4-5-thinking-high": AntigravityModelInfo(
        id="claude-opus-4-5-thinking-high",
        name="Claude Opus 4.5 Thinking High",
        context_window=200_000,
        max_output=64_000,
        supports_thinking=True,
    ),
}


def get_antigravity_credential_path(custom_path: str | None = None) -> Path:
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
    return Path.home() / ANTIGRAVITY_DIR / ANTIGRAVITY_CREDENTIAL_FILENAME
