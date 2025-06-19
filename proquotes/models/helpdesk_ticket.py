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

class ticket(models.Model):
    _inherit = 'helpdesk.ticket'

    def _default_footer(self):
        """
        Determine the default footer based on the active company and the sending user's first name.
        """
        current_user = self.env.user
        company_name = self.env.company.name
        footer = False

        # Personal footers based on first name
        if current_user.name.startswith('Horia'):
            footer = self.env.ref('proquotes.footer_horia', raise_if_not_found=False)
        elif current_user.name.startswith('Bill'):
            footer = self.env.ref('proquotes.footer_bill', raise_if_not_found=False)
        elif current_user.name.startswith('Maël'):
            footer = self.env.ref('proquotes.footer_mael', raise_if_not_found=False)

        # Default footers based on company name
        if not footer:
            if company_name == 'R-E-A-L.iT Solutions':
                footer = self.env['header.footer'].search(
                    [('name', '=', 'EMAIL - Canadian Default Footer')],
                    limit=1
                )
            elif company_name == 'R-E-A-L.iT U.S. Inc.':
                footer = self.env['header.footer'].search(
                    [('name', '=', 'EMAIL - American Default Footer')],
                    limit=1
                )

        return footer.id if footer else False

    footer_id = fields.Many2one(
        "header.footer",
        default=_default_footer,
        required=False,
        domain=[('record_type', '=', 'Footer')],
        string="Footer"
    )
    
    @api.model
    def create(self, vals):
        
        helpdesk_ticket = super(ticket, self).create(vals)
        helpdesk_team = helpdesk_ticket.team_id

        if not helpdesk_team:
            _logger.info("No helpdesk team assigned to this ticket.")
            return helpdesk_ticket

        partners_with_emails = helpdesk_team.message_partner_ids.filtered(lambda partner: partner.email)

        if not partners_with_emails:
            _logger.info("No users with emails found in the helpdesk team: %s", helpdesk_team.name)
            return helpdesk_ticket

        _logger.info("Sending email to the following users: %s", ", ".join([partner.name for partner in partners_with_emails]))

        return helpdesk_ticket