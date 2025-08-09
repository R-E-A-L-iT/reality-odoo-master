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

    @api.depends("company_id")
    def _get_default_footer(self):
        # Get Company
        company = None
        if self.company_id == False or self.company_id == None:
            company = self.company_id
        else:
            company = self.env.company

        # Get User
        user = None
        if self.user_id == False or self.user_id == None:
            user = self.user_id
        else:
            user = self.env.user

        # Get Prefered Footers
        result_raw = user.prefered_quote_footers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify footers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]

        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", False),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Footer Available")

    footer_id = fields.Many2one(
        "header.footer", required=True, default=_get_default_footer
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
                email_layout_xmlid='mail.mail_notification_light',
                attachment_ids=attachment_ids,
            )

        return res


class stock(models.Model):
    _inherit = "stock.picking"

    footer = fields.Selection([
        ('ABtechFooter_Atlantic_Derek', "Abtech_Atlantic_Derek"),
        ('ABtechFooter_Atlantic_Ryan', "Abtech_Atlantic_Ryan"),
        ('ABtechFooter_Ontario_Derek', "Abtech_Ontario_Derek"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Ontario_Phil', "Abtech_Ontario_Phil"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Quebec_Alexandre', "Abtech_Quebec_Alexandre"),
        ('ABtechFooter_Quebec_Benoit_Carl', "ABtechFooter_Quebec_Benoit_Carl"),
        ('ABtechFooter_Quebec_Derek', "Abtech_Quebec_Derek"),
        ('GeoplusFooterCanada', "Geoplus_Canada"),
        ('GeoplusFooterUS', "Geoplus_America"),
        ('Leica_Footer_Ali', "Leica Ali"),
        ('REALiTFooter_Derek_US', "REALiTFooter_Derek_US"),
        ('REALiTFooter_Martin', "REALiTFooter_Martin"),
        ('REALiTSOLUTIONSLLCFooter_Derek_US', "R-E-A-L.iT Solutions Derek"),
        ('REALiTFooter_Derek', "REALiTFooter_Derek"),
        ('REALiTFooter_Derek_Transcanada', "REALiTFooter_Derek_Transcanada"),
    ], default='REALiTFooter_Derek', required=True, help="Footer selection field", string="Footer OLD")

    footer_id = fields.Many2one(
        'header.footer')