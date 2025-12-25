from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator


class ModelConfig(BaseModel):
    name: str
    provider: str
    alias: str
    temperature: float = 0.2
    input_price: float = 0.0
    output_price: float = 0.0
    context: int = 128000
    max_output: int = 32000

    @model_validator(mode="before")
    @classmethod
    def _default_alias_to_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "alias" not in data or data["alias"] is None:
                data["alias"] = data.get("name")
        return data


DEFAULT_MODELS = [
    # Mistral models
    ModelConfig(
        name="mistral-vibe-cli-latest",
        provider="mistral",
        alias="devstral-2",
        input_price=0.4,
        output_price=2.0,
        context=200000,
        max_output=32000,
    ),
    ModelConfig(
        name="devstral-small-latest",
        provider="mistral",
        alias="devstral-small",
        input_price=0.1,
        output_price=0.3,
        context=200000,
        max_output=32000,
    ),
    # OpenAI models
    ModelConfig(
        name="gpt-4o",
        provider="openai",
        alias="gpt-4o",
        input_price=2.5,
        output_price=10.0,
    ),
    ModelConfig(
        name="gpt-4o-mini",
        provider="openai",
        alias="gpt-4o-mini",
        input_price=0.15,
        output_price=0.6,
    ),
    ModelConfig(
        name="o1",
        provider="openai",
        alias="o1",
        input_price=15.0,
        output_price=60.0,
    ),
    ### Groq models
    ModelConfig(
        name="moonshotai/kimi-k2-instruct-0905",
        provider="groq",
        alias="kimi-k2",
        input_price=1,
        output_price=3,
        context=262144,
        max_output=16384,
    ),
    ModelConfig(
        name="openai/gpt-oss-120b",
        provider="groq",
        alias="gpt-oss-120b",
        input_price=0.15,
        output_price=0.60,
        context=131072,
        max_output=65536,
    ),
    ModelConfig(
        name="qwen/qwen3-32b",
        provider="groq",
        alias="qwen3-32b",
        input_price=0.29,
        output_price=0.59,
        context=131072,
        max_output=40960,
    ),
    ModelConfig(
        name="llama-3.3-70b-versatile",
        provider="groq",
        alias="llama-3.3-70b",
        input_price=0.59,
        output_price=0.79,
        context=131072,
        max_output=32768,
    ),
    ModelConfig(
        name="zai-org/GLM-4.7-FP8",
        provider="huggingface",
        alias="glm-4.7",
    ),
]
