from __future__ import annotations

from dataclasses import dataclass
import re

TOKENS_PER_KIBI = 1024
TOKENS_PER_MEBI = TOKENS_PER_KIBI * TOKENS_PER_KIBI

DEFAULT_CONTEXT_LENGTH = 128 * TOKENS_PER_KIBI
DEFAULT_MAX_OUTPUT_TOKENS = 16 * TOKENS_PER_KIBI
DEFAULT_MIN_RESERVED_INPUT_TOKENS = 1_024

CLAUDE_TOTAL_TOKENS = 200 * TOKENS_PER_KIBI
CLAUDE_MAX_INPUT_TOKENS = CLAUDE_TOTAL_TOKENS - 32 * TOKENS_PER_KIBI
CLAUDE_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI

DEVSTRAL_MAX_INPUT_TOKENS = 256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI
DEVSTRAL_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI

DEEPSEEK_TOTAL_TOKENS = 160 * TOKENS_PER_KIBI
DEEPSEEK_MAX_OUTPUT_TOKENS = 16 * TOKENS_PER_KIBI
DEEPSEEK_MAX_INPUT_TOKENS = DEEPSEEK_TOTAL_TOKENS - DEEPSEEK_MAX_OUTPUT_TOKENS

FIXED_128K_MAX_INPUT_TOKENS = 128 * TOKENS_PER_KIBI - 16 * TOKENS_PER_KIBI
FIXED_128K_MAX_OUTPUT_TOKENS = 16 * TOKENS_PER_KIBI

FIXED_256K_MAX_INPUT_TOKENS = 256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI
FIXED_256K_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI

FIXED_64K_TOTAL_TOKENS = 64 * TOKENS_PER_KIBI
FIXED_64K_MAX_OUTPUT_TOKENS = 8 * TOKENS_PER_KIBI
FIXED_64K_MAX_INPUT_TOKENS = FIXED_64K_TOTAL_TOKENS - FIXED_64K_MAX_OUTPUT_TOKENS

GEMINI_1M_TOTAL_TOKENS = TOKENS_PER_MEBI
GEMINI25_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI
GEMINI25_MAX_INPUT_TOKENS = GEMINI_1M_TOTAL_TOKENS - GEMINI25_MAX_OUTPUT_TOKENS
GEMINI2_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI
GEMINI2_MAX_INPUT_TOKENS = GEMINI_1M_TOTAL_TOKENS - GEMINI2_MAX_OUTPUT_TOKENS
GEMINI3_MAX_OUTPUT_TOKENS = 64 * TOKENS_PER_KIBI
GEMINI3_MAX_INPUT_TOKENS = GEMINI_1M_TOTAL_TOKENS - GEMINI3_MAX_OUTPUT_TOKENS

GPT4_1_TOTAL_TOKENS = TOKENS_PER_MEBI
GPT4_1_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI
GPT4_1_MAX_INPUT_TOKENS = GPT4_1_TOTAL_TOKENS - GPT4_1_MAX_OUTPUT_TOKENS

GPT5_MAX_INPUT_TOKENS = 400 * TOKENS_PER_KIBI - 64 * TOKENS_PER_KIBI
GPT5_MAX_OUTPUT_TOKENS = 64 * TOKENS_PER_KIBI

MIMOV2_PRO_TOTAL_TOKENS = TOKENS_PER_MEBI
MIMOV2_PRO_MAX_OUTPUT_TOKENS = 64 * TOKENS_PER_KIBI
MIMOV2_PRO_MAX_INPUT_TOKENS = MIMOV2_PRO_TOTAL_TOKENS - MIMOV2_PRO_MAX_OUTPUT_TOKENS

MIMOV2_OMNI_MAX_INPUT_TOKENS = 256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI
MIMOV2_OMNI_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI

QWEN35_TOTAL_TOKENS = 256 * TOKENS_PER_KIBI
QWEN35_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI
QWEN35_MAX_INPUT_TOKENS = QWEN35_TOTAL_TOKENS - QWEN35_MAX_OUTPUT_TOKENS

QWEN35_1M_MAX_INPUT_TOKENS = TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI
QWEN35_1M_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI

QWEN36_1M_MAX_INPUT_TOKENS = TOKENS_PER_MEBI - 32 * TOKENS_PER_KIBI
QWEN36_1M_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI

MINIMAX_TOTAL_TOKENS = 205 * TOKENS_PER_KIBI
MINIMAX_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI
MINIMAX_MAX_INPUT_TOKENS = MINIMAX_TOTAL_TOKENS - MINIMAX_MAX_OUTPUT_TOKENS

HIGH_CONTEXT_THRESHOLD = 200 * TOKENS_PER_KIBI
HIGH_CONTEXT_MAX_OUTPUT_TOKENS = 32 * TOKENS_PER_KIBI


