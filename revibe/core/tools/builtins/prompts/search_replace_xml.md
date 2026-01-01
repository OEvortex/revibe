# search_replace - XML Format

## CRITICAL RULES

1. **ALWAYS read_file FIRST** - See exact content before editing
2. **EXACT MATCH REQUIRED** - Every space, tab, newline must match exactly
3. **USE PROPER FORMAT** - Follow the delimiters precisely

## XML Call Format

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>path/to/file</file_path>
<content>
<<<<<<< SEARCH
exact text from file
=======
new replacement text
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Parameters

- `file_path` - File to edit (required)
- `content` - SEARCH/REPLACE blocks (required)

## Block Rules

- Use **7 or more** `<`, `=`, `>` characters
- **Exact whitespace match** - spaces/tabs/newlines must match file
- Multiple blocks execute sequentially
- First occurrence only (adds warning if multiple matches)

## Example: Single Edit

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>config.py</file_path>
<content>
<<<<<<< SEARCH
DEFAULT_TIMEOUT = 30
=======
DEFAULT_TIMEOUT = 60
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Example: Multiple Edits

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>utils.py</file_path>
<content>
<<<<<<< SEARCH
def old_function():
    pass
=======
def new_function():
    return True
>>>>>>> REPLACE

<<<<<<< SEARCH
VERSION = "1.0"
=======
VERSION = "2.0"
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Common Errors

| Error | Fix |
|-------|-----|
| "Search text not found" | Read file first, copy EXACTLY |
| Wrong indentation | Match spaces/tabs from file |
| Whitespace mismatch | Check trailing spaces |
| Multiple matches | Add more context |

## Best Practices

1. ✅ **Read first** - Always use `read_file` before editing
2. ✅ **Copy exactly** - Don't retype, copy from file content
3. ✅ **Minimal search** - Include only enough to be unique
4. ✅ **Check errors** - Fuzzy match shows what's close

## DO NOT

❌ Never use `bash` with `sed`, `awk`, `echo >` for file editing
❌ Never guess file content - always read first
❌ Never escape newlines with `\n` - use actual newlines
