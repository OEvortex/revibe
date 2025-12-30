# Write File Tool – XML Format Guide

Use `write_file` to create new files or fully overwrite existing ones.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>path/to/file</path>
<content>file content here</content>
<overwrite>false</overwrite>
</parameters>
</tool_call>
```

## Parameters
- `path` *(required)* – Target file path
- `content` *(required)* – UTF-8 text to write
- `overwrite` *(optional, default false)* – Must be `true` to replace existing file

## Safety Guarantees
- Size limit enforced (~64 KB)
- Paths outside project root are blocked
- Overwrite guard prevents accidental data loss
- Parent directories created automatically

## Example XML Calls

```xml
<!-- Create a new file -->
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>src/new_module.py</path>
<content>
"""New module for feature X."""

def helper():
    return True
</content>
</parameters>
</tool_call>

<!-- Overwrite existing file (after reading it first!) -->
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>config/settings.json</path>
<content>
{
  "debug": true,
  "version": "2.0"
}
</content>
<overwrite>true</overwrite>
</parameters>
</tool_call>

<!-- Create file in new directory -->
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>docs/api/README.md</path>
<content># API Documentation

This folder contains API docs.
</content>
</parameters>
</tool_call>
```

## Best Practices
- Always `read_file` before overwriting
- Prefer `search_replace` for partial edits
- `write_file` replaces entire file content
