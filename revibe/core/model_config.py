from __future__ import annotations

from typing import Any
from pydantic import BaseModel, model_validator


class ModelConfig(BaseModel):
    name: str
    provider: str
    alias: str
    temperature: float = 0.2
    input_price: float = 0.0  # Price per million input tokens
    output_price: float = 0.0  # Price per million output tokens

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
    ),
    ModelConfig(
        name="devstral-small-latest",
        provider="mistral",
        alias="devstral-small",
        input_price=0.1,
        output_price=0.3,
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
    # Anthropic models
    ModelConfig(
        name="claude-sonnet-4-20250514",
        provider="anthropic",
        alias="claude-sonnet-4",
        input_price=3.0,
        output_price=15.0,
    ),
    ModelConfig(
        name="claude-3-5-haiku-20241022",
        provider="anthropic",
        alias="claude-haiku",
        input_price=0.8,
        output_price=4.0,
    ),
    # Groq models
    ModelConfig(
        name="llama-3.3-70b-versatile",
        provider="groq",
        alias="llama-70b",
        input_price=0.59,
        output_price=0.79,
    ),
    ModelConfig(
        name="llama-3.1-8b-instant",
        provider="groq",
        alias="llama-8b",
        input_price=0.05,
        output_price=0.08,
    ),
    # Local models
    ModelConfig(
        name="devstral",
        provider="llamacpp",
        alias="local",
        input_price=0.0,
        output_price=0.0,
    ),
    ModelConfig(
        name="codellama",
        provider="ollama",
        alias="ollama-codellama",
        input_price=0.0,
        output_price=0.0,
    ),
]
