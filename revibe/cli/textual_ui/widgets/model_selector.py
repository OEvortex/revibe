from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Static

from revibe.core.config import ModelConfig, ProviderConfig

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
        def __init__(self, model_alias: str, model_name: str, provider: str) -> None:
            super().__init__()
            self.model_alias = model_alias
            self.model_name = model_name
            self.provider = provider

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
        # When a provider requires an API key but none is set, we show an explanatory message
        self._missing_api_key_message: str | None = None

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
        # Always attempt to fetch dynamic models (for the filtered provider or all providers)
        await self._fetch_dynamic_models()
        self._update_display()
        self.focus()

    async def _fetch_dynamic_models(self) -> None:
        """Fetch models from provider backends. If provider_filter is set, only fetch for that provider,
        otherwise attempt to fetch models for all known providers (defaults + configured).
        """
        self._missing_api_key_message = None
        self.loading = True
        self.refresh(layout=True)

        try:
            from revibe.core.llm.backend.factory import BACKEND_FACTORY
            from revibe.core.config import DEFAULT_PROVIDERS

            # Build a merged provider map (defaults + user config)
            providers_map: dict[str, ProviderConfig] = {}
            for p in DEFAULT_PROVIDERS:
                providers_map[p.name] = p
            for p in self.config.providers:
                providers_map[p.name] = p

            providers_to_query: list[ProviderConfig] = []

            import os

            if self.provider_filter:
                provider = providers_map.get(self.provider_filter)
                if provider:
                    # If provider requires an API key and none is set, show a helpful message
                    if provider.api_key_env_var and not os.getenv(provider.api_key_env_var):
                        self._missing_api_key_message = (
                            f"API key required: set {provider.api_key_env_var} to list models for {provider.name}"
                        )
                        # Clear any models we had filtered earlier
                        self.models = [m for m in self.models if m.provider != provider.name]
                        self.loading = False
                        return
                    providers_to_query.append(provider)
            else:
                # Query all providers (better UX for model browsing)
                # Skip providers that require API keys but don't have one set
                for p in providers_map.values():
                    if p.api_key_env_var and not os.getenv(p.api_key_env_var):
                        continue
                    providers_to_query.append(p)

            existing_names = {(m.provider, m.name) for m in self.models}
            added_any = False

            for provider in providers_to_query:
                try:
                    backend_cls = BACKEND_FACTORY.get(provider.backend)
                    if backend_cls:
                        async with backend_cls(provider=provider) as backend:
                            model_names = await backend.list_models()
                            if model_names:
                                for name in model_names:
                                    key = (provider.name, name)
                                    if key not in existing_names:
                                        self.models.append(
                                            ModelConfig(name=name, provider=provider.name, alias=name)
                                        )
                                        existing_names.add(key)
                                        added_any = True
                except Exception:
                    # Ignore failures per-provider so one bad provider doesn't block others
                    continue

            if added_any:
                # Sort models by provider then name for stable display
                self.models.sort(key=lambda x: (x.provider, x.name))

                # Update selected index if current active_model exists
                for i, m in enumerate(self.models):
                    if m.alias == self.config.active_model:
                        self.selected_index = i
                        break
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
        title = "Select Model" if not self.provider_filter else f"Select Model ({self.provider_filter})"
        widgets.append(Static(title, classes="settings-title"))
        widgets.append(Static(""))

        for _ in self.models:
            widget = Static("", classes="settings-option")
            self.option_widgets.append(widget)
            widgets.append(widget)

        if self._missing_api_key_message:
            widgets.append(Static(f"  {self._missing_api_key_message}", classes="settings-option"))
        elif not self.models:
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
            self.post_message(
                self.ModelSelected(
                    model_alias=model.alias,
                    model_name=model.name,
                    provider=model.provider,
                )
            )

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())

    def on_blur(self, event: events.Blur) -> None:
        # Only refocus if we are still mounted and not blurring to a child
        if self.is_mounted and self.app.focused != self:
            self.call_after_refresh(self._ensure_focus)

    def _ensure_focus(self) -> None:
        if self.is_mounted and self.app.focused is None:
            self.focus()

