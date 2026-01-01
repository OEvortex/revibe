from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Vertical
from textual.widgets import Static

from revibe.core.config import DEFAULT_PROVIDERS, ProviderConfig, VibeConfig
from revibe.setup.onboarding.base import OnboardingScreen
from revibe.setup.onboarding.provider_info import build_provider_description

VISIBLE_NEIGHBORS = 2
FADE_CLASSES = ["fade-1", "fade-2"]


class ProviderSelectionScreen(OnboardingScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "Select", show=False, priority=True),
        Binding("space", "select", "Select", show=False),
        Binding("up", "prev_provider", "Previous", show=False),
        Binding("down", "next_provider", "Next", show=False),
        Binding("i", "toggle_details", "Toggle details", show=False),
        Binding("ctrl+c", "cancel", "Cancel", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    NEXT_SCREEN = "theme_selection"

    def __init__(self) -> None:
        super().__init__()
        self._provider_index = 0
        self._provider_widgets: list[Static] = []
        self._providers: list[ProviderConfig] = list(DEFAULT_PROVIDERS)
        self._show_details = False

    def _compose_provider_list(self) -> ComposeResult:
        for _ in range(VISIBLE_NEIGHBORS * 2 + 1):
            widget = Static("", classes="provider-item")
            self._provider_widgets.append(widget)
            yield widget

    def compose(self) -> ComposeResult:
        with Center(id="provider-outer"):
            with Vertical(id="provider-content"):
                yield Static("Choose your AI provider", id="provider-title")
                yield Static(
                    "[dim]You can add more providers later in config.toml[/]",
                    id="provider-subtitle",
                )
                yield Center(
                    Vertical(
                        Static("↑", id="nav-up", classes="nav-arrow"),
                        Vertical(*self._compose_provider_list(), id="provider-list"),
                        Static("↓", id="nav-down", classes="nav-arrow"),
                        id="provider-nav",
                    )
                )
                yield Static("", id="provider-description")
                yield Center(
                    Static(
                        "[dim]Press[/] Enter [dim]to select, [/]i[dim] to toggle details[/]",
                        id="provider-hint",
                    )
                )

    def on_mount(self) -> None:
        self._update_display()
        self.focus()

    def _get_provider_at_offset(self, offset: int) -> ProviderConfig:
        index = (self._provider_index + offset) % len(self._providers)
        return self._providers[index]

    def _update_display(self) -> None:
        for i, widget in enumerate(self._provider_widgets):
            offset = i - VISIBLE_NEIGHBORS
            provider = self._get_provider_at_offset(offset)

            widget.remove_class("selected", *FADE_CLASSES)

            display_name = provider.name.capitalize()
            if offset == 0:
                widget.update(f" ● {display_name} ")
                widget.add_class("selected")
            else:
                distance = min(abs(offset) - 1, len(FADE_CLASSES) - 1)
                widget.update(f"   {display_name}")
                widget.add_class(FADE_CLASSES[distance])

        # Update description
        current = self._providers[self._provider_index]
        desc = build_provider_description(current, self._show_details)
        self.query_one("#provider-description", Static).update(desc)

    def _navigate(self, direction: int) -> None:
        self._provider_index = (self._provider_index + direction) % len(self._providers)
        self._update_display()

    def action_next_provider(self) -> None:
        self._navigate(1)

    def action_prev_provider(self) -> None:
        self._navigate(-1)

    def action_toggle_details(self) -> None:
        self._show_details = not self._show_details
        self._update_display()

    def action_select(self) -> None:
        selected = self._providers[self._provider_index]

        # Save the selected provider name directly instead of model alias
        try:
            VibeConfig.save_updates({"active_provider": selected.name})
        except OSError as e:
            # Log the error but don't fail silently - this is critical for setup
            from rich import print as rprint
            rprint(f"[yellow]Warning: Could not save provider selection: {e}[/]")
        self.action_next()
