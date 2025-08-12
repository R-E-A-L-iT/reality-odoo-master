# -*- coding: utf-8 -*-

import ast
import base64
import requests
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from odoo.tools import format_date
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)



class productType(models.Model):
    _inherit = "product.template"
    skuhidden = fields.One2many("ir.model.data", "res_id", readonly=True)
    sku = fields.Char(related="skuhidden.name", string="SKU")

    def import_images_from_url(self):
        for product in self:
            sku = product.sku
            if not sku:
                continue

            image_url = f"https://cdn.r-e-a-l.it/images/ecommerce/Leica/{sku}/{sku}-01.png"

            try:
                response = requests.get(image_url, timeout=5)
                if response.status_code == 200:
                    product.image_1920 = base64.b64encode(response.content)
                    _logger.info(f"ProPortal: Uploaded image for {sku}")
                    self.env.cr.commit()
                else:
                    _logger.warning(f"ProPortal: Image not found for {sku} (status {response.status_code})")
            except Exception as e:
                _logger.error(f"ProPortal: Error processing {sku}: {e}")

    @api.model
    def create(self, vals):
        record = super(productType, self).create(vals)
        if "sku" in vals:
            self._update_skuhidden(record.id, vals["sku"], record.name)
        return record

    def write(self, vals):
        result = super(productType, self).write(vals)
        if "sku" in vals:
            for record in self:
                self._update_skuhidden(record.id, vals["sku"], record.name)
        return result

    def _update_skuhidden(self, record_id, sku_value, record_name):
        IrModelData = self.env["ir.model.data"]
        data = IrModelData.search([("res_id", "=", record_id), ("model", "=", "product.template")], limit=1)
        if data:
            data.write({"name": sku_value, "display_name": record_name})
        else:
            IrModelData.create({"name": sku_value, "module": "",
                                "model": "product.template", "res_id": record_id,
                                "display_name": record_name,
                                })

class visitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", help="The IP address of the visitor")

class person(models.Model):
    _inherit = "res.partner"

    products = fields.One2many(
        "stock.lot", "owner", string="Products", readonly=True
    )
    parentProducts = fields.One2many(
        related="parent_id.products", string="Company Products", readonly=True
    )

    type = fields.Selection(
        selection_add=[("renewal", "Renewal contact")],
        ondelete={"renewal": "set default"},  # fallback if removed
    )

    def action_open_create_renewal_contact(self):
        """Open the child partner creation dialog prefilled as a Renewal contact."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("base.action_partner_form")
        
        action.update({
            "view_mode": "form",
            "views": [(self.env.ref("base.view_partner_form").id, "form")],
            "target": "current",
            "context": {
                **self._context,
                "default_parent_id": self.id,
                "default_type": "renewal",
                "default_is_company": False,
            },
        })
        return action

    @api.model
    def cron_send_ccp_renewal_reminders(self):
        env = self.env
        Lot = env["stock.lot"].sudo()

        owner_field = "owner" if "owner" in Lot._fields else "owner_id"

        companies = self.sudo().search([
            ("is_company", "=", True),
            ("child_ids.type", "=", "renewal"),
            ("child_ids.email", "!=", False),
            ("active", "=", True),
        ])
        if not companies:
            return

        sent_total = 0
        for company in companies:
            renewal_contacts = company.child_ids.filtered(
                lambda p: p.type == "renewal" and p.email
            )
            if not renewal_contacts:
                continue

            lots = Lot.search([
                (owner_field, "=", company.id),
                ("expire", "!=", False),
                ("ccp_renewal_reminder_sent", "=", False),
            ])
            if not lots:
                continue

            expiring = lots.filtered(lambda l: l.ccp_status == "expiring")
            if not expiring:
                continue

            items = []
            for l in expiring:
                prod = l.product_id.display_name or ""
                sku = getattr(l, "sku", False) or getattr(l.product_id, "default_code", False)
                sku_part = f" ({sku})" if sku else ""
                exp_str = format_date(env, l.expire)
                items.append(f"<li>{prod}{sku_part} — SN: {l.name} — Expires {exp_str}</li>")

            email_to = ",".join(sorted(set(renewal_contacts.mapped("email"))))
            email_from = company.email or env.company.email or False

            email_values = {"email_to": email_to}
            if email_from:
                email_values["email_from"] = email_from

            template = self.env.ref("proportal.tmpl_ccp_renewal_reminder")
            items_html = "<ul>" + "".join(items) + "</ul>"
            template.with_context(items_html=items_html).send_mail(
                company.id, force_send=True, email_values={"email_to": email_to, "email_from": email_from}
            )

            expiring.write({
                "ccp_renewal_reminder_sent": True,
                "ccp_renewal_reminder_sent_on": fields.Datetime.now(),
            })
            sent_total += len(expiring)

        _logger.info("CCP renewal reminders sent for %s lots", sent_total)


class productInstance(models.Model):
    _inherit = "stock.lot"

    # Store Data For CCP Tracking
    owner = fields.Many2one("res.partner", string="Owner")
    equipment_number = fields.Char(string="Equipment Number")
    sku = fields.Char(related="product_id.sku", readonly=True, string="SKU")
    expire = fields.Date(
        string="Expiration Date",
        default=lambda self: fields.Date.today(),
        required=False,
    )
    formated_label = fields.Char(compute="_label")
    publish = fields.Boolean(string="publish", default="True")

    ccp_status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("expiring", "Expiring soon"),
            ("expired", "Expired"),
        ],
        string="Status",
        compute="_compute_ccp_status",
        store=False,
        readonly=True,
    )

    firmware_version = fields.Text(string='Firmware Version', help='Firmware version associated with this lot.')

    ccp_renewal_reminder_sent = fields.Boolean(
        string="CCP Renewal Reminder Sent", default=False, index=True
    )
    ccp_renewal_reminder_sent_on = fields.Datetime(
        string="CCP Reminder Sent On"
    )

    @api.depends("expire")
    def _compute_ccp_status(self):
        today = fields.Date.context_today(self)
        one_month = today + relativedelta(months=1)

        def _to_date(v):
            if not v:
                return None
            if isinstance(v, date):
                return v
            if isinstance(v, datetime):
                return v.date()
            # strings / anything else
            return fields.Date.to_date(v)

        for lot in self:
            lot.ccp_status = False
            exp = _to_date(lot.expire)
            if exp:
                if exp <= today:
                    lot.ccp_status = "expired"
                elif exp <= one_month:
                    lot.ccp_status = "expiring"
                else:
                    lot.ccp_status = "active"

    # Automate formated_label
    def _label(self):
        for i in self:
            parsedLabel = i.product_id.name.split(" - ")
            if len(parsedLabel) > 1:
                result = parsedLabel[1]
                for section in parsedLabel[2:]:
                    result = result + " - " + str(section)
                parsedLabel = result
            else:
                parsedLabel = parsedLabel[0]
            r = "#ccplabel+" + str(i.name) + "+" + str(parsedLabel)
            if i.expire != False:
                r = r + "+" + str(i.expire) 
            i.formated_label = r
