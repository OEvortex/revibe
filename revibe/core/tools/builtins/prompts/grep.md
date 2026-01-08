# Find/Grep Tool - Text Search Across Files

Search files for text patterns using regex. **This is the primary search tool** - use it instead of bash commands like `grep`, `find`, `rg`, or `ack`.

## 🚫 CRITICAL: NEVER USE BASH FOR SEARCHING

**DO NOT use `bash` tool with `grep`, `find`, `rg`, `ack`, `Select-String`, or any shell search commands.** This tool is specifically designed for all search operations and is far superior to shell commands.

## Required Parameter

- **`pattern`** (string) - Regex pattern to search for. Supports full regex syntax. Examples: `"def "`, `"TODO|FIXME"`, `r"class\s+\w+"`, `"import\s+\w+"`.

## Optional Parameters

- **`path`** (string, default: `"."`) - Directory or file path to search (relative to project root or absolute). Searches recursively in directories. Examples: `"src/"`, `"tests/"`, `"./config.py"`.
- **`max_matches`** (integer, default: 100) - Maximum number of matches to return. Use to limit results for common patterns. Output may be truncated if exceeded.
- **`use_default_ignore`** (boolean, default: True) - Whether to respect `.gitignore` and `.revibeignore` files. Set to `False` to search ignored files (e.g., `node_modules`, `.venv`).

## Why Use This Tool (NOT Bash)

- ✅ **Cross-platform** - Works identically on Windows, macOS, Linux
- ✅ **Smart ignores** - Automatically respects `.gitignore`, `.revibeignore` by default
- ✅ **Fast & safe** - Uses ripgrep (rg) when available, falls back to grep, with built-in timeouts
- ✅ **Structured output** - Returns clean, parseable results with match counts
- ✅ **No shell injection risks** - Safe parameter handling
- ✅ **Better error handling** - Clear error messages and truncation detection
- ✅ **Automatic exclusions** - Skips common directories like `node_modules`, `.venv`, `.git`, etc.

## When to Use This Tool

**ALWAYS use this tool for:**
- Finding function/class definitions: `grep(pattern=r"def my_function", path="src")`
- Searching for variable or method usage: `grep(pattern=r"\bMyClass\b", path=".")`
- Looking for TODO comments or error messages: `grep(pattern="TODO|FIXME", path=".")`
- Finding configuration references: `grep(pattern="API_KEY", path="config")`
- Searching log files or test outputs: `grep(pattern="ERROR", path="logs")`
- Any text search across files in the project

## Example Usage

```python
# Find a function definition
grep(pattern=r"def calculate_total", path="src")

# Search for class usage with word boundaries (exact match)
grep(pattern=r"\bMyClass\b", path=".")

# Find all TODO/FIXME comments
grep(pattern="TODO|FIXME", path=".", max_matches=50)

# Search for error messages in logs
grep(pattern=r"ERROR.*connection", path="logs")

# Find configuration keys
grep(pattern="API_KEY", path="config")

# Search in specific file
grep(pattern="import", path="src/main.py")

# Search with case-insensitive pattern (regex)
grep(pattern="(?i)debug", path="src")

# Search ignored directories too
grep(pattern="test", path=".", use_default_ignore=False)
```

## Regex Pattern Tips

- **Simple text**: `"TODO"` - matches literal "TODO"
- **Word boundaries**: `r"\bclass\b"` - matches "class" as whole word
- **Alternatives**: `"TODO|FIXME"` - matches either TODO or FIXME
- **Character classes**: `r"\d+"` - matches one or more digits
- **Escaping**: Use `r"..."` raw strings for regex with backslashes
- **Case insensitive**: `"(?i)pattern"` - case-insensitive match

## Output Format

Returns a result object with:
- **`matches`** (string) - Formatted search results showing file paths and matching lines
- **`match_count`** (integer) - Total number of matches found
- **`was_truncated`** (boolean) - True if output was cut short by `max_matches` or size limits

If `was_truncated=True`, increase `max_matches` or narrow the search `path`.

## Common Patterns

| Task | Pattern Example |
|------|----------------|
| Find function definitions | `r"def\s+\w+"` |
| Find class definitions | `r"class\s+\w+"` |
| Find imports | `r"^import\s+"` or `r"^from\s+"` |
| Find TODO comments | `"TODO|FIXME|XXX"` |
| Find specific variable | `r"\bVARIABLE_NAME\b"` |
| Find error messages | `r"ERROR|Exception|Traceback"` |
| Find configuration | `"API_KEY|SECRET|PASSWORD"` |

## Best Practices

1. **Use word boundaries** - `r"\bword\b"` for exact word matches (avoids partial matches)
2. **Start simple** - Begin with literal text, add regex complexity if needed
3. **Limit results** - Use `max_matches` for common patterns to avoid huge outputs
4. **Narrow path** - Search specific directories instead of entire project when possible
5. **Check truncation** - If `was_truncated=True`, refine search or increase `max_matches`

## ⚠️ Reminder: This tool replaces ALL bash search commands

❌ **Never use:** `bash(command="grep -r pattern .")`, `bash(command="find . -name '*.py'")`, `bash(command="rg pattern")`
✅ **Always use:** `grep(pattern="pattern", path=".")` - it's safer, faster, and cross-platform
