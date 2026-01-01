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

from revibe.core.config import DEFAULT_PROVIDERS, ProviderConfigUnion, VibeConfig
from revibe.core.model_config import DEFAULT_MODELS, ModelConfig
from revibe.core.paths.global_paths import GLOBAL_ENV_FILE
from revibe.setup.onboarding.base import OnboardingScreen
from revibe.setup.onboarding.provider_info import PROVIDER_HELP, mask_key

CONFIG_DOCS_URL = "https://github.com/OEvortex/revibe?tab=readme-ov-file#configuration"


MODEL_CONFIG_ADAPTER = TypeAdapter(list[ModelConfig])
PROVIDER_ADAPTER = TypeAdapter(list[ProviderConfigUnion])


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

        # Try to get active_provider first (new setup flow), fallback to active_model (existing flow)
        active_provider = getattr(config, 'active_provider', None)

        if active_provider:
            # New flow: provider is saved directly
            for provider in config.providers:
                if provider.name == active_provider:
                    self.provider = provider
                    break
            else:
                # Fallback to DEFAULT_PROVIDERS if not in config
                for provider in DEFAULT_PROVIDERS:
                    if provider.name == active_provider:
                        self.provider = provider
                        break
        else:
            # Existing flow: try to get provider from model
            try:
                active_model = config.get_active_model()
                self.provider = config.get_provider_for_model(active_model)
            except (ValueError, KeyError):
                # If model lookup fails, try to find provider by name
                if hasattr(config, 'active_model') and "-" in config.active_model:
                    provider_name = config.active_model.split("-")[0]
                    for provider in config.providers:
                        if provider.name == provider_name:
                            self.provider = provider
                            break

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
        provider_name = getattr(self.provider, 'name', '')

        if provider_name == "antigravity":
            # Check if already authenticated
            from revibe.core.llm.backend.antigravity.types import get_antigravity_credential_path
            cred_path = get_antigravity_credential_path()
            if cred_path.exists():
                yield Static(
                    "[green]✓[/] Antigravity is already authenticated!",
                    id="no-api-key-message",
                )
                yield Static(
                    f"Credentials saved at: {cred_path}",
                    id="antigravity-cred-path",
                    classes="subtle",
                )
                yield Center(
                    Button(
                        "Re-authenticate with Google",
                        id="antigravity-auth-button",
                        variant="default",
                    )
                )
            else:
                yield Static(
                    "Antigravity uses Google OAuth for authentication.",
                    id="no-api-key-message",
                )
                yield Static(
                    "Click the button below to open your browser and sign in with Google.",
                    id="antigravity-instructions",
                    classes="subtle",
                )
                yield Center(
                    Button(
                        "🔐 Sign in with Google",
                        id="antigravity-auth-button",
                        variant="success",
                        classes="primary-action",
                    )
                )
        elif provider_name == "qwencode":
            yield Static(
                f"{provider_name.capitalize()} does not require an API key.",
                id="no-api-key-message",
            )
            yield Static(
                "Please install qwen-code if not installed: `npm install -g @qwen-code/qwen-code@latest`\n"
                "then use `/auth` in qwen to authenticate, then you can close qwen and use qwencode provider in ReVibe",
                id="qwen-instructions",
            )
        elif provider_name == "geminicli":
            yield Static(
                f"{provider_name.capitalize()} does not require an API key.",
                id="no-api-key-message",
            )
            yield Static(
                "Please install gemini CLI: `npm install -g @anthropic-ai/gemini@latest`\n"
                "then use `gemini auth login` to authenticate.",
                id="geminicli-instructions",
            )
        else:
            yield Static(
                f"{provider_name.capitalize()} does not require an API key.",
                id="no-api-key-message",
            )
        yield Static("", id="feedback")


    def compose(self) -> ComposeResult:
        # Ensure provider is loaded (in case on_show hasn't been called yet)
        if self.provider is None:
            config = self._load_config()

            # Try to get active_provider first (new setup flow), fallback to active_model (existing flow)
            active_provider = getattr(config, 'active_provider', None)

            if active_provider:
                # New flow: provider is saved directly
                for provider in config.providers:
                    if provider.name == active_provider:
                        self.provider = provider
                        break
                else:
                    # Fallback to DEFAULT_PROVIDERS if not in config
                    for provider in DEFAULT_PROVIDERS:
                        if provider.name == active_provider:
                            self.provider = provider
                            break
            else:
                # Existing flow: try to get provider from model
                try:
                    active_model = config.get_active_model()
                    self.provider = config.get_provider_for_model(active_model)
                except (ValueError, KeyError):
                    # If model lookup fails, try to find provider by name
                    if hasattr(config, 'active_model') and "-" in config.active_model:
                        provider_name = config.active_model.split("-")[0]
                        for provider in config.providers:
                            if provider.name == provider_name:
                                self.provider = provider
                                break

        # Skip API key input for providers that don't require it
        if not getattr(self.provider, "api_key_env_var", ""):
            with Vertical(id="api-key-outer"):
                yield Static("Credentials", classes="eyebrow")
                yield Center(Static("No API Key Required", id="api-key-title"))
                with Center():
                    with Vertical(id="api-key-content", classes="card"):
                        yield from self._compose_no_api_key_content()
                yield Static("", classes="spacer")
            return

        env_key = getattr(self.provider, "api_key_env_var", "")
        existing_key = os.getenv(env_key)
        if existing_key:
            # Show detected key UI
            self.input_widget = Input(
                password=True,
                id="key",
                placeholder="Paste a new API key to replace (optional)",
                validators=[
                    Length(minimum=1, failure_description="No API key provided.")
                ],
            )
            with Vertical(id="api-key-outer"):
                yield Static("Credentials", classes="eyebrow")
                yield Center(Static("API Key Detected", id="api-key-title"))
                yield Center(
                    Static(
                        f"{getattr(self.provider, 'name', '').capitalize()} is already connected",
                        classes="lede",
                    )
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
            return

        self.input_widget = Input(
            password=True,
            id="key",
            placeholder="Paste your API key here",
            validators=[Length(minimum=1, failure_description="No API key provided.")],
        )

        with Vertical(id="api-key-outer"):
            yield Static("Credentials", classes="eyebrow")
            yield Center(Static("Connect your API key", id="api-key-title"))
            with Center():
                with Vertical(id="api-key-content", classes="card"):
                    yield from self._compose_provider_link(
                        getattr(self.provider, 'name', '').capitalize()
                    )
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
            self.app.exit(f"save_error:{err}")
            return
        self.app.exit("completed")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue-button":
            self.app.exit("completed")
        elif event.button.id == "antigravity-auth-button":
            self._run_antigravity_auth()

    def _run_antigravity_auth(self) -> None:
        """Run Antigravity OAuth authentication in a background thread."""
        import asyncio
        import threading

        feedback = self.query_one("#feedback", Static)
        button = self.query_one("#antigravity-auth-button", Button)

        # Disable button and show loading state
        button.disabled = True
        button.label = "Opening browser..."
        feedback.update("[dim]Please complete the authentication in your browser...[/]")

        def run_auth():
            """Run the async OAuth flow."""
            try:
                from revibe.core.llm.backend.antigravity.oauth import AntigravityOAuthManager

                oauth_manager = AntigravityOAuthManager()

                # Run the async authenticate method
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    credentials = loop.run_until_complete(oauth_manager.authenticate())
                    # Post success to main thread
                    self.app.call_from_thread(self._on_auth_success, credentials)
                except Exception as e:
                    # Post error to main thread
                    self.app.call_from_thread(self._on_auth_error, str(e))
                finally:
                    loop.close()
            except Exception as e:
                self.app.call_from_thread(self._on_auth_error, str(e))

        # Run in background thread
        thread = threading.Thread(target=run_auth, daemon=True)
        thread.start()

    def _on_auth_success(self, credentials) -> None:
        """Called when OAuth authentication succeeds."""
        feedback = self.query_one("#feedback", Static)
        feedback.update(f"[green]✓ Authenticated as: {credentials.email or 'Unknown'}[/]")
        feedback.add_class("success")

        # Update button to show success
        try:
            button = self.query_one("#antigravity-auth-button", Button)
            button.label = "✓ Authenticated"
            button.variant = "success"
            button.disabled = False
        except Exception:
            pass

        # Auto-complete after a brief delay
        self.set_timer(1.5, lambda: self.app.exit("completed"))

    def _on_auth_error(self, error: str) -> None:
        """Called when OAuth authentication fails."""
        feedback = self.query_one("#feedback", Static)
        feedback.update(f"[red]Authentication failed: {error}[/]")
        feedback.add_class("error")

        # Re-enable button
        try:
            button = self.query_one("#antigravity-auth-button", Button)
            button.disabled = False
            button.label = "🔐 Try Again"
        except Exception:
            pass

    def action_finish(self) -> None:
        self.app.exit("completed")

