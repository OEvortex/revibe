# Write File Tool – XML Format Guide

Create new files or completely overwrite existing files with UTF-8 content using XML format. **For partial edits, use `search_replace` instead.**

## Required Parameters

- **`path`** (string) - File path to create or overwrite (relative to project root or absolute). Parent directories created automatically.
- **`content`** (string) - Complete UTF-8 file content. This replaces the entire file.

## Optional Parameters

- **`overwrite`** (boolean, default: false) - Must be `true` to overwrite existing files. If file exists and `overwrite=false`, operation fails to prevent accidental data loss.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>path/to/file</path>
<content>file content here</content>
</parameters>
</tool_call>
```

With overwrite:
```xml
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>path/to/file</path>
<content>file content here</content>
<overwrite>true</overwrite>
</parameters>
</tool_call>
```

## When to Use write_file vs search_replace

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
3. **Overwrite protection** - Existing files require `overwrite=true` to prevent accidental data loss
4. **Auto-create directories** - Parent directories created automatically (default behavior)

## Example XML Calls

### Create a new file
```xml
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>src/new_module.py</path>
<content>"""New module for feature X."""

def helper():
    return True
</content>
</parameters>
</tool_call>
```

### Overwrite existing file (ALWAYS read first!)
```xml
<!-- Step 1: Read to understand current content -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>config/settings.json</path>
</parameters>
</tool_call>

<!-- Step 2: Overwrite with new content -->
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>config/settings.json</path>
<content>{
  "debug": true,
  "version": "2.0"
}
</content>
<overwrite>true</overwrite>
</parameters>
</tool_call>
```

### Create file in new directory (parent dirs auto-created)
```xml
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

## Important Rules

1. **Read before overwriting** - Always use `read_file` first to understand existing content
2. **Complete replacement** - `write_file` replaces the ENTIRE file - there's no partial update
3. **Overwrite flag** - Must set `overwrite=true` for existing files (prevents accidents)
4. **Content size** - Keep content under ~64KB (use `search_replace` for larger files)
5. **Check your content** - Double-check the `content` parameter before calling - it replaces everything

## Common Mistakes

❌ **WRONG** - Overwriting without reading first:
```xml
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>config.py</path>
<content>...</content>
<overwrite>true</overwrite>
</parameters>
</tool_call>
<!-- You don't know what you're replacing! -->
```

✅ **CORRECT** - Read first, then overwrite:
```xml
<!-- Step 1: Read -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>config.py</path>
</parameters>
</tool_call>

<!-- Step 2: Overwrite -->
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>config.py</path>
<content>...</content>
<overwrite>true</overwrite>
</parameters>
</tool_call>
```

❌ **WRONG** - Using write_file for small edits:
```xml
<!-- Don't rewrite entire 1000-line file for one change! -->
<tool_call>
<tool_name>write_file</tool_name>
<parameters>
<path>large_file.py</path>
<content>[entire file with one small change]</content>
<overwrite>true</overwrite>
</parameters>
</tool_call>
```

✅ **CORRECT** - Use search_replace for edits:
```xml
<!-- Step 1: Read -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>large_file.py</path>
</parameters>
</tool_call>

<!-- Step 2: Edit with search_replace -->
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>large_file.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
[small section to change]
=======
[new content]
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

## Best Practices

1. **Read existing files first** - Understand structure before overwriting
2. **Use for new files** - Primary use case is creating new files
3. **Prefer search_replace** - For edits, use `search_replace` instead
4. **Verify content** - Double-check your content string before writing
5. **Clean up** - Remove temporary files unless user wants them kept
