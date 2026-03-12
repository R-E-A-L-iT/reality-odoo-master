# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CcpTypeConfig(models.Model):
    _name = 'ccp.type.config'
    _description = 'CCP Type Configuration'
    _order = 'sequence, name'

    name = fields.Char(
        string='Type Code',
        required=True,
        help='CCP type code (e.g., BASIC, BLUE, BRONZE, SILVER, GOLD)'
    )
    display_name = fields.Char(
        string='Display Name',
        help='Optional display label. If not set, uses the Type Code.'
    )
    icon = fields.Selection(
        selection=[
            ('fa-star', 'Star'),
            ('fa-shield', 'Shield'),
            ('fa-medal', 'Medal'),
            ('fa-award', 'Award'),
            ('fa-crown', 'Crown'),
            ('fa-certificate', 'Certificate'),
            ('fa-gem', 'Gem'),
            ('fa-trophy', 'Trophy'),
        ],
        string='Icon',
        default='fa-star',
        help='Font Awesome icon to display for this CCP type'
    )
    color = fields.Char(
        string='Color',
        default='#95A5A6',
        help='Hex color code for UI styling (e.g., #FFD700)'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in CCP type selection'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to hide this CCP type from selections'
    )

    scanner_ids = fields.Many2many(
        'ccp.scanner.config',
        'ccp_scanner_type_rel',
        'type_id',
        'scanner_id',
        string='Scanners'
    )

    def name_get(self):
        """Display the display_name if set, otherwise fall back to name"""
        result = []
        for record in self:
            name = record.display_name or record.name
            result.append((record.id, name))
        return result

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'CCP Type Code must be unique!')
    ]
