from __future__ import annotations

from tests.backend.data import Chunk, JsonResponse, ResultData, Url

SIMPLE_CONVERSATION_PARAMS: list[tuple[Url, JsonResponse, ResultData]] = [
    (
        "https://api-inference.huggingface.co",
        {
            "id": "hf-cmpl-123456789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "mistralai/Mistral-7B-Instruct-v0.2",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Bonjour! How can I assist you today?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 18,
                "total_tokens": 30,
            },
        },
        {
            "message": "Bonjour! How can I assist you today?",
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 18,
            },
        },
    )
]

TOOL_CONVERSATION_PARAMS: list[tuple[Url, JsonResponse, ResultData]] = [
    (
        "https://api-inference.huggingface.co",
        {
            "id": "hf-cmpl-123456789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "mistralai/Mistral-7B-Instruct-v0.2",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Let me fetch that information.",
                        "tool_calls": [
                            {
                                "id": "call-hf-123456789",
                                "type": "function",
                                "function": {
                                    "name": "fetch_data",
                                    "arguments": '{"source": "huggingface", "format": "json"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 30,
                "total_tokens": 55,
            },
        },
        {
            "message": "Let me fetch that information.",
            "tool_calls": [
                {
                    "name": "fetch_data",
                    "arguments": '{"source": "huggingface", "format": "json"}',
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 30,
            },
        },
    )
]

STREAMED_SIMPLE_CONVERSATION_PARAMS: list[tuple[Url, list[Chunk], list[ResultData]]] = [
    (
        "https://api-inference.huggingface.co",
        [
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content":"Bonjour"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": "!"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " How"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " can"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " I"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " assist"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " you"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " today"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": "?"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":18,"total_tokens":30}}',
            b"data: [DONE]",
        ],
        [
            {"message": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "Bonjour", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "!", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " How", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " can", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " I", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " assist", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " you", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " today", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "?", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "usage": {"prompt_tokens": 12, "completion_tokens": 18}},
        ],
    )
]

STREAMED_TOOL_CONVERSATION_PARAMS: list[tuple[Url, list[Chunk], list[ResultData]]] = [
    (
        "https://api-inference.huggingface.co",
        [
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content":"Let"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " me"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " fetch"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " that"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": " information"},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"content": "."},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call-hf-123456789","type":"function","function":{"name":"fetch_data","arguments":""}}]},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\"source\": \"huggingface\", \"format\": \"json\"}"}}]},"finish_reason":null}]}',
            b'data: {"id":"hf-cmpl-123456789","object":"chat.completion.chunk","created":1234567890,"model":"mistralai/Mistral-7B-Instruct-v0.2","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":25,"completion_tokens":30,"total_tokens":55}}',
            b"data: [DONE]",
        ],
        [
            {"message": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "Let", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " me", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " fetch", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " that", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": " information", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": ".", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "tool_calls": [{"name": "fetch_data", "arguments": "", "index": 0}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "tool_calls": [{"name": "", "arguments": '{"source": "huggingface", "format": "json"}', "index": 0}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            {"message": "", "usage": {"prompt_tokens": 25, "completion_tokens": 30}},
        ],
    )
]