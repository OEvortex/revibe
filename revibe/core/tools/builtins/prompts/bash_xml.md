# Bash Tool – XML Format Guide

Execute shell commands using XML format. **⚠️ BASH IS THE TOOL OF LAST RESORT** - always check if a dedicated tool exists first.

## ⚠️ CRITICAL: Check for Dedicated Tools First

**STOP! Before using bash, check if a dedicated tool exists:**

| Task | ❌ DO NOT USE BASH | ✅ USE THIS INSTEAD |
|------|-------------------|---------------------|
| Searching files | `find`, `grep`, `rg`, `ack`, `Select-String` | `grep` tool |
| Reading files | `cat`, `type`, `Get-Content`, `less`, `more` | `read_file` tool |
| Editing files | `sed`, `awk`, shell redirects, `echo >` | `search_replace` tool |
| Creating files | `echo >`, `touch`, `cat >`, `printf >` | `write_file` tool |

## When to ACTUALLY Use Bash

**ONLY** use bash for tasks without dedicated tools:
- **Git operations**: `git status`, `git log`, `git diff`, `git commit`, `git branch`
- **Directory listings**: `dir` (Windows) or `ls -la` (Unix/Mac), `tree`
- **System information**: `pwd`, `whoami`, `uname -a`, `date`, `env | grep VAR`
- **Network probes**: `curl -I <url>`, `ping -c 1 <host>`, `wget --spider <url>`
- **Process info**: `ps aux`, `top -b -n 1` (non-interactive)
- **Lightweight utilities**: `wc -l file.txt`, `stat file.txt` (for metadata only, not content)

## Required Parameter

- **`command`** (string) - The shell command to execute. Use absolute or project-relative paths. Avoid interactive commands.

## Optional Parameter

- **`timeout`** (integer, default: 30) - Override default timeout in seconds. Long-running commands will be terminated.

## XML Tool Call Format

```xml
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>your shell command here</command>
</parameters>
</tool_call>
```

With optional timeout:
```xml
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>your shell command here</command>
<timeout>60</timeout>
</parameters>
</tool_call>
```

## Platform Compatibility

Check the OS in the system prompt and use appropriate commands:
- **Windows**: `dir`, `type`, `where`, `ver`, `findstr`
- **Unix/Mac**: `ls`, `cat`, `which`, `grep`, `find`

## Example XML Calls (VALID uses of bash)

### Git Operations
```xml
<!-- Git status - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>git status -sb</command>
</parameters>
</tool_call>

<!-- Git log - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>git log --oneline -5</command>
</parameters>
</tool_call>

<!-- Git diff - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>git diff --stat</command>
</parameters>
</tool_call>
```

### Directory Listings
```xml
<!-- List directory - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>ls -la src/</command>
</parameters>
</tool_call>
```

### System Information
```xml
<!-- Current directory - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>pwd</command>
</parameters>
</tool_call>

<!-- System info - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>uname -a</command>
</parameters>
</tool_call>
```

### Network Probes
```xml
<!-- HTTP header check - valid use of bash -->
<tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>curl -I https://example.com</command>
</parameters>
</tool_call>
```

## ❌ INVALID Uses (Use dedicated tools instead)

### Searching Files
```xml
<!-- DON'T DO THIS - use grep tool instead! -->
<!-- <tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>grep -r "pattern" src/</command>
</parameters>
</tool_call> -->

<!-- DO THIS INSTEAD: -->
<tool_call>
<tool_name>grep</tool_name>
<parameters>
<pattern>pattern</pattern>
<path>src</path>
</parameters>
</tool_call>
```

### Reading Files
```xml
<!-- DON'T DO THIS - use read_file tool instead! -->
<!-- <tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>cat src/main.py</command>
</parameters>
</tool_call> -->

<!-- DO THIS INSTEAD: -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>src/main.py</path>
</parameters>
</tool_call>
```

### Editing Files
```xml
<!-- DON'T DO THIS - use search_replace tool instead! -->
<!-- <tool_call>
<tool_name>bash</tool_name>
<parameters>
<command>sed -i 's/old/new/' file.txt</command>
</parameters>
</tool_call> -->

<!-- DO THIS INSTEAD: -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>file.txt</path>
</parameters>
</tool_call>
<!-- Then use search_replace with exact text -->
```

## Important Rules

1. **Commands are non-interactive** - No interactive editors, REPLs, or shells
2. **Clean environment** - Each command runs in a fresh, non-interactive environment
3. **Timeout limits** - Commands are terminated after timeout (default 30s)
4. **Output limits** - Output is capped (~16KB), use dedicated tools for large data
5. **Platform aware** - Use Windows commands on Windows, Unix commands on Unix/Mac

## Best Practices

1. **Check for dedicated tools first** - Always prefer `grep`, `read_file`, `write_file`, `search_replace`
2. **Use for git/system only** - Reserve bash for git operations and system introspection
3. **Keep commands simple** - Single-purpose, idempotent commands work best
4. **Avoid chaining** - Prefer separate tool calls over complex command chains
5. **Check platform** - Verify commands work on the detected OS before suggesting them
