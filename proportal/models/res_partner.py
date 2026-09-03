# -*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request

from markupsafe import Markup

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Odoo 19 removed the standard res.partner.mobile field. Re-declared here so
    # this module's mobile references keep working regardless of module load order.
    mobile = fields.Char(string="Mobile")

    def init(self):
        # The official 17->19 upgrade drops the native res_partner.mobile column.
        # _auto_init won't re-create it reliably on the upgrade platform (and the
        # base upgrade may drop it again after a version-gated migration), so we
        # force it here: init() runs on every module update, after base has fully
        # loaded, so the re-declared column is guaranteed to exist each build.
        super().init()
        self.env.cr.execute(
            "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS mobile varchar"
        )

    portal_administrator = fields.Boolean(
        string="Portal Administrative User",
        help="If enabled on this contact, the associated portal user sees Company Settings."
    )
    portal_companies_ids = fields.Many2many('res.partner', relation='res_partner_companies_rel', column1='res_partner_id', column2='id', string='Portal Companies', domain=[('active', '=', True), ('is_company', '!=', False)])

    products = fields.One2many(
        "stock.lot", "owner", string="Products", readonly=True, domain=[('company_id', '=', 1)],
    )
    parentProducts = fields.One2many(
        related="parent_id.products", string="Company Products", readonly=True
    )

    type = fields.Selection(
        selection_add=[("renewal", "Renewal contact")],
        ondelete={"renewal": "set default"},  # fallback if removed
    )

    def get_portal_company_ids(self):
        self.ensure_one()
        main_company = self.commercial_partner_id
        companies = (main_company | self.portal_companies_ids)
        return companies.ids

    def action_open_create_renewal_contact(self):
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
                # Markup % escapes its arguments, so a product name containing
                # & or < can't corrupt the email markup.
                items.append(Markup("<li>%s%s — SN: %s — Expires %s</li>")
                             % (prod, sku_part, l.name, exp_str))

            email_to = ",".join(sorted(set(renewal_contacts.mapped("email"))))
            email_from = company.email or env.company.email or False

            email_values = {"email_to": email_to}
            if email_from:
                email_values["email_from"] = email_from

            template = self.env.ref("proportal.tmpl_ccp_renewal_reminder")
            # t-out escapes plain strings (t-raw, which didn't, was removed
            # in Odoo 19), so this must be Markup or the renewal list would
            # render as literal <li> tags in the email. Markup.join keeps the
            # already-escaped items safe.
            items_html = Markup("<ul>") + Markup("").join(items) + Markup("</ul>")
            template.with_context(items_html=items_html).send_mail(
                company.id, force_send=True, email_values={"email_to": email_to, "email_from": email_from}
            )

            expiring.write({
                "ccp_renewal_reminder_sent": True,
                "ccp_renewal_reminder_sent_on": fields.Datetime.now(),
            })
            sent_total += len(expiring)

        _logger.info("CCP renewal reminders sent for %s lots", sent_total)

    def _calc_nick(self):
        if self.is_company == True:
            self.company_nickname = False
        else:
            self.company_nickname = "_"

    def _calc_nick_return(self):
        if self.is_company == True:
            return False
        else:
            return "_"

    # Function to initilize required field.
    def init_company_nickname(self):
        _logger.error("INIT NICKNAME")
        for partner in self.env["res.partner"].search(
            [("company_nickname", "=", False)]
        ):
            partner.company_nickname = "_"

        for partner in self.env["res.partner"].search(
            [("company_nickname", "=", False), ("active", "=", False)]
        ):
            partner.company_nickname = "_"

    company_nickname = fields.Char(
        string="Unique Company Nickname", default=_calc_nick_return, required=True
    )

    # Set company Nickname when 'res.parner' toggles between company and individual
    @api.onchange("is_company")
    def type_change(self):
        if self.is_company == True and self.company_nickname == "_":
            self.company_nickname = False
        elif self.is_company == False and self.company_nickname == False:
            self.company_nickname = "_"

    # Verify Company Nickname
    @api.onchange("company_nickname")
    def verify_unique(self):
        if self.is_company == False:
            return
        if self.company_nickname == False:
            return
        if self.is_company == True and self.company_nickname == "_":
            raise UserError("Company Nickname Cannot Be _")
        self.company_nickname = self.company_nickname.upper()
        records = self.env["res.partner"].search(
            [("company_nickname", "=", self.company_nickname)]
        )
        if len(records) > 1:
            raise ValidationError(
                "Company Nickname already used: " + str(self.company_nickname)
            )
        if len(records) == 1 and records[0].id != self.id:
            raise ValidationError(
                "Company Nickname already used: " + str(self.company_nickname)
            )
