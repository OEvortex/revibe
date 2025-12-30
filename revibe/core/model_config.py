from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


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
        name="gpt-5.2",
        provider="openai",
        alias="gpt-5.2",
        input_price=1.75,
        output_price=14.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5.1",
        provider="openai",
        alias="gpt-5.1",
        input_price=1.25,
        output_price=10.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5",
        provider="openai",
        alias="gpt-5",
        input_price=1.25,
        output_price=10.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5-mini",
        provider="openai",
        alias="gpt-5-mini",
        input_price=0.25,
        output_price=2.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5.1-codex-max",
        provider="openai",
        alias="gpt-5.1-codex-max",
        input_price=1.25,
        output_price=10.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5.1-codex",
        provider="openai",
        alias="gpt-5.1-codex",
        input_price=1.25,
        output_price=10.0,
        context=1000000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5-codex",
        provider="openai",
        alias="gpt-5-codex",
        input_price=1.25,
        output_price=10.0,
        context=1000000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5.2-pro",
        provider="openai",
        alias="gpt-5.2-pro",
        input_price=21.0,
        output_price=168.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-5-pro",
        provider="openai",
        alias="gpt-5-pro",
        input_price=15.0,
        output_price=120.0,
        context=400000,
        max_output=128000,
    ),
    ModelConfig(
        name="gpt-4.1",
        provider="openai",
        alias="gpt-4.1",
        input_price=2.0,
        output_price=8.0,
        context=1000000,
        max_output=32768,
    ),
    # Groq models
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
        alias="gpt-oss-120b-groq",
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
        alias="llama-3.3-70b-groq",
        input_price=0.59,
        output_price=0.79,
        context=131072,
        max_output=32768,
    ),
    ModelConfig(
        name="zai-org/GLM-4.7",
        provider="huggingface",
        alias="glm-4.7",
        input_price=0.6,
        output_price=2.2,
        context=204800,
    ),
    ModelConfig(
        name="MiniMaxAI/MiniMax-M2.1",
        provider="huggingface",
        alias="minimax-m2.1",
        input_price=0.3,
        output_price=1.2,
        context=204800,
    ),
    ModelConfig(
        name="XiaomiMiMo/MiMo-V2-Flash",
        provider="huggingface",
        alias="mimo-v2-flash",
        input_price=0.098,
        output_price=0.293,
        context=262144,
    ),
    ModelConfig(
        name="deepseek-ai/DeepSeek-V3.2",
        provider="huggingface",
        alias="deepseek-v3.2",
        input_price=0.269,
        output_price=0.4,
        context=163840,
    ),
    ModelConfig(
        name="MiniMaxAI/MiniMax-M2",
        provider="huggingface",
        alias="minimax-m2",
        input_price=0.24,
        output_price=0.96,
        context=204800,
    ),
    ModelConfig(
        name="zai-org/GLM-4.6V-Flash",
        provider="huggingface",
        alias="glm-4.6v-flash",
        input_price=0.3,
        output_price=0.9,
        context=131072,
    ),
    ModelConfig(
        name="moonshotai/Kimi-K2-Thinking",
        provider="huggingface",
        alias="kimi-k2-thinking",
        input_price=0.48,
        output_price=2.0,
        context=262144,
    ),
    ModelConfig(
        name="moonshotai/Kimi-K2-Instruct-0905",
        provider="huggingface",
        alias="kimi-k2-instruct",
        input_price=0.48,
        output_price=2.0,
        context=262144,
    ),
    ModelConfig(
        name="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        provider="huggingface",
        alias="qwen3-coder-30b",
        input_price=0.1,
        output_price=0.3,
        context=262144,
    ),
    ModelConfig(
        name="deepseek-ai/DeepSeek-V3.2-Exp",
        provider="huggingface",
        alias="deepseek-v3.2-exp",
        input_price=0.216,
        output_price=0.328,
        context=163840,
    ),
    ModelConfig(
        name="MiniMaxAI/MiniMax-M1-80k",
        provider="huggingface",
        alias="minimax-m1-80k",
        input_price=0.44,
        output_price=1.76,
        context=1000000,
    ),
    ModelConfig(
        name="Qwen/Qwen3-Coder-480B-A35B-Instruct",
        provider="huggingface",
        alias="qwen3-coder-480b",
        input_price=0.24,
        output_price=1.04,
        context=262144,
    ),
    # Cerebras models
    ModelConfig(
        name="zai-glm-4.6",
        provider="cerebras",
        alias="zai-glm-4.6",
        input_price=2.25,
        output_price=2.75,
        context=131072,
        max_output=40960,
    ),
    ModelConfig(
        name="qwen-3-235b-a22b-instruct-2507",
        provider="cerebras",
        alias="qwen-3-235b",
        input_price=0.60,
        output_price=1.20,
        context=131072,
        max_output=40960,
    ),
    ModelConfig(
        name="llama-3.3-70b",
        provider="cerebras",
        alias="llama-3.3-70b-cerebras",
        input_price=0.85,
        output_price=1.20,
        context=128000,
        max_output=65536,
    ),
    ModelConfig(
        name="qwen-3-32b",
        provider="cerebras",
        alias="qwen-3-32b",
        input_price=0.40,
        output_price=0.80,
        context=131072,
        max_output=8192,
    ),
    ModelConfig(
        name="gpt-oss-120b",
        provider="cerebras",
        alias="gpt-oss-120b-cerebras",
        input_price=0.35,
        output_price=0.75,
        context=131072,
        max_output=40960,
    ),
    # Qwen Code models
    ModelConfig(
        name="qwen3-coder-plus",
        provider="qwencode",
        alias="qwen-coder-plus",
        input_price=0.0,
        output_price=0.0,
        context=1000000,
        max_output=65536,
    ),
    ModelConfig(
        name="qwen3-coder-flash",
        provider="qwencode",
        alias="qwen-coder-flash",
        input_price=0.0,
        output_price=0.0,
        context=1000000,
        max_output=65536,
    ),
]
