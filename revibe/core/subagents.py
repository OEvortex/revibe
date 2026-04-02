from __future__ import annotations

from enum import StrEnum, auto
import html
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


class AgentType(StrEnum):
    AGENT = auto()
    SUBAGENT = auto()


class SubagentProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str = ""
    agent_type: AgentType = AgentType.AGENT
    path: Path | None = Field(default=None, exclude=True)
    builtin: bool = False


BUILTIN_SUBAGENTS: tuple[SubagentProfile, ...] = (
    SubagentProfile(
        name="explore",
        description="Read-only exploration and analysis for codebase discovery.",
        agent_type=AgentType.SUBAGENT,
        builtin=True,
    ),
)


def _load_toml_file(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_custom_subagent(path: Path) -> SubagentProfile | None:
    try:
        raw = _load_toml_file(path)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return None

    profile = SubagentProfile.model_validate({
        **raw,
        "name": raw.get("name") or path.stem,
        "path": path,
    })
    if profile.agent_type is not AgentType.SUBAGENT:
        return None
    return profile


def discover_subagents(agent_dir: Path) -> list[SubagentProfile]:
    profiles: dict[str, SubagentProfile] = {
        profile.name: profile for profile in BUILTIN_SUBAGENTS
    }

    if agent_dir.is_dir():
        for path in sorted(agent_dir.glob("*.toml")):
            if (profile := _load_custom_subagent(path)) is not None:
                profiles[profile.name] = profile

    return sorted(profiles.values(), key=lambda profile: profile.name.lower())


def get_available_subagents() -> list[SubagentProfile]:
    from revibe.core.paths.config_paths import AGENT_DIR

    return discover_subagents(AGENT_DIR.path)


def get_available_subagents_section() -> str:
    subagents = get_available_subagents()
    if not subagents:
        return ""

    lines = [
        "# Available Subagents",
        "",
        "You can delegate focused work to these subagents with the `task` tool.",
        "Use the smallest subagent that can solve the request.",
        "",
        "<available_subagents>",
    ]

    for profile in subagents:
        lines.append("  <subagent>")
        lines.append(f"    <name>{html.escape(profile.name)}</name>")
        lines.append(
            f"    <description>{html.escape(profile.description or 'No description provided.')}</description>"
        )
        lines.append(
            f"    <agent_type>{html.escape(str(profile.agent_type))}</agent_type>"
        )
        if profile.path is not None:
            lines.append(f"    <path>{html.escape(str(profile.path))}</path>")
        lines.append(f"    <builtin>{str(profile.builtin).lower()}</builtin>")
        lines.append("  </subagent>")

    lines.append("</available_subagents>")
    return "\n".join(lines)


def build_subagent_config(config: VibeConfig, agent_name: str) -> VibeConfig:
    match agent_name.strip().lower():
        case "explore":
            from revibe.core.modes import AgentMode
            from revibe.core.config import VibeConfig as _VibeConfig

            subagent_config = _VibeConfig.model_validate({
                **config.model_dump(mode="python"),
                **AgentMode.PLAN.config_overrides,
                "agent_type": AgentType.SUBAGENT,
            })
        case _:
            subagent_config = VibeConfig.load(agent=agent_name)

            if subagent_config.agent_type is not AgentType.SUBAGENT:
                raise ValueError(
                    f"Agent '{agent_name}' is not marked as a subagent. "
                    'Set agent_type = "subagent" in the agent TOML file.'
                )

    return subagent_config


async def execute_subagent(
    agent_name: str,
    prompt: str,
    *,
    max_turns: int = 8,
    base_config: VibeConfig | None = None,
) -> str:
    from revibe.core.agent import Agent
    from revibe.core.types import AssistantEvent

    from revibe.core.config import VibeConfig as _VibeConfig

    config = base_config or _VibeConfig()
    subagent_config = build_subagent_config(config, agent_name)
    subagent = Agent(subagent_config, max_turns=max_turns)

    responses: list[str] = []
    async for event in subagent.act(prompt):
        if isinstance(event, AssistantEvent) and event.content:
            responses.append(event.content)

    return "\n".join(responses).strip()
