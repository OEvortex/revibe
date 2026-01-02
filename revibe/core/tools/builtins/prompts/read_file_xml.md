# Read File Tool – XML Format

Read the contents of a text file using XML tool call format.

## Required Parameter

**`path`** - **REQUIRED**. The file path to read. You MUST include this parameter.

## XML Format

```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>YOUR_FILE_PATH_HERE</path>
</parameters>
</tool_call>
```

## Examples

### Basic file read (path is REQUIRED)
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>pyproject.toml</path>
</parameters>
</tool_call>
```

### Read specific line range
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

### Read from a specific offset
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>logs/app.log</path>
<offset>200</offset>
</parameters>
</tool_call>
```

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `path` | **YES** | string | File path to read |
| `offset` | No | integer | Start line (0-indexed), default: 0 |
| `limit` | No | integer | Max lines to return |

## Common Mistakes

❌ **WRONG** - Missing path:
```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
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
