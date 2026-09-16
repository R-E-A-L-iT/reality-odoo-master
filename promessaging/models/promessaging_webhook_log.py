import json

from odoo import _, fields, models


class PromessagingWebhookLog(models.Model):
    """One record per webhook call, so failures can be inspected and retried."""
    _name = "promessaging.webhook.log"
    _description = "Sub-user Webhook Call"
    _order = "create_date desc"
    _rec_name = "event_id"

    subuser_id = fields.Many2one("promessaging.subuser", required=True, ondelete="cascade", index=True)
    webhook_type = fields.Char(required=True, index=True)
    event_id = fields.Char(index=True, readonly=True)

    res_model = fields.Char(string="Document Model")
    res_id = fields.Integer(string="Document ID")

    state = fields.Selection(
        [("pending", "Pending"), ("done", "Done"), ("error", "Error")],
        default="pending", required=True, index=True,
    )
    status_code = fields.Integer()
    request_url = fields.Char(string="URL")
    request_headers = fields.Text(string="Headers Sent")
    request_body = fields.Text()
    response_body = fields.Text()
    error = fields.Text()

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def action_retry(self):
        """Send the same envelope again."""
        self.ensure_one()
        envelope = json.loads(self.request_body or "{}")
        record = None
        if self.res_model and self.res_id and self.res_model in self.env:
            record = self.env[self.res_model].browse(self.res_id).exists()
        return self.subuser_id.dispatch(
            envelope.get("type") or self.webhook_type,
            envelope.get("payload") or {},
            record=record,
        )
