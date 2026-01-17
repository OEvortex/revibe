from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from revibe.core.config import Backend, ModelConfig, ProviderConfigUnion

CONTEXT_MILLION = 1_000_000
CONTEXT_THOUSAND = 1000

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


def _format_price(input_price: float, output_price: float) -> str:
    """Format model pricing info."""
    if input_price == 0 and output_price == 0:
        return "free"
    return f"${input_price:.2f}/${output_price:.2f}"


def _format_context(context: int) -> str:
    """Format context window size."""
    if context >= CONTEXT_MILLION:
        return f"{context // CONTEXT_MILLION}M ctx"
    if context >= CONTEXT_THOUSAND:
        return f"{context // CONTEXT_THOUSAND}K ctx"
    return f"{context} ctx"


class ModelSelector(Container):
    """Modern widget for selecting a model with search, grouping, and rich metadata."""

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
        # Map option index to model (accounts for separators)
        self._option_to_model: dict[int, ModelConfig] = {}

    def compose(self) -> ComposeResult:
        title = "🔮 Select Model"
        if self.provider_filter:
            title = f"🔮 Select Model • {self.provider_filter}"

        with Vertical(id="model-content"):
            yield Static(title, classes="settings-title")
            yield Input(placeholder="Search models...", id="model-selector-filter")
            yield OptionList(id="model-selector-list")
            with Horizontal(classes="model-detail-row"):
                yield Static("", id="model-detail", classes="model-detail")
            yield Static(
                "↑↓ navigate  Enter select  / search  ESC cancel",
                classes="settings-help",
            )

    async def on_mount(self) -> None:
        self._update_list()
        # Fetch dynamic models (for ollama/llamacpp)
        await self._fetch_dynamic_models()
        self.query_one("#model-selector-filter", Input).focus()

    @on(Input.Changed, "#model-selector-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._update_list(event.value)

    def _format_model_option(self, model: ModelConfig, is_active: bool) -> str:
        """Format a model option with metadata badges."""
        active_marker = "▸ " if is_active else "  "
        price = _format_price(model.input_price, model.output_price)
        ctx = _format_context(model.context)

        # Truncate long aliases
        alias = model.alias[:24] + "…" if len(model.alias) > 25 else model.alias  # noqa: PLR2004
        return f"{active_marker}{alias:<26} {price:<12} {ctx}"

    def _update_list(self, filter_text: str = "") -> None:
        option_list = self.query_one("#model-selector-list", OptionList)
        option_list.clear_options()
        self._option_to_model.clear()

        filter_text_lower = filter_text.lower()

        self._filtered_models = [
            m
            for m in self.models
            if filter_text_lower in m.alias.lower()
            or filter_text_lower in m.provider.lower()
            or filter_text_lower in m.name.lower()
        ]

        # Show loading/error states
        if self._missing_api_key_message:
            option_list.add_option(
                Option(f"  ⚠ {self._missing_api_key_message}", disabled=True)
            )
            self._update_detail_panel()
            return

        if not self._filtered_models:
            msg = "  Loading models..." if self.loading else "  No models found"
            option_list.add_option(Option(msg, disabled=True))
            self._update_detail_panel()
            return

        # Group models by provider
        models_by_provider: dict[str, list[ModelConfig]] = {}
        for m in self._filtered_models:
            models_by_provider.setdefault(m.provider, []).append(m)

        # Determine active model
        active_alias: str | None = self.config.active_model
        option_idx = 0
        highlight_idx: int | None = None

        for provider in sorted(models_by_provider.keys()):
            provider_models = models_by_provider[provider]

            # Add provider header (only when showing multiple providers)
            if not self.provider_filter and len(models_by_provider) > 1:
                option_list.add_option(Option(f"─── {provider} ───", disabled=True))
                option_idx += 1

            for model in provider_models:
                is_active = model.alias == active_alias
                label = self._format_model_option(model, is_active)
                option_list.add_option(Option(label))
                self._option_to_model[option_idx] = model

                if is_active and highlight_idx is None:
                    highlight_idx = option_idx

                option_idx += 1

        # Set highlight
        if highlight_idx is not None:
            option_list.highlighted = highlight_idx
        elif self._option_to_model:
            option_list.highlighted = min(self._option_to_model.keys())

        self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        """Update the detail panel with info about the highlighted model."""
        option_list = self.query_one("#model-selector-list", OptionList)
        detail_widget = self.query_one("#model-detail", Static)

        if option_list.highlighted is not None:
            model = self._option_to_model.get(option_list.highlighted)
            if model:
                thinking = " • thinking" if model.supports_thinking else ""
                detail_widget.update(
                    f"{model.name}  •  {model.provider}{thinking}  •  max output: {model.max_output:,}"
                )
                return

        detail_widget.update("")

    @on(OptionList.OptionHighlighted)
    def on_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self._update_detail_panel()

    def _build_provider_map(self) -> dict[str, ProviderConfigUnion]:
        """Build a merged provider map from defaults and user config."""
        from revibe.core.config import DEFAULT_PROVIDERS

        providers_map: dict[str, ProviderConfigUnion] = {}
        for p in DEFAULT_PROVIDERS:
            providers_map[p.name] = p
        for p in self.config.providers:
            providers_map[p.name] = p
        return providers_map

    def _get_providers_to_query(
        self, providers_map: dict[str, ProviderConfigUnion]
    ) -> list[ProviderConfigUnion]:
        """Determine which providers to query for dynamic models."""
        import os

        providers_to_query: list[ProviderConfigUnion] = []

        if self.provider_filter:
            provider = providers_map.get(self.provider_filter)
            if provider:
                # Only fetch dynamic models for ollama and llamacpp
                if provider.backend not in {Backend.OLLAMA, Backend.LLAMACPP}:
                    return []

                # Check API key requirement
                if provider.api_key_env_var and not os.getenv(provider.api_key_env_var):
                    self._missing_api_key_message = f"Set {provider.api_key_env_var} to list models"
                    self.models = [
                        m for m in self.models if m.provider != provider.name
                    ]
                    return []
                providers_to_query.append(provider)
        else:
            # Query only ollama and llamacpp providers for dynamic models
            for p in providers_map.values():
                if p.backend not in {Backend.OLLAMA, Backend.LLAMACPP}:
                    continue
                if p.api_key_env_var and not os.getenv(p.api_key_env_var):
                    continue
                providers_to_query.append(p)

        return providers_to_query

    async def _fetch_models_from_provider(
        self, provider: ProviderConfigUnion, existing_names: set[tuple[str, str]]
    ) -> bool:
        """Fetch models from a single provider. Returns True if any models were added."""
        from revibe.core.llm.backend.factory import BACKEND_FACTORY

        try:
            backend_cls = BACKEND_FACTORY.get(provider.backend)
            if not backend_cls:
                return False

            model_names = await backend_cls(provider=provider).list_models()
            if not model_names:
                return False

            added_any = False
            for name in model_names:
                key = (provider.name, name)
                if key not in existing_names:
                    self.models.append(
                        ModelConfig(
                            name=name,
                            provider=provider.name,
                            alias=name,
                        )
                    )
                    existing_names.add(key)
                    added_any = True

            return added_any
        except Exception:
            return False

    async def _fetch_models_from_providers(
        self, providers_to_query: list[ProviderConfigUnion]
    ) -> bool:
        """Fetch models from the specified providers."""
        existing_names = {(m.provider, m.name) for m in self.models}
        added_any = False

        for provider in providers_to_query:
            if await self._fetch_models_from_provider(provider, existing_names):
                added_any = True

        return added_any

    async def _fetch_dynamic_models(self) -> None:
        """Fetch models from provider backends (ollama/llamacpp only)."""
        self._missing_api_key_message = None
        self.loading = True
        self._update_list(self.query_one("#model-selector-filter", Input).value)

        try:
            providers_map = self._build_provider_map()
            providers_to_query = self._get_providers_to_query(providers_map)

            if providers_to_query:
                added_any = await self._fetch_models_from_providers(providers_to_query)
                if added_any:
                    self.models.sort(key=lambda x: (x.provider, x.name))
        finally:
            self.loading = False
            self._update_list(self.query_one("#model-selector-filter", Input).value)

    def on_key(self, event: events.Key) -> None:
        option_list = self.query_one("#model-selector-list", OptionList)
        search_input = self.query_one("#model-selector-filter", Input)

        # Handle escape globally
        if event.key == "escape":
            self.action_close()
            event.stop()
            event.prevent_default()
            return

        # If OptionList has focus
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

        # Search input focused - proxy navigation to OptionList
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
        """Select the currently highlighted model."""
        option_list = self.query_one("#model-selector-list", OptionList)
        if option_list.highlighted is not None:
            model = self._option_to_model.get(option_list.highlighted)
            if model:
                self.post_message(
                    self.ModelSelected(
                        model_alias=model.alias,
                        model_name=model.name,
                        provider=model.provider,
                    )
                )

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        model = self._option_to_model.get(event.option_index)
        if model:
            self.post_message(
                self.ModelSelected(
                    model_alias=model.alias,
                    model_name=model.name,
                    provider=model.provider,
                )
            )

    def action_close(self) -> None:
        self.post_message(self.SelectorClosed())
