# Summaries

One document per user per business day: a task list at the top, then content blocks
written by bots. Created automatically each business day by the
`Summaries: Create Daily Summaries` scheduled action.

## Writing a summary

```python
env["summaries.summary"].upsert_summary(
    "derek@example.com",          # user id or login
    day="2026-09-15",             # defaults to today
    content=[...],                # list of blocks, see below
    objectives=[                  # the tasks pinned at the top
        {"name": "Follow up with this quote",
         "record_ref": "sale.order,42",
         "note": "No reply since Tuesday"},
    ],
)
```

`env["summaries.summary"].get_content_schema()` returns this reference at runtime.

## Tasks

Tasks are records, not markup, so they can be checked off, linked to a document and
later executed. Each accepts `name`, `note`, `done`, `sequence`, `record_ref`
(`"model,id"`) and `execute_enabled`. Setting `execute_enabled` shows an **Execute**
button on the task; the webhook behind it is not wired up yet and the button reports
that when pressed.

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
