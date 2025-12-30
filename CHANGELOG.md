# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-12-30

### Added

- Support for XML-based tool calling via `--tool-format xml` flag.
- XML-specific prompts for all built-in tools (`bash`, `grep`, `read_file`, `write_file`, `search_replace`, `todo`).
- `XMLToolFormatHandler` for robust parsing of XML tool calls and generation of XML tool results.
- `supported_formats` field in `ModelConfig` and backend implementations to manage compatibility.
- Dynamic tool prompt resolution in `BaseTool` allowing automatic fallback to standard prompts if XML version is missing.
- First public release of ReVibe with all core functionality.
- New models added to Hugging Face provider.
- Animated "ReVibe" text logo in setup completion screen with gradient colors.
- Provider help URLs for all API key requiring providers (Hugging Face, Cerebras).

### Changed

- ReVibe configuration and data now saved in `.revibe` directory (migrated from `.vibe`).
- Setup TUI improvements:
  - Skip API key input screen for providers that don't require API keys (ollama, llamacpp, qwencode)
  - Display setup completion screen with "Press Enter to exit" instruction
  - Hide configuration documentation links from completion screen
  - Show usage message "Use 'revibe' to start using ReVibe" after setup completion
- TUI Visual & Functional Enhancements:
  - Added `redact_xml_tool_calls(text)` utility in `revibe/core/utils.py` to remove raw `<tool_call>...<tool_call>` blocks from assistant output stream
  - Refactored `StreamingMessageBase` in `revibe/cli/textual_ui/widgets/messages.py` to track `_displayed_content` for smart UI updates
  - Enhanced premium tool summaries in chat history:
    * Find now shows as `Find (pattern)` instead of `grep: 'pattern'`
    * Bash now shows as `Bash (command)` instead of raw command string
    * Read File now shows as `Read (filename)` with cleaner summary
    * Write File now shows as `Write (filename)`
    * Search & Replace now shows as `Patch (filename)`
  - Applied redaction logic to `ReasoningMessage` in `revibe/cli/textual_ui/widgets/messages.py` to hide raw XML in reasoning blocks
- Model alias validation now allows same aliases for different providers while maintaining uniqueness within each provider.

### Fixed

- Duplicate model alias found in `VibeConfig` when multiple providers used same alias.
- AttributeError in `revibe --setup` caused by models loaded as dicts instead of ModelConfig objects.
- Type errors in config loading and provider handling.
- Various TUI bug fixes and stability improvements.
- Case-sensitivity issue when specifying tool format via CLI.
- Type errors in backends when implementing `BackendLike` protocol (added missing `supported_formats`).
- Typo in `XMLToolFormatHandler` name property.

## [0.1.5.1] - 2025-12-30

### Added

- Support for XML-based tool calling via `--tool-format xml` flag.
- XML-specific prompts for all built-in tools (`bash`, `grep`, `read_file`, `write_file`, `search_replace`, `todo`).
- `XMLToolFormatHandler` for robust parsing of XML tool calls and generation of XML tool results.
- `supported_formats` field in `ModelConfig` and backend implementations to manage compatibility.
- Dynamic tool prompt resolution in `BaseTool` allowing automatic fallback to standard prompts if XML version is missing.

### Fixed

- Case-sensitivity issue when specifying tool format via CLI.
- Type errors in backends when implementing `BackendLike` protocol (added missing `supported_formats`).
- Typo in `XMLToolFormatHandler` name property.

## [0.1.5.0] - 2025-12-30

### Added

- Support for XML-based tool calling via `--tool-format xml` flag.
- XML-specific prompts for all built-in tools (`bash`, `grep`, `read_file`, `write_file`, `search_replace`, `todo`).
- `XMLToolFormatHandler` for robust parsing of XML tool calls and generation of XML tool results.
- `supported_formats` field in `ModelConfig` and backend implementations to manage compatibility.
- Dynamic tool prompt resolution in `BaseTool` allowing automatic fallback to standard prompts if XML version is missing.

### Fixed

- Case-sensitivity issue when specifying tool format via CLI.
- Type errors in backends when implementing `BackendLike` protocol (added missing `supported_formats`).
- Typo in `XMLToolFormatHandler` name property.

## [0.1.4.0] - 2025-12-25

### Added

- Dynamic version display from pyproject.toml
- REVIBE text logo in welcome banner with animated colors
- New provider support: Hugging Face, Groq, Ollama, Cerebras, llama.cpp, and Qwen Code
- Added high-performance models: Llama 3.3 70B, Qwen 3 (235B & 32B), Z.ai GLM 4.6, GPT-OSS 120B (via Cerebras), and Qwen3 Coder (Plus & Flash)
- Unified HTTP client using httpx package across all backends
- Implemented Qwen OAuth authentication mirroring Roo-Code for seamless integration with Qwen CLI credentials

