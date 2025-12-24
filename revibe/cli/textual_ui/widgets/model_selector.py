from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Static, OptionList, Input
from textual.widgets.option_list import Option

from revibe.core.config import Backend, ModelConfig, ProviderConfig

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


class ModelSelector(Container):
    """Widget for selecting a model with high performance and filtering."""

    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Cancel", show=False),
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
        self.provider_filter = provider_filter
        self.loading = False
        self._missing_api_key_message: str | None = None

        # Filter models by provider if specified
        if provider_filter:
            self.models: list[ModelConfig] = [
                m for m in config.models if m.provider == provider_filter
            ]
        else:
            self.models = list(config.models)

        self._filtered_models: list[ModelConfig] = list(self.models)

    def compose(self) -> ComposeResult:
        title = "Select Model"
        if self.provider_filter:
            title = f"Select Model ({self.provider_filter})"

        with Vertical(id="model-content"):
            yield Static(title, classes="settings-title")
            yield Input(placeholder="Search models...", id="model-selector-filter")
            yield OptionList(id="model-selector-list")
            yield Static(
                "↑↓ navigate  Enter select  ESC cancel", classes="settings-help"
            )

    async def on_mount(self) -> None:
        self._update_list()
        # Always attempt to fetch dynamic models (for the filtered provider or all providers)
        await self._fetch_dynamic_models()
        self.query_one("#model-selector-filter").focus()

    @on(Input.Changed, "#model-selector-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._update_list(event.value)

    def _update_list(self, filter_text: str = "") -> None:
        option_list = self.query_one("#model-selector-list", OptionList)
        option_list.clear_options()

        filter_text = filter_text.lower()

        self._filtered_models = [
            m for m in self.models
            if filter_text in m.alias.lower() or filter_text in m.provider.lower()
        ]

        if self._missing_api_key_message:
            option_list.add_option(Option(f"  {self._missing_api_key_message}", disabled=True))
        elif not self._filtered_models:
            if self.loading:
                option_list.add_option(Option("  Loading models...", disabled=True))
            else:
                option_list.add_option(Option("  No models available", disabled=True))
        else:
            for model in self._filtered_models:
                option_list.add_option(Option(f"{model.alias} ({model.provider})"))

            # Highlight active model if it's in the list, otherwise highlight first
            found_active = False
            for i, m in enumerate(self._filtered_models):
                if m.alias == self.config.active_model:
                    option_list.highlighted = i
                    found_active = True
                    break

            if not found_active and self._filtered_models:
                option_list.highlighted = 0

    async def _fetch_dynamic_models(self) -> None:
        """Fetch models from provider backends. Only fetches dynamically for ollama and llamacpp,
        other providers use hardcoded DEFAULT_MODELS.
        """
        self._missing_api_key_message = None
        self.loading = True
        self._update_list(self.query_one("#model-selector-filter", Input).value)

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
                    # Only fetch dynamic models for ollama and llamacpp
                    if provider.backend not in (Backend.OLLAMA, Backend.LLAMACPP):
                        # Use hardcoded models for other providers
                        self.loading = False
                        self._update_list(self.query_one("#model-selector-filter", Input).value)
                        return

                    # If provider requires an API key and none is set, show a helpful message
                    if provider.api_key_env_var and not os.getenv(provider.api_key_env_var):
                        self._missing_api_key_message = (
                            f"API key required: set {provider.api_key_env_var} to list models for {provider.name}"
                        )
                        # Clear any models we had filtered earlier
                        self.models = [m for m in self.models if m.provider != provider.name]
                        self.loading = False
                        self._update_list(self.query_one("#model-selector-filter", Input).value)
                        return
                    providers_to_query.append(provider)
            else:
                # Query only ollama and llamacpp providers for dynamic models
                # Skip providers that require API keys but don't have one set
                for p in providers_map.values():
                    if p.backend not in (Backend.OLLAMA, Backend.LLAMACPP):
                        continue
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
        finally:
            self.loading = False
            self._update_list(self.query_one("#model-selector-filter", Input).value)

    @on(Input.Submitted, "#model-selector-filter")
    def on_filter_submitted(self, event: Input.Submitted) -> None:
        option_list = self.query_one("#model-selector-list", OptionList)
        if option_list.highlighted is not None and 0 <= option_list.highlighted < len(self._filtered_models):
            model = self._filtered_models[option_list.highlighted]
            self.post_message(
                self.ModelSelected(
                    model_alias=model.alias,
                    model_name=model.name,
                    provider=model.provider,
                )
            )

    def on_key(self, event: events.Key) -> None:
        if self.query_one("#model-selector-filter").has_focus:
            if event.key in ("up", "down", "pageup", "pagedown"):
                option_list = self.query_one("#model-selector-list", OptionList)
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

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        if 0 <= event.option_index < len(self._filtered_models):
            model = self._filtered_models[event.option_index]
            self.post_message(
                self.ModelSelected(
                    model_alias=model.alias,
                    model_name=model.name,
                    provider=model.provider,
                )
            )

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())

