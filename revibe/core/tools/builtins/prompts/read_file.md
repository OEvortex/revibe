# Read File Tool

Read the contents of a text file as UTF-8 text. **Always read files before editing them** to see the exact content.

## Required Parameter

**`path`** (string) - **REQUIRED**. The file path to read.
- Can be relative to project root: `"src/main.py"`, `"README.md"`
- Or absolute path: `"/home/user/project/config.json"`
- Must point to an existing file (not a directory)

## Optional Parameters

- **`offset`** (integer, default: 0) - Starting line number (0-indexed, inclusive). Use to skip header lines or start from a specific position.
- **`limit`** (integer or null, default: None) - Maximum number of lines to return. Use with `offset` for pagination or reading specific sections.

## When to Use

✅ **Use read_file when:**
- You need to see file contents before editing
- Reading configuration files, source code, documentation
- Inspecting file structure or content
- Preparing for search_replace operations

❌ **Don't use bash commands like `cat`, `type`, or `Get-Content`** - use this tool instead

## Example Usage

```python
# Basic file read - path is REQUIRED
read_file(path="pyproject.toml")

# Read specific line range (lines 51-150)
read_file(path="src/main.py", offset=50, limit=100)

# Read from line 200 to end
read_file(path="logs/app.log", offset=200)

# Read first 50 lines
read_file(path="README.md", offset=0, limit=50)
```

## Output Format

Returns a result object with:
- **`content`** (string) - The file contents as UTF-8 text
- **`lines_read`** (integer) - Number of lines returned
- **`was_truncated`** (boolean) - True if file was cut off due to size limits (~64KB)
- **`path`** (string) - The resolved absolute file path

## Important Rules

1. **`path` is REQUIRED** - Always include it. If you get a validation error, you forgot the path parameter.
2. **Read before editing** - Always use `read_file` first before `search_replace` to see exact content.
3. **Use relative paths** - Prefer project-relative paths for portability.
4. **Large files** - Files larger than ~64KB are truncated. Use `offset` and `limit` to read in chunks.
5. **Exact matching** - When copying text for search_replace, copy exactly as shown (whitespace matters).

## Common Workflow

```python
# Step 1: Read the file
result = read_file(path="config.py")

# Step 2: Use the content to create search_replace blocks
# Copy text EXACTLY from result.content
search_replace(
    file_path="config.py",
    content="""<<<<<<< SEARCH
[exact text from result.content]
=======
[new text]
>>>>>>> REPLACE"""
)
```
