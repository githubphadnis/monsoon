# WorkFlowy mirror — fractal task + context

WorkFlowy is monsoon's **visual layer**: a todo outline where each task is a node and
**all follow-up information lives as children** under that node. Postgres owns state
(reminders, ids, sync); WorkFlowy is where Prakalp thinks, expands, and adds context.

Everything is fractal — use the tree, not flat titles stuffed with metadata.

---

## Mental model

| Layer | Where | Role |
|-------|--------|------|
| **Bucket** | `Inbox` / `Today` / `Waiting` / … | Status column (folder) |
| **Task node** | Child of bucket | Title + `layoutMode: todo` + compact **note** metadata |
| **Context children** | Under task node | Human + monsoon follow-ups, links, snippets |

When you follow up on a task — in WorkFlowy or via WhatsApp — **new content attaches
under the same task node**, not as a sibling or a new top-level bullet.

---

## Example tree

```text
Personal Capture & Reminder
└── Today
    └── Call bank about wire transfer          ← task (todo)
        │   note: T18 · whatsapp · waiting · due 2026-07-08 10:00
        ├── [2026-07-07 14:22] spoke to agent, case #44921
        ├── link: https://bank.com/status
        ├── waiting: callback promised Thursday
        └── wa: excerpt from thread with Raj …  ← monsoon-pushed context
```

Prakalp adds bullets 6–7 manually in WorkFlowy. monsoon may append 8 when it links
a WA message or email to task #18.

---

## Sync rules

### Postgres → WorkFlowy (v1 push)

| Event | WorkFlowy action |
|-------|------------------|
| Task created | Create todo node under bucket with compact `note` (`T{n} · source · status · due`); store `tasks.workflowy_node_id` |
| Task status / bucket change | Move task node to new bucket parent |
| Task completed | Mark todo complete; move under `Done` |
| **Follow-up / context** | `POST /api/v1/nodes` with `parent_id = workflowy_node_id` |
| Reminder fired | Optional child: `[reminder sent] …` |

Context push triggers:

- WhatsApp: `note 18 …` or LLM links free-text to task id
- Gmail: promote email snippet to task
- Ollama: structured extract appended as child bullet

### WorkFlowy → Postgres (v1.2 reverse sync)

Read-only reconciliation on a schedule:

- List children of `workflowy_node_id`
- Skip known system prefixes (`id:`, `source:`, `due:`, `status:`)
- Upsert remaining children into `task_context_items`
- Feed context slice for Ollama / digest

**Postgres remains canonical** for reminders and task ids; WorkFlowy children are the
human-editable context surface.

---

## Data model (Postgres)

**Existing**

- `tasks.workflowy_node_id` — the task bullet

**Planned**

```text
task_context_items
  id
  task_id              → tasks
  workflowy_node_id    → child bullet in WF (null until synced)
  source               whatsapp | email | manual | monsoon | workflowy
  body                 text content
  source_ref           optional (inbound_message_id, email_message_id, …)
  created_at
```

`task_events` continues to log *that* something was added; `task_context_items` is
the queryable copy for LLM context slices.

---

## API notes (WorkFlowy)

- Create child: `POST /api/v1/nodes` with `parent_id` = task's `workflowy_node_id`
- Task bullet: `layoutMode: "todo"` on create
- Long text: use `note` field or child bullet (prefer **child** for fractal visibility)
- Position: `"bottom"` for chronological follow-ups

Ref: https://beta.workflowy.com/api-reference/

---

## WhatsApp ergonomics (future)

| Command | Behavior |
|---------|----------|
| `note 18 called, waiting callback` | Append context child under task #18 in WF + DB |
| `todo …` (new) | New task node |
| Reply threading (later) | Link inbound WA to open task → append under that node |

---

## What this is not

- Flat mirror where title = entire story
- WorkFlowy as reminder engine (due dates stay in Postgres)
- Replacing WorkFlowy UI — this **is** the UI for task context
