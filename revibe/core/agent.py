from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from enum import StrEnum, auto
import inspect
import time
from typing import cast
from uuid import uuid4

from pydantic import BaseModel

from revibe.core.config import ToolFormat, VibeConfig
from revibe.core.interaction_logger import InteractionLogger
from revibe.core.llm.backend.factory import get_backend_for_provider
from revibe.core.llm.format import (
    APIToolFormatHandler,
    ResolvedMessage,
    XMLToolFormatHandler,
)
from revibe.core.llm.types import BackendLike
from revibe.core.middleware import (
    AutoCompactMiddleware,
    ContextWarningMiddleware,
    ConversationContext,
    MiddlewareAction,
    MiddlewarePipeline,
    MiddlewareResult,
    PlanModeMiddleware,
    PriceLimitMiddleware,
    ResetReason,
    TurnLimitMiddleware,
)
from revibe.core.modes import AgentMode
from revibe.core.prompts import UtilityPrompt
from revibe.core.skills.manager import SkillManager
from revibe.core.system_prompt import get_universal_system_prompt
from revibe.core.tools.base import ToolError, ToolPermission, ToolPermissionError
from revibe.core.tools.manager import ToolManager
from revibe.core.types import (
    AgentStats,
    ApprovalCallback,
    ApprovalResponse,
    AssistantEvent,
    AsyncApprovalCallback,
    BaseEvent,
    CompactEndEvent,
    CompactStartEvent,
    LLMChunk,
    LLMMessage,
    LLMUsage,
    ReasoningEvent,
    Role,
    SyncApprovalCallback,
    ToolCallEvent,
    ToolResultEvent,
)
from revibe.core.utils import (
    TOOL_ERROR_TAG,
    VIBE_STOP_EVENT_TAG,
    CancellationReason,
    get_user_agent,
    get_user_cancellation_message,
    is_user_cancellation_event,
)


class ToolExecutionResponse(StrEnum):
    SKIP = auto()
    EXECUTE = auto()


class ToolDecision(BaseModel):
    verdict: ToolExecutionResponse
    feedback: str | None = None


class AgentError(Exception):
    """Base exception for Agent errors."""


class AgentStateError(AgentError):
    """Raised when agent is in an invalid state."""


class LLMResponseError(AgentError):
    """Raised when LLM response is malformed or missing expected data."""


