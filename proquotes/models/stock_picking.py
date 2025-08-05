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

    def action_open_related_lots(self):
        self.ensure_one()

        # Get all lot_ids from move lines (those actually used in receipt)
        lots = self.move_line_ids.lot_id.filtered(lambda l: l)

        if not lots:
            return {
                'type': 'ir.actions.act_window',
                'name': 'No Lots Found',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'target': 'new',
                'views': [(False, 'form')],
                'res_id': self.id,
                'context': {'default_note': 'No lots found on this receipt.'},
            }

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Edit Lot PDFs',
            'view_mode': 'tree,form',
            'res_model': 'stock.lot',
            'domain': [('id', 'in', lots.ids)],
            'target': 'current',
        }
        return action

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
                continue  # Only deliveries

            pdf_attachments = []

            for move_line in picking.move_line_ids:
                lot = move_line.lot_id
                if lot and lot.document_pdf:
                    pdf_attachments.append({
                        'name': lot.document_pdf_filename or f'{lot.name}.pdf',
                        'datas': lot.document_pdf,
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                    })

            if pdf_attachments:
                sale_order = picking.sale_id
                if sale_order:
                    followers = sale_order.message_follower_ids.mapped('partner_id.email')
                    if followers:
                        mail_values = {
                            'subject': 'Your Software License(s)',
                            'body_html': "<p>Attached is your software license document.</p>",
                            'email_to': ", ".join(followers),
                            'attachment_ids': [],
                            'auto_delete': True,
                        }
                        attachment_ids = []
                        for pdf_att in pdf_attachments:
                            attachment = self.env['ir.attachment'].create({
                                'name': pdf_att['name'],
                                'type': 'binary',
                                'datas': pdf_att['datas'],
                                'res_model': 'sale.order',
                                'res_id': sale_order.id,
                                'mimetype': 'application/pdf',
                            })
                            attachment_ids.append(attachment.id)
                        mail_values['attachment_ids'] = [(6, 0, attachment_ids)]
                        self.env['mail.mail'].create(mail_values).send()
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