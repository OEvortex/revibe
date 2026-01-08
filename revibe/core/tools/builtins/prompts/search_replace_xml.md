# search_replace - XML Format

Edit files using SEARCH/REPLACE blocks in XML format. **This is the primary tool for editing files** - use it instead of bash commands.

## CRITICAL RULES (MUST FOLLOW)

1. **ALWAYS read_file FIRST** - You MUST see the exact file content before editing
2. **EXACT MATCH REQUIRED** - Every space, tab, newline must match exactly (copy directly from read_file output)
3. **USE PROPER FORMAT** - Follow the delimiter pattern precisely (7+ characters)
4. **WHITESPACE MATTERS** - Spaces ≠ tabs, trailing spaces matter, line endings matter

## Required Parameters

- **`file_path`** (string) - File to edit (relative to project root or absolute). File must exist.
- **`content`** (string) - SEARCH/REPLACE blocks containing your edits

## XML Tool Call Format

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>path/to/file</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
[exact text from file - copy EXACTLY from read_file output]
=======
[new text to replace with]
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

**Note:** In XML, you may need to escape `<` as `&lt;` and `>` as `&gt;` in the content, or use CDATA sections. The tool accepts both formats.

## SEARCH/REPLACE Block Format

```
<<<<<<< SEARCH
[exact text from file - copy it EXACTLY from read_file output]
=======
[new text to replace with]
>>>>>>> REPLACE
```

**Format Rules:**
- Use **7 or more** `<`, `=`, `>` characters (minimum: `<<<<<<<`, `=======`, `>>>>>>>`)
- SEARCH text must match file content exactly (whitespace, indentation, everything)
- Multiple blocks execute sequentially (top to bottom)
- First occurrence only per block (if multiple matches, only first is replaced)

## Complete Workflow Example

```xml
<!-- Step 1: ALWAYS read the file first -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>config.py</path>
</parameters>
</tool_call>

<!-- Step 2: After receiving results, copy text EXACTLY from result.content -->
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>config.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
TIMEOUT = 30
MAX_RETRIES = 3
=======
TIMEOUT = 60
MAX_RETRIES = 5
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

## Example: Single Edit

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>config.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
DEFAULT_TIMEOUT = 30
=======
DEFAULT_TIMEOUT = 60
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

## Example: Multiple Edits in One Call

```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>utils.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
def old_function():
    pass
=======
def new_function():
    return True
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE

&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
VERSION = "1.0"
=======
VERSION = "2.0"
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

## Common Errors & Solutions

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Search text not found" | SEARCH doesn't match file exactly | Read file first, copy text EXACTLY from read_file output |
| "Invalid SEARCH/REPLACE format" | Wrong delimiter format | Use 7+ characters: `<<<<<<<`, `=======`, `>>>>>>>` |
| Wrong indentation | Spaces/tabs don't match | Copy indentation exactly (spaces ≠ tabs) |
| Whitespace mismatch | Trailing spaces or line endings differ | Copy text exactly, including all whitespace |
| Multiple matches warning | SEARCH text appears multiple times | Add more context to make search unique (include surrounding lines) |

## Best Practices

1. ✅ **Read first, edit second** - Always use `read_file` before `search_replace`
2. ✅ **Copy exactly** - Don't retype text, copy directly from `read_file` output
3. ✅ **Minimal SEARCH** - Include only enough text to be unique (but enough context to match correctly)
4. ✅ **Preserve structure** - Keep indentation, spacing, and formatting exactly as in file
5. ✅ **Test incrementally** - Make one edit at a time for complex changes, verify each step
6. ✅ **Read error messages** - They show fuzzy matches and suggest what's close

## Common Mistakes

❌ **WRONG** - Editing without reading first:
```xml
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>config.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
TIMEOUT = 30
=======
TIMEOUT = 60
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
<!-- You don't know if this matches! -->
```

✅ **CORRECT** - Read first, then edit:
```xml
<!-- Step 1: Read -->
<tool_call>
<tool_name>read_file</tool_name>
<parameters>
<path>config.py</path>
</parameters>
</tool_call>

<!-- Step 2: Edit with exact text from result -->
<tool_call>
<tool_name>search_replace</tool_name>
<parameters>
<file_path>config.py</file_path>
<content>
&lt;&lt;&lt;&lt;&lt;&lt;&lt; SEARCH
[copy EXACTLY from read_file result.content]
=======
[new text]
&gt;&gt;&gt;&gt;&gt;&gt;&gt; REPLACE
</content>
</parameters>
</tool_call>
```

## DO NOT Use Bash for Editing

❌ **Never use:** `bash` with `sed`, `awk`, `echo >`, `cat >`, `printf >`, or any shell redirection
✅ **Always use:** `search_replace` - it's safer, provides better error messages, and handles edge cases

## XML Escaping Notes

In XML content, you may need to escape special characters:
- `<` can be written as `&lt;` or use CDATA
- `>` can be written as `&gt;` or use CDATA
- The tool accepts both escaped and unescaped formats in most cases
