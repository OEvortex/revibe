"""Token limit resolution and model capability detection.

Model-specific token limits and capabilities are defined as data-driven
profiles rather than hardcoded detection functions. When models are
fetched from provider APIs, their limits and capabilities are stored
directly in ModelConfig fields. The profiles here serve as fallbacks
for models that don't have explicit configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

TOKENS_PER_KIBI = 1024
TOKENS_PER_MEBI = TOKENS_PER_KIBI * TOKENS_PER_KIBI

DEFAULT_CONTEXT_LENGTH = 128 * TOKENS_PER_KIBI
DEFAULT_MAX_OUTPUT_TOKENS = 16 * TOKENS_PER_KIBI
DEFAULT_MIN_RESERVED_INPUT_TOKENS = 1_024

HIGH_CONTEXT_THRESHOLD = 200 * TOKENS_PER_KIBI
HIGH_CONTEXT_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI


@dataclass(frozen=True, slots=True)
class TokenLimits:
    max_input_tokens: int
    max_output_tokens: int

    @property
    def total_context_tokens(self) -> int:
        return self.max_input_tokens + self.max_output_tokens


@dataclass(frozen=True, slots=True)
class _ModelProfile:
    """Data-driven model profile for token limits and capabilities."""

    pattern: str
    limits: TokenLimits
    supports_vision: bool = False

    def matches(self, model_id: str) -> bool:
        return bool(re.search(self.pattern, model_id, flags=re.IGNORECASE))


# Data-driven model profiles. Each entry defines a regex pattern to match
# model IDs, the token limits to use, and whether the model supports vision.
# Order matters: first matching profile wins.
MODEL_PROFILES: list[_ModelProfile] = [
    _ModelProfile(
        r"qwen[-_]?3(?:\.|[-_])?5[-_]?(?:flash|plus)",
        TokenLimits(TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"qwen[-_]?3(?:\.|[-_])?6",
        TokenLimits(TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"gpt-5",
        TokenLimits(400 * TOKENS_PER_KIBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"gpt-4-1",
        TokenLimits(TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"gpt-4o",
        TokenLimits(128 * TOKENS_PER_KIBI - 16 * TOKENS_PER_KIBI, 16 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"nova[-_]?2",
        TokenLimits(TOKENS_PER_MEBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"claude[-_]?opus[-_]?4(?:\.|-)6",
        TokenLimits(TOKENS_PER_MEBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"claude[-_]?",
        TokenLimits(200 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"gemini[-_]?3(?:\.[-_]?1)?",
        TokenLimits(TOKENS_PER_MEBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"gemini[-_]?2(?:\.|-)5",
        TokenLimits(TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"gemini[-_]?2(?!\.|-?5)",
        TokenLimits(TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"gemini[-_]?\d",
        TokenLimits(TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"mimo[-_]?v2[-_]?pro",
        TokenLimits(TOKENS_PER_MEBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"mimo[-_]?v2[-_]?omni",
        TokenLimits(256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"ming[-_]?flash[-_]?omni[-_]?2(?:\.|-)0",
        TokenLimits(64 * TOKENS_PER_KIBI - 8 * TOKENS_PER_KIBI, 8 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"ming-flash-omni-2-0",
        TokenLimits(64 * TOKENS_PER_KIBI - 8 * TOKENS_PER_KIBI, 8 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"minimax[-_]?m2",
        TokenLimits(205 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"deepseek[-_]?",
        TokenLimits(160 * TOKENS_PER_KIBI - 16 * TOKENS_PER_KIBI, 16 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"devstral[-_]?2",
        TokenLimits(256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"gemma[-_]?3",
        TokenLimits(128 * TOKENS_PER_KIBI - 16 * TOKENS_PER_KIBI, 16 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"llama[-_]?3[-_]?2",
        TokenLimits(128 * TOKENS_PER_KIBI - 16 * TOKENS_PER_KIBI, 16 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"kimi[-_/]?k2(?:\.|-)5",
        TokenLimits(256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"kimi[-_]?k2",
        TokenLimits(256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
    ),
    _ModelProfile(
        r"qwen3\.5",
        TokenLimits(256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
        supports_vision=True,
    ),
    _ModelProfile(
        r"nemotron[-_]?3",
        TokenLimits(256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI),
    ),
]

# Models matching these patterns support vision regardless of MODEL_PROFILES
_VISION_PATTERNS: list[str] = [r"gpt(?!-oss)"]


def _match_profile(model_id: str) -> _ModelProfile | None:
    """Find the first matching model profile for a model ID."""
    for profile in MODEL_PROFILES:
        if profile.matches(model_id):
            return profile
    return None


def resolve_global_token_limits(
    model_id: str,
    context_length: int,
    *,
    default_context_length: int = DEFAULT_CONTEXT_LENGTH,
    default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    min_reserved_input_tokens: int | None = None,
) -> TokenLimits:
    """Resolve token limits for a model using data-driven profiles.

    Falls back to computed defaults based on advertised context_length
    when no profile matches.
    """
    reserved_input_tokens = (
        min_reserved_input_tokens
        if min_reserved_input_tokens and min_reserved_input_tokens > 0
        else DEFAULT_MIN_RESERVED_INPUT_TOKENS
    )

    if profile := _match_profile(model_id):
        return profile.limits

    safe_context_length = (
        context_length
        if isinstance(context_length, int) and context_length > reserved_input_tokens
        else default_context_length
    )
    max_output = min(
        max(1, default_max_output_tokens),
        max(1, safe_context_length - reserved_input_tokens),
    )
    max_input = max(1, safe_context_length - max_output)
    return TokenLimits(max_input, max_output)


def resolve_advertised_token_limits(
    model_id: str,
    advertised_context_length: int | None,
    *,
    default_context_length: int = DEFAULT_CONTEXT_LENGTH,
    default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    advertised_max_output_tokens: int | None = None,
    min_reserved_input_tokens: int | None = None,
) -> TokenLimits:
    """Resolve token limits considering both global profiles and advertised values."""
    resolved_limits = resolve_global_token_limits(
        model_id,
        advertised_context_length
        if advertised_context_length is not None
        else default_context_length,
        default_context_length=default_context_length,
        default_max_output_tokens=default_max_output_tokens,
        min_reserved_input_tokens=min_reserved_input_tokens,
    )

    if (
        advertised_max_output_tokens is None
        or not isinstance(advertised_max_output_tokens, int)
        or advertised_max_output_tokens <= 0
    ):
        return resolved_limits

    total_context_tokens = resolved_limits.total_context_tokens
    bounded_max_output_tokens = min(
        advertised_max_output_tokens, max(1, total_context_tokens - 1)
    )
    return TokenLimits(
        max(1, total_context_tokens - bounded_max_output_tokens),
        bounded_max_output_tokens,
    )


def resolve_global_capabilities(
    model_id: str,
    *,
    detected_tool_calling: bool | None = None,
    detected_image_input: bool | None = None,
) -> dict[str, bool]:
    """Resolve model capabilities using data-driven profiles.

    detected_* parameters allow the caller to override defaults based on
    API-reported capabilities. The model profile's supports_vision flag
    serves as a fallback.
    """
    image_input = bool(detected_image_input)

    if not image_input:
        if profile := _match_profile(model_id):
            image_input = profile.supports_vision

    if not image_input:
        for pattern in _VISION_PATTERNS:
            if re.search(pattern, model_id, flags=re.IGNORECASE):
                image_input = True
                break

    return {
        "toolCalling": True
        if detected_tool_calling is None
        else bool(detected_tool_calling),
        "imageInput": image_input,
    }