@dataclass(frozen=True, slots=True)
class TokenLimits:
    max_input_tokens: int
    max_output_tokens: int

    @property
    def total_context_tokens(self) -> int:
        return self.max_input_tokens + self.max_output_tokens


def is_devstral_model(model_id: str) -> bool:
    return bool(re.search(r"devstral[-_]?2", model_id, flags=re.IGNORECASE))


def is_deepseek_model(model_id: str) -> bool:
    return bool(re.search(r"deepseek[-_]?", model_id, flags=re.IGNORECASE))


def is_gemma3_model(model_id: str) -> bool:
    return bool(re.search(r"gemma[-_]?3", model_id, flags=re.IGNORECASE))


def is_llama32_model(model_id: str) -> bool:
    return bool(re.search(r"llama[-_]?3[-_]?2", model_id, flags=re.IGNORECASE))


def is_gemini25_model(model_id: str) -> bool:
    return bool(re.search(r"gemini[-_]?2(?:\.|-)5", model_id, flags=re.IGNORECASE))


def is_gemini2_model(model_id: str) -> bool:
    return bool(re.search(r"gemini[-_]?2(?!\.|-?5)", model_id, flags=re.IGNORECASE))


def is_gemini3_model(model_id: str) -> bool:
    return bool(re.search(r"gemini[-_]?3(?:\.[-_]?1)?", model_id, flags=re.IGNORECASE))


def is_gemini_model(model_id: str) -> bool:
    return bool(re.search(r"gemini[-_]?\d", model_id, flags=re.IGNORECASE))


def is_glm45_model(model_id: str) -> bool:
    return bool(re.search(r"glm-4\.5(?!\d)", model_id, flags=re.IGNORECASE))


def is_glm_model(model_id: str) -> bool:
    return bool(re.search(r"glm-(?:5|4\.(?:6|7))(?!\d)", model_id, flags=re.IGNORECASE))


def is_gpt41_model(model_id: str) -> bool:
    return bool(re.search(r"gpt-4-1", model_id, flags=re.IGNORECASE))


def is_gpt4o_model(model_id: str) -> bool:
    return bool(re.search(r"gpt-4o", model_id, flags=re.IGNORECASE))


def is_gpt5_model(model_id: str) -> bool:
    return bool(re.search(r"gpt-5", model_id, flags=re.IGNORECASE))


def is_qwen35_model(model_id: str) -> bool:
    return bool(re.search(r"qwen3\.5", model_id, flags=re.IGNORECASE))


def is_nemotron3_model(model_id: str) -> bool:
    return bool(re.search(r"nemotron[-_]?3", model_id, flags=re.IGNORECASE))


def is_nova2_model(model_id: str) -> bool:
    return bool(re.search(r"nova[-_]?2", model_id, flags=re.IGNORECASE))


def is_qwen35_one_million_context_model(model_id: str) -> bool:
    return bool(
        re.search(
            r"qwen[-_]?3(?:\.|[-_])?5[-_]?(?:flash|plus)", model_id, flags=re.IGNORECASE
        )
    )


def is_qwen36_one_million_context_model(model_id: str) -> bool:
    return bool(re.search(r"qwen[-_]?3(?:\.|[-_])?6", model_id, flags=re.IGNORECASE))


def is_claude_model(model_id: str) -> bool:
    return bool(re.search(r"claude[-_]?", model_id, flags=re.IGNORECASE))


def is_kimi_k25_model(model_id: str) -> bool:
    return bool(re.search(r"kimi[-_/]?k2(?:\.|-)5", model_id, flags=re.IGNORECASE))


def is_kimi_model(model_id: str) -> bool:
    return bool(re.search(r"kimi[-_]?k2", model_id, flags=re.IGNORECASE))


def is_minimax_model(model_id: str) -> bool:
    return bool(re.search(r"minimax[-_]?m2", model_id, flags=re.IGNORECASE))


def is_claude_opus_46_model(model_id: str) -> bool:
    return bool(
        re.search(r"claude[-_]?opus[-_]?4(?:\.|-)6", model_id, flags=re.IGNORECASE)
    )


def is_vision_gpt_model(model_id: str) -> bool:
    return bool(re.search(r"gpt", model_id, flags=re.IGNORECASE)) and not bool(
        re.search(r"gpt-oss", model_id, flags=re.IGNORECASE)
    )


def is_ming_flash_omni_model(model_id: str) -> bool:
    return bool(
        re.search(
            r"ming[-_]?flash[-_]?omni[-_]?2(?:\.|-)0", model_id, flags=re.IGNORECASE
        )
        or re.search(r"ming-flash-omni-2-0", model_id, flags=re.IGNORECASE)
    )


def is_mimo_v2_pro_model(model_id: str) -> bool:
    return bool(re.search(r"mimo[-_]?v2[-_]?pro", model_id, flags=re.IGNORECASE))


