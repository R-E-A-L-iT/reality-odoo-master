# Summaries

One document per user per business day: free-form intro blocks, a task list, then
content blocks written by bots. Created automatically each business day by the
`Summaries: Create Daily Summaries` scheduled action.

## Writing a summary

```python
env["summaries.summary"].upsert_summary(
    "derek@example.com",          # user id or login
    day="2026-09-15",             # defaults to today
    intro=[...],                  # blocks ABOVE the tasks, free-form
    content=[...],                # blocks BELOW the tasks, see below
    objectives=[                  # the tasks pinned at the top
        {"name": "Follow up with this quote",
         "record_ref": "sale.order,42",
         "note": "No reply since Tuesday"},
    ],
)
```

`env["summaries.summary"].get_content_schema()` returns this reference at runtime.

## The three areas

| Field | Where | Use |
|---|---|---|
| `intro` | above the tasks | Whatever this particular day needs: a briefing, meeting notes, a heads-up. No fixed structure. |
| *(tasks)* | middle, always | `objectives`: checkable records with document links. |
| `content` | below the tasks | Objectives of the day, insights for tomorrow, stats. |

Both `intro` and `content` take the same blocks and are set the same way
(`set_intro`, `set_content`). An empty `intro` renders nothing.

## Tasks

Tasks are records, not markup, so they can be checked off, linked to a document and
later executed. Each accepts `name`, `note`, `done`, `sequence`, `record_ref`
(`"model,id"`) and `execute_enabled`. Setting `execute_enabled` shows an **Execute**
button on the task; the webhook behind it is not wired up yet and the button reports
that when pressed.

## Plans on a task

A task can carry a **plan**: the steps needed to finish it, each marked as something the
**AI** can do or something a **human** must do. A **Plan** button appears on the right of
the task only once a plan exists; it opens a window where the steps can be read, edited,
reordered by hand, or sent off with **Execute**.

**Execute** hands the task and its plan to the reader's **Default AI Assistant**
(Settings → Users → Access Rights → Messaging) as a `task_execute` webhook. Editing then
pressing Execute saves first, so the assistant always receives what is on screen.

A plan is stored as JSON:

```json
{
  "summary": "Chase the renewal before Friday",
  "steps": [
    {"text": "Pull the last quote and its line items", "actor": "ai"},
    {"text": "Draft the follow-up email", "actor": "ai"},
    {"text": "Call the customer to confirm the budget", "actor": "human"}
  ]
}
```

`actor` is `ai` or `human`; anything else is rejected. A step may also carry `note` and
`done`.

### Finishing steps

Each step has a checkbox in the plan window. Ticking the last remaining step marks the
whole task done. The task's own checkbox still works on its own, without opening the
plan, for when it is finished some other way.

A bot ticks off what it did without resending the plan:

```json
{"subuser": "jerry", "key": "pmsg_...", "objective_id": 34, "steps_done": [0, 1],
 "message": "Quote pulled and follow-up drafted."}
```

`steps_done` takes step positions (0 is the first). `"steps_done_actor": "ai"` ticks off
every AI step at once. The reply reports back `task_done`, `plan_state` and the counts,
so the bot knows what it left for the person.

### Colours in the task list

Each task carries a stripe showing where it stands, with a tally above the list:

| Colour | State | Meaning |
|---|---|---|
| purple | `ai_ready` | the AI can still take steps on it |
| amber | `human_next` | under way, everything left needs a person |
| blue | `human_only` | nothing done yet and every step needs a person |
| green | `done` | finished |
| none | `no_plan` | no plan written |

## Writing plans and summaries as a bot

Both go through ProMessaging's reply endpoint, `POST /promessaging/webhook/reply`, with
the sub-user's Reply Key:

```json
{"subuser": "jerry", "key": "pmsg_...", "objective_id": 12,
 "plan": {"steps": [{"text": "...", "actor": "ai"}]}}
```

| Field | Meaning |
|---|---|
| `objective_id` + `plan` | write the plan for that task |
| `objective_id` + `message` | report back on the task; the text lands in its detail line |
| `summary_id` + `summary` | `{"intro": [...], "content": [...], "objectives": [...]}` to fill a day's summary |

The `task_execute` webhook already carries `objective_id` in
`payload.reply.async.body`, so a bot can answer the request it was given. Answering the
webhook directly with `{"plan": {"steps": [...]}}` updates the plan on the spot.

## Inline markup

Usable in any block text, and in task names:

| Markup | Result |
|---|---|
| `**bold**` | bold |
| `*italic*` | italic |
| `` `code` `` | monospace |
| `[label](https://example.com)` | external link |
| `[label](odoo:sale.order:42)` | opens that record in Odoo |

## Blocks

`content` is a JSON list. Every block is an object with a `type`. Blocks accepting a
`style` take one of: `default`, `primary`, `success`, `warning`, `danger`, `info`, `muted`.

```json
[
  {"type": "heading", "text": "Main objectives", "level": 2, "style": "primary"},
  {"type": "text", "text": "Chase [QT-123456](odoo:sale.order:42) before **noon**."},
  {"type": "callout", "style": "warning", "title": "Watch out", "text": "Renewal expires Friday."},
  {"type": "list", "style": "bullet", "items": ["First", "Second"]},
  {"type": "checklist", "items": [{"text": "Reviewed pipeline", "done": true}]},
  {"type": "kpi", "items": [{"label": "Quotes sent", "value": "12", "delta": "+3", "style": "success"}]},
  {"type": "progress", "label": "Monthly target", "value": 65, "style": "success"},
  {"type": "table", "columns": ["Quote", "Value"], "rows": [["QT-1", "$1,200"]]},
  {"type": "links", "items": [{"label": "QT-123456", "model": "sale.order", "id": 42},
                              {"label": "Docs", "url": "https://example.com"}]},
  {"type": "image", "src": "/web/image/...", "alt": "Chart", "width": "100%"},
  {"type": "divider"},
  {"type": "html", "html": "<b>sanitized</b> raw html"},
  {"type": "stats"},
  {"type": "section", "title": "Looking ahead", "style": "info",
   "blocks": [{"type": "text", "text": "Nested blocks, up to 3 levels deep."}]}
]
```

- `stats` renders the user's role-based performance graphs (sales, CRM, projects,
  timesheets) with a 4/12/26-week selector; clicking a bar opens those records.
- `html` is sanitized server-side; use it only when no other block fits.
- An unknown `type` or `style` is rejected with an error rather than silently dropped.

## Access

Everyone sees and edits their own summaries. The **Summaries Manager** group
(Settings → Users → Access Rights) sees and edits everyone's.
