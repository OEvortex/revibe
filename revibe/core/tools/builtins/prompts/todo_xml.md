# Todo Tool – XML Format Guide

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

## XML Tool Call Format

### Read todos
```xml
<tool_call>
<tool_name>todo</tool_name>
<parameters>
<action>read</action>
</parameters>
</tool_call>
```

### Write todos
```xml
<tool_call>
<tool_name>todo</tool_name>
<parameters>
<action>write</action>
<todos>[
  {"id": "1", "content": "Task description", "status": "pending", "priority": "high"}
]</todos>
</parameters>
</tool_call>
```

## Parameters
- `action` *(required)* – `"read"` or `"write"`
- `todos` *(required for write)* – JSON array of todo items

## Todo Item Fields
| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | str | Unique identifier |
| `content` | str | Clear, actionable description |
| `status` | `pending` \| `in_progress` \| `completed` \| `cancelled` | Only one `in_progress` |
| `priority` | `low` \| `medium` \| `high` | Default `medium` |

## Best Practices
- Initialize todos early after understanding requirements
- Keep only one task `in_progress` at a time
- Update todos as you discover new subtasks
- Mark tasks `completed` only when fully done
- Use clear descriptions with file names/modules

## Example XML Calls

```xml
<!-- Read current todo list -->
<tool_call>
<tool_name>todo</tool_name>
<parameters>
<action>read</action>
</parameters>
</tool_call>

<!-- Create initial plan -->
<tool_call>
<tool_name>todo</tool_name>
<parameters>
<action>write</action>
<todos>[
  {"id": "1", "content": "Review existing code", "status": "pending", "priority": "high"},
  {"id": "2", "content": "Implement feature X", "status": "pending", "priority": "high"},
  {"id": "3", "content": "Write tests", "status": "pending", "priority": "medium"}
]</todos>
</parameters>
</tool_call>

<!-- Update progress -->
<tool_call>
<tool_name>todo</tool_name>
<parameters>
<action>write</action>
<todos>[
  {"id": "1", "content": "Review existing code", "status": "completed", "priority": "high"},
  {"id": "2", "content": "Implement feature X", "status": "in_progress", "priority": "high"},
  {"id": "3", "content": "Write tests", "status": "pending", "priority": "medium"}
]</todos>
</parameters>
</tool_call>
```
