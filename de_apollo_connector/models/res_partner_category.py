# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    apl_id = fields.Char(
        string='Apollo ID',
        help="The Apollo ID is used for tracking purposes."
    )
    apl_date_update = fields.Date('Synronization Date', help="he date of the most recent update of tags with Apollo.")