def is_mimo_v2_omni_model(model_id: str) -> bool:
    return bool(re.search(r"mimo[-_]?v2[-_]?omni", model_id, flags=re.IGNORECASE))


def resolve_global_token_limits(  # noqa: PLR0911, PLR0912
    model_id: str,
    context_length: int,
    *,
    default_context_length: int = DEFAULT_CONTEXT_LENGTH,
    default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    min_reserved_input_tokens: int | None = None,
) -> TokenLimits:
    reserved_input_tokens = (
        min_reserved_input_tokens
        if min_reserved_input_tokens and min_reserved_input_tokens > 0
        else DEFAULT_MIN_RESERVED_INPUT_TOKENS
    )

    if is_deepseek_model(model_id):
        return TokenLimits(DEEPSEEK_MAX_INPUT_TOKENS, DEEPSEEK_MAX_OUTPUT_TOKENS)

    if is_devstral_model(model_id):
        return TokenLimits(DEVSTRAL_MAX_INPUT_TOKENS, DEVSTRAL_MAX_OUTPUT_TOKENS)

    if is_gemma3_model(model_id):
        return TokenLimits(FIXED_128K_MAX_INPUT_TOKENS, FIXED_128K_MAX_OUTPUT_TOKENS)

    if is_llama32_model(model_id):
        return TokenLimits(FIXED_128K_MAX_INPUT_TOKENS, FIXED_128K_MAX_OUTPUT_TOKENS)

    if is_qwen35_one_million_context_model(model_id):
        return TokenLimits(QWEN35_1M_MAX_INPUT_TOKENS, QWEN35_1M_MAX_OUTPUT_TOKENS)

    if is_qwen36_one_million_context_model(model_id):
        return TokenLimits(QWEN36_1M_MAX_INPUT_TOKENS, QWEN36_1M_MAX_OUTPUT_TOKENS)

    if is_gpt41_model(model_id):
        return TokenLimits(GPT4_1_MAX_INPUT_TOKENS, GPT4_1_MAX_OUTPUT_TOKENS)

    if is_gpt4o_model(model_id):
        return TokenLimits(FIXED_128K_MAX_INPUT_TOKENS, FIXED_128K_MAX_OUTPUT_TOKENS)

    if is_gpt5_model(model_id):
        return TokenLimits(GPT5_MAX_INPUT_TOKENS, GPT5_MAX_OUTPUT_TOKENS)

    if is_ming_flash_omni_model(model_id):
        return TokenLimits(FIXED_64K_MAX_INPUT_TOKENS, FIXED_64K_MAX_OUTPUT_TOKENS)

    if is_mimo_v2_pro_model(model_id):
        return TokenLimits(MIMOV2_PRO_MAX_INPUT_TOKENS, MIMOV2_PRO_MAX_OUTPUT_TOKENS)

    if is_mimo_v2_omni_model(model_id):
        return TokenLimits(MIMOV2_OMNI_MAX_INPUT_TOKENS, MIMOV2_OMNI_MAX_OUTPUT_TOKENS)

    if is_minimax_model(model_id):
        return TokenLimits(MINIMAX_MAX_INPUT_TOKENS, MINIMAX_MAX_OUTPUT_TOKENS)

    if is_claude_model(model_id):
        return TokenLimits(CLAUDE_MAX_INPUT_TOKENS, CLAUDE_MAX_OUTPUT_TOKENS)

    if is_kimi_model(model_id):
        return TokenLimits(FIXED_256K_MAX_INPUT_TOKENS, FIXED_256K_MAX_OUTPUT_TOKENS)

    if is_qwen35_model(model_id):
        return TokenLimits(QWEN35_MAX_INPUT_TOKENS, QWEN35_MAX_OUTPUT_TOKENS)

    if is_nemotron3_model(model_id):
        return TokenLimits(
            256 * TOKENS_PER_KIBI - 32 * TOKENS_PER_KIBI, 32 * TOKENS_PER_KIBI
        )

    if is_nova2_model(model_id):
        return TokenLimits(TOKENS_PER_MEBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI)

    if is_claude_opus_46_model(model_id):
        return TokenLimits(TOKENS_PER_MEBI - 64 * TOKENS_PER_KIBI, 64 * TOKENS_PER_KIBI)

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
    image_input = bool(detected_image_input) or any((
        is_claude_model(model_id),
        is_kimi_k25_model(model_id),
        is_vision_gpt_model(model_id),
        is_gemini_model(model_id),
        is_qwen35_model(model_id),
        is_qwen35_one_million_context_model(model_id),
        is_qwen36_one_million_context_model(model_id),
        is_mimo_v2_omni_model(model_id),
    ))

    return {
        "toolCalling": True
        if detected_tool_calling is None
        else bool(detected_tool_calling),
        "imageInput": image_input,
    }
