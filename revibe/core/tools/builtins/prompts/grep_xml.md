# Find/Grep Tool – XML Format Guide

Search files for text patterns using regex in XML format. **This is the primary search tool** - use it instead of bash commands like `grep`, `find`, `rg`, or `ack`.

## 🚫 CRITICAL: NEVER USE BASH FOR SEARCHING

**NEVER, EVER use the `bash` tool with:**
- `grep`, `find`, `rg`, `ack`, `ag`, `Select-String`
- `cat file | grep`
- `find . -name "*.py" | xargs grep`
- Any shell search commands

This `grep` tool is your ONLY option for searching. It is designed to be superior in every way.

## Required Parameter

- **`pattern`** (string) - Regex pattern to search for. Supports full regex syntax. Examples: `"def "`, `"TODO|FIXME"`, `r"class\s+\w+"`, `"import\s+\w+"`.

## Optional Parameters

- **`path`** (string, default: `"."`) - Directory or file path to search (relative to project root or absolute). Searches recursively in directories. Examples: `"src/"`, `"tests/"`, `"./config.py"`.
- **`max_matches`** (integer, default: 100) - Maximum number of matches to return. Use to limit results for common patterns. Output may be truncated if exceeded.
- **`use_default_ignore`** (boolean, default: true) - Whether to respect `.gitignore` and `.revibeignore` files. Set to `false` to search ignored files (e.g., `node_modules`, `.venv`).

## XML Tool Call Format

```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>your_regex_pattern</pattern>
</parameters>
</tool_call>
```

With all parameters:
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>your_regex_pattern</pattern>
<path>src</path>
<max_matches>50</max_matches>
<use_default_ignore>true</use_default_ignore>
</parameters>
</tool_call>
```

## Why This Tool Beats Bash Searching

- 🚀 **Faster** - Uses ripgrep (rg) when available, fastest search tool available
- 🛡️ **Safer** - No shell injection vulnerabilities, safe parameter handling
- 🌐 **Cross-platform** - Works identically on Windows, macOS, Linux
- 🎯 **Smart filtering** - Auto-ignores junk files and respects .gitignore by default
- 📊 **Structured results** - Clean, parseable output with match counts
- ⏱️ **Timeout protection** - Won't hang your session (built-in timeouts)
- 🔍 **Better regex** - Full regex support with smart case sensitivity
- 🚫 **Automatic exclusions** - Skips common directories like `node_modules`, `.venv`, `.git`, etc.

## When to Use This Tool (MANDATORY)

**You MUST use this tool for ALL searching:**
- Finding function definitions: `grep(pattern="def function_name", path="src")`
- Finding class usage: `grep(pattern=r"\bClassName\b", path=".")`
- Searching for TODOs: `grep(pattern="TODO|FIXME", path=".")`
- Finding error messages: `grep(pattern="ERROR", path="logs")`
- Looking for configuration: `grep(pattern="API_KEY", path="config")`
- Any text search in files across the project

## Example XML Calls

### Find function definition
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>def process_data</pattern>
<path>src</path>
</parameters>
</tool_call>
```

### Search for class usage with word boundaries
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>\bUserModel\b</pattern>
<path>.</path>
</parameters>
</tool_call>
```

### Find all TODO/FIXME comments
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>TODO|FIXME</pattern>
<path>.</path>
<max_matches>50</max_matches>
</parameters>
</tool_call>
```

### Search logs for errors
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>ERROR.*timeout</pattern>
<path>logs</path>
</parameters>
</tool_call>
```

### Search in specific file
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>import</pattern>
<path>src/main.py</path>
</parameters>
</tool_call>
```

### Search ignored directories too
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>test</pattern>
<path>.</path>
<use_default_ignore>false</use_default_ignore>
</parameters>
</tool_call>
```

## Regex Pattern Tips

- **Simple text**: `"TODO"` - matches literal "TODO"
- **Word boundaries**: `r"\bclass\b"` - matches "class" as whole word
- **Alternatives**: `"TODO|FIXME"` - matches either TODO or FIXME
- **Character classes**: `r"\d+"` - matches one or more digits
- **Escaping**: Use `r"..."` raw strings for regex with backslashes
- **Case insensitive**: `"(?i)pattern"` - case-insensitive match

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

## Critical Rules

- **ALWAYS** use this tool instead of bash searching
- If results are truncated (`was_truncated=true`), increase `max_matches` or narrow the `path`
- Use word boundaries (`\b`) for exact word matches (avoids partial matches)
- Narrow `path` for faster, more focused results
- Start with simple patterns, add regex complexity if needed

## Common Mistakes

❌ **WRONG** - Using bash for searching:
```xml
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>grep -r "pattern" src/</command>
</parameters>
</tool_call>
```

✅ **CORRECT** - Use grep tool:
```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>pattern</pattern>
<path>src</path>
</parameters>
</tool_call>
```

## 🚫 FINAL WARNING

Using bash for searching will be incorrect, inefficient, and may not work cross-platform. **Always use the `grep` tool for all text searching.**
