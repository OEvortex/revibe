# Search & Replace Tool – XML Format Guide

Use `search_replace` for deterministic file edits with SEARCH/REPLACE blocks.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>path/to/file</file_path>
<content>
<<<<<<< SEARCH
exact text to replace
=======
new text
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Parameters
- `file_path` *(required)* – Target file path
- `content` *(required)* – SEARCH/REPLACE blocks

## Block Format
```
<<<<<<< SEARCH
<exact text to replace>
=======
<new text>
>>>>>>> REPLACE
```

## Key Rules
- **Exact match required:** Whitespace, indentation, and newlines must match
- **Multiple blocks:** Stack blocks in single `content` payload
- **First occurrence:** If text appears multiple times, only first is replaced

## Example XML Calls

```xml
<!-- Simple replacement -->
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>revibe/core/config.py</file_path>
<content>
<<<<<<< SEARCH
DEFAULT_TIMEOUT = 30
=======
DEFAULT_TIMEOUT = 60
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>

<!-- Multiple replacements in one call -->
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>src/utils.py</file_path>
<content>
<<<<<<< SEARCH
def old_function():
    pass
=======
def new_function():
    return True
>>>>>>> REPLACE

<<<<<<< SEARCH
CONSTANT = "old"
=======
CONSTANT = "new"
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Best Practices
1. **Inspect first** – Always use `read_file` before editing
2. **Keep blocks tight** – Include only necessary context for uniqueness
3. **One concern per block** – Separate unrelated edits
4. **Order matters** – Later blocks see earlier modifications
