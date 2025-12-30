<div align="center">

# 🌊 ReVibe

**Multi-provider CLI coding agent with a clean, minimal interface.**

[![PyPI Version](https://img.shields.io/pypi/v/revibe?style=flat-square&color=blue)](https://pypi.org/project/revibe)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](https://www.python.org/downloads/release/python-3120/)
[![License](https://img.shields.io/github/license/OEvortex/revibe?style=flat-square)](https://github.com/OEvortex/revibe/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

[Features](#-key-features) • [Installation](#-installation) • [Setup](#️-setup) • [Usage](#-usage) • [Configuration](#-configuration)

</div>

---

ReVibe is a high-performance command-line coding assistant powered by a wide range of Large Language Models. It provides a conversational interface to your codebase, enabling you to explore, refactor, and build complex features through natural language and a robust set of autonomous tools.

## ✨ Key Features

- 🚀 **Multi-Provider Ecosystem**: Support for OpenAI, Mistral, Qwen, Cerebras, Groq, HuggingFace, Ollama, and LlamaCPP.
- 🔄 **Hot-Swapping**: Switch providers and models instantly mid-session with `/provider` and `/model`.
- 🎨 **Modern TUI**: A polished, minimal interface inspired by leading AI coding tools for zero distraction.
- 🛠️ **Autonomous Toolset**: File system operations, advanced code search, git integration, and command execution.
- 🛡️ **Safe by Design**: Granular tool permissions with an interactive approval system.
- 🧩 **MCP Support**: Extend capabilities with Model Context Protocol servers.

## 🚀 Installation

### Using uv (Recommended)
```bash
uv tool install revibe
```

### Using pip
```bash
pip install revibe
```

### From Source
```bash
git clone https://github.com/OEvortex/revibe.git
cd revibe
uv sync --all-extras
uv run revibe
```

## 🛠️ Setup

### Quick Start
1. Navigate to your project directory.
2. Run `revibe` to start the onboarding process.
3. ReVibe will automatically create your configuration at `~/.revibe/config.toml` and prompt for necessary API keys.

### 🔑 Authentication & Environment Variables

ReVibe manages API keys in `~/.revibe/.env`. You can also set them directly in your shell.

| Provider | Environment Variable | Auth Method |
| :--- | :--- | :--- |
| **OpenAI** | `OPENAI_API_KEY` | API Key |
| **Mistral** | `MISTRAL_API_KEY` | API Key |
| **Groq** | `GROQ_API_KEY` | API Key |
| **Cerebras** | `CEREBRAS_API_KEY` | API Key |
| **Hugging Face** | `HUGGINGFACE_API_KEY` | API Key |
| **Qwen** | *None (Default)* | **OAuth** (via `/auth` in qwen CLI) |
| **Ollama** | *Not Required* | Local (Default: `http://localhost:11434`) |
| **Llama.cpp** | *Not Required* | Local (Default: `http://localhost:8080`) |

> [!TIP]
> For Qwen, install qwen-code if not installed: `npm install -g @qwen-code/qwen-code@latest`, then use `/auth` in qwen to authenticate, then you can close qwen and use qwencode provider in ReVibe.

## 📖 Usage

### 💬 Interactive Mode
Simply run `revibe` to enter the interactive TUI.

*   **Multi-line Input**: Use `Ctrl+J` or `Shift+Enter` for newlines.
*   **File Referencing**: Type `@` to trigger fuzzy path autocompletion.
*   **Direct Commands**: Prefix with `!` to execute shell commands (e.g., `!npm test`).

### 🤖 Programmatic Mode
Execute single prompts directly from your shell:
```bash
revibe --prompt "Explain the logic in @revibe/core/agent.py"
```

### ⚡ Slash Commands
| Command | Action |
| :--- | :--- |
| `/provider` | Switch the active LLM provider |
| `/model` | Change the model for the current provider |
| `/config` | Open configuration settings |
| `/status` | View session stats and token usage |
| `/clear` | Reset conversation context |
| `/exit` | Terminate the session |

## ⚙️ Configuration

ReVibe uses TOML for configuration. It checks `./.revibe/config.toml` first, then falls back to `~/.revibe/config.toml`.

<details>
<summary><b>Example MCP Configuration</b></summary>

```toml
[[mcp_servers]]
name = "fetch_server"
transport = "stdio"
command = "uvx"
args = ["mcp-server-fetch"]

[[mcp_servers]]
name = "github"
transport = "http"
url = "https://mcp-github-server.com"
api_key_env = "GITHUB_TOKEN"
```
</details>

<details>
<summary><b>Customizing Agent Behavior</b></summary>

You can create specialized agents in `~/.revibe/agents/my_agent.toml`:
```toml
active_model = "gpt-4o"
system_prompt_id = "architect"
disabled_tools = ["bash"]

[tools.read_file]
permission = "always"
```
Launch with `revibe --agent my_agent`.
</details>

## 🖥️ Editor Integration
ReVibe supports the **Agent Client Protocol (ACP)**, allowing it to act as a backend for compatible editors like Zed. See [ACP Setup](docs/acp-setup.md) for instructions.

## 📄 License
Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

<div align="center">
Made with ❤️ by the ReVibe Contributors
</div>
