from __future__ import annotations

from revibe.core.config import Backend
from revibe.core.llm.backend.cerebras import CerebrasBackend
from revibe.core.llm.backend.groq import GroqBackend
from revibe.core.llm.backend.huggingface import HuggingFaceBackend
from revibe.core.llm.backend.llamacpp import LlamaCppBackend
from revibe.core.llm.backend.mistral import MistralBackend
from revibe.core.llm.backend.ollama import OllamaBackend
from revibe.core.llm.backend.openai import OpenAIBackend
from revibe.core.llm.backend.qwen import QwenBackend

BACKEND_FACTORY = {
    Backend.MISTRAL: MistralBackend,
    Backend.GENERIC: OpenAIBackend,
    Backend.OPENAI: OpenAIBackend,
    Backend.HUGGINGFACE: HuggingFaceBackend,
    Backend.GROQ: GroqBackend,
    Backend.OLLAMA: OllamaBackend,
    Backend.LLAMACPP: LlamaCppBackend,
    Backend.CEREBRAS: CerebrasBackend,
    Backend.QWEN: QwenBackend,
}
