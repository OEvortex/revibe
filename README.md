# ReVibe

[![PyPI Version](https://img.shields.io/pypi/v/revibe)](https://pypi.org/project/revibe)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/release/python-3120/)
[![License](https://img.shields.io/github/license/OEvortex/revibe)](https://github.com/OEvortex/revibe/blob/main/LICENSE)

**Multi-provider CLI coding agent with a clean, minimal interface.**

ReVibe is a command-line coding assistant powered by multiple language model providers. It provides a conversational interface to your codebase, allowing you to use natural language to explore, modify, and interact with your projects through a powerful set of tools.

### ✨ Key Features

- **Multi-Provider Support**: OpenAI, Anthropic, Mistral, HuggingFace, Groq, and local models
- **Runtime Provider Switching**: Use `/provider` and `/model` commands to switch providers on the fly
- **Clean Minimal TUI**: Inspired by Codex CLI and Claude Code for distraction-free coding
- **Powerful Toolset**: File manipulation, code search, version control, and command execution

> [!NOTE]
> ReVibe works on Windows, macOS, and Linux.

## Installation

### Using uv (recommended)

```bash
uv tool install revibe
```

### Using pip

```bash
pip install revibe
```

## Quick Start

1. Navigate to your project directory:

   ```bash
   cd /path/to/your/project
   ```

2. Run ReVibe:

   ```bash
   revibe
   ```

3. On first run, ReVibe will:
   - Create a default configuration at `~/.vibe/config.toml`
   - Prompt you to enter your API key
   - Save your API key to `~/.vibe/.env`

4. Start coding with natural language!

## Features

- **Interactive Chat**: Conversational AI that understands your requests and breaks down complex tasks
- **Powerful Toolset**: File manipulation, code search, version control, and command execution
- **Project-Aware Context**: Automatic project structure and Git status scanning
- **Runtime Provider/Model Switching**: Use `/provider` and `/model` commands
- **Highly Configurable**: Customize via `config.toml`
- **Safety First**: Tool execution approval system

## Usage

### Interactive Mode

Run `revibe` to start the interactive session.

- **Multi-line Input**: `Ctrl+J` or `Shift+Enter`
- **File Paths**: Use `@` for autocompletion (e.g., `@src/main.py`)
- **Shell Commands**: Prefix with `!` (e.g., `!ls -l`)
- **Provider Switching**: Use `/provider` to switch providers
- **Model Selection**: Use `/model` to select models

```bash
revibe "Refactor the main function to be more modular."
```

### Programmatic Mode

Run non-interactively with `--prompt`:

```bash
revibe --prompt "Refactor the main function to be more modular."
```

### Slash Commands

Use slash commands for configuration and control:

- `/provider` - Switch between providers
- `/model` - Select a model
- `/config` - Edit settings
- `/help` - Show help
- `/clear` - Clear history
- `/status` - Show agent statistics

## Configuration

ReVibe is configured via `config.toml`. It looks for this file first in `./.vibe/config.toml` and then falls back to `~/.vibe/config.toml`.

### API Key Configuration

ReVibe supports multiple ways to configure API keys:

1. **Interactive Setup**: On first run, ReVibe will prompt for API keys

2. **Environment Variables**:
   ```bash
   export OPENAI_API_KEY="your_key"
   export ANTHROPIC_API_KEY="your_key"
   export MISTRAL_API_KEY="your_key"
   export GROQ_API_KEY="your_key"
   ```

3. **`.env` File** in `~/.vibe/`:
   ```bash
   OPENAI_API_KEY=your_key
   ANTHROPIC_API_KEY=your_key
   ```

### Custom Agent Configurations

Create agent configurations in `~/.vibe/agents/`:

```bash
revibe --agent my_custom_agent
```

Example custom agent configuration (`~/.vibe/agents/redteam.toml`):

```toml
# Custom agent configuration for red-teaming
active_model = "devstral-2"
system_prompt_id = "redteam"

# Disable some tools for this agent
disabled_tools = ["search_replace", "write_file"]

# Override tool permissions for this agent
[tools.bash]
permission = "always"

[tools.read_file]
permission = "always"
```

Note: this implies that you have setup a redteam prompt names `~/.vibe/prompts/redteam.md`

### MCP Server Configuration

You can configure MCP (Model Context Protocol) servers to extend ReVibe's capabilities:

```toml
# Example MCP server configurations
[[mcp_servers]]
name = "my_http_server"
transport = "http"
url = "http://localhost:8000"
headers = { "Authorization" = "Bearer my_token" }
api_key_env = "MY_API_KEY_ENV_VAR"
api_key_header = "Authorization"
api_key_format = "Bearer {token}"

[[mcp_servers]]
name = "my_streamable_server"
transport = "streamable-http"
url = "http://localhost:8001"
headers = { "X-API-Key" = "my_api_key" }

[[mcp_servers]]
name = "fetch_server"
transport = "stdio"
command = "uvx"
args = ["mcp-server-fetch"]
```

Supported transports:

- `http`: Standard HTTP transport
- `streamable-http`: HTTP transport with streaming support
- `stdio`: Standard input/output transport (for local processes)

Key fields:

- `name`: A short alias for the server (used in tool names)
- `transport`: The transport type
- `url`: Base URL for HTTP transports
- `headers`: Additional HTTP headers
- `api_key_env`: Environment variable containing the API key
- `command`: Command to run for stdio transport
- `args`: Additional arguments for stdio transport

MCP tools are named using the pattern `{server_name}_{tool_name}` and can be configured with permissions like built-in tools:

```toml
# Configure permissions for specific MCP tools
[tools.fetch_server_get]
permission = "always"

[tools.my_http_server_query]
permission = "ask"
```

### Enable/disable tools with patterns

You can control which tools are active using `enabled_tools` and `disabled_tools`.
These fields support exact names, glob patterns, and regular expressions.

Examples:

```toml
# Only enable tools that start with "serena_" (glob)
enabled_tools = ["serena_*"]

# Regex (prefix with re:) — matches full tool name (case-insensitive)
enabled_tools = ["re:^serena_.*$"]

# Heuristic regex support (patterns like `serena.*` are treated as regex)
enabled_tools = ["serena.*"]

# Disable a group with glob; everything else stays enabled
disabled_tools = ["mcp_*", "grep"]
```

Notes:

- MCP tool names use underscores, e.g., `serena_list` not `serena.list`.
- Regex patterns are matched against the full tool name using fullmatch.

### Custom Home Directory

By default, ReVibe stores configuration in `~/.vibe/`. Override with `VIBE_HOME`:

```bash
export VIBE_HOME="/path/to/custom/home"
```

## Editors/IDEs

ReVibe can be used in editors supporting [Agent Client Protocol](https://agentclientprotocol.com/overview/clients). See [ACP Setup](docs/acp-setup.md) for details.

## Resources

- [CHANGELOG](CHANGELOG.md)
- [CONTRIBUTING](CONTRIBUTING.md)

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
