from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


class ProviderSelector(Container):
    """Widget for selecting a provider using OptionList for performance."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Cancel", show=False)
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
        # Merge DEFAULT_PROVIDERS with the loaded configuration so the selector
        # shows all built-in providers even if a user's config omits some entries.
        from revibe.core.config import DEFAULT_PROVIDERS, ProviderConfigUnion

        providers_map: dict[str, ProviderConfigUnion] = {}
        for p in DEFAULT_PROVIDERS:
            providers_map[p.name] = p
        for p in config.providers:
            providers_map[p.name] = p

        self.providers = list(providers_map.values())

    def compose(self) -> ComposeResult:
        with Vertical(id="provider-content"):
            yield Static("Select Provider", classes="settings-title")
            yield OptionList(id="provider-selector-list")
            yield Static(
                "↑↓ navigate  Enter select  ESC cancel", classes="settings-help"
            )

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#provider-selector-list").focus()

    def on_key(self, event: events.Key) -> None:
        option_list = self.query_one("#provider-selector-list", OptionList)

        # If OptionList has focus, it handles up/down/enter itself.
        # We only need to handle ESC to close the selector.
        if option_list.has_focus:
            if event.key == "escape":
                self.action_close()
                event.stop()
                event.prevent_default()
            return

        # If we are here, focus is likely elsewhere in the widget (e.g. container).
        # Proxy navigation keys to the OptionList.
        if event.key in {"up", "down", "pageup", "pagedown"}:
            if event.key == "up":
                option_list.action_cursor_up()
            elif event.key == "down":
                option_list.action_cursor_down()
            elif event.key == "pageup":
                option_list.action_page_up()
            elif event.key == "pagedown":
                option_list.action_page_down()
            event.stop()
            event.prevent_default()
        elif event.key == "enter":
            if (
                option_list.highlighted is not None
                and 0 <= option_list.highlighted < len(self.providers)
            ):
                provider = self.providers[option_list.highlighted]
                self.post_message(self.ProviderSelected(provider_name=provider.name))
                event.stop()
                event.prevent_default()
        elif event.key == "escape":
            self.action_close()
            event.stop()
            event.prevent_default()

    def _update_list(self) -> None:
        option_list = self.query_one("#provider-selector-list", OptionList)
        option_list.clear_options()

        for provider in self.providers:
            option_list.add_option(Option(provider.name))

        # Highlight active provider
        try:
            active_model = self.config.get_active_model()
            for i, p in enumerate(self.providers):
                if p.name == active_model.provider:
                    option_list.highlighted = i
                    break
        except ValueError:
            pass

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        if 0 <= event.option_index < len(self.providers):
            provider = self.providers[event.option_index]
            self.post_message(self.ProviderSelected(provider_name=provider.name))

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())
