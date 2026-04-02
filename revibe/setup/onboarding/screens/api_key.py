from __future__ import annotations

import os
from typing import ClassVar

from dotenv import set_key
from pydantic import TypeAdapter
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Container, Horizontal, Vertical
from textual.timer import Timer
from textual.validation import Length
from textual.widgets import Button, Input, Link, Static

from revibe.core.config import DEFAULT_PROVIDERS, ProviderConfig, VibeConfig
from revibe.core.model_config import ModelConfig
from revibe.core.model_sources import get_available_models
from revibe.core.paths.global_paths import GLOBAL_ENV_FILE
from revibe.setup.onboarding.base import OnboardingScreen
from revibe.setup.onboarding.provider_info import PROVIDER_HELP, mask_key

CONFIG_DOCS_URL = "https://github.com/OEvortex/revibe?tab=readme-ov-file#configuration"


MODEL_CONFIG_ADAPTER = TypeAdapter(list[ModelConfig])
PROVIDER_ADAPTER = TypeAdapter(list[ProviderConfig])


def _save_api_key_to_env_file(env_key: str, api_key: str) -> None:
    GLOBAL_ENV_FILE.path.parent.mkdir(parents=True, exist_ok=True)
    set_key(GLOBAL_ENV_FILE.path, env_key, api_key)


GRADIENT_COLORS = [
    "#ff6b00",
    "#ff7b00",
    "#ff8c00",
    "#ff9d00",
    "#ffae00",
    "#ffbf00",
    "#ffae00",
    "#ff9d00",
    "#ff8c00",
    "#ff7b00",
]


def _apply_gradient(text: str, offset: int) -> str:
    result = []
    for i, char in enumerate(text):
        color = GRADIENT_COLORS[(i + offset) % len(GRADIENT_COLORS)]
        result.append(f"[bold {color}]{char}[/]")
    return "".join(result)


def _resolve_provider(config: VibeConfig) -> ProviderConfig | None:
    active_provider = getattr(config, "active_provider", None)
    if active_provider:
        for provider in config.providers:
            if provider.name == active_provider:
                return provider
        for provider in DEFAULT_PROVIDERS:
            if provider.name == active_provider:
                return provider
        return None

    try:
        active_model = config.get_active_model()
        return config.get_provider_for_model(active_model)
    except (ValueError, KeyError):
        active_model_name = getattr(config, "active_model", "")
        if active_model_name:
            for model in config.models:
                if active_model_name in {model.alias, model.name}:
                    return config.get_provider_for_model(model)

        if config.models:
            return config.get_provider_for_model(config.models[0])
    return None


