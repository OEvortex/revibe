# search_replace - File Editor

## CRITICAL RULES

1. **ALWAYS read_file FIRST** - You MUST see the exact file content before editing
2. **EXACT MATCH REQUIRED** - Every space, tab, newline must match exactly
3. **USE PROPER FORMAT** - Follow the delimiter pattern precisely

## Format

```
<<<<<<< SEARCH
[exact text from file - copy it EXACTLY]
=======
[new text to replace with]
>>>>>>> REPLACE
```

- Use **7 or more** `<`, `=`, `>` characters
- Whitespace matters - copy spaces/tabs exactly as they appear
- Multiple blocks execute sequentially

## Arguments

- `file_path` - File to edit (required)
- `content` - SEARCH/REPLACE blocks (required)

## Example Workflow

```python
# 1. Read file to see content
read_file(path="config.py")

# 2. Edit with exact match from file
search_replace(
    file_path="config.py",
    content="""
<<<<<<< SEARCH
TIMEOUT = 30
=======
TIMEOUT = 60
>>>>>>> REPLACE
"""
)
```

## Multiple Edits

```python
search_replace(
    file_path="utils.py",
    content="""
<<<<<<< SEARCH
def old_func():
    pass
=======
def new_func():
    return True
>>>>>>> REPLACE

<<<<<<< SEARCH
VERSION = "1.0"
=======
VERSION = "2.0"
>>>>>>> REPLACE
"""
)
```

## Common Errors

| Error | Solution |
|-------|----------|
| "Search text not found" | Read the file first, copy text EXACTLY |
| Wrong indentation | Use spaces/tabs exactly as in file |
| Whitespace mismatch | Check for trailing spaces, line endings |
| Multiple matches | Add more context to make search unique |

## Tips

- **Keep SEARCH minimal** - Only include enough to be unique
- **Preserve indentation** - Copy spaces/tabs exactly
- **Read errors carefully** - Fuzzy match suggestions show what's close
- **One edit at a time** - Don't guess, verify with read_file

## DO NOT Use bash for Editing

❌ Never use `sed`, `awk`, `echo >`, or shell commands for file editing
✅ Always use this tool - it's safer and gives better error messages
