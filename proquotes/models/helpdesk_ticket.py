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
from odoo.http import request

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

    def _set_company_based_on_visitor_country(self, ticket):
        """Assign company based on visitor's country: US → R-E-A-L.iT U.S. Inc., Others → R-E-A-L.iT Solutions"""
        company_to_assign = None

        # Try to get visitor from request context (for website-submitted tickets)
        try:
            if request and hasattr(request, 'env'):
                visitor = request.env['website.visitor']._get_visitor_from_request()
                if visitor and visitor.country_id:
                    us_country = self.env.ref('base.us', raise_if_not_found=False)
                    _logger.info('>>>>>>>Helpdesk ticket - visitor country: %s', visitor.country_id.name)

                    if us_country and visitor.country_id.id == us_country.id:
                        # US visitor → assign to R-E-A-L.iT U.S. Inc.
                        company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT U.S. Inc.')], limit=1)
                        _logger.info('>>>>>>>Assigning US company to helpdesk ticket>>>:%s', company_to_assign.name if company_to_assign else None)
                    else:
                        # Non-US visitor → assign to R-E-A-L.iT Solutions
                        company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
                        _logger.info('>>>>>>>Assigning Solutions company to helpdesk ticket>>>:%s', company_to_assign.name if company_to_assign else None)
        except Exception as e:
            _logger.warning('>>>>>>>Could not get visitor from request for helpdesk ticket: %s', str(e))

        # Fallback: if no visitor or country unknown → default to R-E-A-L.iT Solutions
        if not company_to_assign:
            company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
            _logger.info('>>>>>>>Fallback to Solutions company for helpdesk ticket>>>:%s', company_to_assign.name if company_to_assign else None)

        # Assign the company
        if company_to_assign:
            ticket.company_id = company_to_assign.id

    @api.model
    def create(self, vals):

        helpdesk_ticket = super(ticket, self).create(vals)

        # Assign company based on visitor location for website tickets
        self._set_company_based_on_visitor_country(helpdesk_ticket)

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