### Changed

- Replace block logo with "REVIBE" text in welcome banner
- Make token display dynamic based on model context instead of hardcoded values
- Refactor LLM backend: Unified OpenAI-compatible providers to wrap `OpenAIBackend` and removed `GenericBackend`

### Fixed

- Fix hardcoded "200k tokens" display to show actual model context limit
- Fix continuation message to use "revibe" instead of "vibe"
- Fix welcome banner animation rendering with new REVIBE logo
- Update model configs with explicit context and max_output values
- Fix keyboard navigation bugs in model and provider selectors
- Fix Qwen OAuth token refresh failure caused by Alibaba Cloud WAF (added User-Agent support)
- Correct Qwen API endpoint resolution to prioritize OAuth portal (`portal.qwen.ai`) when using credentials
- Fix `list index out of range` crash in Qwen streaming loop when receiving empty choices chunks
- Remove conflicting default `api_base` for Qwen provider to allow proper endpoint auto-detection
- Enhance Qwen backend robustness with improved SSE parsing and graceful JSON error handling

## [0.1.3.0] - 2025-12-23

### Added

- agentskills.io support
- Reasoning support
- Native terminal theme support
- Issue templates for bug reports and feature requests
- Auto update zed extension on release creation

### Changed

- Improve ToolUI system with better rendering and organization
- Use pinned actions in CI workflows
- Remove 100k -> 200k tokens config migration

### Fixed

- Fix `-p` mode to auto-approve tool calls
- Fix crash when switching mode
- Fix some cases where clipboard copy didn't work

## [0.1.2.2] - 2025-12-22

### Fixed

- Remove dead code
- Fix artefacts automatically attached to the release
- Refactor agent post streaming

## [0.1.2.1] - 2025-12-18

### Fixed

- Improve error message when running in home dir
- Do not show trusted folder workflow in home dir

## [0.1.2.0] - 2025-12-18

### Added

- Modular mode system
- Trusted folder mechanism for local .vibe directories
- Document public setup for vibe-acp in zed, jetbrains and neovim
- `--version` flag

### Changed

- Improve UI based on feedback
- Remove unnecessary logging and flushing for better performance
- Update textual
- Update nix flake
- Automate binary attachment to GitHub releases

### Fixed

- Prevent segmentation fault on exit by shutting down thread pools
- Fix extra spacing with assistant message

## [0.1.1.3] - 2025-12-12

### Added

- Add more copy_to_clipboard methods to support all cases
- Add bindings to scroll chat history

### Changed

- Relax config to accept extra inputs
- Remove useless stats from assistant events
- Improve scroll actions while streaming
- Do not check for updates more than once a day
- Use PyPI in update notifier

### Fixed

- Fix tool permission handling for "allow always" option in ACP
- Fix security issue: prevent command injection in GitHub Action prompt handling
- Fix issues with vLLM

## [0.1.1.2] - 2025-12-11

### Changed

- add `terminal-auth` auth method to ACP agent only if the client supports it
- fix `user-agent` header when using Mistral backend, using SDK hook

## [0.1.1.1] - 2025-12-10

### Changed

- added `include_commit_signature` in `config.toml` to disable signing commits

## [0.1.1.0] - 2025-12-10

### Fixed

- fixed crash in some rare instances when copy-pasting

### Changed

- improved context length from 100k to 200k

## [0.1.0.6] - 2025-12-10

### Fixed

- add missing steps in bump_version script
- move `pytest-xdist` to dev dependencies
- take into account config for bash timeout

### Changed

- improve textual performance
- improve README:
  - improve windows installation instructions
  - update default system prompt reference
  - document MCP tool permission configuration

## [0.1.0.5] - 2025-12-10

### Fixed

- Fix streaming with OpenAI adapter

## [0.1.0.4] - 2025-12-09

### Changed

- Rename agent in distribution/zed/extension.toml to mistral-vibe

### Fixed

- Fix icon and description in distribution/zed/extension.toml

### Removed

- Remove .envrc file

## [0.1.0.3] - 2025-12-09

### Added

- Add LICENCE symlink in distribution/zed for compatibility with zed extension release process

## [0.1.0.2] - 2025-12-09

### Fixed

- Fix setup flow for vibe-acp builds

## [0.1.0.1] - 2025-12-09

### Fixed

- Fix update notification

## [0.1.0.0] - 2025-12-09

### Added

- Initial release
