from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Static

if TYPE_CHECKING:
    from revibe.core.config import ModelConfig, VibeConfig


class ModelSelector(Container):
    """Widget for selecting a model."""

    can_focus = True
    can_focus_children = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("space", "select", "Select", show=False),
    ]

    class ModelSelected(Message):
        def __init__(self, model_alias: str) -> None:
            super().__init__()
            self.model_alias = model_alias

    class SelectorClosed(Message):
        pass

    def __init__(self, config: VibeConfig, provider_filter: str | None = None) -> None:
        super().__init__(id="model-selector")
        self.config = config
        self.selected_index = 0
        self.provider_filter = provider_filter

        # Filter models by provider if specified
        if provider_filter:
            self.models: list[ModelConfig] = [
                m for m in config.models if m.provider == provider_filter
            ]
        else:
            self.models = list(config.models)

        self.title_widget: Static | None = None
        self.option_widgets: list[Static] = []
        self.help_widget: Static | None = None

        # Find current model index
        for i, m in enumerate(self.models):
            if m.alias == config.active_model:
                self.selected_index = i
                break

    def compose(self) -> ComposeResult:
        title = "Select Model"
        if self.provider_filter:
            title = f"Select Model ({self.provider_filter})"

        with Vertical(id="model-content"):
            self.title_widget = Static(title, classes="settings-title")
            yield self.title_widget
            yield Static("")

            for _ in self.models:
                widget = Static("", classes="settings-option")
                self.option_widgets.append(widget)
                yield widget

            if not self.models:
                yield Static("  No models available", classes="settings-option")

            yield Static("")
            self.help_widget = Static(
                "↑↓ navigate  Enter select  ESC cancel", classes="settings-help"
            )
            yield self.help_widget

    def on_mount(self) -> None:
        self._update_display()
        self.focus()

    def _update_display(self) -> None:
        for i, (model, widget) in enumerate(
            zip(self.models, self.option_widgets, strict=True)
        ):
            is_selected = i == self.selected_index
            cursor = "› " if is_selected else "  "
            text = f"{cursor}{model.alias} ({model.provider})"

            widget.update(text)
            widget.remove_class("settings-value-cycle-selected")
            widget.remove_class("settings-value-cycle-unselected")

            if is_selected:
                widget.add_class("settings-value-cycle-selected")
            else:
                widget.add_class("settings-value-cycle-unselected")

    def action_move_up(self) -> None:
        if self.models:
            self.selected_index = (self.selected_index - 1) % len(self.models)
            self._update_display()

    def action_move_down(self) -> None:
        if self.models:
            self.selected_index = (self.selected_index + 1) % len(self.models)
            self._update_display()

    def action_select(self) -> None:
        if self.models:
            model = self.models[self.selected_index]
            self.post_message(self.ModelSelected(model_alias=model.alias))

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())

    def on_blur(self, event: events.Blur) -> None:
        self.call_after_refresh(self.focus)

