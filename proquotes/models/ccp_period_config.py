# -*- coding: utf-8 -*-
from odoo import models, fields


class CcpPeriodConfig(models.Model):
    _name = 'ccp.period.config'
    _description = 'CCP Period Configuration'
    _order = 'sequence, name'

    name = fields.Char(
        string='Period Code',
        required=True,
        help='Period code used in product search (e.g., "1 yr", "2 yr", "3 yr", "5 yr")'
    )
    display_name_en = fields.Char(
        string='Display Name (English)',
        help='Display label shown to English-speaking users'
    )
    display_name_fr = fields.Char(
        string='Display Name (French)',
        help='Display label shown to French-speaking users'
    )
    icon = fields.Selection(
        selection=[
            ('fa-clock-o', 'Clock'),
            ('fa-calendar', 'Calendar'),
            ('fa-calendar-check-o', 'Calendar Check'),
            ('fa-calendar-plus-o', 'Calendar Plus'),
            ('fa-history', 'History'),
            ('fa-hourglass-half', 'Hourglass'),
            ('fa-time', 'Time'),
        ],
        string='Icon',
        default='fa-clock-o',
        help='Font Awesome icon to display for this time period'
    )
    icon_image = fields.Binary(
        string='Icon Image',
        attachment=True,
        help='Upload a custom icon image. If set, this will be displayed instead of the Font Awesome icon.'
    )
    icon_image_filename = fields.Char(
        string='Icon Image Filename'
    )
    color = fields.Char(
        string='Color',
        default='#3498DB',
        help='Hex color code for UI styling (e.g., #3498DB)'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in period selection'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to hide this period from selections'
    )

    scanner_ids = fields.Many2many(
        'ccp.scanner.config',
        'ccp_scanner_period_rel',
        'period_id',
        'scanner_id',
        string='Scanners'
    )

    def name_get(self):
        """Display the appropriate display_name based on context language, or fall back to name"""
        result = []
        lang = self.env.context.get('lang', 'en_US')
        for record in self:
            if lang in ('fr_CA', 'fr_FR', 'fr_BE'):
                name = record.display_name_fr or record.display_name_en or record.name
            else:
                name = record.display_name_en or record.name
            result.append((record.id, name))
        return result

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'CCP Period Code must be unique!')
    ]
