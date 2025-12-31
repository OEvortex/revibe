make a new geminicli provider in
C:\Users\koula\Desktop\DEVELOPER\Projects\revibe\revibe\core\llm
simar to qwen (qwencode) provider
make geminicli provider based on this repo
https://github.com/google-gemini/gemini-cli
Here's a comprehensive list of **all important files** with their links organized by category:

## 🤖 Model Configuration & IDs

| File | Link |
|------|------|
| Model constants and resolution | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/config/models.ts |
| Default model configurations | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/config/defaultModelConfigs.ts |
| Token limits per model | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/core/tokenLimits.ts |
| Model availability service | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/availability/modelAvailabilityService.ts |
| Model policy definitions | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/availability/modelPolicy.ts |

## 🔐 Authentication & Auth Types

| File | Link |
|------|------|
| Initial authentication flow | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/core/auth. ts |
| OAuth2 implementation | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/oauth2.ts |
| OAuth credential storage | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/oauth-credential-storage.ts |
| Non-interactive auth validation | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/validateNonInterActiveAuth.ts |
| Auth slash commands | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/ui/commands/authCommand.ts |
| Auth provider interface | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/mcp/auth-provider.ts |

## 🛠️ Tool Calling & Tool API

| File | Link |
|------|------|
| Core tool interface | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/tools.ts |
| Tool names constants | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/tool-names.ts |
| MCP tool integration | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/mcp-tool.ts |
| MCP client implementation | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/mcp-client.ts |
| Tool utilities | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/utils/tool-utils.ts |
| Tools API documentation | https://github.com/google-gemini/gemini-cli/blob/main/docs/core/tools-api.md |

## 📄 Built-in Tools Implementation

| File | Link |
|------|------|
| Read file tool | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/read-file.ts |
| Edit file tool | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/edit. ts |
| Shell execution tool | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/shell. ts |
| Directory listing tool | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/ls.ts |
| File search tool (grep) | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/grep.ts |
| Web fetching tool | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/tools/web-fetch.ts |

## 🔀 Model Routing & Selection

| File | Link |
|------|------|
| Model routing service | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/routing/modelRouterService.ts |
| Model configuration service | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/services/modelConfigService.ts |
| Model config service test utils | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/services/modelConfigServiceTestUtils.ts |

## 📡 MCP OAuth & Authentication

| File | Link |
|------|------|
| MCP OAuth provider | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/mcp/oauth-provider.ts |
| OAuth token storage | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/mcp/oauth-token-storage. ts |
| Google credential provider for MCP | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/mcp/google-auth-provider.ts |
| OAuth utility functions | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/mcp/oauth-utils.ts |

## ⚙️ Core Configuration

| File | Link |
|------|------|
| Configuration documentation | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md |
| Settings schema validation | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/config/settings-validation.ts |
| Settings schema definitions | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/config/settingsSchema.ts |
| Core constants | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/config/constants.ts |
| Configuration v1 (legacy) | https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/configuration-v1.md |

## 🎨 UI & Commands

| File | Link |
|------|------|
| Model selection command | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/ui/commands/modelCommand.ts |
| Model command hook | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/ui/hooks/useModelCommand.ts |
| Keyboard binding configuration | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/config/keyBindings.ts |
| Config context (React) | https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/ui/contexts/ConfigContext.tsx |

## 📝 Documentation & Guides

| File | Link |
|------|------|
| README - Project overview | https://github.com/google-gemini/gemini-cli/blob/main/README. md |
| GEMINI. md - Development guidelines | https://github.com/google-gemini/gemini-cli/blob/main/GEMINI.md |
| ROADMAP - Feature roadmap | https://github.com/google-gemini/gemini-cli/blob/main/ROADMAP.md |
| CONTRIBUTING - Contribution guide | https://github.com/google-gemini/gemini-cli/blob/main/CONTRIBUTING. md |
| SECURITY - Security policy | https://github.com/google-gemini/gemini-cli/blob/main/SECURITY.md |
| Gemini 3 setup guide | https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/gemini-3. md |
| Headless mode documentation | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless. md |
| Hooks reference | https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md |
| Model selection guide | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/model. md |

## 🏗️ Build & Configuration

| File | Link |
|------|------|
| Package.json | https://github.com/google-gemini/gemini-cli/blob/main/package.json |
| ESBuild configuration | https://github.com/google-gemini/gemini-cli/blob/main/esbuild.config.js |
| ESLint configuration | https://github.com/google-gemini/gemini-cli/blob/main/eslint.config.js |
| TypeScript configuration | https://github.com/google-gemini/gemini-cli/blob/main/tsconfig.json |
| Dockerfile | https://github.com/google-gemini/gemini-cli/blob/main/Dockerfile |
| Makefile | https://github.com/google-gemini/gemini-cli/blob/main/Makefile |

## 📁 Directory Structure

| Directory | Link |
|-----------|------|
| Root repository | https://github.com/google-gemini/gemini-cli |
| Packages (monorepo) | https://github.com/google-gemini/gemini-cli/tree/main/packages |
| Core package | https://github.com/google-gemini/gemini-cli/tree/main/packages/core |
| CLI package | https://github.com/google-gemini/gemini-cli/tree/main/packages/cli |
| Documentation | https://github.com/google-gemini/gemini-cli/tree/main/docs |
| Integration tests | https://github.com/google-gemini/gemini-cli/tree/main/integration-tests |
| Scripts | https://github.com/google-gemini/gemini-cli/tree/main/scripts |
| Schemas | https://github.com/google-gemini/gemini-cli/tree/main/schemas |

## Core Gemini Chat & LLM

| File | Link |
|------|------|
| Gemini chat implementation | https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/core/geminiChat.ts |

This comprehensive list covers all the important files related to **models**, **authentication**, **tool calling**, and **API configuration**. You can click any link to view the file directly on GitHub! 
