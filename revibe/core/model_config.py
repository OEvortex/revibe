from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from revibe.core.llm.backend.known_providers import iter_known_models
from revibe.core.llm.context_manager import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_MAX_OUTPUT_TOKENS,
    resolve_advertised_token_limits,
    resolve_global_capabilities,
    resolve_global_token_limits,
)


class ModelConfig(BaseModel):
    """Configuration for an LLM model.

    Attributes:
        supported_formats: List of supported tool calling formats.
            - "native": Uses API's native function/tool calling
            - "xml": Uses XML-based tool calling in prompts
            Models default to supporting both formats.
    """

    name: str
    provider: str
    alias: str
    temperature: float = 0.2
    input_price: float = 0.0
    output_price: float = 0.0
    context: int = 128000
    max_output: int = 32000
    supported_formats: list[str] = Field(default_factory=lambda: ["native", "xml"])
    auto_compact_threshold: int | None = Field(
        default=None,
        description=(
            "Per-model auto-compact threshold. If set, overrides the global "
            "auto_compact_threshold for this specific model. Value is in tokens."
        ),
    )
    capabilities: dict[str, bool] = Field(
        default_factory=lambda: {"toolCalling": True, "imageInput": False},
        description="Model capabilities: toolCalling and imageInput support.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_defaults(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if "alias" not in data or data["alias"] is None:
            data["alias"] = data.get("name")

        model_name = data.get("name") or data.get("alias")
        if not isinstance(model_name, str) or not model_name:
            return data

        context_value = data.get("context")
        max_output_value = data.get("max_output")

        if context_value is None and max_output_value is None:
            limits = resolve_global_token_limits(
                model_name,
                DEFAULT_CONTEXT_LENGTH,
                default_context_length=DEFAULT_CONTEXT_LENGTH,
                default_max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            )
            data["context"] = limits.total_context_tokens
            data["max_output"] = limits.max_output_tokens
            return data

        if context_value is None and max_output_value is not None:
            limits = resolve_global_token_limits(
                model_name,
                int(max_output_value),
                default_context_length=DEFAULT_CONTEXT_LENGTH,
                default_max_output_tokens=int(max_output_value),
            )
            data["context"] = limits.total_context_tokens
            return data

        if context_value is not None and max_output_value is None:
            limits = resolve_advertised_token_limits(
                model_name,
                int(context_value),
                default_context_length=int(context_value),
                default_max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            )
            data["max_output"] = limits.max_output_tokens

        if "capabilities" not in data or data.get("capabilities") is None:
            data["capabilities"] = resolve_global_capabilities(model_name)

        return data


def _build_default_models() -> list[ModelConfig]:
    return [ModelConfig.model_validate(model) for model in iter_known_models()]


DEFAULT_MODELS = _build_default_models()
