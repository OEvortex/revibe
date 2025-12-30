# Bash Tool Quick Guide

Use the `bash` tool **only** for shell-level introspection or commands that have no dedicated tool equivalent. Every invocation runs in a clean, non-interactive environment, so commands cannot rely on previous shell state.

## When to Reach for Bash
- System context: `pwd`, `whoami`, `env | grep VAR`, `uname -a`, `date`
- Repository insight: `ls -la`, `tree`, `git status`, `git log --oneline -20`, `git diff --stat`
- Diagnostics: `ps aux`, `top -b -n 1`, `ping -c 1 <host>`, `curl -I <url>`
- Lightweight text utilities that **do not** read or mutate project files (e.g., `wc -l file.txt`, `stat file.txt`)

## Hard Rules
1. **Prefer purpose-built tools:**
   - Reading files ➜ `read_file`
   - Searching ➜ `grep`
   - Editing ➜ `search_replace`
   - Creating/overwriting files ➜ `write_file`
2. **Never** spawn interactive editors, REPLs, shells, or background daemons.
3. Commands are truncated to the configured timeout (default 30s). Long-running jobs will be canceled.
4. Output is capped. If you need large data, use the specific tool designed for that task.

## Disallowed / Redirected Examples
| Instead of… | Use… |
| ----------- | ---- |
| `bash("cat src/app.py")` | `read_file(path="src/app.py")` |
| `bash("grep -r 'TODO' src")` | `grep(pattern="TODO", path="src")` |
| `bash("sed -i 's/foo/bar/' file")` | `search_replace` with SEARCH/REPLACE block |
| `bash("echo 'text' > file")` | `write_file(path="file", content="text", overwrite=True)` |

## Command Construction Checklist
- Keep commands single-purpose and idempotent.
- Chain commands (`&`, `&&`, `|`) only when each piece is safe and non-interactive.
- Use absolute or project-relative paths; avoid `~` expansions when possible.
- Confirm the command is **not** on the denylist (interactive editors, shells, debuggers, package managers that mutate state, etc.).

## Example Calls
```python
# Inspect current repository state
bash(command="git status -sb")

# Show last 5 commits
bash(command="git log --oneline -5")

# Check a single file's metadata
bash(command="stat revibe/core/tools/base.py")

# Quick network probe
bash(command="curl -I https://example.com")
```

Remember: bash is the tool of last resort. If a higher-level tool exists, you are expected to use it to keep the workflow safe, auditable, and reproducible.