# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'


    state = fields.Selection(selection_add=[('011_not_started', 'Not started')],default='011_not_started',ondelete={'011_not_started': 'cascade'})

