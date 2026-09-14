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
        return {
            "id": self.id,
            "body": self.body or "",
            "author": self.create_uid.display_name,
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
        draft = self._find_draft(res_model, res_id)
        if draft:
            draft.write({"body": body})
        else:
            draft = self.create({
                "res_model": res_model,
                "res_id": int(res_id),
                "body": body,
            })
        return draft._draft_data()

    def _body_html(self):
        self.ensure_one()
        return Markup("<br>").join(escape(line) for line in (self.body or "").splitlines())

    def action_send_draft(self):
        """Post the draft as a real message to the document's followers."""
        self.ensure_one()
        self.env["res.users"]._promessaging_check_send_message()
        record = self._get_document(self.res_model, self.res_id)
        record.message_post(
            body=self._body_html(),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.unlink()
        return True

    def action_discard_draft(self):
        self.ensure_one()
        self._get_document(self.res_model, self.res_id)
        self.unlink()
        return True
