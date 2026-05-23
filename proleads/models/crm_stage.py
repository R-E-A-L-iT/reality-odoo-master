# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrmStage(models.Model):
    _inherit = "crm.stage"

    use_probability_override = fields.Boolean(
        string="Use Probability Override",
        help="If enabled, opportunities moved into this stage will have their "
             "probability set to the value below."
    )
    probability_override = fields.Float(
        string="Probability Override (%)",
        help="Probability (0 to 100) to apply to opportunities entering this stage "
             "when 'Use Probability Override' is enabled.",
        default=0.0
    )

    @api.constrains('probability_override')
    def _check_probability_bounds(self):
        for rec in self:
            if rec.probability_override < 0.0 or rec.probability_override > 100.0:
                raise ValidationError(_("Probability Override must be between 0 and 100."))
