from __future__ import annotations

from revibe.core.config import Backend
from revibe.core.llm.backend.generic import GenericBackend
from revibe.core.llm.backend.groq import GroqBackend
from revibe.core.llm.backend.huggingface import HuggingFaceBackend
from revibe.core.llm.backend.mistral import MistralBackend
from revibe.core.llm.backend.openai import OpenAIBackend

BACKEND_FACTORY = {
    Backend.MISTRAL: MistralBackend,
    Backend.GENERIC: GenericBackend,
    Backend.OPENAI: OpenAIBackend,
    Backend.HUGGINGFACE: HuggingFaceBackend,
    Backend.GROQ: GroqBackend,
}
