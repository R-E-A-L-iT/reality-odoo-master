# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], default='0', index=True, string="Priority", tracking=True)
