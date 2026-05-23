# -*- coding: utf-8 -*-

from odoo import fields, models


class CRMStage(models.Model):
    _inherit = 'crm.stage'

    apl_id = fields.Char(
        string='Apollo ID',
        help="The Apollo ID is used for tracking purposes."
    )
    apl_date_update = fields.Date('Last Update Date', help="he date of the most recent update of stages with Apollo.")
