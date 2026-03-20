# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    hide_on_portal = fields.Boolean(
        string="Hide on Portal",
        default=False,)

    def _get_available_footer_domain(self):
        return [
            ("active", "=", True),
            ("record_type", "=", "Footer"),
        ]

    @api.model
    def _get_first_available_footer(self, company=False):
        domain = self._get_available_footer_domain()
        footers = self.env["header.footer"].search(domain, order="id asc")
        if company:
            company_specific = footers.filtered(
                lambda f: not f.company_ids or company in f.company_ids
            )
            if company_specific:
                return company_specific[0]
        return footers[:1]

    @api.model
    def _get_user_company_footer(self, user=False, company=False):
        user = user or self.env.user
        company = company or self.env.company

        if not user or not company:
            return self.env["header.footer"]

        # New per-company mapping model from the previous change
        line = self.env["res.users.company.footer"].search(
            [
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if line and line.footer_id and line.footer_id.active and line.footer_id.record_type == "Footer":
            return line.footer_id

        return self.env["header.footer"]

    @api.model
    def _get_company_default_footer(self, company=False):
        company = company or self.env.company
        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.record_type == "Footer"
        ):
            return company.default_footer_id
        return self.env["header.footer"]

    @api.model
    def _default_footer_id(self):
        user = self.env.user
        company = self.env.company

        footer = self._get_user_company_footer(user=user, company=company)
        if footer:
            return footer.id

        footer = self._get_company_default_footer(company=company)
        if footer:
            return footer.id

        footer = self._get_first_available_footer(company=company)
        return footer.id if footer else False

    footer_id = fields.Many2one(
        "header.footer",
        string="Footer",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
        default=_default_footer_id,
    )

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue

            attachment_ids = []
            lots_for_body = []

            for ml in picking.move_line_ids:
                lot = ml.lot_id
                if lot and lot.document_pdf:
                    att = self.env['ir.attachment'].create({
                        'name': lot.document_pdf_filename or f'{lot.name}.pdf',
                        'type': 'binary',
                        'datas': lot.document_pdf,
                        'res_model': 'sale.order',
                        'res_id': picking.sale_id.id if picking.sale_id else False,
                        'mimetype': 'application/pdf',
                    })
                    attachment_ids.append(att.id)
                    lots_for_body.append((ml.product_id.display_name, lot.name))

            if not attachment_ids or not picking.sale_id:
                continue

            sale_order = picking.sale_id

            partners = sale_order.message_follower_ids.mapped('partner_id').filtered(lambda p: p.email)
            if not partners:
                continue

            body_html = self.env['ir.qweb']._render(
                'proquotes.software_license_email_body',
                {
                    'sale_order': sale_order,
                    'picking': picking,
                    'lots': lots_for_body,
                },
            )

            sale_order.with_context(
                lang=sale_order.partner_id.lang,
                mail_notify_force_send=True,
            ).message_post(
                partner_ids=partners.ids,
                subject=f"Software Licenses for {sale_order.name}",
                body=body_html,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_layout',
                attachment_ids=attachment_ids,
            )

        return res
