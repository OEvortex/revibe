# Search & Replace Tool – Structured File Editing

Use `search_replace` for deterministic file edits. Provide one or more SEARCH/REPLACE blocks that exactly match the existing content. The tool validates each block and reports precise errors if the search text is missing or ambiguous.

## Arguments
- `file_path` *(str)* – Target file (relative or absolute within project).
- `content` *(str)* – Concatenated SEARCH/REPLACE blocks.

## Block Format
```
<<<<<<< SEARCH
<exact text to replace>
=======
<new text>
>>>>>>> REPLACE
```
- Use at least five `<`/`=`/`>` characters (already enforced by tool regexes).
- Multiple blocks can be stacked in a single `content` payload; they execute sequentially.
- Blocks may be wrapped in fenced code blocks ```…```; both styles are accepted.

## Guarantees & Behavior
- **Exact match required:** Whitespace, indentation, and newlines must align with the file.
- **Single replacement per block:** If the search text appears multiple times, only the **first** occurrence is replaced and a warning is emitted so you can disambiguate later.
- **Fuzzy diagnostics:** If no exact match is found, the tool surfaces nearby context and a diff of the closest match to help you adjust the block.
- **Safety rails:**
  - Rejects empty file paths or content.
  - Enforces `max_content_size` (default 100 KB).
  - Can create backups when `create_backup=True` in config.

## Workflow Tips
1. **Inspect first** – Always call `read_file` to capture the current text before crafting blocks.
2. **Keep blocks tight** – Include only the code you need to change plus sufficient neighboring lines to ensure uniqueness.
3. **One concern per block** – Separate unrelated edits into different blocks for clearer diffs and easier retries.
4. **Order matters** – Later blocks operate on the already-modified content from earlier blocks.
5. **Line endings** – Ensure your block uses the same `\n`/`\r\n` style as the file.

## Example Payload
```python
search_replace(
  file_path="revibe/core/tools/base.py",
  content="""
<<<<<<< SEARCH
class ToolError(Exception):
    """Raised when the tool encounters an unrecoverable problem."""
=======
class ToolError(Exception):
    """Raised when a tool encounters an unrecoverable problem."""
>>>>>>> REPLACE

<<<<<<< SEARCH
ARGS_COUNT = 4
=======
ARGS_COUNT = 4  # (<ToolArgs, ToolResult, ToolConfig, ToolState>)
>>>>>>> REPLACE
"""
)
```

If a block fails, the exception message includes troubleshooting hints. Adjust the block and retry until all intended replacements succeed.