from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PromessagingDraft(models.Model):
    """A draft message parked on a document's chatter. Users who may not send
    messages write one; users who may send messages edit it and send it."""
    _name = "promessaging.draft"
    _description = "Chatter Draft Message"
    _order = "write_date desc"

    res_model = fields.Char(string="Document Model", required=True, index=True)
    res_id = fields.Integer(string="Document ID", required=True, index=True)
    body = fields.Text(string="Draft Message")
    subuser_id = fields.Many2one(
        "promessaging.subuser", string="Written By (AI)", ondelete="set null",
        help="Set when an AI sub-user wrote this draft.",
    )

    _sql_constraints = [
        ("promessaging_draft_unique_document", "unique(res_model, res_id)",
         "A document can only have one draft message at a time."),
    ]

    @api.model
    def _get_document(self, res_model, res_id, mode="read"):
        """Return the document, making sure the user really has access to it."""
        if res_model not in self.env:
            raise UserError(_("Unknown document model %s.", res_model))
        Model = self.env[res_model]
        if not hasattr(Model, "message_post"):
            raise UserError(_("Documents of type %s have no chatter.", res_model))
        record = Model.browse(int(res_id)).exists()
        if not record:
            raise UserError(_("This document no longer exists."))
        record.check_access_rights(mode)
        record.check_access_rule(mode)
        return record

    @api.model
    def _find_draft(self, res_model, res_id):
        return self.search(
            [("res_model", "=", res_model), ("res_id", "=", int(res_id))], limit=1
        )

    def _draft_data(self):
        """Values sent to the chatter. Empty recordset means no draft."""
        if not self:
            return False
        self.ensure_one()
        subuser = self.subuser_id.sudo()
        return {
            "id": self.id,
            "body": self.body or "",
            "author": subuser.name if subuser else self.create_uid.display_name,
            "is_ai": bool(subuser),
            "can_regenerate": bool(self._regenerate_subuser()),
            "subuser": {"id": subuser.id, "name": subuser.name, "handle": subuser.handle}
            if subuser else False,
            "date": fields.Datetime.to_string(self.write_date),
        }

    @api.model
    def get_draft(self, res_model, res_id):
        self._get_document(res_model, res_id)
        return self._find_draft(res_model, res_id)._draft_data()

    @api.model
    def set_draft(self, res_model, res_id, body):
        """Create or overwrite the single draft of a document."""
        self._get_document(res_model, res_id)
        body = (body or "").strip()
        if not body:
            raise UserError(_("The draft message is empty."))
        acting = self.env["promessaging.subuser"]._active_subuser()
        draft = self._find_draft(res_model, res_id)
        values = {"body": body, "subuser_id": acting.id if acting else False}
        if draft:
            draft.write(values)
        else:
            draft = self.create(dict(values, res_model=res_model, res_id=int(res_id)))
        return draft._draft_data()

    def _body_html(self):
        self.ensure_one()
        return Markup("<br>").join(escape(line) for line in (self.body or "").splitlines())

    def _check_email_subject(self, record):
        """Opportunities must carry an Email Subject, same as the composer."""
        if record._name != "crm.lead" or "ba_email_subject" not in record._fields:
            return
        if record.type == "opportunity" and not record.ba_email_subject:
            raise UserError(_(
                "Please set an Email Subject on this opportunity before sending the draft."
            ))

    def action_send_draft(self):
        """Post the draft as a real message to the document's followers, the same
        way the chatter composer would."""
        self.ensure_one()
        self.env["res.users"]._promessaging_check_send_message()
        record = self._get_document(self.res_model, self.res_id)
        self._check_email_subject(record)

        # leads send the customer a header-less layout (chatter_google_message);
        # the flag is only set while the notification emails are rendered
        simple_layout = "simple_email_layout" in record._fields
        original_layout = record.simple_email_layout if simple_layout else False
        if simple_layout and not original_layout:
            record.write({"simple_email_layout": True})
        try:
            record.message_post(
                body=self._body_html(),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        finally:
            if simple_layout and record.simple_email_layout != original_layout:
                record.write({"simple_email_layout": original_layout})

        self.unlink()
        return True

    def action_regenerate(self, instructions=None):
        """Ask the sub-user that wrote this draft to rewrite it."""
        self.ensure_one()
        subuser = self._regenerate_subuser()
        if not subuser:
            raise UserError(_(
                "No AI assistant to ask. Set a default AI assistant on your user, "
                "or have one write the draft first."
            ))
        record = self._get_document(self.res_model, self.res_id)
        payload = {
            "prompt": instructions or _(
                "Rewrite this draft using the current state of the document."
            ),
            "draft": {
                "id": self.id,
                "body": self.body or "",
                "written_at": fields.Datetime.to_string(self.write_date),
            },
            "requested_by": {
                "user_id": self.env.user.id,
                "name": self.env.user.name,
            },
            "reply": subuser._reply_instructions(
                thread_model=self.res_model, thread_id=self.res_id
            ),
        }
        # answers come back to the draft, not the chatter
        payload["reply"]["async"]["body"]["draft_id"] = self.id
        payload["reply"]["async"]["body"].pop("thread_model", None)
        payload["reply"]["async"]["body"].pop("thread_id", None)
        payload["reply"]["sync"] = _(
            "Answer with JSON {\"reply\": \"text\"} to replace the draft immediately."
        )

        result = subuser.dispatch("draft_rewrite", payload, record=record)
        reply = (result.get("data") or {}).get("reply") if result.get("ok") else None
        if reply:
            self.write({"body": str(reply), "subuser_id": subuser.id})
        return {
            "ok": bool(result.get("ok")),
            "error": result.get("error"),
            "updated": bool(reply),
        }

    def _regenerate_subuser(self):
        """Who to ask: whoever wrote it, else the reader's default assistant."""
        self.ensure_one()
        written_by = self.subuser_id.sudo()
        if written_by and written_by._allowed_for(self.env.user):
            return written_by
        return self.env.user._promessaging_default_subuser()

    def action_discard_draft(self):
        self.ensure_one()
        self._get_document(self.res_model, self.res_id)
        self.unlink()
        return True
