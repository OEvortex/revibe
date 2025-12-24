from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Static

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


class ProviderSelector(Container):
    """Widget for selecting a provider."""

    can_focus = True
    can_focus_children = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("space", "select", "Select", show=False),
    ]

    class ProviderSelected(Message):
        def __init__(self, provider_name: str) -> None:
            super().__init__()
            self.provider_name = provider_name

    class SelectorClosed(Message):
        pass

    def __init__(self, config: VibeConfig) -> None:
        super().__init__(id="provider-selector")
        self.config = config
        self.selected_index = 0
        # Merge DEFAULT_PROVIDERS with the loaded configuration so the selector
        # shows all built-in providers even if a user's config omits some entries.
        from revibe.core.config import DEFAULT_PROVIDERS, ProviderConfig

        providers_map: dict[str, ProviderConfig] = {}
        for p in DEFAULT_PROVIDERS:
            providers_map[p.name] = p
        for p in config.providers:
            providers_map[p.name] = p

        self.providers = list(providers_map.values())
        self.title_widget: Static | None = None
        self.option_widgets: list[Static] = []
        self.help_widget: Static | None = None

        # Find current provider index
        try:
            active_model = config.get_active_model()
            for i, p in enumerate(self.providers):
                if p.name == active_model.provider:
                    self.selected_index = i
                    break
        except ValueError:
            pass

    def compose(self) -> ComposeResult:
        with Vertical(id="provider-content"):
            self.title_widget = Static("Select Provider", classes="settings-title")
            yield self.title_widget
            yield Static("")

            for _ in self.providers:
                widget = Static("", classes="settings-option")
                self.option_widgets.append(widget)
                yield widget

            yield Static("")
            self.help_widget = Static(
                "↑↓ navigate  Enter select  ESC cancel", classes="settings-help"
            )
            yield self.help_widget

    def on_mount(self) -> None:
        self._update_display()
        self.focus()

    def _update_display(self) -> None:
        for i, (provider, widget) in enumerate(
            zip(self.providers, self.option_widgets, strict=True)
        ):
            is_selected = i == self.selected_index
            cursor = "› " if is_selected else "  "
            text = f"{cursor}{provider.name}"

            widget.update(text)
            widget.remove_class("settings-value-cycle-selected")
            widget.remove_class("settings-value-cycle-unselected")

            if is_selected:
                widget.add_class("settings-value-cycle-selected")
            else:
                widget.add_class("settings-value-cycle-unselected")

    def action_move_up(self) -> None:
        self.selected_index = (self.selected_index - 1) % len(self.providers)
        self._update_display()

    def action_move_down(self) -> None:
        self.selected_index = (self.selected_index + 1) % len(self.providers)
        self._update_display()

    def action_select(self) -> None:
        provider = self.providers[self.selected_index]
        self.post_message(self.ProviderSelected(provider_name=provider.name))

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())

    def on_blur(self, event: events.Blur) -> None:
        self.call_after_refresh(self.focus)

