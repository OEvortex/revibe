from __future__ import annotations

from enum import StrEnum, auto
import os
from pathlib import Path
import re
import shlex
import sys
import tomllib
from typing import Annotated, Any, Literal

from dotenv import dotenv_values
from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_core import to_jsonable_python
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
import tomli_w

from revibe.core.model_config import ModelConfig
from revibe.core.model_sources import get_available_models
from revibe.core.paths.config_paths import (
    AGENT_DIR,
    CONFIG_DIR,
    CONFIG_FILE,
    PROMPT_DIR,
)
from revibe.core.paths.global_paths import GLOBAL_ENV_FILE, SESSION_LOG_DIR
from revibe.core.prompts import SystemPrompt
from revibe.core.subagents import AgentType
from revibe.core.tools.base import BaseToolConfig

PROJECT_DOC_FILENAMES = ["AGENTS.md", "REVIBE.md", ".revibe.md"]

SdkMode = Literal["anthropic", "openai", "oai-response"]


def _read_fifo_path(path_str: str) -> str | None:
    """Read credential from a FIFO (named pipe) path for secure credential management.

    FIFO paths allow credentials to be provided on-demand by a credential manager,
    avoiding persistent storage of secrets on disk.
    """
    from pathlib import Path
    import stat

    path = Path(path_str).expanduser()
    if not path.exists():
        return None
    try:
        mode = path.stat().st_mode
        if stat.S_ISFIFO(mode):
            with path.open("r") as f:
                return f.read().strip()
    except OSError:
        pass
    return None


def load_api_keys_from_env() -> None:
    """Load API keys from .env file, with FIFO path support for secure credentials."""
    if GLOBAL_ENV_FILE.path.is_file():
        env_vars = dotenv_values(GLOBAL_ENV_FILE.path)
        for key, value in env_vars.items():
            if not value:
                continue
            if value.startswith("fifo:"):
                fifo_content = _read_fifo_path(value[5:])
                if fifo_content:
                    os.environ.setdefault(key, fifo_content)
            else:
                os.environ.setdefault(key, value)


class MissingAPIKeyError(RuntimeError):
    def __init__(self, env_key: str, provider_name: str) -> None:
        super().__init__(
            f"Missing {env_key} environment variable for {provider_name} provider"
        )
        self.env_key = env_key
        self.provider_name = provider_name


class MissingPromptFileError(RuntimeError):
    def __init__(self, system_prompt_id: str, prompt_dir: str) -> None:
        super().__init__(
            f"Invalid system_prompt_id value: '{system_prompt_id}'. "
            f"Must be one of the available prompts ({', '.join(f'{p.name.lower()}' for p in SystemPrompt)}), "
            f"or correspond to a .md file in {prompt_dir}"
        )
        self.system_prompt_id = system_prompt_id
        self.prompt_dir = prompt_dir


class TomlFileSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self.toml_data = self._load_toml()

    def _load_toml(self) -> dict[str, Any]:
        file = CONFIG_FILE.path
        try:
            with file.open("rb") as f:
                return tomllib.load(f)
        except FileNotFoundError:
            return {}
        except tomllib.TOMLDecodeError as e:
            raise RuntimeError(f"Invalid TOML in {file}: {e}") from e
        except OSError as e:
            raise RuntimeError(f"Cannot read {file}: {e}") from e

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return self.toml_data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return self.toml_data


class ProjectContextConfig(BaseSettings):
    max_chars: int = 40_000
    default_commit_count: int = 5
    max_doc_bytes: int = 32 * 1024
    truncation_buffer: int = 1_000
    max_depth: int = 3
    max_files: int = 1000
    max_dirs_per_level: int = 20
    timeout_seconds: float = 2.0


class SessionLoggingConfig(BaseSettings):
    save_dir: str = ""
    session_prefix: str = "session"
    enabled: bool = True

    @field_validator("save_dir", mode="before")
    @classmethod
    def set_default_save_dir(cls, v: str) -> str:
        if not v:
            return str(SESSION_LOG_DIR.path)
        return v

    @field_validator("save_dir", mode="after")
    @classmethod
    def expand_save_dir(cls, v: str) -> str:
        return str(Path(v).expanduser().resolve())


class ToolFormat(StrEnum):
    """Tool calling format for LLM interactions.

    NATIVE: Use the API's native function/tool calling mechanism
    XML: Use XML-based tool calling embedded in prompts (for models without native support)
    """

    NATIVE = auto()
    XML = auto()


