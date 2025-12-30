# Todo Tool – Lightweight Task Tracker

Use the `todo` tool to capture, update, and report progress on multi-step assignments. Maintaining a live checklist demonstrates planning discipline and makes it easy to resume work after interruptions.

## Interface Recap
- `action: "read"` – Return the current todo list.
- `action: "write"` – Replace the entire list with the provided `todos` array. You **must** send every task you want to keep; omissions are treated as deletions.

Each todo entry requires:
| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | str | Unique identifier ("1", "setup", etc.). |
| `content` | str | Clear, actionable description. |
| `status` | `pending` \| `in_progress` \| `completed` \| `cancelled` | Default `pending`. Only one task should be `in_progress`. |
| `priority` | `low` \| `medium` \| `high` | Default `medium`. |

## When to Create / Update Todos
- User provides multiple requirements or a numbered list.
- Work spans more than a couple of straightforward steps.
- You need to track investigations, blockers, or follow-ups.
- After finishing a task to log completion and next actions.

## Good Habits
1. **Initialize early:** After understanding the request, capture the major steps before diving into code.
2. **One task in progress:** Switch statuses proactively as you start/finish work.
3. **Reflect reality:** If you discover new subtasks or blockers, add them immediately.
4. **Keep descriptions precise:** Include file names, modules, or acceptance criteria so the intent is clear to reviewers.
5. **Close the loop:** Mark tasks `completed` only when changes are merged/tested according to the acceptance criteria.

## Examples
### Reading current list
```json
{
  "action": "read"
}
```

### Creating a plan
```json
{
  "action": "write",
  "todos": [
    {"id": "1", "content": "Audit builtin tool prompts", "status": "pending", "priority": "high"},
    {"id": "2", "content": "Improve bash + grep prompts", "status": "pending", "priority": "high"},
    {"id": "3", "content": "Update remaining tool prompts", "status": "pending", "priority": "medium"}
  ]
}
```

### Marking progress and adding discoveries
```json
{
  "action": "write",
  "todos": [
    {"id": "1", "content": "Audit builtin tool prompts", "status": "completed", "priority": "high"},
    {"id": "2", "content": "Improve bash + grep prompts", "status": "in_progress", "priority": "high"},
    {"id": "3", "content": "Update remaining tool prompts", "status": "pending", "priority": "medium"},
    {"id": "4", "content": "Document testing expectations", "status": "pending", "priority": "medium"}
  ]
}
```

### Wrapping up
```json
{
  "action": "write",
  "todos": [
    {"id": "2", "content": "Improve bash + grep prompts", "status": "completed", "priority": "high"},
    {"id": "3", "content": "Update remaining tool prompts", "status": "completed", "priority": "medium"},
    {"id": "4", "content": "Document testing expectations", "status": "completed", "priority": "medium"}
  ]
}
```

Maintain this list diligently to show deliberate planning and ensure no requirement is overlooked.