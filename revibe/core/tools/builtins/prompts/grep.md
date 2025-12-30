# 🔍 FIND TOOL - Your Primary Search Command

## 🚫 CRITICAL: NEVER USE BASH FOR SEARCHING

**DO NOT use `bash` tool with `grep`, `find`, `rg`, `ack`, or any shell search commands.** This `find` tool is specifically designed for all search operations and is far superior to shell commands.

## Why Use This Tool (NOT Bash)
- ✅ **Cross-platform** - Works identically on Windows, macOS, Linux
- ✅ **Smart ignores** - Automatically respects `.gitignore`, `.revibeignore`
- ✅ **Fast & safe** - Uses ripgrep when available, with built-in timeouts
- ✅ **Structured output** - Returns clean, parseable results
- ✅ **No shell injection risks** - Safe parameter handling
- ✅ **Better error handling** - Clear error messages and truncation detection

## Arguments
- `pattern` *(str, required)* – Regex pattern to search for
- `path` *(str, default ".")* – Directory/file to search in
- `max_matches` *(int, default 100)* – Maximum results to return
- `use_default_ignore` *(bool, default True)* – Respect .gitignore rules

## When to Use This Tool
**ALWAYS use this tool for:**
- Finding function/class definitions
- Searching for variable or method usage
- Looking for TODO comments or error messages
- Finding configuration references
- Searching log files or test outputs
- Any text search across files

## Common Search Patterns
```python
# Find a function definition
find(pattern=r"def my_function", path="src")

# Search for class usage with word boundaries
find(pattern=r"\bMyClass\b", path=".")

# Find all TODO comments
find(pattern="TODO", path=".", max_matches=50)

# Search for error messages in logs
find(pattern="ERROR.*connection", path="logs")

# Find configuration keys
find(pattern="API_KEY", path="config")
```

## Output Format
Returns: `matches` (string), `match_count` (int), `was_truncated` (bool)

If `was_truncated=True`, increase `max_matches` or narrow the search path.

## ⚠️ Reminder: This tool replaces ALL bash search commands