from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LeicaRegisterConfirmWizard(models.TransientModel):
    """Shows the user exactly what will be typed into the Leica portal and asks
    for confirmation before triggering the registration runner. A lead can only
    be registered once, so this is the last chance to fix anything."""
    _name = "leica.register.confirm.wizard"
    _description = "Confirm Leica Lead Registration"

    lead_id = fields.Many2one("crm.lead", string="Lead", required=True, readonly=True, ondelete="cascade")

    sales_region = fields.Char(string="Sales Region", readonly=True)
    market_segment = fields.Char(string="Market Segment", readonly=True)
    first_name = fields.Char(string="Contact First Name", readonly=True)
    last_name = fields.Char(string="Contact Last Name", readonly=True)
    company_name = fields.Char(string="Company Name", readonly=True)
    email = fields.Char(string="Email", readonly=True)
    phone = fields.Char(string="Contact Phone", readonly=True)
    address = fields.Char(string="Address", readonly=True)
    city = fields.Char(string="City", readonly=True)
    state_name = fields.Char(string="State/Province", readonly=True)
    zip_code = fields.Char(string="Zip", readonly=True)
    company_website = fields.Char(string="Company Website", readonly=True)
    product_interest = fields.Char(string="Product Interest", readonly=True)
    blk_arc_carrier = fields.Char(string="BLK ARC Carrier Type", readonly=True)
    media_category = fields.Char(string="Media & Entertainment Category", readonly=True)
    quantity = fields.Char(string="Quantity", readonly=True)
    expected_purchase_date = fields.Char(string="Expected Purchase Date", readonly=True)
    is_rfp = fields.Char(string="Part of an RFP?", readonly=True)
    demo_requested = fields.Boolean(string="Demonstration Requested", readonly=True)
    pricing_requested = fields.Boolean(string="Pricing Requested", readonly=True)
    meeting_requested = fields.Boolean(string="Meeting Requested", readonly=True)
    discussion_notes = fields.Text(string="Discussion Notes", readonly=True)

    is_blk_arc = fields.Boolean(readonly=True)
    is_media_segment = fields.Boolean(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        lead_id = res.get("lead_id") or self.env.context.get("default_lead_id") or self.env.context.get("active_id")
        if not lead_id:
            return res
        lead = self.env["crm.lead"].browse(lead_id)
        lead.ensure_one()
        data = lead._leica_portal_data()
        region_label = {"ca": _("Canada"), "us": _("United States")}.get(data["sales_region"], "")
        res.update({
            "lead_id": lead.id,
            "sales_region": region_label,
            "market_segment": data["market_segment"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "company_name": data["company_name"],
            "email": data["email"],
            "phone": data["phone"],
            "address": data["address"],
            "city": data["city"],
            "state_name": data["state_name"],
            "zip_code": data["zip"],
            "company_website": data["company_website"],
            "product_interest": data["product_interest"],
            "blk_arc_carrier": data["blk_arc_carrier"],
            "media_category": data["media_category"],
            "quantity": data["quantity"],
            "expected_purchase_date": data["expected_purchase_date"],
            "is_rfp": data["is_rfp"],
            "demo_requested": data["demo_requested"],
            "pricing_requested": data["pricing_requested"],
            "meeting_requested": data["meeting_requested"],
            "discussion_notes": data["discussion_notes"],
            "is_blk_arc": bool(data["blk_arc_carrier"]),
            "is_media_segment": lead.leica_market_segment == "media_ent",
        })
        return res

    def action_confirm_register(self):
        self.ensure_one()
        if not self.lead_id:
            raise UserError(_("No lead linked to this confirmation."))
        return self.lead_id._leica_do_register()
