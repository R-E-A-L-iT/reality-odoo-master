# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2015 - Present, Braincrew Apps (<http://www.braincrewapps.com>). All Rights Reserved

# Odoo Proprietary License v1.0
#
# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps,  braincrewapps.com, or if you have received a written
# agreement from the authors of the Software.
#
# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).
#
# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.
#
# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.constrains('date')
    def _check_timesheet_date(self):
        today = fields.Date.today()
        allowed_past_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'timesheet.allowed_past_days', default=0
        ))
        min_allowed_date = today - timedelta(days=allowed_past_days)

        for record in self:
            if record.date < min_allowed_date:
                raise ValidationError(_("You cannot log timesheets before %s.") % min_allowed_date)
            if record.date > today:
                raise ValidationError(_("You cannot log timesheets for future dates."))
