# TUI Visual & Functional Enhancements

I have implemented several key changes to the TUI to improve the visual experience and support the new XML-based tool calling mode.

## 1. XML Tool Call Redaction
- **File**: `revibe/core/utils.py`
- **Change**: Added `redact_xml_tool_calls(text)` utility.
- **Purpose**: This function detects and removes raw `<tool_call>...</tool_call>` blocks from the assistant's output stream. It supports partially written tags, ensuring that raw XML never "flickers" on screen during streaming.

## 2. Streaming UI Refresh
- **File**: `revibe/cli/textual_ui/widgets/messages.py`
- **Change**: Refactored `StreamingMessageBase` to track `_displayed_content`.
- **Purpose**: Allows the UI to smart-update only when visible content changes. If a tool call block starts in the stream, the UI detects the decrease in "visible" characters (due to redaction) and resets the stream to prevent showing fragments of XML.

## 3. Premium Tool Summaries
I updated the display logic for all built-in tools to provide a cleaner, more premium aesthetic in the chat history:

- **Grep**: Now shows as `Grep (pattern)` instead of `grep: 'pattern'`.
- **Bash**: Now shows as `Bash (command)` instead of a raw command string.
- **Read File**: Now shows as `Read (filename)` with a cleaner summary.
- **Write File**: Now shows as `Write (filename)`.
- **Search & Replace**: Now shows as `Patch (filename)`.

## 4. Reasoning Integration
- **File**: `revibe/cli/textual_ui/widgets/messages.py`
- **Change**: Applied the same redaction logic to `ReasoningMessage`.
- **Purpose**: Ensures that even if the model starts thinking about tool calls in its reasoning block, the raw tags remain hidden from the user.

---
*Created on 2025-12-30 following TUI Aesthetic overhaul.*
