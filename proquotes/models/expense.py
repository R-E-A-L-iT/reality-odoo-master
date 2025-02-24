# -*- coding: utf-8 -*-
from odoo.tools.translate import _
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    mileage = fields.Float(string='Mileage (km)')
    mileage_reimbursement = fields.Float(
        string='Mileage Reimbursement',
        compute='_compute_mileage_reimbursement',
        store=True,
        readonly=True
    )

    @api.depends('mileage')
    def _compute_mileage_reimbursement(self):
        for record in self:
            if record.mileage <= 5000:
                record.mileage_reimbursement = record.mileage * 70
            else:
                record.mileage_reimbursement = (5000 * 70) + ((record.mileage - 5000) * 64)