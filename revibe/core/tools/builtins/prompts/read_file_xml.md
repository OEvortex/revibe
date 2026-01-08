# Read File Tool – XML Format

Read the contents of a text file as UTF-8 text using XML tool call format. **Always read files before editing them** to see the exact content.

## Required Parameter

**`path`** (string) - **REQUIRED**. The file path to read (relative to project root or absolute). You MUST include this parameter.

## Optional Parameters

- **`offset`** (integer, default: 0) - Starting line number (0-indexed, inclusive). Use to skip header lines or start from a specific position.
- **`limit`** (integer, default: None) - Maximum number of lines to return. Use with `offset` for pagination.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>YOUR_FILE_PATH_HERE</path>
</parameters>
</tool_call>
```

## Example XML Calls

### Basic file read (path is REQUIRED)
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>pyproject.toml</path>
</parameters>
</tool_call>
```

### Read specific line range (lines 51-150)
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>src/main.py</path>
<offset>50</offset>
<limit>100</limit>
</parameters>
</tool_call>
```

### Read from line 200 to end
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>logs/app.log</path>
<offset>200</offset>
</parameters>
</tool_call>
```

### Read first 50 lines
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>README.md</path>
<offset>0</offset>
<limit>50</limit>
</parameters>
</tool_call>
```

## Complete Workflow: Read Before Edit

```xml
<!-- Step 1: Read the file first -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>config.py</path>
</parameters>
</tool_call>

<!-- Step 2: After receiving results, use exact text from read_file output -->
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>config.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
[copy text EXACTLY from read_file result.content]
=======
[new text]
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

## Parameters Summary

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `path` | **YES** | string | File path to read (relative or absolute) |
| `offset` | No | integer | Start line (0-indexed), default: 0 |
| `limit` | No | integer | Max lines to return, default: None (reads until byte limit) |

## Common Mistakes

❌ **WRONG** - Missing required path parameter:
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<!-- Missing path! This will fail -->
</parameters>
</tool_call>
```

✅ **CORRECT** - Always include path:
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>README.md</path>
</parameters>
</tool_call>
```

❌ **WRONG** - Using bash instead:
```xml
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>cat src/main.py</command>
</parameters>
</tool_call>
```

✅ **CORRECT** - Use read_file tool:
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>src/main.py</path>
</parameters>
</tool_call>
```

## Important Notes

1. **`path` is REQUIRED** - Always include it. If you get a validation error, you forgot the path parameter.
2. **Read before editing** - Always use `read_file` first before `search_replace` to see exact content.
3. **Copy exactly** - When copying text for search_replace, copy exactly as shown in the result (whitespace matters).
4. **Large files** - Files larger than ~64KB are truncated. Use `offset` and `limit` to read in chunks.