class Agent:
    def __init__(
        self,
        config: VibeConfig,
        mode: AgentMode = AgentMode.DEFAULT,
        message_observer: Callable[[LLMMessage], None] | None = None,
        max_turns: int | None = None,
        max_price: float | None = None,
        backend: BackendLike | None = None,
        enable_streaming: bool = False,
    ) -> None:
        """Initialize the agent with configuration and mode."""
        self.config = config
        self._mode = mode
        self._max_turns = max_turns
        self._max_price = max_price

        self.tool_manager = ToolManager(config)
        self.skill_manager = SkillManager(config)

        # Select format handler based on config
        if config.effective_tool_format == ToolFormat.XML:
            self.format_handler: APIToolFormatHandler | XMLToolFormatHandler = (
                XMLToolFormatHandler()
            )
        else:
            self.format_handler = APIToolFormatHandler()

        self.backend_factory = lambda: backend or self._select_backend()
        self.backend = self.backend_factory()

        self.message_observer = message_observer
        self._last_observed_message_index: int = 0
        self.middleware_pipeline = MiddlewarePipeline()
        self.enable_streaming = enable_streaming
        self._setup_middleware()

        system_prompt = get_universal_system_prompt(
            self.tool_manager, config, self.skill_manager, include_subagents=False
        )
        self.messages = [LLMMessage(role=Role.system, content=system_prompt)]

        if self.message_observer:
            self.message_observer(self.messages[0])
            self._last_observed_message_index = 1

        self.stats = AgentStats()
        try:
            active_model = config.get_active_model()
            self.stats.input_price_per_million = active_model.input_price
            self.stats.output_price_per_million = active_model.output_price
        except ValueError:
            pass

        self.approval_callback: ApprovalCallback | None = None

        self.session_id = str(uuid4())

        self.interaction_logger = InteractionLogger(
            config.session_logging,
            self.session_id,
            self.auto_approve,
            config.effective_workdir,
        )

    @property
    def mode(self) -> AgentMode:
        return self._mode

    @property
    def auto_approve(self) -> bool:
        return self._mode.auto_approve

    def _select_backend(self) -> BackendLike:
        active_model = self.config.get_active_model()
        provider = self.config.get_provider_for_model(active_model)
        timeout = self.config.api_timeout
        backend_cls = get_backend_for_provider(provider)
        return cast(BackendLike, backend_cls(provider=provider, timeout=timeout))

    def add_message(self, message: LLMMessage) -> None:
        self.messages.append(message)

    def _flush_new_messages(self) -> None:
        if not self.message_observer:
            return

        if self._last_observed_message_index >= len(self.messages):
            return

        for msg in self.messages[self._last_observed_message_index :]:
            self.message_observer(msg)
        self._last_observed_message_index = len(self.messages)

    def _is_xml_mode(self) -> bool:
        return self.format_handler.name == "xml"

    def _has_xml_tool_calls(self, content: str) -> bool:
        if not content.strip():
            return False

        import re

        return bool(
            re.search(r"<tool_call>.*?</tool_call>", content, re.DOTALL | re.IGNORECASE)
        )

    def _build_completion_headers(self) -> dict[str, str]:
        active_model = self.config.get_active_model()
        provider = self.config.get_provider_for_model(active_model)
        return {
            "user-agent": get_user_agent(provider.backend),
            "x-affinity": self.session_id,
        }

    def _update_usage_stats(self, usage: LLMUsage | None) -> None:
        if usage is None:
            return

        self.stats.context_tokens = usage.prompt_tokens + usage.completion_tokens
        self.stats.session_prompt_tokens += usage.prompt_tokens
        self.stats.session_completion_tokens += usage.completion_tokens
        self.stats.last_turn_prompt_tokens = usage.prompt_tokens
        self.stats.last_turn_completion_tokens = usage.completion_tokens

    async def _should_execute_tool(
        self, tool_instance, tool_args, tool_call_id: str
    ) -> ToolDecision:
        tool_name = tool_instance.get_name()
        allowlist_decision = tool_instance.check_allowlist_denylist(tool_args)
        if allowlist_decision is not None:
            permission = allowlist_decision
        else:
            permission = self.tool_manager.get_tool_config(tool_name).permission

        match permission:
            case ToolPermission.ALWAYS:
                return ToolDecision(verdict=ToolExecutionResponse.EXECUTE)
            case ToolPermission.NEVER:
                return ToolDecision(
                    verdict=ToolExecutionResponse.SKIP,
                    feedback=f"Tool '{tool_name}' is permanently disabled.",
                )
            case ToolPermission.ASK:
                if self.auto_approve:
                    return ToolDecision(verdict=ToolExecutionResponse.EXECUTE)

                if self.approval_callback is None:
                    return ToolDecision(
                        verdict=ToolExecutionResponse.SKIP,
                        feedback=f"Tool '{tool_name}' is not permitted without approval.",
                    )

                callback_result = self.approval_callback(
                    tool_name, tool_args, tool_call_id
                )
                if inspect.isawaitable(callback_result):
                    approval, feedback = await callback_result
                else:
                    approval, feedback = callback_result

                match approval:
                    case ApprovalResponse.YES:
                        return ToolDecision(
                            verdict=ToolExecutionResponse.EXECUTE, feedback=feedback
                        )
                    case ApprovalResponse.NO:
                        return ToolDecision(
                            verdict=ToolExecutionResponse.SKIP,
                            feedback=feedback
                            or f"Tool '{tool_name}' was not permitted.",
                        )

        raise AgentStateError(
            f"Unsupported tool permission for {tool_name!r}: {permission!r}"
        )

    def _clean_message_history(self) -> None:
        if not self.messages:
            return

        if self._is_xml_mode():
            import re
            from uuid import uuid4

            tool_call_pattern = re.compile(
                r"<tool_call>.*?</tool_call>", re.DOTALL | re.IGNORECASE
            )
            i = 0
            while i < len(self.messages):
                msg = self.messages[i]
                if msg.role == Role.assistant:
                    content = msg.content or ""
                    if self._has_xml_tool_calls(content):
                        expected_calls = len(tool_call_pattern.findall(content))
                        if expected_calls > 0:
                            actual_responses = 0
                            j = i + 1
                            while j < len(self.messages):
                                result_msg = self.messages[j]
                                result_content = result_msg.content or ""
                                if (
                                    result_msg.role == Role.user
                                    and result_content.strip().startswith(
                                        "<tool_result"
                                    )
                                ):
                                    actual_responses += 1
                                    j += 1
                                else:
                                    break

                            if actual_responses < expected_calls:
                                insertion_point = i + 1 + actual_responses
                                for _call_idx in range(
                                    actual_responses, expected_calls
                                ):
                                    call_id = f"xml_{uuid4().hex[:12]}"
                                    empty_response = LLMMessage(
                                        role=Role.user,
                                        content=(
                                            f'<tool_result name="unknown" call_id="{call_id}">\n'
                                            f"<status>error</status>\n"
                                            f"<error>No response received</error>\n"
                                            f"</tool_result>"
                                        ),
                                    )
                                    self.messages.insert(
                                        insertion_point, empty_response
                                    )
                                    insertion_point += 1

                i += 1
        else:
            i = 0
            while i < len(self.messages):
                msg = self.messages[i]
                if msg.role == Role.assistant and msg.tool_calls:
                    expected_calls = msg.tool_calls
                    actual_responses = 0
                    j = i + 1
                    while j < len(self.messages):
                        result_msg = self.messages[j]
                        if result_msg.role != Role.tool:
                            break

                        if actual_responses >= len(expected_calls):
                            break

                        expected_call = expected_calls[actual_responses]
                        if (
                            result_msg.tool_call_id is not None
                            and expected_call.id is not None
                            and result_msg.tool_call_id != expected_call.id
                        ):
                            break

                        actual_responses += 1
                        j += 1

                    if actual_responses < len(expected_calls):
                        insertion_point = i + 1 + actual_responses
                        for expected_call in expected_calls[actual_responses:]:
                            placeholder = LLMMessage(
                                role=Role.tool,
                                tool_call_id=expected_call.id,
                                name=expected_call.function.name,
                                content=str(
                                    get_user_cancellation_message(
                                        CancellationReason.TOOL_NO_RESPONSE
                                    )
                                ),
                            )
                            self.messages.insert(insertion_point, placeholder)
                            insertion_point += 1

                i += 1

        self._ensure_assistant_after_tools()

    async def _chat(self) -> LLMChunk:
        active_model = self.config.get_active_model()
        tools = self.format_handler.get_available_tools(self.tool_manager, self.config)
        tool_choice = self.format_handler.get_tool_choice()

        async with self.backend as backend:
            result = await backend.complete(
                model=active_model,
                messages=self.messages,
                temperature=0.2,
                tools=tools,
                max_tokens=None,
                tool_choice=tool_choice,
                extra_headers=self._build_completion_headers(),
            )

        self._update_usage_stats(result.usage)
        self.messages.append(result.message)
        return result

    async def _chat_streaming(self) -> AsyncGenerator[LLMChunk, None]:
        active_model = self.config.get_active_model()
        tools = self.format_handler.get_available_tools(self.tool_manager, self.config)
        tool_choice = self.format_handler.get_tool_choice()
        aggregated_chunk: LLMChunk | None = None

        async with self.backend as backend:
            async for chunk in backend.complete_streaming(
                model=active_model,
                messages=self.messages,
                temperature=0.2,
                tools=tools,
                max_tokens=None,
                tool_choice=tool_choice,
                extra_headers=self._build_completion_headers(),
            ):
                aggregated_chunk = (
                    chunk if aggregated_chunk is None else aggregated_chunk + chunk
                )
                yield chunk

        if aggregated_chunk is None:
            aggregated_chunk = LLMChunk(
                message=LLMMessage(role=Role.assistant, content="")
            )

        self._update_usage_stats(aggregated_chunk.usage)
        self.messages.append(aggregated_chunk.message)

    async def act(self, msg: str) -> AsyncGenerator[BaseEvent]:
        self._clean_message_history()
        async for event in self._conversation_loop(msg):
            yield event

    def _get_effective_compact_threshold(self) -> int:
        """Get effective auto-compact threshold, preferring per-model setting."""
        try:
            active_model = self.config.get_active_model()
            if active_model.auto_compact_threshold is not None:
                return active_model.auto_compact_threshold
        except ValueError:
            pass
        return self.config.auto_compact_threshold

    def _setup_middleware(self) -> None:
        """Configure middleware pipeline for this conversation."""
        self.middleware_pipeline.clear()

        if self._max_turns is not None:
            self.middleware_pipeline.add(TurnLimitMiddleware(self._max_turns))

        if self._max_price is not None:
            self.middleware_pipeline.add(PriceLimitMiddleware(self._max_price))

        threshold = self._get_effective_compact_threshold()
        if threshold > 0:
            self.middleware_pipeline.add(AutoCompactMiddleware(threshold))
            if self.config.context_warnings:
                self.middleware_pipeline.add(ContextWarningMiddleware(0.5, threshold))

        self.middleware_pipeline.add(PlanModeMiddleware(lambda: self._mode))

    async def _handle_middleware_result(
        self, result: MiddlewareResult
    ) -> AsyncGenerator[BaseEvent]:
        match result.action:
            case MiddlewareAction.STOP:
                yield AssistantEvent(
                    content=f"<{VIBE_STOP_EVENT_TAG}>{result.reason}</{VIBE_STOP_EVENT_TAG}>",
                    stopped_by_middleware=True,
                )

            case MiddlewareAction.INJECT_MESSAGE:
                if result.message and len(self.messages) > 0:
                    last_msg = self.messages[-1]
                    if last_msg.content:
                        last_msg.content += f"\n\n{result.message}"
                    else:
                        last_msg.content = result.message

            case MiddlewareAction.COMPACT:
                old_tokens = result.metadata.get(
                    "old_tokens", self.stats.context_tokens
                )
                threshold = result.metadata.get(
                    "threshold", self.config.auto_compact_threshold
                )

                yield CompactStartEvent(
                    current_context_tokens=old_tokens, threshold=threshold
                )

                summary = await self.compact()

                yield CompactEndEvent(
                    old_context_tokens=old_tokens,
                    new_context_tokens=self.stats.context_tokens,
                    summary_length=len(summary),
                )

            case MiddlewareAction.CONTINUE:
                pass

    def _get_context(self) -> ConversationContext:
        return ConversationContext(
            messages=self.messages, stats=self.stats, config=self.config
        )

    async def _conversation_loop(self, user_msg: str) -> AsyncGenerator[BaseEvent]:
        self.messages.append(LLMMessage(role=Role.user, content=user_msg))
        self.stats.steps += 1

        try:
            should_break_loop = False
            while not should_break_loop:
                result = await self.middleware_pipeline.run_before_turn(
                    self._get_context()
                )
                async for event in self._handle_middleware_result(result):
                    yield event

                if result.action == MiddlewareAction.STOP:
                    return

                self.stats.steps += 1
                user_cancelled = False
                async for event in self._perform_llm_turn():
                    if is_user_cancellation_event(event):
                        user_cancelled = True
                    yield event

                last_message = self.messages[-1]
                should_break_loop = not self.format_handler.is_tool_response(
                    last_message
                )

                self._flush_new_messages()

                if user_cancelled:
                    return

                after_result = await self.middleware_pipeline.run_after_turn(
                    self._get_context()
                )
                async for event in self._handle_middleware_result(after_result):
                    yield event

                if after_result.action == MiddlewareAction.STOP:
                    return

        finally:
            self._flush_new_messages()
            await self.interaction_logger.save_interaction(
                self.messages, self.stats, self.config, self.tool_manager
            )

    async def _perform_llm_turn(self) -> AsyncGenerator[BaseEvent, None]:
        if self.enable_streaming:
            async for event in self._stream_assistant_events():
                yield event
        else:
            assistant_event = await self._get_assistant_event()
            if assistant_event.content:
                yield assistant_event

        last_message = self.messages[-1]

        parsed = self.format_handler.parse_message(last_message)
        resolved = self.format_handler.resolve_tool_calls(
            parsed, self.tool_manager, self.config
        )

        if not resolved.tool_calls and not resolved.failed_calls:
            return

        async for event in self._handle_tool_calls(resolved):
            yield event

    async def _stream_assistant_events(
        self,
    ) -> AsyncGenerator[AssistantEvent | ReasoningEvent]:
        content_buffer = ""
        reasoning_buffer = ""
        chunks_with_content = 0
        chunks_with_reasoning = 0
        thinking_start_time: float | None = None
        is_thinking = False
        BATCH_SIZE = 5

        async for chunk in self._chat_streaming():
            if chunk.message.reasoning_content:
                if content_buffer:
                    yield AssistantEvent(content=content_buffer)
                    content_buffer = ""
                    chunks_with_content = 0

                # Track when thinking starts
                if thinking_start_time is None:
                    thinking_start_time = time.perf_counter()
                    is_thinking = True

                reasoning_buffer += chunk.message.reasoning_content
                chunks_with_reasoning += 1

                if chunks_with_reasoning >= BATCH_SIZE:
                    yield ReasoningEvent(content=reasoning_buffer)
                    reasoning_buffer = ""
                    chunks_with_reasoning = 0

            if chunk.message.content:
                # If we were thinking and now content starts, emit final duration event
                if is_thinking:
                    thinking_duration = None
                    if thinking_start_time is not None:
                        thinking_duration = time.perf_counter() - thinking_start_time
                    # Emit any remaining reasoning content with duration
                    if reasoning_buffer:
                        yield ReasoningEvent(
                            content=reasoning_buffer, duration=thinking_duration
                        )
                        reasoning_buffer = ""
                        chunks_with_reasoning = 0
                    else:
                        # Just emit duration completion signal (empty content)
                        yield ReasoningEvent(content="", duration=thinking_duration)
                    thinking_start_time = None
                    is_thinking = False

                content_buffer += chunk.message.content
                chunks_with_content += 1

                if chunks_with_content >= BATCH_SIZE:
                    yield AssistantEvent(content=content_buffer)
                    content_buffer = ""
                    chunks_with_content = 0

        # Handle remaining buffers at end of stream
        if reasoning_buffer or is_thinking:
            thinking_duration = None
            if thinking_start_time is not None:
                thinking_duration = time.perf_counter() - thinking_start_time
            yield ReasoningEvent(content=reasoning_buffer, duration=thinking_duration)

        if content_buffer:
            yield AssistantEvent(content=content_buffer)

    async def _get_assistant_event(self) -> AssistantEvent:
        llm_result = await self._chat()
        return AssistantEvent(content=llm_result.message.content or "")

    async def _handle_tool_calls(
        self, resolved: ResolvedMessage
    ) -> AsyncGenerator[ToolCallEvent | ToolResultEvent]:
        for failed in resolved.failed_calls:
            error_msg = f"<{TOOL_ERROR_TAG}>{failed.tool_name}: {failed.error}</{TOOL_ERROR_TAG}>"

            yield ToolResultEvent(
                tool_name=failed.tool_name,
                tool_class=None,
                error=error_msg,
                tool_call_id=failed.call_id,
            )

            self.stats.tool_calls_failed += 1
            self.messages.append(
                self.format_handler.create_failed_tool_response_message(
                    failed, error_msg
                )
            )

        if resolved.tool_calls:
            async for event in self._execute_tools_in_parallel(resolved.tool_calls):
                yield event

    async def _execute_tools_in_parallel(
        self, tool_calls: list
    ) -> AsyncGenerator[ToolCallEvent | ToolResultEvent]:
        """Execute multiple tool calls in parallel using asyncio.gather.

        Tools are executed concurrently when they don't depend on each other,
        significantly improving performance for independent operations.
        """
        tool_call_events: list[ToolCallEvent] = []
        for tool_call in tool_calls:
            tool_call_id = tool_call.call_id
            tool_call_events.append(
                ToolCallEvent(
                    tool_name=tool_call.tool_name,
                    tool_class=tool_call.tool_class,
                    args=tool_call.validated_args,
                    tool_call_id=tool_call_id,
                )
            )

        for event in tool_call_events:
            yield event

        async def _execute_single(tool_call):
            tool_call_id = tool_call.call_id
            try:
                tool_instance = self.tool_manager.get(tool_call.tool_name)
            except Exception as exc:
                return {
                    "tool_call": tool_call,
                    "error": f"Error getting tool '{tool_call.tool_name}': {exc}",
                    "type": "get_error",
                }

            decision = await self._should_execute_tool(
                tool_instance, tool_call.validated_args, tool_call_id
            )

            if decision.verdict == ToolExecutionResponse.SKIP:
                self.stats.tool_calls_rejected += 1
                skip_reason = decision.feedback or str(
                    get_user_cancellation_message(
                        CancellationReason.TOOL_SKIPPED, tool_call.tool_name
                    )
                )
                return {
                    "tool_call": tool_call,
                    "skip_reason": skip_reason,
                    "type": "skip",
                }

            self.stats.tool_calls_agreed += 1

            try:
                start_time = time.perf_counter()
                result_model = await tool_instance.invoke(**tool_call.args_dict)
                duration = time.perf_counter() - start_time

                text = "\n".join(
                    f"{k}: {v}" for k, v in result_model.model_dump().items()
                )

                return {
                    "tool_call": tool_call,
                    "result_model": result_model,
                    "text": text,
                    "duration": duration,
                    "type": "success",
                }

            except asyncio.CancelledError:
                cancel = str(
                    get_user_cancellation_message(CancellationReason.TOOL_INTERRUPTED)
                )
                return {
                    "tool_call": tool_call,
                    "error": cancel,
                    "exception": asyncio.CancelledError(),
                    "type": "cancelled",
                }

            except KeyboardInterrupt:
                cancel = str(
                    get_user_cancellation_message(CancellationReason.TOOL_INTERRUPTED)
                )
                return {
                    "tool_call": tool_call,
                    "error": cancel,
                    "exception": KeyboardInterrupt(),
                    "type": "cancelled",
                }

            except (ToolError, ToolPermissionError) as exc:
                error_msg = f"<{TOOL_ERROR_TAG}>{tool_instance.get_name()} failed: {exc}</{TOOL_ERROR_TAG}>"
                return {
                    "tool_call": tool_call,
                    "error": error_msg,
                    "is_permission": isinstance(exc, ToolPermissionError),
                    "type": "tool_error",
                }

        tasks = [_execute_single(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks)

        for result in results:
            tool_call = result["tool_call"]
            tool_call_id = tool_call.call_id

            match result["type"]:
                case "success":
                    self.messages.append(
                        LLMMessage.model_validate(
                            self.format_handler.create_tool_response_message(
                                tool_call, result["text"]
                            )
                        )
                    )

                    yield ToolResultEvent(
                        tool_name=tool_call.tool_name,
                        tool_class=tool_call.tool_class,
                        result=result["result_model"],
                        duration=result["duration"],
                        tool_call_id=tool_call_id,
                    )

                    self.stats.tool_calls_succeeded += 1

                case "skip":
                    yield ToolResultEvent(
                        tool_name=tool_call.tool_name,
                        tool_class=tool_call.tool_class,
                        skipped=True,
                        skip_reason=result["skip_reason"],
                        tool_call_id=tool_call_id,
                    )

                    self.messages.append(
                        LLMMessage.model_validate(
                            self.format_handler.create_tool_response_message(
                                tool_call, result["skip_reason"]
                            )
                        )
                    )

                case "get_error":
                    yield ToolResultEvent(
                        tool_name=tool_call.tool_name,
                        tool_class=tool_call.tool_class,
                        error=result["error"],
                        tool_call_id=tool_call_id,
                    )
                    self.messages.append(
                        LLMMessage.model_validate(
                            self.format_handler.create_tool_response_message(
                                tool_call, result["error"]
                            )
                        )
                    )

                case "cancelled":
                    yield ToolResultEvent(
                        tool_name=tool_call.tool_name,
                        tool_class=tool_call.tool_class,
                        error=result["error"],
                        tool_call_id=tool_call_id,
                    )
                    self.messages.append(
                        LLMMessage.model_validate(
                            self.format_handler.create_tool_response_message(
                                tool_call, result["error"]
                            )
                        )
                    )
                    raise result["exception"]

                case "tool_error":
                    yield ToolResultEvent(
                        tool_name=tool_call.tool_name,
                        tool_class=tool_call.tool_class,
                        error=result["error"],
                        tool_call_id=tool_call_id,
                    )

                    if result.get("is_permission"):
                        self.stats.tool_calls_agreed -= 1
                        self.stats.tool_calls_rejected += 1
                    else:
                        self.stats.tool_calls_failed += 1
                    self.messages.append(
                        LLMMessage.model_validate(
                            self.format_handler.create_tool_response_message(
                                tool_call, result["error"]
                            )
                        )
                    )

    def _ensure_assistant_after_tools(self) -> None:
        MIN_MESSAGE_SIZE = 2
        if len(self.messages) < MIN_MESSAGE_SIZE:
            return

        last_msg = self.messages[-1]

        # Handle native tool responses
        if last_msg.role is Role.tool:
            empty_assistant_msg = LLMMessage(role=Role.assistant, content="Understood.")
            self.messages.append(empty_assistant_msg)
            return

        # Handle XML tool responses (role=user with <tool_result> content)
        if self._is_xml_mode():
            last_content = last_msg.content or ""
            if last_msg.role == Role.user and last_content.strip().startswith(
                "<tool_result"
            ):
                empty_assistant_msg = LLMMessage(
                    role=Role.assistant, content="Understood."
                )
                self.messages.append(empty_assistant_msg)

    def _reset_session(self) -> None:
        self.session_id = str(uuid4())
        self.interaction_logger.reset_session(self.session_id)

    def set_approval_callback(self, callback: ApprovalCallback) -> None:
        self.approval_callback = callback

    async def clear_history(self) -> None:
        await self.interaction_logger.save_interaction(
            self.messages, self.stats, self.config, self.tool_manager
        )
        self.messages = self.messages[:1]

        self.stats = AgentStats()

        try:
            active_model = self.config.get_active_model()
            self.stats.update_pricing(
                active_model.input_price, active_model.output_price
            )
        except ValueError:
            pass

        self.middleware_pipeline.reset()
        self.tool_manager.reset_all()
        self._reset_session()

    async def compact(self) -> str:
        """Compact the conversation history."""
        try:
            self._clean_message_history()
            await self.interaction_logger.save_interaction(
                self.messages, self.stats, self.config, self.tool_manager
            )

            last_user_message = None
            for msg in reversed(self.messages):
                if msg.role == Role.user:
                    last_user_message = msg.content
                    break

            summary_request = UtilityPrompt.COMPACT.read()
            self.messages.append(LLMMessage(role=Role.user, content=summary_request))
            self.stats.steps += 1

            summary_result = await self._chat()
            if summary_result.usage is None:
                raise LLMResponseError(
                    "Usage data missing in compaction summary response"
                )
            summary_content = summary_result.message.content or ""

            if last_user_message:
                summary_content += (
                    f"\n\nLast request from user was: {last_user_message}"
                )

            system_message = self.messages[0]
            summary_message = LLMMessage(role=Role.user, content=summary_content)
            self.messages = [system_message, summary_message]

            active_model = self.config.get_active_model()
            provider = self.config.get_provider_for_model(active_model)

            async with self.backend as backend:
                actual_context_tokens = await backend.count_tokens(
                    model=active_model,
                    messages=self.messages,
                    tools=self.format_handler.get_available_tools(
                        self.tool_manager, self.config
                    ),
                    extra_headers={"user-agent": get_user_agent(provider.backend)},
                )

            self.stats.context_tokens = actual_context_tokens

            self._reset_session()
            await self.interaction_logger.save_interaction(
                self.messages, self.stats, self.config, self.tool_manager
            )

            self.middleware_pipeline.reset(reset_reason=ResetReason.COMPACT)

            return summary_content or ""

        except Exception:
            await self.interaction_logger.save_interaction(
                self.messages, self.stats, self.config, self.tool_manager
            )
            raise

    async def switch_mode(self, new_mode: AgentMode) -> None:
        if new_mode == self._mode:
            return
        new_config = VibeConfig.load(
            workdir=self.config.workdir, **new_mode.config_overrides
        )

        await self.reload_with_initial_messages(config=new_config)
        self._mode = new_mode

    async def reload_with_initial_messages(
        self,
        config: VibeConfig | None = None,
        max_turns: int | None = None,
        max_price: float | None = None,
    ) -> None:
        await self.interaction_logger.save_interaction(
            self.messages, self.stats, self.config, self.tool_manager
        )

        preserved_messages = self.messages[1:] if len(self.messages) > 1 else []

        if config is not None:
            self.config = config
            self.backend = self.backend_factory()

        if max_turns is not None:
            self._max_turns = max_turns
        if max_price is not None:
            self._max_price = max_price

        self.tool_manager = ToolManager(self.config)
        self.skill_manager = SkillManager(self.config)

        new_system_prompt = get_universal_system_prompt(
            self.tool_manager, self.config, self.skill_manager, include_subagents=False
        )
        self.messages = [LLMMessage(role=Role.system, content=new_system_prompt)]

        if preserved_messages:
            self.messages.extend(preserved_messages)

        if len(self.messages) == 1:
            self.stats.reset_context_state()

        try:
            active_model = self.config.get_active_model()
            self.stats.update_pricing(
                active_model.input_price, active_model.output_price
            )
        except ValueError:
            pass

        self._last_observed_message_index = 0

        self._setup_middleware()

        if self.message_observer:
            for msg in self.messages:
                self.message_observer(msg)
            self._last_observed_message_index = len(self.messages)

        self.tool_manager.reset_all()

        await self.interaction_logger.save_interaction(
            self.messages, self.stats, self.config, self.tool_manager
        )
