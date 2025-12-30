from __future__ import annotations

from tests.backend.data import Chunk, JsonResponse, ResultData, Url

SIMPLE_CONVERSATION_PARAMS: list[tuple[Url, JsonResponse, ResultData]] = [
    (
        "https://api.groq.com",
        {
            "id": "chatcmpl-groq-123456789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "llama3-70b-8192",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello from Groq! How can I assist you?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 8,
                "completion_tokens": 12,
                "total_tokens": 20,
            },
        },
        {
            "message": "Hello from Groq! How can I assist you?",
            "usage": {
                "prompt_tokens": 8,
                "completion_tokens": 12,
            },
        },
    )
]

TOOL_CONVERSATION_PARAMS: list[tuple[Url, JsonResponse, ResultData]] = [
    (
        "https://api.groq.com",
        {
            "id": "chatcmpl-groq-123456789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "llama3-70b-8192",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Let me process that request.",
                        "tool_calls": [
                            {
                                "id": "call-groq-123456789",
                                "type": "function",
                                "function": {
                                    "name": "process_data",
                                    "arguments": '{"format": "json", "compression": "gzip"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 18,
                "total_tokens": 33,
            },
        },
        {
            "message": "Let me process that request.",
            "tool_calls": [
                {
                    "name": "process_data",
                    "arguments": '{"format": "json", "compression": "gzip"}',
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 18,
            },
        },
    )
]

STREAMED_SIMPLE_CONVERSATION_PARAMS: list[tuple[Url, list[Chunk], list[ResultData]]] = [
    (
        "https://api.groq.com",
        [
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " from"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " Groq"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": "!"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " How"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " can"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " I"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " assist"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " you"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": "?"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":8,"completion_tokens":12,"total_tokens":20}}',
            b"data: [DONE]",
        ],
        [
            {"message": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "Hello", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " from", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " Groq", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "!", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " How", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " can", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " I", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " assist", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " you", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "?", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "usage": {"prompt_tokens": 8, "completion_tokens": 12}},
        ],
    )
]

STREAMED_TOOL_CONVERSATION_PARAMS: list[tuple[Url, list[Chunk], list[ResultData]]] = [
    (
        "https://api.groq.com",
        [
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content":"Let"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " me"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " process"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " that"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": " request"},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"content": "."},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call-groq-123456789","type":"function","function":{"name":"process_data","arguments":""}}]},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\"format\": \"json\", \"compression\": \"gzip\"}"}}]},"finish_reason":null}]}',
            b'data: {"id":"chatcmpl-groq-123456789","object":"chat.completion.chunk","created":1234567890,"model":"llama3-70b-8192","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":15,"completion_tokens":18,"total_tokens":33}}',
            b"data: [DONE]",
        ],
        [
            {"message": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "Let", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " me", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " process", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " that", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " request", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": ".", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "tool_calls": [{"name": "process_data", "arguments": "", "index": 0}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "tool_calls": [{"name": "", "arguments": '{"format": "json", "compression": "gzip"}', "index": 0}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "usage": {"prompt_tokens": 15, "completion_tokens": 18}},
        ],
    )
]
