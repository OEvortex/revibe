# Todo Tool – Task Tracker for Multi-Step Work

Create and manage structured task lists for complex coding sessions. Use this to track progress on multi-step tasks.

## Required Parameter

- **`action`** (string) - Action to perform: `"read"` (view current todos) or `"write"` (update todos)

## Optional Parameter

- **`todos`** (array of TodoItem objects) - Complete list of todos when `action="write"`. Required for write operations.

## When to Use

✅ **Use todo tool when:**
- Task has 3+ steps or multiple components
- User requests a todo list explicitly
- Breaking down user requirements into actionable items
- Tracking progress on multi-step implementations
- Managing complex refactoring or feature development

❌ **Don't use for:**
- Single, trivial tasks
- Purely informational queries
- Tasks completable in <3 steps

## TodoItem Structure

Each todo item requires these fields:

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `id` | string | Yes | Unique identifier (e.g., "1", "task-1", "setup") |
| `content` | string | Yes | Clear, actionable description of the task |
| `status` | string | No | One of: `"pending"`, `"in_progress"`, `"completed"`, `"cancelled"`. Default: `"pending"` |
| `priority` | string | No | One of: `"low"`, `"medium"`, `"high"`. Default: `"medium"` |

## Important Rules

1. **Complete list required** - When `action="write"`, you must provide the COMPLETE list of todos (not incremental updates)
2. **Unique IDs** - Each todo `id` must be unique within the list
3. **One in_progress** - Only one task should be `in_progress` at a time
4. **Max limit** - Maximum 100 todos allowed
5. **Read before write** - Use `action="read"` first to see current state, then update

## Example Usage

### Read current todos
```python
todo(action="read")
# Returns: message, todos list, total_count
```

### Create initial plan
```python
todo(
    action="write",
    todos=[
        {"id": "1", "content": "Review existing codebase structure", "status": "pending", "priority": "high"},
        {"id": "2", "content": "Implement new feature X in src/feature.py", "status": "in_progress", "priority": "high"},
        {"id": "3", "content": "Write unit tests in tests/test_feature.py", "status": "pending", "priority": "medium"},
        {"id": "4", "content": "Update documentation", "status": "pending", "priority": "low"}
    ]
)
```

### Update progress (provide complete list)
```python
# First read current state
current = todo(action="read")

# Then write complete updated list
todo(
    action="write",
    todos=[
        {"id": "1", "content": "Review existing codebase structure", "status": "completed", "priority": "high"},
        {"id": "2", "content": "Implement new feature X in src/feature.py", "status": "completed", "priority": "high"},
        {"id": "3", "content": "Write unit tests in tests/test_feature.py", "status": "in_progress", "priority": "medium"},
        {"id": "4", "content": "Update documentation", "status": "pending", "priority": "low"},
        {"id": "5", "content": "Add integration tests", "status": "pending", "priority": "medium"}  # New task added
    ]
)
```

## Best Practices

1. **Initialize early** - Create todos right after understanding requirements
2. **Clear descriptions** - Include file names, modules, or specific actions in `content`
3. **One in_progress** - Keep only one task `in_progress` at a time
4. **Update frequently** - Update todos as you complete tasks or discover new subtasks
5. **Complete updates** - Always provide the full list when writing (merge with existing)
6. **Mark completed** - Only mark tasks `completed` when fully done (not just started)
7. **Use priorities** - Set `priority` appropriately to guide work order

## Output Format

Returns a result object with:
- **`message`** (string) - Status message (e.g., "Retrieved 5 todos" or "Updated 5 todos")
- **`todos`** (array) - Complete list of TodoItem objects
- **`total_count`** (integer) - Total number of todos

## Common Workflow

```python
# Step 1: Read current todos (if any)
current_todos = todo(action="read")

# Step 2: Create or update plan
todo(
    action="write",
    todos=[
        {"id": "1", "content": "Task 1", "status": "completed", "priority": "high"},
        {"id": "2", "content": "Task 2", "status": "in_progress", "priority": "high"},
        {"id": "3", "content": "Task 3", "status": "pending", "priority": "medium"}
    ]
)

# Step 3: As you work, update status
todo(
    action="write",
    todos=[
        {"id": "1", "content": "Task 1", "status": "completed", "priority": "high"},
        {"id": "2", "content": "Task 2", "status": "completed", "priority": "high"},
        {"id": "3", "content": "Task 3", "status": "in_progress", "priority": "medium"}
    ]
)
```
