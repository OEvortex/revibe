from __future__ import annotations

import os
from typing import ClassVar

from dotenv import set_key
from pydantic import TypeAdapter
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Horizontal, Vertical
from textual.timer import Timer
from textual.validation import Length
from textual.widgets import Button, Input, Link, Static

from revibe.core.config import DEFAULT_PROVIDERS, ProviderConfigUnion, VibeConfig
from revibe.core.model_config import DEFAULT_MODELS, ModelConfig
from revibe.core.paths.global_paths import GLOBAL_ENV_FILE
from revibe.setup.onboarding.base import OnboardingScreen

PROVIDER_HELP = {
    "mistral": ("https://console.mistral.ai/api-keys", "Mistral AI Console"),
    "openai": ("https://platform.openai.com/api-keys", "OpenAI Platform"),
    "anthropic": ("https://console.anthropic.com/settings/keys", "Anthropic Console"),
    "groq": ("https://console.groq.com/keys", "Groq Console"),
    "huggingface": ("https://huggingface.co/settings/tokens", "Hugging Face Settings"),
    "cerebras": (
        "https://cloud.cerebras.ai/platform/api-keys",
        "Cerebras Cloud Platform",
    ),
}
CONFIG_DOCS_URL = "https://github.com/OEvortex/revibe?tab=readme-ov-file#configuration"


MODEL_CONFIG_ADAPTER = TypeAdapter(list[ModelConfig])
PROVIDER_ADAPTER = TypeAdapter(list[ProviderConfigUnion])


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
            toml_data["models"] = list(DEFAULT_MODELS)

        # Merge default models if not present
        existing_keys = {(m.name, m.provider) for m in toml_data["models"]}
        for m in DEFAULT_MODELS:
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
        active_model = config.get_active_model()
        self.provider = config.get_provider_for_model(active_model)

    def _compose_provider_link(self, provider_name: str) -> ComposeResult:
        if not self.provider or self.provider.name not in PROVIDER_HELP:
            return

        help_url, help_name = PROVIDER_HELP[self.provider.name]
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
        yield Static(
            f"{self.provider.name.capitalize()} does not require an API key.",
            id="no-api-key-message",
        )
        if self.provider.name == "qwencode":
            yield Static(
                "Please install qwen-code if not installed: `npm install -g @qwen-code/qwen-code@latest`\n"
                "then use `/auth` in qwen to authenticate, then you can close qwen and use qwencode provider in ReVibe",
                id="qwen-instructions",
            )
        yield Static("", id="feedback")

    def compose(self) -> ComposeResult:
        # Ensure provider is loaded (in case on_show hasn't been called yet)
        if self.provider is None:
            config = self._load_config()
            active_model = config.get_active_model()
            self.provider = config.get_provider_for_model(active_model)

        # Skip API key input for providers that don't require it
        if not getattr(self.provider, "api_key_env_var", ""):
            with Vertical(id="api-key-outer"):
                yield Static("", classes="spacer")
                yield Center(Static("", id="api-key-title"))
                with Center():
                    with Vertical(id="api-key-content"):
                        yield from self._compose_no_api_key_content()
                yield Static("", classes="spacer")
            return

        self.input_widget = Input(
            password=True,
            id="key",
            placeholder="Paste your API key here",
            validators=[Length(minimum=1, failure_description="No API key provided.")],
        )

        with Vertical(id="api-key-outer"):
            yield Static("", classes="spacer")
            yield Center(Static("One last thing...", id="api-key-title"))
            with Center():
                with Vertical(id="api-key-content"):
                    yield from self._compose_no_api_key_content()
            yield Static("", classes="spacer")
            yield Vertical(
                Vertical(*self._compose_config_docs(), id="config-docs-group"),
                id="config-docs-section",
            )

    def _start_gradient_animation(self) -> None:
        self._gradient_timer = self.set_interval(0.08, self._animate_gradient)

    def _animate_gradient(self) -> None:
        self._gradient_offset = (self._gradient_offset + 1) % len(GRADIENT_COLORS)
        title_widget = self.query_one("#api-key-title", Static)
        title_widget.update(self._render_title())

    def _render_title(self) -> str:
        title = "Setup Completed"
        return _apply_gradient(title, self._gradient_offset)

    def on_mount(self) -> None:
        title_widget = self.query_one("#api-key-title", Static)
        if title_widget:
            title_widget.update(self._render_title())
            self._start_gradient_animation()
        if hasattr(self, "input_widget") and self.input_widget:
            self.input_widget.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        feedback = self.query_one("#feedback", Static)
        input_box = self.query_one("#input-box")

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
        env_key = self.provider.api_key_env_var
        os.environ[env_key] = api_key
        try:
            _save_api_key_to_env_file(env_key, api_key)
        except OSError as err:
            self.app.exit(f"save_error:{err}")
            return
        self.app.exit("completed")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue-button":
            self.app.exit("completed")

    def action_finish(self) -> None:
        self.app.exit("completed")
