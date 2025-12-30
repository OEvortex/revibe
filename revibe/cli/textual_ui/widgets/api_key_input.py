from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Input, Static

if TYPE_CHECKING:
    from revibe.core.config import ProviderConfigUnion


class ApiKeyInput(Container):
    """Widget for entering an API key for a provider."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "submit", "Submit", show=False),
    ]

    class ApiKeySubmitted(Message):
        def __init__(self, provider_name: str, api_key: str) -> None:
            super().__init__()
            self.provider_name = provider_name
            self.api_key = api_key

    class ApiKeyCancelled(Message):
        pass

    def __init__(self, provider: ProviderConfigUnion) -> None:
        super().__init__(id="api-key-input")
        self.provider = provider
        self.title_widget: Static | None = None
        self.input_widget: Input | None = None
        self.help_widget: Static | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="api-key-content"):
            if not self.provider.api_key_env_var:
                self.title_widget = Static(
                    f"{self.provider.name.capitalize()} does not require an API key",
                    classes="settings-title",
                )
                yield self.title_widget
                yield Static("")
                yield Static(
                    "This provider works without an API key. No further setup needed.",
                    classes="settings-help",
                )
                yield Static("")
                self.help_widget = Static(
                    "Enter to continue  ESC cancel", classes="settings-help"
                )
                yield self.help_widget
                return

            self.title_widget = Static(
                f"Enter API Key for {self.provider.name}", classes="settings-title"
            )
            yield self.title_widget
            yield Static("")
            yield Static(
                f"Environment variable: {self.provider.api_key_env_var}",
                classes="settings-help",
            )
            yield Static("")
            self.input_widget = Input(
                placeholder="Enter your API key...", password=True, id="api-key-field"
            )
            yield self.input_widget
            yield Static("")
            self.help_widget = Static(
                "Enter to save  ESC cancel", classes="settings-help"
            )
            yield self.help_widget

    def on_mount(self) -> None:
        if self.input_widget:
            self.input_widget.focus()

    def on_focus(self, event: events.Focus) -> None:
        if self.input_widget:
            self.input_widget.focus()

    def on_click(self, event: events.Click) -> None:
        if self.input_widget:
            self.input_widget.focus()

    def on_blur(self, event: events.Blur) -> None:
        # If we are blurring, check if we need to refocus
        # We use call_after_refresh to check the focus state after the change
        self.call_after_refresh(self._ensure_focus)

    def _ensure_focus(self) -> None:
        if self.is_mounted and self.app.focused != self.input_widget:
            if self.input_widget:
                self.input_widget.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        api_key = event.value.strip()
        if api_key or not self.provider.api_key_env_var:
            self.post_message(self.ApiKeySubmitted(self.provider.name, api_key))

    def action_cancel(self) -> None:
        self.post_message(self.ApiKeyCancelled())

    def action_submit(self) -> None:
        self.post_message(self.ApiKeySubmitted(self.provider.name, ""))
