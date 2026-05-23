# -*- coding: utf-8 -*-

from odoo import fields, models


class ApolloPeopleEmployment(models.Model):
    _name = 'apl.people.employment'
    _description = 'Apollo People Employement History'

    apl_people_id = fields.Many2one('apl.people', string='People', readonly=True)
    degree = fields.Char('Degree', readonly=True)
    start_date = fields.Date('Start Date', readonly=True)
    end_date = fields.Date('End Date', readonly=True)
    grade_level = fields.Char('Grade Level', readonly=True)
    kind = fields.Char('Kind', readonly=True)
    major = fields.Char('Major', readonly=True)
    description = fields.Text('Description', readonly=True)
