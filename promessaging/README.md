# ProMessaging

Messaging controls for the chatter:

- **Can Send Messages** per user; blocked users write drafts instead.
- **Chatter drafts**: one parked draft per document, sent by someone with permission.
- **AI sub-users**: personas of an AI user, pinged with `~handle`, which forward the
  message to a webhook.

## AI sub-users

Mark a user as an **AI User** (Settings → Users → Access Rights → Messaging), then add
sub-users to it. Each sub-user has a unique `handle` and its own webhook settings.
Typing `~` in any message or log note opens a suggestion list, exactly like `@` does for
real users, and picking one inserts `~handle`.

When a message containing `~handle` is posted, that sub-user's webhook receives it as a
prompt. Messages authored by an AI user never trigger a webhook, so bots cannot loop.
Every call is recorded under Settings → Technical → Email → **Sub-user Webhook Calls**,
with the exact request, the response, and a **Retry** button.

## Signing in as a sub-user (browser)

When someone opens Odoo on a new device or session while logged into an **AI User**
account, a full-screen prompt asks which sub-user they are and for that sub-user's PIN.
Nothing else in the web client can be used until it is answered.

The choice is stored in the Odoo session, so it holds for every request from that
device until logout. A systray badge at the top right names the sub-user in charge;
clicking it re-opens the prompt to switch identity.

Accounts that are not marked as AI users see none of this.

## Acting as a sub-user (API)

Several AIs can share one Odoo account and still be told apart. Give each sub-user a
**PIN / API Key**, then have the AI sign in as the shared account and pass its handle and
PIN in the call context:

```python
models.execute_kw(db, uid, password, "sale.order", "write", [[42], {"state": "sent"}],
                  {"context": {"subuser_handle": "jerry", "subuser_pin": "…"}})
```

Everything written during that call is attributed to the sub-user: chatter messages,
log notes, and the tracking entries Odoo posts by itself ("Quotation confirmed",
field changes). The chatter shows the sub-user's name and avatar instead of the shared
account's, and every message carries a `subuser_id` for filtering later.

`promessaging.subuser.authenticate(handle, pin)` returns the sub-user's identity, or
`false`, so an AI can check its credentials before starting.

A wrong or missing PIN is not an error: the action simply proceeds under the shared
account, as before.

The sub-user's identity is a contact created automatically on first use, named after
the sub-user, carrying its avatar and the owning account's email address.

## Webhook request

`POST` to the sub-user's URL, `Content-Type: application/json`.

A sub-user's webhook settings mirror what the receiver gives you, one for one:

| Receiver shows | Sub-user field |
|---|---|
| POST to | **POST to** |
| key | **key** |
| header | **header** — paste the whole line, e.g. `Authorization: Bearer crsr_...` |

The **header** line is sent verbatim. If it holds only a header name, the **key** is sent
as its value; with nothing but a key, `Authorization: Bearer <key>` is used. Odoo also
sends `X-REAL-Event` and `X-REAL-Type` so a receiver can route by event.

Every call shares one envelope; only `payload` changes per type:

```json
{
  "version": "1.0",
  "type": "prompt",
  "event_id": "3f2a…",
  "sent_at": "2026-09-16T14:03:11Z",
  "odoo": {"base_url": "https://…", "database": "prod", "company": {"id": 1, "name": "R-E-A-L.iT Solutions"}},
  "subuser": {"id": 3, "name": "Grok Sales", "handle": "groksales", "description": "…",
              "ai_user": {"id": 12, "name": "Grokbot"}},
  "actor": {"user_id": 7, "name": "Ezekiel deBlois", "login": "ezekiel@…", "email": "ezekiel@…"},
  "context": {"model": "crm.lead", "id": 42, "name": "BLK360 G2 Rental", "url": "https://…"},
  "payload": { }
}
```

`context` is `false` when the call is not about a document.

### type: `prompt`

Sent when a user pings the sub-user in a message.

