from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto


class ChunkType(StrEnum):
    THINK = auto()
    TEXT = auto()


@dataclass
class ThinkChunk:
    """Represents a chunk of thinking/reasoning content from the LLM."""

    content: str
    timestamp: float | None = None


@dataclass
class TextChunk:
    """Represents a chunk of regular text content from the LLM."""

    content: str
    timestamp: float | None = None


@dataclass
class ChunkedResponse:
    """A response composed of alternating think and text chunks."""

    chunks: list[ThinkChunk | TextChunk]

    @property
    def thinking_content(self) -> str:
        """Extract all thinking content from the response."""
        return "".join(
            chunk.content for chunk in self.chunks if isinstance(chunk, ThinkChunk)
        )

    @property
    def text_content(self) -> str:
        """Extract all regular text content from the response."""
        return "".join(
            chunk.content for chunk in self.chunks if isinstance(chunk, TextChunk)
        )

    @property
    def has_thinking(self) -> bool:
        """Check if the response contains any thinking content."""
        return any(isinstance(chunk, ThinkChunk) for chunk in self.chunks)

    def to_dict(self) -> dict[str, str]:
        """Convert to a dict with thinking and text keys."""
        return {"thinking": self.thinking_content, "text": self.text_content}
