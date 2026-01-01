# ✏️ SEARCH & REPLACE TOOL - Your Primary File Editor

## 🚫 CRITICAL: NEVER USE BASH FOR FILE EDITING

**DO NOT use `bash` tool with `sed`, `awk`, `echo >`, or any shell text manipulation commands.** This `search_replace` tool is specifically designed for all file editing operations and is far superior to shell commands.

## Why Use This Tool (NOT Bash)
- ✅ **Deterministic edits** - Exact text matching ensures predictable changes
- ✅ **Smart error diagnostics** - Fuzzy matching shows you the closest text when searches fail
- ✅ **Atomic operations** - All blocks apply or none do (with detailed error reports)
- ✅ **Multi-block support** - Apply several edits in a single call
- ✅ **Safety rails** - Size limits, backup options, and detailed validation
- ✅ **Cross-platform** - Works identically on Windows, macOS, Linux

## Arguments
- `file_path` *(str, required)* – Target file path (relative or absolute within project)
- `content` *(str, required)* – One or more SEARCH/REPLACE blocks

## Block Format Syntax
```
<<<<<<< SEARCH
<exact text to find>
=======
<replacement text>
>>>>>>> REPLACE
```

### Block Rules
- Use **at least 5** `<`, `=`, and `>` characters (7 recommended for clarity)
- **Exact whitespace match required** - Every space, tab, and newline must match
- Blocks may be wrapped in code fences (` ``` `) - both formats are accepted
- Multiple blocks execute **sequentially** - later blocks see earlier changes

## ⚠️ Common Pitfalls to Avoid

| ❌ WRONG | ✅ CORRECT |
|----------|-----------|
| Guessing file content | Always `read_file` first to see exact text |
| Changing indentation in SEARCH | Copy indentation exactly from file |
| Including too much context | Keep SEARCH minimal but unique |
| Using `\n` escape sequences | Use actual newlines in the block |
| Forgetting trailing whitespace | Check for spaces at line ends |

## Best Practices

### 1️⃣ Always Read First
```python
# FIRST: Inspect the file
read_file(path="src/config.py")

# THEN: Apply precise edits based on what you saw
search_replace(
    file_path="src/config.py",
    content="""
<<<<<<< SEARCH
DEFAULT_TIMEOUT = 30
=======
DEFAULT_TIMEOUT = 60
>>>>>>> REPLACE
"""
)
```

### 2️⃣ Keep SEARCH Blocks Minimal But Unique
```python
# ❌ BAD: Too much context (fragile, may break on unrelated changes)
search_replace(
    file_path="app.py",
    content="""
<<<<<<< SEARCH
import os
import sys
from typing import Optional

class Config:
    timeout = 30  # <-- only this line needs to change
    retries = 3
=======
import os
...huge replacement...
>>>>>>> REPLACE
"""
)

# ✅ GOOD: Just enough to be unique
search_replace(
    file_path="app.py",
    content="""
<<<<<<< SEARCH
    timeout = 30  # <-- only this line needs to change
=======
    timeout = 60  # increased for slow networks
>>>>>>> REPLACE
"""
)
```

### 3️⃣ Multiple Edits in One Call
```python
# Apply several related changes atomically
search_replace(
    file_path="src/utils.py",
    content="""
<<<<<<< SEARCH
def old_function():
    pass
=======
def new_function():
    return True
>>>>>>> REPLACE

<<<<<<< SEARCH
CONSTANT = "old"
=======
CONSTANT = "new"
>>>>>>> REPLACE

<<<<<<< SEARCH
# TODO: refactor this
=======
# DONE: refactored
>>>>>>> REPLACE
"""
)
```

### 4️⃣ Creating New Content (Empty SEARCH Block)
```python
# Insert new code by searching for a unique anchor point
search_replace(
    file_path="src/models.py",
    content="""
<<<<<<< SEARCH
class User:
=======
from datetime import datetime

class User:
>>>>>>> REPLACE
"""
)
```

## Error Recovery Guide

### ❓ "Search text not found"
1. Run `read_file` to see the current file content
2. Check for **exact whitespace** (spaces vs tabs, trailing spaces)
3. Verify **line endings** match (`\n` vs `\r\n`)
4. The error message includes **fuzzy match suggestions** - use them!

### ❓ "Multiple occurrences found"
- The tool replaces only the **first** occurrence
- Add more surrounding context to make your search unique
- Consider if you actually want to replace all occurrences (use multiple blocks)

### ❓ "Content size exceeds limit"
- Default max is 100KB per call
- Split large changes into multiple calls
- Consider using `write_file` for complete file rewrites

## Behavior Guarantees
- **First occurrence only**: If search text appears multiple times, only the first match is replaced (with a warning)
- **Sequential execution**: Blocks apply in order; each sees the result of previous blocks
- **Fuzzy diagnostics**: Failed searches show similar text with diff highlighting
- **Permission respected**: Cannot edit files outside project boundaries
- **Optional backups**: Enable `create_backup=True` in config for `.bak` file creation

## Quick Reference

| Want to... | Do this |
|------------|---------|
| Edit part of a file | Use `search_replace` with precise blocks |
| Create a new file | Use `write_file` |
| Overwrite entire file | Use `write_file` with `overwrite=True` |
| Read file first | Use `read_file` before editing |
| Search for text | Use `grep` or `find` tool |

---

📌 **Remember**: Always `read_file` before `search_replace`. The edit will only succeed if your SEARCH text matches the file **exactly**.
