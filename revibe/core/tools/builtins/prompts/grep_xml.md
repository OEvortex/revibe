# 🚫 STOP! USE THIS TOOL FOR ALL SEARCHING

## ⚠️ ABSOLUTELY FORBIDDEN: Do NOT use bash tool for searching

**NEVER, EVER use the `bash` tool with:**
- `grep`, `find`, `rg`, `ack`, `ag`
- `cat file | grep`
- `find . -name "*.py" | xargs grep`
- Any shell search commands

This `find` tool is your ONLY option for searching. It is designed to be superior in every way.

## Why This Tool Beats Bash Searching
- 🚀 **Faster** - Uses ripgrep (fastest search tool available)
- 🛡️ **Safer** - No shell injection vulnerabilities
- 🌐 **Cross-platform** - Works identically everywhere
- 🎯 **Smart filtering** - Auto-ignores junk files and respects .gitignore
- 📊 **Structured results** - Clean, parseable output
- ⏱️ **Timeout protection** - Won't hang your session
- 🔍 **Better regex** - Full regex support with smart case sensitivity

## XML Format (REQUIRED)
```xml
<tool_call>
<tool_name>find</tool_name>
<parameters>
<pattern>your_regex_pattern</pattern>
<path>.</path>
<max_matches>100</max_matches>
<use_default_ignore>true</use_default_ignore>
</parameters>
</tool_call>
```

## Parameters
- `pattern` *(REQUIRED)* – The regex pattern to search for
- `path` *(default ".")* – Directory or file to search
- `max_matches` *(default 100)* – How many results to return
- `use_default_ignore` *(default true)* – Respect .gitignore rules

## When to Use This Tool (MANDATORY)
**You MUST use this tool for ALL searching:**
- Finding function definitions: `find(pattern="def function_name")`
- Finding class usage: `find(pattern="\\bClassName\\b")`
- Searching for TODOs: `find(pattern="TODO")`
- Finding error messages: `find(pattern="ERROR")`
- Looking for configuration: `find(pattern="API_KEY")`
- Any text search in files

## Example XML Calls

```xml
<!-- Find function definition -->
<tool_call>
<tool_name>find</tool_name>
<parameters>
<pattern>def process_data</pattern>
<path>src</path>
</parameters>
</tool_call>

<!-- Search for class usage -->
<tool_call>
<tool_name>find</tool_name>
<parameters>
<pattern>\bUserModel\b</pattern>
<path>.</path>
</parameters>
</tool_call>

<!-- Find all TODO comments -->
<tool_call>
<tool_name>find</tool_name>
<parameters>
<pattern>TODO</pattern>
<path>.</path>
<max_matches>50</max_matches>
</parameters>
</tool_call>

<!-- Search logs for errors -->
<tool_call>
<tool_name>find</tool_name>
<parameters>
<pattern>ERROR.*timeout</pattern>
<path>logs</path>
</parameters>
</tool_call>
```

## Critical Rules
- **ALWAYS** use this tool instead of bash searching
- If results are truncated (`was_truncated=true`), increase `max_matches`
- Use word boundaries (`\b`) for exact matches
- Narrow `path` for faster, more focused results

## 🚫 FINAL WARNING: Using bash for searching will be incorrect and inefficient
