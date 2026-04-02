from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from revibe.core.agent import Agent
from revibe.core.config import (
    ModelConfig,
    ProviderConfig,
    SessionLoggingConfig,
    VibeConfig,
)
from revibe.core.llm.backend.openai import OpenAIBackend as GenericBackend
from revibe.core.llm.format import APIToolFormatHandler
from revibe.core.types import AssistantEvent, LLMMessage, ReasoningEvent, Role
from tests.mock.utils import mock_llm_chunk
from tests.stubs.fake_backend import FakeBackend


def make_config() -> VibeConfig:
    return VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        auto_compact_threshold=0,
        system_prompt_id="tests",
        include_project_context=False,
        include_prompt_detail=False,
        include_model_info=False,
        include_commit_signature=False,
        enabled_tools=[],
        tools={},
    )


class TestGenericBackendReasoningContent:
    @pytest.mark.asyncio
    async def test_complete_extracts_reasoning_content(self):
        base_url = "https://api.example.com"
        json_response = {
            "id": "fake_id",
            "created": 1234567890,
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "The answer is 42.",
                        "reasoning_content": "Let me think step by step...",
                    },
                }
            ],
        }

        with respx.mock(base_url=base_url) as mock_api:
            mock_api.post("/v1/chat/completions").mock(
                return_value=httpx.Response(status_code=200, json=json_response)
            )
            provider = ProviderConfig(
                name="test", api_base=f"{base_url}/v1", api_key_env_var="API_KEY"
            )
            backend = GenericBackend(provider=provider)
            model = ModelConfig(name="test-model", provider="test", alias="test")
            messages = [LLMMessage(role=Role.user, content="What is the answer?")]

            result = await backend.complete(
                model=model,
                messages=messages,
                temperature=0.2,
                tools=None,
                max_tokens=None,
                tool_choice=None,
                extra_headers=None,
            )

            assert result.message.content == "The answer is 42."
            assert result.message.reasoning_content == "Let me think step by step..."

    @pytest.mark.asyncio
    async def test_complete_streaming_extracts_reasoning_content(self):
        base_url = "https://api.example.com"
        chunks = [
            b'data: {"id":"id1","object":"chat.completion.chunk","created":123,"model":"test","choices":[{"index":0,"delta":{"role":"assistant","reasoning_content":"Thinking..."},"finish_reason":null}]}',
            b'data: {"id":"id1","object":"chat.completion.chunk","created":123,"model":"test","choices":[{"index":0,"delta":{"content":"Answer"},"finish_reason":null}]}',
            b'data: {"id":"id1","object":"chat.completion.chunk","created":123,"model":"test","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5}}',
            b"data: [DONE]",
        ]

        with respx.mock(base_url=base_url) as mock_api:
            mock_api.post("/v1/chat/completions").mock(
                return_value=httpx.Response(
                    status_code=200,
                    stream=httpx.ByteStream(stream=b"\n\n".join(chunks)),
                    headers={"Content-Type": "text/event-stream"},
                )
            )
            provider = ProviderConfig(
                name="test", api_base=f"{base_url}/v1", api_key_env_var="API_KEY"
            )
            backend = GenericBackend(provider=provider)
            model = ModelConfig(name="test-model", provider="test", alias="test")
            messages = [LLMMessage(role=Role.user, content="Stream please")]

            results = []
            async for chunk in backend.complete_streaming(
                model=model,
                messages=messages,
                temperature=0.2,
                tools=None,
                max_tokens=None,
                tool_choice=None,
                extra_headers=None,
            ):
                results.append(chunk)

            assert results[0].message.reasoning_content == "Thinking..."
            assert results[0].message.content == ""
            assert results[1].message.content == "Answer"
            assert results[1].message.reasoning_content is None


class TestAPIToolFormatHandlerReasoningContent:
    def test_process_api_response_message_extracts_reasoning_content(self):
        handler = APIToolFormatHandler()

        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = "The answer is 42."
        mock_message.reasoning_content = "Let me think..."
        mock_message.tool_calls = None

        result = handler.process_api_response_message(mock_message)

        assert result.content == "The answer is 42."
        assert result.reasoning_content == "Let me think..."

    def test_process_api_response_message_handles_missing_reasoning_content(self):
        handler = APIToolFormatHandler()

        mock_message = MagicMock(spec=["role", "content", "tool_calls"])
        mock_message.role = "assistant"
        mock_message.content = "Hello"
        mock_message.tool_calls = None

        result = handler.process_api_response_message(mock_message)

        assert result.content == "Hello"
        assert result.reasoning_content is None


class TestAgentStreamingReasoningEvents:
    @pytest.mark.asyncio
    async def test_streaming_accumulates_reasoning_in_message(self):
        backend = FakeBackend([
            mock_llm_chunk(content="", reasoning_content="First thought. "),
            mock_llm_chunk(content="", reasoning_content="Second thought."),
            mock_llm_chunk(content="Final answer."),
        ])
        agent = Agent(make_config(), backend=backend, enable_streaming=True)

        [_ async for _ in agent.act("Think and answer")]

        assistant_msg = next(m for m in agent.messages if m.role == Role.assistant)
        assert assistant_msg.reasoning_content == "First thought. Second thought."
        assert assistant_msg.content == "Final answer."

    @pytest.mark.asyncio
    async def test_streaming_content_only_no_reasoning(self):
        backend = FakeBackend([
            mock_llm_chunk(content="Hello "),
            mock_llm_chunk(content="world!"),
        ])
        agent = Agent(make_config(), backend=backend, enable_streaming=True)

        events = [event async for event in agent.act("Say hello")]

        reasoning_events = [e for e in events if isinstance(e, ReasoningEvent)]
        assert len(reasoning_events) == 0

        assistant_events = [e for e in events if isinstance(e, AssistantEvent)]
        assert len(assistant_events) == 1

        assistant_msg = next(m for m in agent.messages if m.role == Role.assistant)
        assert assistant_msg.reasoning_content is None
        assert assistant_msg.content == "Hello world!"


class TestLLMMessageReasoningContent:
    def test_llm_message_from_dict_with_reasoning_content(self):
        data = {
            "role": "assistant",
            "content": "Answer",
            "reasoning_content": "Thinking...",
        }

        msg = LLMMessage.model_validate(data)

        assert msg.reasoning_content == "Thinking..."

    def test_llm_message_model_dump_includes_reasoning_content(self):
        msg = LLMMessage(
            role=Role.assistant, content="Answer", reasoning_content="Thinking..."
        )

        dumped = msg.model_dump(exclude_none=True)

        assert dumped["reasoning_content"] == "Thinking..."

    def test_llm_message_model_dump_excludes_none_reasoning_content(self):
        msg = LLMMessage(role=Role.assistant, content="Answer")

        dumped = msg.model_dump(exclude_none=True)

        assert "reasoning_content" not in dumped
