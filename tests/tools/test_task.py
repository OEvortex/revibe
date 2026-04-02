from __future__ import annotations

import pytest

from revibe.core.tools.builtins.task import Task, TaskArgs, TaskConfig, TaskResult
from revibe.core.tools.base import BaseToolState


@pytest.mark.asyncio
async def test_task_tool_delegates_to_execute_subagent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = TaskConfig()
    task = Task(config, BaseToolState())

    async def fake_execute_subagent(
        agent: str, prompt: str, *, max_turns: int = 8
    ) -> str:
        assert agent == "explore"
        assert prompt == "Summarize the repo"
        assert max_turns == 8
        return "subagent output"

    monkeypatch.setattr(
        "revibe.core.tools.builtins.task.execute_subagent", fake_execute_subagent
    )

    result = await task.run(TaskArgs(agent="explore", prompt="Summarize the repo"))

    assert isinstance(result, TaskResult)
    assert result.agent == "explore"
    assert result.output == "subagent output"
