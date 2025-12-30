# Grep Tool – XML Format Guide

## ⚠️ ALWAYS USE THIS TOOL FOR SEARCHING

**NEVER use `bash` with `grep`, `find`, `rg`, `Select-String`, or any shell search commands.**
This `grep` tool is cross-platform, faster, and automatically handles:
- `.gitignore` rules
- Binary file exclusions
- Common junk directories (node_modules, .git, __pycache__, etc.)

Use `grep` for fast, recursive regex searches across the project.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>your regex pattern</pattern>
<path>directory or file to search</path>
<max_matches>100</max_matches>
<use_default_ignore>true</use_default_ignore>
</parameters>
</tool_call>
```

## Parameters
- `pattern` *(required)* – Regex pattern (smart-case)
- `path` *(optional, default ".")* – File or directory to search
- `max_matches` *(optional, default 100)* – Cap number of matches
- `use_default_ignore` *(optional, default true)* – Use .gitignore rules

## When to Use (PREFER THIS OVER BASH)
- **Finding files containing text** → Use `grep`, NOT `bash` with `find | xargs grep`
- **Searching for patterns** → Use `grep`, NOT `bash` with shell grep commands
- **Locating function/class definitions** → Use `grep`
- **Finding symbol usage across codebase** → Use `grep`
- **Discovering TODOs, feature flags, config references** → Use `grep`
- **Investigating errors in logs** → Use `grep`
- **Finding files by name patterns** → Use `grep` with filename patterns

## Example XML Calls

```xml
<!-- Find function definitions -->
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>def build_payload</pattern>
<path>revibe/core</path>
</parameters>
</tool_call>

<!-- Search for TODOs across repo -->
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>TODO</pattern>
<path>.</path>
<max_matches>50</max_matches>
</parameters>
</tool_call>

<!-- Find class usages with word boundaries -->
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>\bToolManager\b</pattern>
<path>revibe</path>
</parameters>
</tool_call>
```

## Tips
- Narrow `path` for faster, focused results
- Use word boundaries `\b` for precision
- If `was_truncated=True`, increase `max_matches` or narrow scope
