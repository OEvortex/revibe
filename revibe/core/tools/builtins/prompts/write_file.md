# Write File Tool – Creating & Overwriting Files

Create new files or completely overwrite existing files with UTF-8 content. **For partial edits, use `search_replace` instead.**

## Required Parameters

- **`path`** (string) - File path to create or overwrite (relative to project root or absolute). Parent directories created automatically.
- **`content`** (string) - Complete UTF-8 file content. This replaces the entire file.

## Optional Parameters

- **`overwrite`** (boolean, default: False) - Must be `True` to overwrite existing files. If file exists and `overwrite=False`, operation fails to prevent accidental data loss.

## When to Use write_file

✅ **Use write_file for:**
- Creating brand new files
- Complete file rewrites (when you want to replace everything)
- Generating new configuration files
- Creating new source files from scratch

❌ **Use search_replace for:**
- Editing specific parts of existing files
- Making targeted changes
- Updating function implementations
- Changing configuration values

## Safety Features

1. **Size limit** - Content larger than ~64KB (`max_write_bytes`) is rejected
2. **Workspace confinement** - Paths outside project root are blocked
3. **Overwrite protection** - Existing files require `overwrite=True` to prevent accidental data loss
4. **Auto-create directories** - Parent directories created automatically (default behavior)

## Complete Workflow

```python
# For NEW files - just create
write_file(
    path="src/utils/helpers.py",
    content="""def helper_function():
    \"\"\"A helper function.\"\"\"
    return True
"""
)

# For EXISTING files - ALWAYS read first, then overwrite
# Step 1: Read to understand current content
current = read_file(path="config.json")

# Step 2: Create new content (can be based on current)
new_content = """{
  "version": "2.0",
  "settings": {
    "debug": true
  }
}"""

# Step 3: Overwrite with new content
write_file(
    path="config.json",
    content=new_content,
    overwrite=True  # REQUIRED for existing files
)
```

## Example Usage

```python
# Create a new Python module
write_file(
    path="src/calculator.py",
    content="""def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

def multiply(a: int, b: int) -> int:
    \"\"\"Multiply two numbers.\"\"\"
    return a * b
"""
)

# Create a new configuration file
write_file(
    path=".env.example",
    content="""API_KEY=your_key_here
DEBUG=false
PORT=8000
"""
)

# Overwrite existing file (after reading it first)
read_file(path="package.json")  # Understand current structure
write_file(
    path="package.json",
    content='{"name": "my-app", "version": "1.0.0"}',
    overwrite=True
)
```

## Important Rules

1. **Read before overwriting** - Always use `read_file` first to understand existing content
2. **Complete replacement** - `write_file` replaces the ENTIRE file - there's no partial update
3. **Overwrite flag** - Must set `overwrite=True` for existing files (prevents accidents)
4. **Content size** - Keep content under ~64KB (use `search_replace` for larger files)
5. **Check your content** - Double-check the `content` parameter before calling - it replaces everything

## Common Mistakes

❌ **WRONG** - Overwriting without reading first:
```python
write_file(path="config.py", content="...", overwrite=True)
# You don't know what you're replacing!
```

✅ **CORRECT** - Read first, then overwrite:
```python
read_file(path="config.py")  # See what's there
write_file(path="config.py", content="...", overwrite=True)
```

❌ **WRONG** - Using write_file for small edits:
```python
write_file(path="large_file.py", content="[entire 1000-line file with one change]")
# Use search_replace instead!
```

✅ **CORRECT** - Use search_replace for edits:
```python
read_file(path="large_file.py")
search_replace(file_path="large_file.py", content="""<<<<<<< SEARCH
[small section to change]
=======
[new content]
>>>>>>> REPLACE""")
```

## Output

Returns:
- **`path`** (string) - The resolved file path
- **`bytes_written`** (integer) - Number of bytes written
- **`file_existed`** (boolean) - True if file already existed
- **`content`** (string) - The content that was written (echo of input)

## Best Practices

1. **Read existing files first** - Understand structure before overwriting
2. **Use for new files** - Primary use case is creating new files
3. **Prefer search_replace** - For edits, use `search_replace` instead
4. **Verify content** - Double-check your content string before writing
5. **Clean up** - Remove temporary files unless user wants them kept
