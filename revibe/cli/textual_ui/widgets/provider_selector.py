from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from revibe.setup.onboarding.provider_info import PROVIDER_DESCRIPTIONS

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion, VibeConfig


class ProviderSelector(Container):
    """Modern widget for selecting a provider with search, status badges, and details."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Cancel", show=False),
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
        # Merge DEFAULT_PROVIDERS with the loaded configuration
        from revibe.core.config import DEFAULT_PROVIDERS

        providers_map: dict[str, ProviderConfigUnion] = {}
        for p in DEFAULT_PROVIDERS:
            providers_map[p.name] = p
        for p in config.providers:
            providers_map[p.name] = p

        self.providers = list(providers_map.values())
        self._filtered_providers: list[ProviderConfigUnion] = list(self.providers)

    def compose(self) -> ComposeResult:
        with Vertical(id="provider-content"):
            yield Static("⚡ Select Provider", classes="settings-title")
            yield Input(placeholder="Search providers...", id="provider-selector-filter")
            yield OptionList(id="provider-selector-list")
            with Horizontal(classes="provider-detail-row"):
                yield Static("", id="provider-detail", classes="provider-detail")
            yield Static(
                "↑↓ navigate  Enter select  / search  ESC cancel",
                classes="settings-help",
            )

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#provider-selector-filter", Input).focus()

    @on(Input.Changed, "#provider-selector-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._update_list(event.value)

    def _get_auth_status(self, provider: ProviderConfigUnion) -> tuple[str, str]:
        """Return (status_emoji, status_text) for provider auth."""
        env_var = getattr(provider, "api_key_env_var", "")
        if not env_var:
            return ("✓", "ready")
        if os.getenv(env_var):
            return ("✓", "ready")
        return ("○", "needs key")

    def _format_provider_option(self, provider: ProviderConfigUnion, is_active: bool) -> str:
        """Format a provider option with status badge."""
        emoji, status = self._get_auth_status(provider)
        active_marker = "▸ " if is_active else "  "
        status_badge = f"[{status}]"
        return f"{active_marker}{emoji} {provider.name:<14} {status_badge}"

    def _update_list(self, filter_text: str = "") -> None:
        option_list = self.query_one("#provider-selector-list", OptionList)
        option_list.clear_options()

        filter_text = filter_text.lower()

        # Filter providers by name or description
        self._filtered_providers = [
            p
            for p in self.providers
            if filter_text in p.name.lower()
            or filter_text in PROVIDER_DESCRIPTIONS.get(p.name, "").lower()
        ]

        # Get active provider for highlighting
        active_provider: str | None = None
        try:
            active_model = self.config.get_active_model()
            active_provider = active_model.provider
        except ValueError:
            pass

        if not self._filtered_providers:
            option_list.add_option(Option("  No providers found", disabled=True))
        else:
            for provider in self._filtered_providers:
                is_active = provider.name == active_provider
                label = self._format_provider_option(provider, is_active)
                option_list.add_option(Option(label))

            # Highlight active provider if visible
            for i, p in enumerate(self._filtered_providers):
                if p.name == active_provider:
                    option_list.highlighted = i
                    break
            else:
                option_list.highlighted = 0

        # Update detail panel for first/highlighted item
        self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        """Update the detail panel with info about the highlighted provider."""
        option_list = self.query_one("#provider-selector-list", OptionList)
        detail_widget = self.query_one("#provider-detail", Static)

        if (
            option_list.highlighted is not None
            and 0 <= option_list.highlighted < len(self._filtered_providers)
        ):
            provider = self._filtered_providers[option_list.highlighted]
            desc = PROVIDER_DESCRIPTIONS.get(provider.name, provider.api_base)
            env_var = getattr(provider, "api_key_env_var", "")
            auth_info = f"  •  {env_var}" if env_var else ""
            detail_widget.update(f"{desc}{auth_info}")
        else:
            detail_widget.update("")

    @on(OptionList.OptionHighlighted)
    def on_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self._update_detail_panel()

    def on_key(self, event: events.Key) -> None:
        option_list = self.query_one("#provider-selector-list", OptionList)
        search_input = self.query_one("#provider-selector-filter", Input)

        # Handle escape globally
        if event.key == "escape":
            self.action_close()
            event.stop()
            event.prevent_default()
            return

        # If OptionList has focus, it handles navigation. Handle enter manually.
        if option_list.has_focus:
            if event.key == "enter":
                self._select_highlighted()
                event.stop()
                event.prevent_default()
            elif event.key == "slash":
                search_input.focus()
                event.stop()
                event.prevent_default()
            return

        # Search input is focused - proxy navigation to OptionList
        match event.key:
            case "up":
                option_list.action_cursor_up()
                self._update_detail_panel()
                event.stop()
                event.prevent_default()
            case "down":
                option_list.action_cursor_down()
                self._update_detail_panel()
                event.stop()
                event.prevent_default()
            case "pageup":
                option_list.action_page_up()
                self._update_detail_panel()
                event.stop()
                event.prevent_default()
            case "pagedown":
                option_list.action_page_down()
                self._update_detail_panel()
                event.stop()
                event.prevent_default()
            case "enter":
                self._select_highlighted()
                event.stop()
                event.prevent_default()

    def _select_highlighted(self) -> None:
        """Select the currently highlighted provider."""
        option_list = self.query_one("#provider-selector-list", OptionList)
        if (
            option_list.highlighted is not None
            and 0 <= option_list.highlighted < len(self._filtered_providers)
        ):
            provider = self._filtered_providers[option_list.highlighted]
            self.post_message(self.ProviderSelected(provider_name=provider.name))

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        if 0 <= event.option_index < len(self._filtered_providers):
            provider = self._filtered_providers[event.option_index]
            self.post_message(self.ProviderSelected(provider_name=provider.name))

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())
