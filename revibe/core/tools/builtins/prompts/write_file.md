# Write File Tool – Creating & Overwriting Files

Use `write_file` when you need to create a brand-new file or fully overwrite an existing one. For partial edits or patch-style updates, prefer `search_replace` instead.

## Arguments
- `path` *(str, required)* – Target file path (project-relative or absolute inside workspace).
- `content` *(str, required)* – UTF‑8 text to persist.
- `overwrite` *(bool, default False)* – Must be `true` to replace an existing file.

## Safety Guarantees
1. **Size limit:** Content larger than the configured `max_write_bytes` (~64 KB) is rejected.
2. **Workspace confinement:** Paths outside the project root are blocked.
3. **Overwrite guard:** If the file exists and `overwrite` is false, the call fails to prevent accidental data loss.
4. **Parent directories:** Created automatically when `create_parent_dirs=True` (default).

## Workflow Recommendations
- ALWAYS inspect the file with `read_file` before overwriting it so you understand the current content.
- Prefer `search_replace` for edits within a file; `write_file` should be reserved for new files or when you intentionally rewrite the entire file.
- Avoid generating boilerplate or documentation unless explicitly requested.
- Remove temporary/testing files you created before finishing the task unless the user asked to keep them.

## Example Calls
```python
# Create a new helper module
write_file(
    path="revibe/core/tools/prompts/README.md",
    content="# Tool Prompts\nGuidelines..."
)

# Overwrite an existing fixture AFTER reading it
# read_file(path="tests/data/sample.json")
write_file(
    path="tests/data/sample.json",
    content="{\n  \"items\": []\n}\n",
    overwrite=True
)
```

Remember: `write_file` replaces the entire file with the provided `content`. Double-check your buffer before sending the command.