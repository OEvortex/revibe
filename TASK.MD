 › Perform a comprehensive refactoring and UX improvement of the project:

 ## 1. Rename "Mistral Vibe" to "ReVibe"
 - Rename all occurrences of "mistral vibe", "mistral-vibe", "MistralVibe", and any other case variations to "ReVibe" (or appropriate case: "revibe",
 "re-vibe", "ReVibe")
 - Update package names, module names, class names, function names, variables, comments, and documentation
 - Update any CLI command names, help text, and user-facing strings
 - Update configuration files, pyproject.toml, and any metadata

 ## 2. Simplify the TUI (Terminal User Interface)
 - Redesign the TUI to be cleaner and more minimalist, inspired by:
   - **Codex CLI**: Simple command input with streaming responses
   - **Claude Code**: Clean conversation flow with clear visual hierarchy
 - Focus on:
   - Minimal visual clutter
   - Clear input/output separation
   - Readable streaming output
   - Simple status indicators
   - Intuitive keyboard shortcuts

 ## 3. Add `/provider` Command and Improve Provider/Model Management
 - Implement a `/provider` slash command for runtime provider switching
 - Add a `/model` command for model selection within a provider
 - Create a provider/model management system similar to:
   - **Roo Code**: Easy provider configuration with API key management
   - **Cline CLI**: Interactive provider/model selection menus
 - Features to include:
   - List available providers and their status
   - Switch between providers (OpenAI, Anthropic, local models, etc.)
   - Select models per provider
   - Persist provider/model preferences
   - Show current active provider and model in the UI
