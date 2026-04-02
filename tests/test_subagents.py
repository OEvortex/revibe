from __future__ import annotations

from pathlib import Path

import pytest
import tomli_w

from revibe.core.config import SessionLoggingConfig, VibeConfig
from revibe.core.paths.config_paths import AGENT_DIR
from revibe.core.subagents import AgentType, build_subagent_config, discover_subagents
from revibe.core.system_prompt import get_universal_system_prompt
from revibe.core.tools.manager import ToolManager


def test_discover_subagents_includes_builtin_and_custom_subagent(
    config_dir: Path,
) -> None:
    agent_dir = AGENT_DIR.path
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "analysis.toml").write_text(
        tomli_w.dumps({
            "agent_type": "subagent",
            "description": "Focused codebase analysis",
            "system_prompt_id": "tests",
            "include_project_context": False,
        }),
        encoding="utf-8",
    )
    (agent_dir / "main.toml").write_text(
        tomli_w.dumps({
            "agent_type": "agent",
            "description": "Main profile should not be exposed",
            "system_prompt_id": "tests",
            "include_project_context": False,
        }),
        encoding="utf-8",
    )

    subagents = discover_subagents(agent_dir)
    names = {profile.name for profile in subagents}

    assert "explore" in names
    assert "analysis" in names
    assert "main" not in names


def test_system_prompt_lists_available_subagents(config_dir: Path) -> None:
    agent_dir = AGENT_DIR.path
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "analysis.toml").write_text(
        tomli_w.dumps({
            "agent_type": "subagent",
            "description": "Focused codebase analysis",
            "system_prompt_id": "tests",
            "include_project_context": False,
        }),
        encoding="utf-8",
    )

    config = VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
        include_prompt_detail=False,
    )
    tool_manager = ToolManager(config)

    prompt = get_universal_system_prompt(tool_manager, config)

    assert "# Available Subagents" in prompt
    assert "explore" in prompt
    assert "analysis" in prompt
    assert "Focused codebase analysis" in prompt


def test_build_subagent_config_marks_builtin_explore_as_subagent() -> None:
    config = VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        system_prompt_id="tests",
        include_project_context=False,
        include_prompt_detail=False,
    )

    subagent_config = build_subagent_config(config, "explore")

    assert subagent_config.agent_type is AgentType.SUBAGENT
    assert subagent_config.enabled_tools == ["grep", "read_file", "todo"]
