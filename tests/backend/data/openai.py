from __future__ import annotations

from tests.backend.data import Chunk, JsonResponse, ResultData, Url

SIMPLE_CONVERSATION_PARAMS: list[tuple[Url, JsonResponse, ResultData]] = [
    (
        "https://api.openai.com",
        {
            "id": "chatcmpl-123456789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25,
            },
        },
        {
            "message": "Hello! How can I help you today?",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
            },
        },
    )
]

TOOL_CONVERSATION_PARAMS: list[tuple[Url, JsonResponse, ResultData]] = [
    (
        "https://api.openai.com",
        {
            "id": "chatcmpl-123456789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "I'll help with that!",
                        "tool_calls": [
                            {
                                "id": "call_123456789",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "San Francisco", "unit": "celsius"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 25,
                "total_tokens": 45,
            },
        },
        {
            "message": "I'll help with that!",
            "tool_calls": [
                {
                    "name": "get_weather",
                    "arguments": '{"location": "San Francisco", "unit": "celsius"}',
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 25,
            },
        },
    )
]

STREAMED_SIMPLE_CONVERSATION_PARAMS: list[tuple[Url, list[Chunk], list[ResultData]]] = [
    (
        "https://api.openai.com",
        [
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content":" How"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " can"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " I"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " help"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " you"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " today"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": "?"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":15,"total_tokens":25}}',
            b"data: [DONE]",
        ],
        [
            {"message": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "Hello", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "!", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " How", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " can", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " I", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " help", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " you", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " today", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "?", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "usage": {"prompt_tokens": 10, "completion_tokens": 15}},
        ],
    )
]

STREAMED_TOOL_CONVERSATION_PARAMS: list[tuple[Url, list[Chunk], list[ResultData]]] = [
    (
        "https://api.openai.com",
        [
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content":"I\'ll"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content":" help"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " with"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": " that"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"content": "!"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_123456789","type":"function","function":{"name":"get_weather","arguments":""}}]},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\"location\": \"San Francisco\", \"unit\": \"celsius\"}"}}]},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-0613","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":20,"completion_tokens":25,"total_tokens":45}}',
            b"data: [DONE]",
        ],
        [
            {"message": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "I'll", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " help", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " with", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " that", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "!", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "tool_calls": [{"name": "get_weather", "arguments": "", "index": 0}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "tool_calls": [{"name": "", "arguments": '{"location": "San Francisco", "unit": "celsius"}', "index": 0}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "usage": {"prompt_tokens": 20, "completion_tokens": 25}},
        ],
    )
]
