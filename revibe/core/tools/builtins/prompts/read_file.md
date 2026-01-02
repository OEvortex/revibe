# Read File Tool

Read the contents of a text file.

## Required Argument

**`path`** (string) - **REQUIRED**. The file path to read. Must be provided.
- Can be relative to the project root: `"src/main.py"`
- Or an absolute path: `"/home/user/project/README.md"`

## Optional Arguments

- **`offset`** (integer, default: 0) - Line number to start reading from (0-indexed)
- **`limit`** (integer or null) - Maximum number of lines to return

## Example Usage

```
# Read a file - path is REQUIRED
read_file(path="pyproject.toml")

# Read with offset and limit
read_file(path="src/main.py", offset=50, limit=100)

# Read from line 200 onwards
read_file(path="logs/app.log", offset=200)
```

## Output

Returns:
- `content` - The file contents as text
- `lines_read` - Number of lines returned
- `was_truncated` - True if file was cut off due to size limits
- `path` - The resolved file path

## Important Notes

1. **Always specify the `path` argument** - it is required and cannot be omitted
2. If you get a validation error about "path required", you forgot to include the path parameter
3. Use relative paths when possible for better portability
4. Large files will be truncated - use `offset` to read subsequent chunks
