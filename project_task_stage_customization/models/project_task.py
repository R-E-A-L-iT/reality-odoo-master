# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'


    state = fields.Selection(selection_add=[('011_not_started', 'Not started')],default='011_not_started',ondelete={'011_not_started': 'cascade'})

    # set default state in case task is a subtask
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('parent_id'):
                vals['state'] = '011_not_started'
            else:
                vals.setdefault('state', '011_not_started')
        return super().create(vals_list)
