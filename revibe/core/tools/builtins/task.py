from __future__ import annotations

from typing import ClassVar, final

from pydantic import BaseModel, Field

from revibe.core.subagents import execute_subagent
from revibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    ToolError,
    ToolPermission,
)
from revibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from revibe.core.types import ToolCallEvent, ToolResultEvent


class TaskArgs(BaseModel):
    agent: str = Field(
        default="explore",
        description=(
            "Optional. Subagent name to delegate to. Defaults to 'explore'. "
            "Use a custom subagent name only when the TOML profile is marked with agent_type = 'subagent'."
        ),
    )
    prompt: str = Field(
        description=(
            "REQUIRED. The task to delegate to the subagent. Provide a complete, self-contained prompt."
        )
    )


class TaskResult(BaseModel):
    agent: str
    output: str


class TaskConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS
    default_agent: str = "explore"
    max_turns: int = 8


class Task(
    BaseTool[TaskArgs, TaskResult, TaskConfig, BaseToolState],
    ToolUIData[TaskArgs, TaskResult],
):
    description: ClassVar[str] = (
        "Delegate a focused task to a subagent. Use for research, codebase exploration, or other bounded work that benefits from a smaller specialized agent. "
        "Built-in subagent 'explore' is read-only and optimized for analysis. Custom subagents can be added with agent_type = 'subagent' in ~/.revibe/agents/*.toml."
    )

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        if not isinstance(event.args, TaskArgs):
            return ToolCallDisplay(summary="Task")

        return ToolCallDisplay(summary=f"Task ({event.args.agent or 'explore'})")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if isinstance(event.result, TaskResult):
            return ToolResultDisplay(
                success=True, message=f"Subagent {event.result.agent} completed"
            )

        if event.error:
            return ToolResultDisplay(success=False, message=event.error)

        return ToolResultDisplay(success=True, message="Completed")

    @classmethod
    def get_status_text(cls) -> str:
        return "Delegating task"

    @final
    async def run(self, args: TaskArgs) -> TaskResult:
        if not args.prompt.strip():
            raise ToolError("Task prompt cannot be empty")

        agent_name = (
            args.agent or self.config.default_agent
        ).strip() or self.config.default_agent
        output = await execute_subagent(
            agent_name, args.prompt, max_turns=self.config.max_turns
        )
        return TaskResult(agent=agent_name, output=output)