class ProviderConfig(BaseModel):
    name: str
    api_base: str
    api_key_env_var: str = ""
    api_style: str = "openai"
    sdk_mode: SdkMode = "openai"
    custom_header: dict[str, str] = Field(default_factory=dict)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    display_name: str = ""
    family: str = ""
    fetch_models: bool = False
    models_endpoint: str = ""
    openai_compat: dict[str, Any] = Field(default_factory=dict)
    anthropic_compat: dict[str, Any] = Field(default_factory=dict)
    responses_compat: dict[str, Any] = Field(default_factory=dict)


type ProviderConfigType = ProviderConfig
PROVIDER_CONFIG_ADAPTER = TypeAdapter(ProviderConfig)


class _MCPBase(BaseModel):
    name: str = Field(description="Short alias used to prefix tool names")
    prompt: str | None = Field(
        default=None, description="Optional usage hint appended to tool descriptions"
    )

    @field_validator("name", mode="after")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", v)
        normalized = normalized.strip("_-")
        return normalized[:256]


class _MCPHttpFields(BaseModel):
    url: str = Field(description="Base URL of the MCP HTTP server")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Additional HTTP headers when using 'http' transport (e.g., Authorization or X-API-Key)."
        ),
    )
    api_key_env: str = Field(
        default="",
        description=(
            "Environment variable name containing an API token to send for HTTP transport."
        ),
    )
    api_key_header: str = Field(
        default="Authorization",
        description=(
            "HTTP header name to carry the token when 'api_key_env' is set (e.g., 'Authorization' or 'X-API-Key')."
        ),
    )
    api_key_format: str = Field(
        default="Bearer {token}",
        description=(
            "Format string for the header value when 'api_key_env' is set. Use '{token}' placeholder."
        ),
    )

    def http_headers(self) -> dict[str, str]:
        hdrs = dict(self.headers or {})
        env_var = (self.api_key_env or "").strip()
        if env_var and (token := os.getenv(env_var)):
            target = (self.api_key_header or "").strip() or "Authorization"
            if not any(h.lower() == target.lower() for h in hdrs):
                try:
                    value = (self.api_key_format or "{token}").format(token=token)
                except Exception:
                    value = token
                hdrs[target] = value
        return hdrs


class MCPHttp(_MCPBase, _MCPHttpFields):
    transport: Literal["http"]


class MCPStreamableHttp(_MCPBase, _MCPHttpFields):
    transport: Literal["streamable-http"]


class MCPStdio(_MCPBase):
    transport: Literal["stdio"]
    command: str | list[str]
    args: list[str] = Field(default_factory=list)

    def argv(self) -> list[str]:
        base = (
            shlex.split(self.command)
            if isinstance(self.command, str)
            else list(self.command or [])
        )
        return [*base, *self.args] if self.args else base


MCPServer = Annotated[
    MCPHttp | MCPStreamableHttp | MCPStdio, Field(discriminator="transport")
]


DEFAULT_PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        name="openai",
        display_name="OpenAI",
        api_base="https://api.openai.com/v1",
        api_key_env_var="OPENAI_API_KEY",
        sdk_mode="openai",
    ),
    ProviderConfig(
        name="deepseek",
        display_name="DeepSeek",
        api_base="https://api.deepseek.com/v1",
        api_key_env_var="DEEPSEEK_API_KEY",
        sdk_mode="openai",
    ),
    ProviderConfig(
        name="openrouter",
        display_name="OpenRouter",
        api_base="https://openrouter.ai/api/v1",
        api_key_env_var="OPENROUTER_API_KEY",
        sdk_mode="openai",
    ),
    ProviderConfig(
        name="opencode",
        display_name="OpenCode",
        api_base="https://opencode.ai/zen/v1",
        api_key_env_var="OPENCODE_API_KEY",
        sdk_mode="openai",
    ),
    ProviderConfig(
        name="ollama",
        display_name="Ollama",
        api_base="http://127.0.0.1:11434/v1",
        api_key_env_var="",
        sdk_mode="openai",
    ),
]


