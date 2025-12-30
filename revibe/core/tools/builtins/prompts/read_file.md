# Read File Tool – Safe File Inspection

`read_file` is the safest way to inspect file contents. It streams UTF-8 text with size guards so large files will not overwhelm the model. Prefer this tool instead of `bash cat`, `head`, or `tail`.

## Arguments
- `path` *(str, required)* – Relative or absolute file path inside the project.
- `offset` *(int, default 0)* – 0-based line to start reading from.
- `limit` *(int | None)* – Maximum lines to return. `None` reads until truncated by byte budget.

## Output
- `content` – Raw text chunk.
- `lines_read` – Number of lines returned.
- `was_truncated` – `True` when the byte limit was reached so more content remains.

## Usage Patterns
1. **Whole file preview (small files):**
   ```python
   read_file(path="revibe/core/tools/base.py")
   ```
2. **Paged reading for large files:**
   ```python
   chunk = read_file(path="logs/run.log", limit=500)
   if chunk.was_truncated:
       read_file(path="logs/run.log", offset=500, limit=500)
   ```
3. **Targeted slices:**
   ```python
   read_file(path="src/service.py", offset=120, limit=80)
   ```

## Best Practices
- Always inspect a file with `read_file` before modifying it via `search_replace` or `write_file`.
- Set `offset`/`limit` to keep responses concise; default chunk size is roughly 64 KB.
- If a file is binary or encoded differently, `read_file` will strip unreadable bytes; plan accordingly.
- Respect denylist/allowlist rules configured in the tool—requests outside the workspace will be rejected.

`read_file` maintains a short history of recently accessed files, helping future guardrails know which files you've inspected.