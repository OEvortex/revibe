from __future__ import annotations

from typing import ClassVar

from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

from revibe.cli.textual_ui.app import VibeApp
from revibe.cli.textual_ui.widgets.chat_input import ChatTextArea
from revibe.core.agent import Agent
from revibe.core.config import SessionLoggingConfig, VibeConfig
from tests.stubs.fake_backend import FakeBackend


def default_config() -> VibeConfig:
    """Default configuration for snapshot testing.
    Remove as much interference as possible from the snapshot comparison, in order to get a clean pixel-to-pixel comparison.
    - Injects a fake backend to prevent (or stub) LLM calls.
    - Disables the welcome banner animation.
    - Forces a value for the displayed workdir
    - Hides the chat input cursor (as the blinking animation is not deterministic).
    """
    return VibeConfig(
        session_logging=SessionLoggingConfig(enabled=False),
        textual_theme="gruvbox",
        disable_welcome_banner_animation=True,
        displayed_workdir="/test/workdir",
        enable_update_checks=False,
    )


class BaseSnapshotTestApp(VibeApp):
    CSS_PATH: ClassVar[list[str]] = [
        "../../revibe/cli/textual_ui/tcss/app/base.tcss",
        "../../revibe/cli/textual_ui/tcss/app/messages.tcss",
        "../../revibe/cli/textual_ui/tcss/app/bash.tcss",
        "../../revibe/cli/textual_ui/tcss/app/status.tcss",
        "../../revibe/cli/textual_ui/tcss/app/tool_results.tcss",
        "../../revibe/cli/textual_ui/tcss/app/todo_loading.tcss",
        "../../revibe/cli/textual_ui/tcss/app/config.tcss",
        "../../revibe/cli/textual_ui/tcss/app/bottom_bar.tcss",
        "../../revibe/cli/textual_ui/tcss/app/approval.tcss",
        "../../revibe/cli/textual_ui/tcss/app/mode_indicator.tcss",
        "../../revibe/cli/textual_ui/tcss/welcome_banner/layout.tcss",
        "../../revibe/cli/textual_ui/tcss/welcome_banner/theme.tcss",
        "../../revibe/cli/textual_ui/tcss/diff/base.tcss",
        "../../revibe/cli/textual_ui/tcss/diff/header.tcss",
        "../../revibe/cli/textual_ui/tcss/diff/hunk.tcss",
        "../../revibe/cli/textual_ui/tcss/diff/lines.tcss",
        "../../revibe/cli/textual_ui/tcss/diff/metadata.tcss",
        "../../revibe/cli/textual_ui/tcss/diff/summary.tcss",
        "../../revibe/cli/textual_ui/tcss/thought/container.tcss",
        "../../revibe/cli/textual_ui/tcss/thought/header.tcss",
        "../../revibe/cli/textual_ui/tcss/thought/content.tcss",
        "../../revibe/cli/textual_ui/tcss/thought/collapsed.tcss",
        "../../revibe/cli/textual_ui/tcss/thought/legacy.tcss",
        "../../revibe/cli/textual_ui/tcss/input/container.tcss",
        "../../revibe/cli/textual_ui/tcss/input/completion.tcss",
        "../../revibe/cli/textual_ui/tcss/input/prompt.tcss",
        "../../revibe/cli/textual_ui/tcss/input/input_area.tcss",
        "../../revibe/cli/textual_ui/tcss/input/hints.tcss",
        "../../revibe/cli/textual_ui/tcss/input/focus.tcss",
        "../../revibe/cli/textual_ui/tcss/selector/container.tcss",
        "../../revibe/cli/textual_ui/tcss/selector/title.tcss",
        "../../revibe/cli/textual_ui/tcss/selector/filter.tcss",
        "../../revibe/cli/textual_ui/tcss/selector/list.tcss",
        "../../revibe/cli/textual_ui/tcss/selector/options.tcss",
    ]

    def __init__(self, config: VibeConfig | None = None, **kwargs):
        config = config or default_config()

        super().__init__(config=config, **kwargs)

        self.agent = Agent(
            config,
            mode=self._current_agent_mode,
            enable_streaming=self.enable_streaming,
            backend=FakeBackend(),
        )

    async def on_mount(self) -> None:
        await super().on_mount()
        self._hide_chat_input_cursor()

    def _hide_chat_input_cursor(self) -> None:
        text_area = self.query_one(ChatTextArea)
        hidden_cursor_theme = TextAreaTheme(name="hidden_cursor", cursor_style=Style())
        text_area.register_theme(hidden_cursor_theme)
        text_area.theme = "hidden_cursor"