```json
"payload": {
  "prompt": "groksales draft a follow-up for this quote",
  "raw_text": "~groksales draft a follow-up for this quote",
  "message": {"id": 991, "body_html": "…", "posted_at": "2026-09-16 14:03:11",
              "is_note": true, "author": {"partner_id": 5, "name": "Ezekiel deBlois"}},
  "reply": {"mode": "chatter_note", "thread_model": "crm.lead", "thread_id": 42,
            "how": "Answer with JSON {\"reply\": \"text\"} to have it posted as a log note."}
}
```

`prompt` is the message text with the `~` stripped off the handles.

**Response.** Any 2xx counts as delivered. Return `{"reply": "text"}` and, when the
sub-user has **Post Replies** on, that text is posted as a log note authored by the AI
user. Return nothing to stay silent and post back through the Odoo API later.

### type: `draft_rewrite`

Sent when someone presses **Regenerate** on a chatter draft an AI wrote. The payload
carries the current draft and who asked:

```json
"payload": {
  "prompt": "Rewrite this draft using the current state of the document.",
  "draft": {"id": 8, "body": "...", "written_at": "2026-09-18 09:12:44"},
  "requested_by": {"user_id": 7, "name": "Ezekiel deBlois"},
  "reply": {"sync": "...", "async": {"url": "...", "body": {"draft_id": 8, "...": "..."}}}
}
```

Answer with `{"reply": "text"}` to replace the draft on the spot, or post to the reply
endpoint later with `draft_id`.

### type: `lead_log`

Reserved for lead logging requests. The envelope is identical; only `payload` differs.
Not emitted yet.

### Adding a type

Call `subuser.dispatch("your_type", payload_dict, record=record)`. The envelope,
signing, logging and retry all come for free.


## What a bot is allowed to do

Each sub-user has its own **Permissions** — the same Odoo groups a user has. Leave the
list empty and the sub-user simply inherits the AI account's permissions. Fill it in and
its actions are limited to those groups *as well as* the account's: a sub-user can never
do more than the account it runs under, only less.

**Mirror Permissions Of** copies a chosen user's groups onto the sub-user, and re-applies
them every time that sub-user signs in, so it keeps matching that person. This is how a
bot shared with one team is kept away from what that team cannot do itself, while the
same kind of bot used by an admin keeps the wider rights.

**Allowed Companies** works the same way: leave it empty to inherit the account's
companies, or list them to limit the sub-user to a subset. The company switcher only
offers what the sub-user may use, and `env.companies` is narrowed server-side, so
records of other companies stay out of reach. A **Default Company** picks which one it
starts in.

Enforced on every model access check and on `has_group`, so menus, buttons and CRUD all
respect it. Two things still follow the account rather than the sub-user: **record rules**
(which rows are visible) and **field-level group restrictions**. Narrow the account
itself if those matter.

## Keeping a user out of pings and DMs

**Cannot Be Pinged** on a user (Settings → Users → Access Rights → Messaging) takes them
out of reach:

- they no longer appear in the `@` list in any composer;
- they no longer appear in Discuss "New message" or in channel invitations;
- a Direct Message to them is refused, as is adding them to a conversation;
- if someone types their name anyway, they are dropped from the recipients rather than
  notified.

Conversations that already exist are hidden from the messaging menu and the Discuss
sidebar, and nothing can be written into them.

They can still message other people and take part in channels they are already in; the
setting only stops others reaching them that way. When they write to someone, that
conversation naturally comes back into view for the person they wrote to.

## Pictures

Each sub-user has an **Avatar** on its form, top right. Upload one and it is used
everywhere that sub-user appears: as the author's face on chatter messages and log notes
it writes, in the assistants panel, in the `~` suggestion list, and in the sub-user list.
Without one, a coloured circle with the sub-user's initial is shown instead.

The picture is copied onto the sub-user's identity contact, so changing it updates the
face on everything it has already posted.

