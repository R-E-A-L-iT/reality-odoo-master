# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.http import request


_logger = logging.getLogger(__name__)

class CrmRevealView(models.Model):
    _inherit = 'crm.reveal.view'

    visitor_id = fields.Many2one(
        'website.visitor',
        string="Website Visitor",
        readonly=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        visitor = None
        # Before we write the crm.reveal.view, pull the current visitor out of the session
        for vals in vals_list:
            try:
                visitor = request.env['website.visitor']._get_visitor_from_request()
            except Exception as e:
                # Exception if called outside HTTP
                _logger.debug("Skipping adding visitor ID on crm.reveal.view create: %s", e)

            if visitor:
                try:
                    vals['visitor_id'] = visitor.id
                except Exception:
                    _logger.exception(
                        "Failed to assign visitor_id=%s to crm.reveal.view vals=%s",
                        visitor.id, vals
                    )

        return super().create(vals_list)
