# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-01-01

### Added

- **Enhanced Diff View TUI**: Completely redesigned diff display similar to `git diff` with modern features
  - Created separate `diff.tcss` stylesheet (350 lines) for better organization and maintainability
  - Dual line number columns (old | new) with visual separator like side-by-side diff
  - Syntax highlighting for code content (Python, JavaScript keywords, strings, numbers, comments, operators)
  - Color-coded backgrounds for additions (green `#1d3f1d`) and deletions (red `#3f1d1d`)
  - Visual whitespace indicators (· for spaces, → for tabs) to help debug formatting issues
  - Enhanced hunk headers with blue-tinted backgrounds (`@@ -x,y +a,b @@`)
  - Support for file status indicators (new, deleted, renamed files)
  - Word-level diff highlighting styles for inline changes
  - Removed 85 lines of duplicate CSS from `app.tcss`
- **Simplified Welcome Banner**: Completely redesigned welcome banner for better terminal compatibility
  - Reduced from 405 lines to 65 lines (84% reduction in code)
  - Removed complex animation system with color interpolation
  - Removed border frame drawing logic
  - Now uses responsive `max-height: 40vh` CSS to cap banner at 40% of terminal height
  - Auto-adjusts size based on terminal dimensions using `height: auto`
  - Cleaner, more compact ASCII logo with version, model, and workspace info
  - Simplified TCSS from 120 lines to 20 lines (83% reduction)

### Changed

- **Search/Replace Tool Improvements**: Completely redesigned error messages and tool display for better UX
  - **Tool Description**: Reduced from 360 to 280 characters with clearer, more concise format
  - **Tool Call Display**: Now shows `Editing filename.py` or `Editing filename.py (3 changes)` instead of generic `Patch`
  - **Result Display**: Shows line changes with `✓ Applied 2 changes (+15 lines)` instead of just block count
  - **Error Messages**: Complete visual redesign with Unicode box drawing and emoji indicators
    - Invalid format errors now show expected format in a visual box with common issues listed
    - Search-not-found errors display:
      - Visual search preview with whitespace indicators (· for space, → for tab)
      - Context analysis showing where first line was found with line numbers
      - Fuzzy match with similarity percentage (🟢 95%+, 🟡 90%+, 🟠 <90%)
      - Side-by-side diff showing exact differences between search and file
      - Actionable "How to fix" steps with specific guidance
    - Line markers use Unicode (▶ for matched line, │ for context)
  - **Warnings**: More concise format `⚠ Block 1: Found 3 matches, replacing first only`
  - **Context Display**: Enhanced with better formatting, similarity indicators, and partial match suggestions
- Updated `grok-code` model pricing to free (0.0 input/output) in model configuration

### Fixed

- **OpenCode Backend**: Fixed `'openai'` KeyError when using OpenCode provider
  - Set `api_style = "opencode"` in `OpenCodeProviderConfig` to match registered adapter
  - Removed hardcoded `list_models()` method from OpenCode backend
- Fixed duplicate tick display in Thought reasoning widget by removing redundant icon widget update
- Cleaned up `SpinnerMixin.stop_spinning()` to prevent duplicate completion indicators
- Simplified Thought widget to show only spinner animation without icon for cleaner UI
- Fixed reasoning/thought sections being collapsed by default in TUI - they now expand automatically to show content immediately



## [0.2.1] - 2025-12-31

### Added

