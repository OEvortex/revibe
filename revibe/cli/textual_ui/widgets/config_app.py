from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, TypedDict, cast

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.theme import BUILTIN_THEMES
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from revibe.cli.textual_ui.terminal_theme import TERMINAL_THEME_NAME

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig

_ALL_THEMES = [TERMINAL_THEME_NAME] + sorted(
    k for k in BUILTIN_THEMES if k != "textual-ansi"
)


class SettingDefinition(TypedDict):
    key: str
    label: str
    type: str
    options: list[str]
    value: str


class ConfigApp(Container):
    """Configuration widget using OptionList for a better UI."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Exit", show=False),
    ]

    class SettingChanged(Message):
        def __init__(self, key: str, value: str) -> None:
            super().__init__()
            self.key = key
            self.value = value

    class ConfigClosed(Message):
        def __init__(self, changes: dict[str, str]) -> None:
            super().__init__()
            self.changes = changes

    def __init__(self, config: VibeConfig, *, has_terminal_theme: bool = False) -> None:
        super().__init__(id="config-app")
        self.config = config
        self.changes: dict[str, str] = {}

        themes = (
            _ALL_THEMES
            if has_terminal_theme
            else [t for t in _ALL_THEMES if t != TERMINAL_THEME_NAME]
        )

        self.settings: list[SettingDefinition] = [
            {
                "key": "active_model",
                "label": "Model",
                "type": "cycle",
                "options": [m.alias for m in self.config.models],
                "value": self.config.active_model,
            },
            {
                "key": "textual_theme",
                "label": "Theme",
                "type": "cycle",
                "options": themes,
                "value": self.config.textual_theme,
            },
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="config-content"):
            yield Static("Settings", classes="settings-title")
            yield OptionList(id="config-option-list")
            yield Static(
                "↑↓ navigate  Enter/Space cycle  ESC exit", classes="settings-help"
            )

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#config-option-list").focus()

    def _update_list(self) -> None:
        option_list = self.query_one("#config-option-list", OptionList)
        option_list.clear_options()

        for setting in self.settings:
            value = self.changes.get(setting["key"], setting["value"])
            option_list.add_option(Option(f"{setting['label']}: {value}"))

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._cycle_setting(event.option_index)

    def _cycle_setting(self, index: int) -> None:
        if 0 <= index < len(self.settings):
            setting = self.settings[index]
            key: str = setting["key"]
            current: str = self.changes.get(key, setting["value"])

            options: list[str] = setting["options"]
            try:
                current_idx = options.index(current)
                next_idx = (current_idx + 1) % len(options)
                new_value: str = options[next_idx]
            except (ValueError, IndexError):
                new_value: str = options[0] if options else current

            self.changes[key] = new_value
            self.post_message(self.SettingChanged(key=key, value=new_value))

            # Update the option text in the list
            option_list = cast("Any", self.query_one("#config-option-list"))
            option_list.replace_option_at_index(index, Option(f"{setting['label']}: {new_value}"))
            option_list.highlighted = index

    def action_close(self) -> None:
        self.post_message(self.ConfigClosed(changes=self.changes.copy()))
