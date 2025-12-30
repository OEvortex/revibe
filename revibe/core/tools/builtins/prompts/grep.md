# Grep Tool – Codebase Search Assistant

Use `grep` for fast, recursive regex searches across the project. It automatically leverages `rg` (ripgrep) when available and falls back to GNU `grep` otherwise. It already ignores common junk directories (`.git`, `.venv`, `node_modules`, etc.) and respects `.gitignore` plus `.vibeignore` entries.

## Arguments
- `pattern` *(str, required)* – Regex pattern (smart-case). Empty strings are rejected.
- `path` *(str, default ".")* – File or directory to search.
- `max_matches` *(int | None)* – Cap the number of matches (default 100). Request a larger window if needed.
- `use_default_ignore` *(bool, default True)* – Set to `false` to bypass `.gitignore`/`.ignore` rules.

## When to Use
- Locate function or class definitions before editing.
- See how a symbol, constant, or error string is used across the repo.
- Discover todos, feature flags, or configuration references.
- Investigate build/test failures by searching logs or stack traces.

## Tips for Better Results
1. Narrow `path` when possible (`src/feature`, `tests/unit`).
2. Use anchors or word boundaries for precision (e.g., `pattern="\bMyClass\b"`).
3. If output is truncated (`was_truncated=True`), rerun with a higher `max_matches` or narrower `path`.
4. Disable default ignore rules (`use_default_ignore=False`) only when you truly need to search generated or vendored code.

## Example Calls
```python
# Find all usages of a helper
grep(pattern="def build_payload", path="revibe/core")

# Search entire repo for TODOs, including ignored files
grep(pattern="TODO", path=".", use_default_ignore=False)

# Look for specific error messages with more results
grep(pattern="ConnectionError", path="logs", max_matches=250)
```

`grep` returns `matches`, `match_count`, and `was_truncated`. If `was_truncated` is true, adjust your query and search again.