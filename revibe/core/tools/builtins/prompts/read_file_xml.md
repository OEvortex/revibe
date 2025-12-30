# Read File Tool – XML Format Guide

`read_file` is the safest way to inspect file contents. It streams UTF-8 text with size guards.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>path/to/file</path>
<offset>0</offset>
<limit>100</limit>
</parameters>
</tool_call>
```

## Parameters
- `path` *(required)* – Relative or absolute file path
- `offset` *(optional, default 0)* – 0-based line to start reading from
- `limit` *(optional)* – Maximum lines to return

## Output
- `content` – Raw text chunk
- `lines_read` – Number of lines returned
- `was_truncated` – `True` if more content remains

## Example XML Calls

```xml
<!-- Read entire file -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>revibe/core/agent.py</path>
</parameters>
</tool_call>

<!-- Read specific line range -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>src/service.py</path>
<offset>120</offset>
<limit>80</limit>
</parameters>
</tool_call>

<!-- Paged reading for large files -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>logs/run.log</path>
<offset>0</offset>
<limit>500</limit>
</parameters>
</tool_call>
```

## Best Practices
- Always inspect a file with `read_file` before modifying it
- Set `offset`/`limit` to keep responses concise
- If `was_truncated` is true, continue reading with updated offset