class VibeConfig(BaseSettings):
    active_model: str = "devstral-2"
    active_provider: str | None = None
    agent_type: AgentType = AgentType.AGENT
    textual_theme: str = "terminal"
    vim_keybindings: bool = False
    disable_welcome_banner_animation: bool = False
    displayed_workdir: str = ""
    auto_compact_threshold: int = 200_000
    context_warnings: bool = False
    instructions: str = ""
    workdir: Path | None = Field(default=None, exclude=True)
    system_prompt_id: str = "cli"
    include_commit_signature: bool = True
    include_model_info: bool = True
    include_project_context: bool = True
    include_prompt_detail: bool = True
    enable_update_checks: bool = True
    api_timeout: float = 720.0
    providers: list[ProviderConfig] = Field(
        default_factory=lambda: list(DEFAULT_PROVIDERS)
    )
    models: list[ModelConfig] = Field(default_factory=get_available_models)

    project_context: ProjectContextConfig = Field(default_factory=ProjectContextConfig)
    session_logging: SessionLoggingConfig = Field(default_factory=SessionLoggingConfig)
    tools: dict[str, BaseToolConfig] = Field(default_factory=dict)
    tool_paths: list[Path] = Field(
        default_factory=list,
        description=(
            "Additional directories to search for custom tools. "
            "Each path may be absolute or relative to the current working directory."
        ),
    )

    mcp_servers: list[MCPServer] = Field(
        default_factory=list, description="Preferred MCP server configuration entries."
    )

    enabled_tools: list[str] = Field(
        default_factory=list,
        description=(
            "An explicit list of tool names/patterns to enable. If set, only these"
            " tools will be active. Supports exact names, glob patterns (e.g.,"
            " 'serena_*'), and regex with 're:' prefix or regex-like patterns (e.g.,"
            " 're:^serena_.*' or 'serena.*')."
        ),
    )
    disabled_tools: list[str] = Field(
        default_factory=list,
        description=(
            "A list of tool names/patterns to disable. Ignored if 'enabled_tools'"
            " is set. Supports exact names, glob patterns (e.g., 'bash*'), and"
            " regex with 're:' prefix or regex-like patterns."
        ),
    )

    skill_paths: list[Path] = Field(
        default_factory=list,
        description=(
            "Additional directories to search for skills. "
            "Each path may be absolute or relative to the current working directory."
        ),
    )

    tool_format: ToolFormat = Field(
        default=ToolFormat.NATIVE,
        description=(
            "Tool calling format: 'native' uses the API's function calling mechanism, "
            "'xml' embeds tool definitions in the system prompt for models without native support."
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="REVIBE_", case_sensitive=False, extra="ignore"
    )

    @property
    def effective_workdir(self) -> Path:
        return self.workdir if self.workdir is not None else Path.cwd()

    @property
    def effective_tool_format(self) -> ToolFormat:
        """Get the effective tool format, auto-switching to XML for antigravity models.

        Antigravity backend only supports XML format, so we auto-select it when
        using an antigravity model to ensure compatibility.
        """
        try:
            active_model = self.get_active_model()
            if active_model.provider == "antigravity":
                return ToolFormat.XML
        except ValueError:
            pass
        return self.tool_format

    @property
    def system_prompt(self) -> str:
        try:
            return SystemPrompt[self.system_prompt_id.upper()].read()
        except KeyError:
            pass

        custom_sp_path = (PROMPT_DIR.path / self.system_prompt_id).with_suffix(".md")
        if not custom_sp_path.is_file():
            raise MissingPromptFileError(self.system_prompt_id, str(PROMPT_DIR.path))
        return custom_sp_path.read_text()

    def get_active_model(self) -> ModelConfig:
        """Get the active model configuration.

        Supports intelligent model selection:
        - Explicit provider<>alias syntax: "provider<>alias" (e.g., "kilocode<>x-ai/grok-code-fast-1")
        - Provider-aware selection: if active_provider is set, prefer models from that provider
        - Fallback: first matching alias if no provider context

        Note: We use '<>' as the separator instead of '/' because some model names
        (like 'x-ai/grok-code-fast-1') contain '/' in their actual name.
        """
        active = self.active_model

        # Check for explicit provider<>alias syntax
        if "<>" in active:
            provider_name, alias = active.split("<>", 1)
            for model in self.models:
                m_alias = (
                    model.alias
                    if isinstance(model, ModelConfig)
                    else model.get("alias")
                )
                m_provider = (
                    model.provider
                    if isinstance(model, ModelConfig)
                    else model.get("provider")
                )
                if m_alias == alias and m_provider == provider_name:
                    return (
                        model
                        if isinstance(model, ModelConfig)
                        else ModelConfig.model_validate(model)
                    )
            raise ValueError(
                f"Model '{alias}' not found for provider '{provider_name}'."
            )

        # If active_provider is set, prefer models from that provider
        if self.active_provider:
            for model in self.models:
                m_alias = (
                    model.alias
                    if isinstance(model, ModelConfig)
                    else model.get("alias")
                )
                m_provider = (
                    model.provider
                    if isinstance(model, ModelConfig)
                    else model.get("provider")
                )
                if m_alias == active and m_provider == self.active_provider:
                    return (
                        model
                        if isinstance(model, ModelConfig)
                        else ModelConfig.model_validate(model)
                    )

        # Fallback: first matching alias
        for model in self.models:
            m_alias = (
                model.alias if isinstance(model, ModelConfig) else model.get("alias")
            )
            if m_alias == active:
                return (
                    model
                    if isinstance(model, ModelConfig)
                    else ModelConfig.model_validate(model)
                )

        raise ValueError(
            f"Active model '{self.active_model}' not found in configuration."
        )

    def get_provider_for_model(self, model: ModelConfig) -> ProviderConfig:
        # Merge DEFAULT_PROVIDERS with configured providers
        providers_map: dict[str, Any] = {}
        for p in DEFAULT_PROVIDERS:
            providers_map[p.name] = p
        for p in self.providers:
            p_name = p.name if not isinstance(p, dict) else p.get("name")
            if p_name is not None:
                providers_map[p_name] = p

        m_provider = (
            model.provider if isinstance(model, ModelConfig) else model.get("provider")
        )
        provider = providers_map.get(m_provider)

        if provider is None:
            m_name = getattr(model, "name", None) or (
                model.get("name") if isinstance(model, dict) else "unknown"
            )
            raise ValueError(
                f"Provider '{m_provider}' for model '{m_name}' not found in configuration."
            )

        return (
            provider
            if not isinstance(provider, dict)
            else PROVIDER_CONFIG_ADAPTER.validate_python(provider)
        )

    def get_provider_tuples(self) -> list[tuple[str, str | None]]:
        """Get provider info as (name, api_key) tuples for dynamic model fetching.

        Returns:
            List of tuples suitable for fetch_all_provider_models.
        """
        import os

        providers_map: dict[str, Any] = {}
        for p in DEFAULT_PROVIDERS:
            providers_map[p.name] = p
        for p in self.providers:
            p_name = p.name if not isinstance(p, dict) else p.get("name")
            if p_name is not None:
                providers_map[p_name] = p

        result: list[tuple[str, str | None]] = []
        for name, provider in providers_map.items():
            api_key_env = getattr(provider, "api_key_env_var", None) or (
                provider.get("api_key_env_var") if isinstance(provider, dict) else None
            )
            api_key = os.getenv(api_key_env) if api_key_env else None
            result.append((name, api_key))
        return result

    async def refresh_dynamic_models(self) -> list[ModelConfig]:
        """Refresh models by fetching from providers that support dynamic fetching.

        Returns:
            Updated list of models including dynamically fetched ones.
        """
        from revibe.core.model_sources import get_models_with_dynamic_fetch_async

        provider_tuples = self.get_provider_tuples()
        fetched_models = await get_models_with_dynamic_fetch_async(provider_tuples)

        existing_keys = {(m.provider, m.alias) for m in self.models}
        new_models = [
            m for m in fetched_models if (m.provider, m.alias) not in existing_keys
        ]
        if new_models:
            self.models.extend(new_models)

        return self.models

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define the priority of settings sources.

        Note: dotenv_settings is intentionally excluded. API keys and other
        non-config environment variables are stored in .env but loaded manually
        into os.environ for use by providers. Only REVIBE_* prefixed environment
        variables (via env_settings) and TOML config are used for Pydantic settings.
        """
        return (
            init_settings,
            env_settings,
            TomlFileSettingsSource(settings_cls),
            file_secret_settings,
        )

    @model_validator(mode="after")
    def _check_api_key(self) -> VibeConfig:
        try:
            # If we have active_provider, use that instead of trying to get provider from model
            if self.active_provider:
                # Find the provider by name
                provider = None
                for p in self.providers:
                    if p.name == self.active_provider:
                        provider = p
                        break

                if (
                    provider
                    and provider.api_key_env_var
                    and not os.getenv(provider.api_key_env_var)
                ):
                    raise MissingAPIKeyError(provider.api_key_env_var, provider.name)
            else:
                # Fallback to model-based lookup for compatibility
                active_model = self.get_active_model()
                provider = self.get_provider_for_model(active_model)
                api_key_env = provider.api_key_env_var
                if api_key_env and not os.getenv(api_key_env):
                    raise MissingAPIKeyError(api_key_env, provider.name)
        except (ValueError, MissingAPIKeyError):
            # Re-raise MissingAPIKeyError, pass ValueError for missing models
            if isinstance(sys.exc_info()[1], MissingAPIKeyError):
                raise
        return self

    @field_validator("tool_paths", mode="before")
    @classmethod
    def _expand_tool_paths(cls, v: Any) -> list[Path]:
        if not v:
            return []
        return [Path(p).expanduser().resolve() for p in v]

    @field_validator("skill_paths", mode="before")
    @classmethod
    def _expand_skill_paths(cls, v: Any) -> list[Path]:
        if not v:
            return []
        return [Path(p).expanduser().resolve() for p in v]

    @field_validator("models", mode="before")
    @classmethod
    def _validate_models(cls, v: Any) -> list[ModelConfig]:
        if not isinstance(v, list):
            return get_available_models()
        return [ModelConfig.model_validate(item) for item in v]

    @field_validator("tools", mode="before")
    @classmethod
    def _normalize_tool_configs(cls, v: Any) -> dict[str, BaseToolConfig]:
        if not isinstance(v, dict):
            return {}

        normalized: dict[str, BaseToolConfig] = {}
        for tool_name, tool_config in v.items():
            if isinstance(tool_config, BaseToolConfig):
                normalized[tool_name] = tool_config
            elif isinstance(tool_config, dict):
                normalized[tool_name] = BaseToolConfig.model_validate(tool_config)
            else:
                normalized[tool_name] = BaseToolConfig()

        return normalized

    @model_validator(mode="after")
    def _validate_model_uniqueness(self) -> VibeConfig:
        provider_aliases: dict[str, set[str]] = {}
        for model in self.models:
            if model.provider not in provider_aliases:
                provider_aliases[model.provider] = set()
            if model.alias in provider_aliases[model.provider]:
                raise ValueError(
                    f"Duplicate model alias found for provider '{model.provider}': '{model.alias}'. Aliases must be unique within each provider."
                )
            provider_aliases[model.provider].add(model.alias)
        return self

    @model_validator(mode="after")
    def _merge_default_models(self) -> VibeConfig:
        available_models = get_available_models()

        existing_keys = {(m.provider, m.name) for m in self.models}
        for m in available_models:
            if (m.provider, m.name) not in existing_keys:
                self.models.append(m)
        return self

    @model_validator(mode="after")
    def _check_system_prompt(self) -> VibeConfig:
        _ = self.system_prompt
        return self

    @classmethod
    def save_updates(cls, updates: dict[str, Any]) -> None:
        CONFIG_DIR.path.mkdir(parents=True, exist_ok=True)
        current_config = TomlFileSettingsSource(cls).toml_data

        def deep_merge(target: dict, source: dict) -> None:
            for key, value in source.items():
                if (
                    key in target
                    and isinstance(target.get(key), dict)
                    and isinstance(value, dict)
                ):
                    deep_merge(target[key], value)
                elif (
                    key in target
                    and isinstance(target.get(key), list)
                    and isinstance(value, list)
                ):
                    if key in {"providers", "models"}:
                        target[key] = value
                    else:
                        target[key] = list(set(value + target[key]))
                else:
                    target[key] = value

        deep_merge(current_config, updates)
        cls.dump_config(
            to_jsonable_python(current_config, exclude_none=True, fallback=str)
        )

    @classmethod
    def dump_config(cls, config: dict[str, Any]) -> None:
        with CONFIG_FILE.path.open("wb") as f:
            tomli_w.dump(config, f)

    @classmethod
    def _get_agent_config(cls, agent: str | None) -> dict[str, Any] | None:
        if agent is None:
            return None

        agent_config_path = (AGENT_DIR.path / agent).with_suffix(".toml")
        try:
            return tomllib.load(agent_config_path.open("rb"))
        except FileNotFoundError:
            raise ValueError(
                f"Config '{agent}.toml' for agent not found in {AGENT_DIR.path}"
            )

    @classmethod
    def _migrate(cls) -> None:
        pass

    @classmethod
    def load(cls, agent: str | None = None, **overrides: Any) -> VibeConfig:
        cls._migrate()
        agent_config = cls._get_agent_config(agent)
        init_data = {**(agent_config or {}), **overrides}
        return cls(**init_data)

    @classmethod
    def create_default(cls) -> dict[str, Any]:
        try:
            config = cls()
        except MissingAPIKeyError:
            config = cls.model_construct()

        config_dict = config.model_dump(mode="json", exclude_none=True)

        from revibe.core.tools.manager import ToolManager

        tool_defaults = ToolManager.discover_tool_defaults()
        if tool_defaults:
            config_dict["tools"] = tool_defaults

        return config_dict