class ApiKeyScreen(OnboardingScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+c", "cancel", "Cancel", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "finish", "Finish", show=False),
    ]

    NEXT_SCREEN = None

    def __init__(self) -> None:
        super().__init__()
        # Provider will be loaded when screen is shown
        self.provider = None
        self._gradient_offset = 0
        self._gradient_timer: Timer | None = None
        self._test_app = None

    @property
    def app(self) -> object:
        if self._test_app is not None:
            return self._test_app
        return super().app

    @app.setter
    def app(self, value: object) -> None:
        self._test_app = value

    def _load_config(self) -> VibeConfig:
        """Load config, handling missing API key since we're in setup.

        Uses model_construct with TOML data to get the saved active_model
        while bypassing API key validation.
        """
        from revibe.core.config import TomlFileSettingsSource

        toml_data = TomlFileSettingsSource(VibeConfig).toml_data

        if "models" in toml_data:
            toml_data["models"] = [ModelConfig(**item) for item in toml_data["models"]]
        else:
            toml_data["models"] = get_available_models()

        # Merge default models if not present
        existing_keys = {(m.name, m.provider) for m in toml_data["models"]}
        for m in get_available_models():
            if (m.name, m.provider) not in existing_keys:
                toml_data["models"].append(m)

        if "providers" in toml_data:
            toml_data["providers"] = PROVIDER_ADAPTER.validate_python(
                toml_data["providers"]
            )
        else:
            toml_data["providers"] = list(DEFAULT_PROVIDERS)

        return VibeConfig.model_construct(**toml_data)

    def on_show(self) -> None:
        """Reload config when screen becomes visible to pick up saved provider selection."""
        config = self._load_config()
        self.provider = _resolve_provider(config)
        if self.provider and not getattr(self.provider, "api_key_env_var", ""):
            self._exit_app("completed")

    def _ensure_provider_loaded(self) -> None:
        if self.provider is not None:
            return
        config = self._load_config()
        self.provider = _resolve_provider(config)

    def _compose_provider_link(self, provider_name: str) -> ComposeResult:
        if not self.provider or getattr(self.provider, "name", "") not in PROVIDER_HELP:
            return

        help_url, help_name = PROVIDER_HELP[getattr(self.provider, "name", "")]
        yield Static(f"Grab your {provider_name} API key from the {help_name}:")
        yield Center(
            Horizontal(
                Static("→ ", classes="link-chevron"),
                Link(help_url, url=help_url),
                classes="link-row",
            )
        )

    def _compose_config_docs(self) -> ComposeResult:
        yield Static("[dim]Learn more about ReVibe configuration:[/]")
        yield Horizontal(
            Static("→ ", classes="link-chevron"),
            Link(CONFIG_DOCS_URL, url=CONFIG_DOCS_URL),
            classes="link-row",
        )

    def _compose_no_api_key_content(self) -> ComposeResult:
        if not self.provider:
            return
        provider_name = getattr(self.provider, "name", "")

        yield Static(
            f"{provider_name.capitalize()} does not require an API key.",
            id="no-api-key-message",
        )
        yield Static("", id="feedback")

    def _compose_no_api_key_screen(self) -> ComposeResult:
        with Vertical(id="api-key-outer"):
            yield Static("Credentials", classes="eyebrow")
            yield Center(Static("No API Key Required", id="api-key-title"))
            with Center():
                with Vertical(id="api-key-content", classes="card"):
                    yield from self._compose_no_api_key_content()
            yield Static("", classes="spacer")

    def _compose_detected_key_screen(
        self, env_key: str, existing_key: str
    ) -> ComposeResult:
        self.input_widget = Input(
            password=True,
            id="key",
            placeholder="Paste a new API key to replace (optional)",
            validators=[Length(minimum=1, failure_description="No API key provided.")],
        )
        provider_name = getattr(self.provider, "name", "").capitalize()

        with Vertical(id="api-key-outer"):
            yield Static("Credentials", classes="eyebrow")
            yield Center(Static("API Key Detected", id="api-key-title"))
            yield Center(
                Static(f"{provider_name} is already connected", classes="lede")
            )
            with Center():
                with Vertical(id="api-key-content", classes="card"):
                    yield Static(
                        f"Found {env_key} in environment", id="key-detected-message"
                    )
                    yield Static(
                        f"Masked key: {mask_key(existing_key)}",
                        id="masked-key",
                        classes="pill code",
                    )
                    yield Static(
                        "Keep the detected key or replace it with a fresh one.",
                        classes="subtle",
                    )
                    yield Static("", id="feedback")
                    yield Center(
                        Button(
                            "Continue with detected key",
                            id="continue-button",
                            variant="success",
                            classes="primary-action",
                        )
                    )
                    yield Static(
                        "Replace it below if you'd prefer to rotate the key.",
                        id="replace-hint",
                    )
                    with Container(id="input-box"):
                        yield self.input_widget
            yield Static("", classes="spacer")
            yield Vertical(
                Vertical(
                    *self._compose_config_docs(),
                    id="config-docs-group",
                    classes="footer-card",
                ),
                id="config-docs-section",
            )

    def _compose_new_key_screen(self, env_key: str) -> ComposeResult:
        self.input_widget = Input(
            password=True,
            id="key",
            placeholder="Paste your API key here",
            validators=[Length(minimum=1, failure_description="No API key provided.")],
        )
        provider_name = getattr(self.provider, "name", "").capitalize()

        with Vertical(id="api-key-outer"):
            yield Static("Credentials", classes="eyebrow")
            yield Center(Static("Connect your API key", id="api-key-title"))
            with Center():
                with Vertical(id="api-key-content", classes="card"):
                    yield from self._compose_provider_link(provider_name)
                    yield Static(f"Env variable: {env_key}", classes="pill code")
                    yield Static(
                        "Your key stays on your machine. Paste it to continue.",
                        classes="subtle",
                    )
                    with Container(id="input-box"):
                        yield self.input_widget
                    yield Static("", id="feedback")
            yield Static("", classes="spacer")
            yield Vertical(
                Vertical(
                    *self._compose_config_docs(),
                    id="config-docs-group",
                    classes="footer-card",
                ),
                id="config-docs-section",
            )

    def compose(self) -> ComposeResult:
        self._ensure_provider_loaded()
        if not self.provider:
            return

        if not getattr(self.provider, "api_key_env_var", ""):
            yield from self._compose_no_api_key_screen()
            return

        env_key = getattr(self.provider, "api_key_env_var", "")
        if existing_key := os.getenv(env_key):
            yield from self._compose_detected_key_screen(env_key, existing_key)
            return

        yield from self._compose_new_key_screen(env_key)

    def _start_gradient_animation(self) -> None:
        self._gradient_timer = self.set_interval(0.08, self._animate_gradient)

    def _animate_gradient(self) -> None:
        self._gradient_offset = (self._gradient_offset + 1) % len(GRADIENT_COLORS)
        title_widget = self.query_one("#api-key-title", Static)
        title_widget.update(self._render_title())

    def _render_title(self) -> str:
        title = "Secure your API key"
        return _apply_gradient(title, self._gradient_offset)

    def on_mount(self) -> None:
        title_widget = self.query_one("#api-key-title", Static)
        if title_widget:
            # Check for specific widgets that only exist in the "detected" state
            is_detected = False
            try:
                self.query_one("#masked-key")
                is_detected = True
            except Exception:
                pass

            if is_detected:
                # No gradient for detected key
                pass
            else:
                title_widget.update(self._render_title())
                self._start_gradient_animation()
        if hasattr(self, "input_widget") and self.input_widget:
            self.input_widget.focus()
        else:
            try:
                continue_button = self.query_one("#continue-button", Button)
                continue_button.focus()
            except Exception:
                pass

    def _exit_app(self, value: str) -> None:
        exit_callable = getattr(self.app, "exit", None)
        if exit_callable is None:
            return
        try:
            exit_callable(value)
        except TypeError:
            raw_exit = getattr(exit_callable, "__func__", None)
            if raw_exit is None:
                raise
            raw_exit(value)

    def on_input_changed(self, event: Input.Changed) -> None:
        feedback = self.query_one("#feedback", Static)
        input_box = self.query_one("#input-box", Container)

        if event.validation_result is None:
            return

        input_box.remove_class("valid", "invalid")
        feedback.remove_class("error", "success")

        if event.validation_result.is_valid:
            feedback.update("Press Enter to submit ↵")
            feedback.add_class("success")
            input_box.add_class("valid")
            return

        descriptions = event.validation_result.failure_descriptions
        feedback.update(descriptions[0])
        feedback.add_class("error")
        input_box.add_class("invalid")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.validation_result and event.validation_result.is_valid:
            self._save_and_finish(event.value)

    def _save_and_finish(self, api_key: str) -> None:
        if not self.provider:
            return
        env_key = getattr(self.provider, "api_key_env_var", "")
        os.environ[env_key] = api_key
        try:
            _save_api_key_to_env_file(env_key, api_key)
        except OSError as err:
            self._exit_app(f"save_error:{err}")
            return
        self._exit_app("completed")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue-button":
            self._exit_app("completed")

    def action_finish(self) -> None:
        self._exit_app("completed")
