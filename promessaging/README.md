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

`POST` to the sub-user's URL, `Content-Type: application/json`. Headers:

| Header | Value |
|---|---|
| *Auth Header* (default `Authorization`) | the **Auth Key**, optionally preceded by **Auth Prefix** (e.g. `Bearer`) |
| `X-REAL-Signature` | HMAC-SHA256 of the raw body, hex, when a signing secret is set |
| `X-REAL-Event` | the envelope's `event_id` |
| `X-REAL-Type` | the envelope's `type` |

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

### type: `lead_log`

Reserved for lead logging requests. The envelope is identical; only `payload` differs.
Not emitted yet.

### Adding a type

Call `subuser.dispatch("your_type", payload_dict, record=record)`. The envelope,
signing, logging and retry all come for free.
