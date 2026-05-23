# -*- coding: utf-8 -*-

from odoo import models


class View(models.Model):
    _inherit = 'ir.ui.view'

    def _render_template(self, template, values=None):
        if template in ['web.login', 'web.webclient_bootstrap']:
            if not values:
                values = {}
            values["title"] = self.env['ir.config_parameter'].sudo().get_param("app_system_name", "R-E-A-L")
        return super(View, self)._render_template(template, values=values)