## Who can use which bot

Each sub-user has a **Usable By** list on its form. Leave it empty and everyone can use
that bot; fill it in and only those users can. The limit is complete:

- only permitted bots appear in the `~` list and in the AI assistants panel;
- typing `~handle` for a bot you may not use leaves plain text, sends no webhook, and
  is not highlighted, so it is visible that nothing was pinged;
- opening a conversation with it is refused server-side.

Users also have an optional **Default AI Assistant** (Settings → Users → Access Rights →
Messaging). It is used when a request needs a bot and none is assigned yet — for
example rewriting a draft that a person wrote. A bot the user may not use is never
chosen, even when set as their default.

## Drafts written by a bot

A draft has a **subject** of its own, kept apart from the body, so nothing has to be
written into the text. Both are set through the reply endpoint — either on an existing
draft, or by writing a new one straight onto a document:

```json
{"subuser": "jerry", "key": "pmsg_...",
 "draft": {"res_model": "sale.order", "res_id": 42,
           "subject": "Following up on your quote",
           "body": "Hi Ken, ..."}}
```

To change one that already exists, send `draft_id` with `subject`, `body`, or both;
whatever is left out keeps its current value. A missing document or body is refused
(`missing_document`, `missing_body`).

When the draft is sent, its subject becomes the message's subject. On an opportunity
that subject also satisfies the Email Subject requirement, so a draft carrying its own
subject sends without one being set on the lead.

### Generating one on demand

The draft panel always carries the same button: **Generate** when there is no draft yet,
**Regenerate** once there is. It asks the reader's Default AI Assistant — or, for an
existing draft, whichever sub-user wrote it — over a `draft_write` (or `draft_rewrite`)
webhook carrying the document.

Answer straight away with `{"draft": {"subject": "...", "body": "..."}}` and the text
appears in the editor for review. Answer later by posting a `draft` back to the reply
endpoint; the panel picks it up.

### On small screens

The assistants bubble is hidden below Odoo's small-screen breakpoint (768px), where it
would sit on top of the controls underneath. Everything else — drafts, pings, sub-user
sign-in — works as usual on a phone.

## Replies from the AI (inbound webhook)

Every prompt Odoo sends carries a `payload.reply` block describing both ways to answer:

- **Immediately**: answer the webhook request with `{"reply": "text"}`.
- **Later**: `POST` to `/promessaging/webhook/reply` on the Odoo instance. Use this when
  the receiver acknowledges first and thinks afterwards (Cursor automations do this:
  they return a run id right away).

### Request

```json
{
  "subuser": "jerry",
  "key": "pmsg_...",
  "chat_id": 12,
  "message": "Here is what I found."
}
```

| Field | Meaning |
|---|---|
| `subuser` | the sub-user's handle (optional, but it makes the key lookup exact) |
| `key` | that sub-user's **Reply Key**, from its settings. May instead be sent as `Authorization: Bearer <key>` |
| `message` | the text to post (`reply` and `text` are accepted too) |
| `chat_id` | the direct conversation to answer, as given in the prompt payload |
| `user_id` / `user_login` | answer a person directly; the conversation with them is created if needed |
| `thread_model` + `thread_id` | instead post a log note on that document, for answers to a `~handle` ping |
| `draft_id` | replace that chatter draft, for answers to a `draft_rewrite` request |

Give one of `chat_id`, `user_id`/`user_login`, `draft_id`, or `thread_model` + `thread_id`.

### Response

```json
{"ok": true, "target": "chat", "chat_id": 12, "user_id": 7, "message_id": 88}
```

Errors come back as `{"ok": false, "error": "invalid_key"}`; other codes are
`missing_message`, `unknown_chat`, `unknown_user`, `unknown_model`,
`unknown_document` and `no_target`.

The reply appears in that person's AI assistants panel, authored by the sub-user, and
the open window picks it up within seconds.
