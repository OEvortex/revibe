# ✏️ SEARCH & REPLACE TOOL - XML Format Reference

## 🚫 CRITICAL: NEVER USE BASH FOR FILE EDITING

**DO NOT use `bash` tool with `sed`, `awk`, `echo >`, or any shell text manipulation commands.** This `search_replace` tool is specifically designed for all file editing operations.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>path/to/file</file_path>
<content>
<<<<<<< SEARCH
exact text to find
=======
replacement text
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Parameters
- `file_path` *(required)* – Target file path (relative or absolute)
- `content` *(required)* – One or more SEARCH/REPLACE blocks

## Block Syntax Rules
```
<<<<<<< SEARCH
<exact text to find - whitespace matters!>
=======
<replacement text>
>>>>>>> REPLACE
```

- Use at least **5 characters** for delimiters (`<`, `=`, `>`)
- **Exact match required** - every space, tab, and newline must match
- Multiple blocks can be stacked in a single `<content>` element
- Blocks execute **sequentially** - later blocks see earlier changes

## ⚠️ Common Mistakes

| ❌ WRONG | ✅ CORRECT |
|----------|-----------|
| Editing without reading first | Always use `read_file` before editing |
| Wrong indentation in SEARCH | Copy indentation exactly from file |
| Using escape sequences like `\n` | Use actual newlines |
| Too much context in SEARCH | Keep it minimal but unique |

## Example XML Calls

### Simple Single Edit
```xml
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
```

### Multiple Edits in One Call
```xml
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

<<<<<<< SEARCH
# TODO: implement
=======
# DONE: implemented
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

### Inserting New Code (Using Anchor Point)
```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>src/models.py</file_path>
<content>
<<<<<<< SEARCH
class User:
=======
from datetime import datetime

class User:
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

### Preserving Indentation
```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>src/handler.py</file_path>
<content>
<<<<<<< SEARCH
    def process(self):
        return None
=======
    def process(self):
        """Process the request."""
        return self._execute()
>>>>>>> REPLACE
</content>
</parameters>
</tool_call>
```

## Best Practices Checklist

1. ✅ **Read first** - Always `read_file` to see exact content before editing
2. ✅ **Minimal context** - Include only enough text to be unique
3. ✅ **Exact whitespace** - Copy indentation and spacing exactly
4. ✅ **One concern per block** - Separate unrelated edits for clarity
5. ✅ **Order matters** - Later blocks operate on modified content

## Error Recovery

### "Search text not found"
- Run `read_file` to see current content
- Check whitespace (spaces vs tabs, trailing spaces)
- Check line endings (`\n` vs `\r\n`)
- Use the fuzzy match suggestions in the error message

### "Multiple occurrences found"
- Add more context to make search unique
- Only first occurrence is replaced (with warning)

## When to Use Other Tools

| Want to... | Use this tool |
|------------|---------------|
| Create new file | `write_file` |
| Overwrite entire file | `write_file` with `overwrite=True` |
| Read file first | `read_file` |
| Search for text | `grep` |
| Edit part of file | `search_replace` ✅ |

---

📌 **Golden Rule**: Read → Understand → Edit. Never guess file content!
