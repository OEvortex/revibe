from __future__ import annotations

from revibe.core.config import Backend
from revibe.core.llm.backend.anthropic.backend import AnthropicBackend
from revibe.core.llm.backend.openai import OpenAIBackend
from revibe.core.llm.backend.oai import OAIBackend

BACKEND_FACTORY = {
    Backend.GENERIC: OpenAIBackend,
    Backend.OPENAI: OpenAIBackend,
    Backend.MISTRAL: OpenAIBackend,
    Backend.HUGGINGFACE: OpenAIBackend,
    Backend.GROQ: OpenAIBackend,
    Backend.OLLAMA: OpenAIBackend,
    Backend.LLAMACPP: OpenAIBackend,
    Backend.CEREBRAS: OpenAIBackend,
    Backend.QWEN: OpenAIBackend,
    Backend.OPENROUTER: OpenAIBackend,
    Backend.KILOCODE: OpenAIBackend,
    Backend.CHUTES: OpenAIBackend,
    Backend.VERTEXAI: OpenAIBackend,
    Backend.VLLM: OpenAIBackend,
    Backend.GEMINICLI: AnthropicBackend,
    Backend.ANTIGRAVITY: AnthropicBackend,
    Backend.OPENCODE: OAIBackend,
}
