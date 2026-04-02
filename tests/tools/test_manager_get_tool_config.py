from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from revibe.core.config import SessionLoggingConfig, VibeConfig
from revibe.core.tools.base import BaseToolConfig, ToolPermission
from revibe.core.tools.builtins.bash import BashToolConfig
from revibe.core.tools.manager import ToolManager


@pytest.fixture
def config() -> VibeConfig:
    return VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
    )


@pytest.fixture
def tool_manager(config: VibeConfig) -> ToolManager:
    return ToolManager(config)


def test_returns_default_config_when_no_overrides(tool_manager: ToolManager) -> None:
    config = cast(BashToolConfig, tool_manager.get_tool_config("bash"))

    assert (
        type(config).__name__ == "BashToolConfig"
    )  # due to vibe's discover system isinstance would fail
    assert config.default_timeout == 30
    assert config.max_output_bytes == 16000
    assert config.permission == ToolPermission.ASK


def test_merges_user_overrides_with_defaults() -> None:
    vibe_config = VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
        tools={"bash": BaseToolConfig(permission=ToolPermission.ALWAYS)},
    )
    manager = ToolManager(vibe_config)

    config = cast(BashToolConfig, manager.get_tool_config("bash"))

    assert (
        type(config).__name__ == "BashToolConfig"
    )  # due to vibe's discover system isinstance would fail
    assert config.permission == ToolPermission.ALWAYS
    assert config.default_timeout == 30


def test_preserves_tool_specific_fields_from_overrides() -> None:
    vibe_config = VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
        tools={"bash": BaseToolConfig(permission=ToolPermission.ASK)},
    )
    vibe_config.tools["bash"].__pydantic_extra__ = {"default_timeout": 600}
    manager = ToolManager(vibe_config)

    config = cast(BashToolConfig, manager.get_tool_config("bash"))

    assert type(config).__name__ == "BashToolConfig"
    assert config.default_timeout == 600


def test_falls_back_to_base_config_for_unknown_tool(
    tool_manager: ToolManager,
) -> None:
    config = tool_manager.get_tool_config("nonexistent_tool")

    assert type(config) is BaseToolConfig
    assert config.permission == ToolPermission.ASK


def test_applies_workdir_from_vibe_config(tmp_path: Path) -> None:
    vibe_config = VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
        workdir=tmp_path,
    )
    manager = ToolManager(vibe_config)

    config = cast(BashToolConfig, manager.get_tool_config("bash"))

    assert config.workdir == tmp_path
    assert config.effective_workdir == tmp_path
