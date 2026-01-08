# search_replace - File Editor Tool

Make targeted edits to files using SEARCH/REPLACE blocks. **This is the primary tool for editing files** - use it instead of bash commands.

## CRITICAL RULES (MUST FOLLOW)

1. **ALWAYS read_file FIRST** - You MUST see the exact file content before editing
2. **EXACT MATCH REQUIRED** - Every space, tab, newline must match exactly (copy directly from read_file output)
3. **USE PROPER FORMAT** - Follow the delimiter pattern precisely (7+ characters)
4. **WHITESPACE MATTERS** - Spaces ≠ tabs, trailing spaces matter, line endings matter

## Required Parameters

- **`file_path`** (string) - File to edit (relative to project root or absolute). File must exist.
- **`content`** (string) - SEARCH/REPLACE blocks containing your edits

## SEARCH/REPLACE Block Format

```
<<<<<<< SEARCH
[exact text from file - copy it EXACTLY from read_file output]
=======
[new text to replace with]
>>>>>>> REPLACE
```

**Format Rules:**
- Use **7 or more** `<`, `=`, `>` characters (minimum: `<<<<<<<`, `=======`, `>>>>>>>`)
- SEARCH text must match file content exactly (whitespace, indentation, everything)
- Multiple blocks execute sequentially (top to bottom)
- First occurrence only per block (if multiple matches, only first is replaced)

## Complete Workflow Example

```python
# Step 1: ALWAYS read the file first
result = read_file(path="config.py")
# Now you can see the exact content in result.content

# Step 2: Copy text EXACTLY from result.content and create edit
search_replace(
    file_path="config.py",
    content="""
<<<<<<< SEARCH
TIMEOUT = 30
MAX_RETRIES = 3
=======
TIMEOUT = 60
MAX_RETRIES = 5
>>>>>>> REPLACE
"""
)
```

## Multiple Edits in One Call

You can make multiple edits in a single call - blocks execute sequentially:

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

<<<<<<< SEARCH
    logger.info("Starting")
=======
    logger.info("Starting application")
>>>>>>> REPLACE
"""
)
```

## When to Use search_replace vs write_file

✅ **Use search_replace for:**
- Editing specific parts of a file
- Changing function implementations
- Updating configuration values
- Fixing bugs or making targeted changes
- Multiple edits to the same file

❌ **Use write_file for:**
- Creating brand new files
- Complete file rewrites
- When you want to replace the entire file

## Common Errors & Solutions

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Search text not found" | SEARCH doesn't match file exactly | Read file first, copy text EXACTLY from read_file output |
| "Invalid SEARCH/REPLACE format" | Wrong delimiter format | Use 7+ characters: `<<<<<<<`, `=======`, `>>>>>>>` |
| Wrong indentation | Spaces/tabs don't match | Copy indentation exactly (spaces ≠ tabs) |
| Whitespace mismatch | Trailing spaces or line endings differ | Copy text exactly, including all whitespace |
| Multiple matches warning | SEARCH text appears multiple times | Add more context to make search unique (include surrounding lines) |

## Best Practices

1. **Read first, edit second** - Always use `read_file` before `search_replace`
2. **Copy exactly** - Don't retype text, copy directly from `read_file` output
3. **Minimal SEARCH** - Include only enough text to be unique (but enough context to match correctly)
4. **Preserve structure** - Keep indentation, spacing, and formatting exactly as in file
5. **Test incrementally** - Make one edit at a time for complex changes, verify each step
6. **Read error messages** - They show fuzzy matches and suggest what's close

## Visual Example: Matching Whitespace

```
File content (from read_file):
    def function():
        if condition:
            return True

CORRECT SEARCH (copied exactly):
<<<<<<< SEARCH
    def function():
        if condition:
            return True
=======
    def function():
        if condition:
            return False
>>>>>>> REPLACE

WRONG (ret typed, wrong indentation):
<<<<<<< SEARCH
def function():
  if condition:
    return True
=======
def function():
  if condition:
    return False
>>>>>>> REPLACE
```

## DO NOT Use Bash for Editing

❌ **Never use:** `sed`, `awk`, `echo >`, `cat >`, `printf >`, or any shell redirection
✅ **Always use:** `search_replace` - it's safer, provides better error messages, and handles edge cases

## Tips for Success

- **Use fuzzy match hints** - Error messages show similar text if exact match fails
- **Add context** - Include surrounding lines to make SEARCH unique
- **Check line endings** - Windows (CRLF) vs Unix (LF) can cause mismatches
- **Verify with read_file** - After editing, read the file again to confirm changes
