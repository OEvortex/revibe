from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from revibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    ToolPendingError,
    ToolPermission,
)
from revibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from revibe.core.types import ToolCallEvent, ToolResultEvent


class QuestionOption(BaseModel):
    label: str = Field(description="Short display text (1-5 words, concise)")
    description: str = Field(description="Explanation of choice")


class QuestionItem(BaseModel):
    question: str = Field(description="Complete question")
    header: str = Field(description="Very short label (max 30 chars)", max_length=30)
    options: list[QuestionOption] = Field(
        description="Available choices", min_length=2, max_length=4
    )
    multiple: bool = Field(
        default=False, description="Allow selecting multiple options"
    )


class AskUserQuestionArgs(BaseModel):
    questions: list[QuestionItem] = Field(
        description="Questions to ask", min_length=1, max_length=4
    )


class AskUserQuestionResult(BaseModel):
    answers: list[dict[str, list[str]]]


class AskUserQuestionConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS


class AskUserQuestionState(BaseToolState):
    pending_questions: list[QuestionItem] | None = None
    resolved_answers: list[dict[str, list[str]]] | None = None


class AskUserQuestion(
    BaseTool[
        AskUserQuestionArgs,
        AskUserQuestionResult,
        AskUserQuestionConfig,
        AskUserQuestionState,
    ],
    ToolUIData[AskUserQuestionArgs, AskUserQuestionResult],
):
    description: ClassVar[str] = (
        "Ask the user one or more questions via a multi-tab UI. "
        "Use when you need clarification on requirements, technical decisions, or preferences. "
        "Supports 1-4 questions per call, each with 2-4 options. "
        "Each question has: question (full text), header (short label, max 30 chars), "
        "options (list of {label, description}), multiple (bool, default false). "
        "An 'Other' option for free-text input is automatically added."
    )

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        if not isinstance(event.args, AskUserQuestionArgs):
            return ToolCallDisplay(summary="Asking user question")
        count = len(event.args.questions)
        label = "question" if count == 1 else "questions"
        return ToolCallDisplay(summary=f"Asking {count} {label}")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if isinstance(event.result, AskUserQuestionResult):
            count = len(event.result.answers)
            label = "question" if count == 1 else "questions"
            return ToolResultDisplay(
                success=True, message=f"User answered {count} {label}"
            )
        if event.error:
            return ToolResultDisplay(success=False, message=event.error)
        return ToolResultDisplay(success=True, message="User responded")

    @classmethod
    def get_status_text(cls) -> str:
        return "Waiting for user response"

    async def run(self, args: AskUserQuestionArgs) -> AskUserQuestionResult:
        self.state.pending_questions = args.questions
        self.state.resolved_answers = None
        raise ToolPendingError(
            "USER_QUESTION_PENDINGING: The agent should pause and wait for the UI to resolve this question. "
            "The UI will re-invoke this tool with the user's answers."
        )
