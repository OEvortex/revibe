# Todo Tool – Lightweight Task Tracker

Create and manage structured task lists for complex coding sessions.

## When to Use
- Task has 3+ steps or multiple components
- User requests a todo list explicitly
- Breaking down user requirements into actionable items
- Tracking progress on multi-step implementations

## When NOT to Use
- Single, trivial tasks
- Purely informational queries
- Tasks completable in <3 steps

## Interface
- `action: "read"` – Return current todo list
- `action: "write"` – Replace entire list with provided `todos` array

## Todo Fields
| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | str | Unique identifier |
| `content` | str | Clear, actionable description |
| `status` | `pending` \| `in_progress` \| `completed` \| `cancelled` | Only one `in_progress` |
| `priority` | `low` \| `medium` \| `high` | Default `medium` |

## Best Practices
1. Initialize todos early after understanding requirements
2. Keep only one task `in_progress` at a time
3. Update todos as you discover new subtasks
4. Mark tasks `completed` only when fully done
5. Use clear descriptions with file names/modules

## Examples

### Read current list
```json
{"action": "read"}
```

### Create plan
```json
{
  "action": "write",
  "todos": [
    {"id": "1", "content": "Review existing code", "status": "pending", "priority": "high"},
    {"id": "2", "content": "Implement feature X", "status": "in_progress", "priority": "high"},
    {"id": "3", "content": "Write tests", "status": "pending", "priority": "medium"}
  ]
}
```

### Update progress
```json
{
  "action": "write",
  "todos": [
    {"id": "1", "content": "Review existing code", "status": "completed", "priority": "high"},
    {"id": "2", "content": "Implement feature X", "status": "completed", "priority": "high"},
    {"id": "3", "content": "Write tests", "status": "in_progress", "priority": "medium"}
  ]
}
```