- Added multiple OpenRouter provider models to DEFAULT_MODELS, exposing a wide range of external models for easy selection and usage:

  - minimax/minimax-m2.1 (205K context) — $0.30/M input, $1.20/M output
  - z-ai/glm-4.7 (203K context) — $0.40/M input, $1.50/M output
  - google/gemini-3-flash-preview (1.05M context) — $0.50/M input, $3/M output, $1/M audio tokens
  - xiaomi/mimo-v2-flash:free (262K context) — free (0.0 input/output)
  - allenai/olmo-3.1-32b-think:free (66K context) — free (0.0 input/output)
  - nvidia/nemotron-3-nano-30b-a3b:free (262K context) — free (0.0 input/output)
  - nvidia/nemotron-3-nano-30b-a3b (262K context) — $0.06/M input, $0.24/M output
  - openai/gpt-5.2-pro (400K context) — $21/M input, $168/M output
  - openai/gpt-5.2 (400K context) — $1.75/M input, $14/M output
  - mistralai/devstral-2512:free (262K context) — free (0.0 input/output)
  - mistralai/devstral-2512 (262K context) — $0.05/M input, $0.22/M output
  - openai/gpt-5.1-codex-max (400K context) — $1.25/M input, $10/M output
  - deepseek/deepseek-v3.2-speciale (164K context) — $0.27/M input, $0.41/M output
  - anthropic/claude-opus-4.5 (200K context) — $5/M input, $25/M output
  - x-ai/grok-4.1-fast (2M context) — $0.20/M input, $0.50/M output
  - google/gemini-3-pro-preview (1M context) — $2/M input, $12/M output
  - openai/gpt-5.1 / openai/gpt-5.1-codex (400K context) — $1.25/M input, $10/M output
  - openai/gpt-5.1-codex-mini (400K context) — $0.25/M input, $2/M output
  - kwaipilot/kat-coder-pro:free (256K context) — free (0.0 input/output)
  - moonshotai/kimi-k2-thinking (262K context) — $0.40/M input, $1.75/M output
  - minimax/minimax-m2 (197K context) — $0.20/M input, $1/M output
  - anthropic/claude-haiku-4.5 (200K context) — $1/M input, $5/M output
  - z-ai/glm-4.6:exacto (205K context) — $0.44/M input, $1.76/M output
  - anthropic/claude-sonnet-4.5 (1M context) — $3/M input, $15/M output
  - qwen/qwen3-coder-plus (128K context) — $1/M input, $5/M output
  - moonshotai/kimi-k2-0905 (262K context) — $0.39/M input, $1.90/M output
  - x-ai/grok-code-fast-1 (256K context) — $0.20/M input, $1.50/M output

- Free variants were added with explicit 0.0 input/output pricing so they are selectable without billing impact.
- Updated revibe/core/model_config.py to include the new OpenRouter entries and canonicalized context/pricing values.
- **Enhanced Onboarding TUI**: Significantly improved the setup experience with richer provider information
  - Added centralized provider metadata in `revibe/setup/onboarding/provider_info.py` to avoid duplication
  - Provider selection screen now shows detailed descriptions including auth status, API bases, example models, and documentation links
  - Added toggle functionality (`i` key) to switch between basic and detailed provider descriptions
  - API key screen now detects existing keys in environment and provides graceful handling with masked display
  - Added OpenRouter provider support to onboarding with proper descriptions and help links
- **Provider Information System**: New helper functions for consistent provider display across the TUI
  - `build_provider_description()`: Builds multi-line provider descriptions with configurable detail levels
  - `check_key_status()`: Checks API key configuration status
  - `get_example_model()`: Retrieves example model aliases for providers
  - `mask_key()`: Safely masks API keys for display

### Changed

- None significant other than the additions above; behavior remains backward compatible. The changes primarily extend available model choices.
- Removed Anthropic provider from onboarding descriptions since it's not currently implemented in ReVibe
- Provider selection now uses centralized metadata instead of hardcoded strings in UI components

### Fixed

- Fixed geminicli provider 403 Forbidden error on API requests by aligning project ID handling with official gemini-cli behavior:
  - Updated `_ensure_project_id()` in geminicli backend to only read `GOOGLE_CLOUD_PROJECT` from environment variables, not `.env` files
  - Modified `get_project_id()` in OAuth module to check only `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_PROJECT_ID` environment variables
  - Fixed API payload to only include `project` field when project_id is truthy (not empty string)
  - Added proper free tier support that doesn't require a project ID
  - Removed invalid placeholder reading from `~/.gemini/.env` file
- Fixed geminicli provider validation error for tool call arguments:
  - The API sends tool call args as dict, but `FunctionCall.arguments` field is typed as `str`
  - Pydantic was coercing dicts to invalid string representation (`"{'pattern': ...}"`) instead of JSON
  - Fixed by serializing args dict to JSON string in `_parse_tool_calls()` before Pydantic sees it
  - Added defensive check in `_prepare_messages()` for any non-string arguments

### Fixed

- Added `revibe/__main__.py` to enable `python -m revibe` command execution on all devices

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
    - Find now shows as `Find (pattern)` instead of `grep: 'pattern'`
    - Bash now shows as `Bash (command)` instead of raw command string
    - Read File now shows as `Read (filename)` with cleaner summary
    - Write File now shows as `Write (filename)`
    - Search & Replace now shows as `Patch (filename)`
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
