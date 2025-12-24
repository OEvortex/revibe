from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Static

from revibe.core.config import ModelConfig

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


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
        self.loading = False

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

            if self.loading:
                yield Static("  Loading models...", id="model-loading")
            else:
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

    async def on_mount(self) -> None:
        if self.provider_filter:
            await self._fetch_dynamic_models()
        self._update_display()
        self.focus()

    async def _fetch_dynamic_models(self) -> None:
        self.loading = True
        self.refresh(layout=True)

        try:
            from revibe.core.llm.backend.factory import BACKEND_FACTORY

            # Get provider config
            provider = None
            for p in self.config.providers:
                if p.name == self.provider_filter:
                    provider = p
                    break

            if not provider:
                from revibe.core.config import DEFAULT_PROVIDERS
                for p in DEFAULT_PROVIDERS:
                    if p.name == self.provider_filter:
                        provider = p
                        break

            if provider:
                backend_cls = BACKEND_FACTORY.get(provider.backend)
                if backend_cls:
                    async with backend_cls(provider=provider) as backend:
                        model_names = await backend.list_models()
                        if model_names:
                            # Create ModelConfig objects for new models
                            existing_names = {m.name for m in self.models}
                            new_models = []
                            for name in model_names:
                                if name not in existing_names:
                                    new_models.append(ModelConfig(
                                        name=name,
                                        provider=self.provider_filter,
                                        alias=name
                                    ))

                            if new_models:
                                self.models.extend(new_models)
                                # Sort models
                                self.models.sort(key=lambda x: x.name)

                                # Update selected index
                                for i, m in enumerate(self.models):
                                    if m.alias == self.config.active_model:
                                        self.selected_index = i
                                        break
        except Exception:
            pass
        finally:
            self.loading = False
            # Re-compose or update widgets
            self.option_widgets = []
            content_container = self.query_one("#model-content")
            await content_container.remove_children()
            await content_container.mount_all(self._get_dynamic_compose())
            self._update_display()

    def _get_dynamic_compose(self) -> list[Static]:
        widgets = []
        widgets.append(Static(f"Select Model ({self.provider_filter})", classes="settings-title"))
        widgets.append(Static(""))

        for _ in self.models:
            widget = Static("", classes="settings-option")
            self.option_widgets.append(widget)
            widgets.append(widget)

        if not self.models:
            widgets.append(Static("  No models available", classes="settings-option"))

        widgets.append(Static(""))
        widgets.append(Static(
            "↑↓ navigate  Enter select  ESC cancel", classes="settings-help"
        ))

        return widgets

    def _update_display(self) -> None:
        if self.loading:
            return

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
        # Only refocus if we are still mounted and not blurring to a child
        if self.is_mounted and self.app.focused != self:
            self.call_after_refresh(self._ensure_focus)

    def _ensure_focus(self) -> None:
        if self.is_mounted and self.app.focused is None:
            self.focus()

