# Bash Tool – XML Format Guide

## ⚠️ BASH IS THE TOOL OF LAST RESORT

**STOP! Before using bash, check if a dedicated tool exists:**

| Task | DO NOT USE BASH | USE THIS INSTEAD |
|------|-----------------|------------------|
| Searching files | ❌ `find`, `grep`, `rg`, `Select-String` | ✅ `grep` tool |
| Reading files | ❌ `cat`, `type`, `Get-Content` | ✅ `read_file` tool |
| Editing files | ❌ `sed`, `awk`, shell redirects | ✅ `search_replace` tool |
| Creating files | ❌ `echo >`, `touch` | ✅ `write_file` tool |

## When to ACTUALLY Use Bash

**ONLY** use bash for:
- Git commands: `git status`, `git log`, `git diff`, `git commit`
- Directory listing: `dir` (Windows) or `ls` (Unix)
- System info: `pwd`, `whoami`
- Network probes: `curl -I <url>`

## XML Tool Call Format

```xml
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>your shell command here</command>
<timeout>30</timeout>
</parameters>
</tool_call>
```

## Parameters
- `command` *(required)* – The shell command to execute
- `timeout` *(optional)* – Override default timeout in seconds

## Platform Compatibility

Check the OS in the system prompt and use appropriate commands:
- **Windows**: `dir`, `type`, `where`
- **Unix/Mac**: `ls`, `cat`, `which`

## Example XML Calls (VALID uses of bash)

```xml
<!-- Git status - this is a valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>git status -sb</command>
</parameters>
</tool_call>

<!-- Git log - this is a valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>git log --oneline -5</command>
</parameters>
</tool_call>
```

## ❌ INVALID Uses (Use dedicated tools instead)

```xml
<!-- DON'T DO THIS - use grep tool instead! -->
<!-- <tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>find . -name "*.py" | xargs grep "pattern"</command>
</parameters>
</tool_call> -->

<!-- DO THIS INSTEAD: -->
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>pattern</pattern>
<path>.</path>
</parameters>
</tool_call>
```
