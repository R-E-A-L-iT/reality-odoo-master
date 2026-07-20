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
        compute='_compute_display_name',
        inverse='_inverse_display_name',
        store=True,
        readonly=False,
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
    period_ids = fields.Many2many(
        'ccp.period.config',
        'ccp_type_period_rel',
        'type_id',
        'period_id',
        string='Available Time Periods',
        help='Restrict this CCP type to specific time periods. If empty, all scanner periods are shown.'
    )

    @api.depends('name')
    def _compute_display_name(self):
        """Display the custom label if set, otherwise fall back to the Type Code.

        Odoo 19 removed name_get(); the label is now driven by the standard
        display_name field. It stays user-editable (inverse below) and only
        falls back to `name` when no custom label has been entered.
        """
        for record in self:
            if not record.display_name:
                record.display_name = record.name

    def _inverse_display_name(self):
        """Allow the computed display_name to be edited/stored directly."""
        # The value is persisted by the framework; no extra work required.
        return

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'CCP Type Code must be unique!')
    ]
