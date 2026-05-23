# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CcpScannerConfig(models.Model):
    _name = 'ccp.scanner.config'
    _description = 'CCP Scanner Configuration'
    _order = 'sequence, name'

    name = fields.Char(
        string='Scanner Name',
        required=True,
        help='Display name of the scanner (e.g., RTC360, BLK ARC, PEGASUS TRK)'
    )
    internal_key = fields.Char(
        string='Internal Key',
        required=True,
        help='Lowercase identifier used in section names and code (e.g., rtc360, blk_arc). Only edit if you know what you\'re doing.'
    )
    section_name = fields.Char(
        string='Section Name',
        compute='_compute_section_name',
        store=True,
        help='Auto-generated section name used in quote lines (e.g., #ccp_selection_rtc360)'
    )
    title_template_en = fields.Char(
        string='Title Template (English)',
        required=True,
        default='Select CCP Type for {scanner_name}',
        help='Title shown above CCP selection. Use {scanner_name} as placeholder.'
    )
    title_template_fr = fields.Char(
        string='Title Template (French)',
        required=True,
        default='Sélectionner le type CCP pour {scanner_name}',
        help='French title shown above CCP selection. Use {scanner_name} as placeholder.'
    )
    product_search_patterns = fields.Text(
        string='Product Search Patterns',
        required=True,
        default='{period} {scanner_name} Laser Scanner CCP {ccp_type}\n{period} {scanner_name} CCP {ccp_type}\nCCP {ccp_type} {scanner_name} {period}',
        help='Search patterns for finding CCP products, one per line. Use placeholders: {scanner_name}, {ccp_type}, {period}'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in scanner list'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to disable this scanner configuration'
    )

    type_ids = fields.Many2many(
        'ccp.type.config',
        'ccp_scanner_type_rel',
        'scanner_id',
        'type_id',
        string='Available CCP Types',
        help='CCP types available for this scanner'
    )
    period_ids = fields.Many2many(
        'ccp.period.config',
        'ccp_scanner_period_rel',
        'scanner_id',
        'period_id',
        string='Available Time Periods',
        help='Time periods available for this scanner'
    )

    @api.depends('internal_key')
    def _compute_section_name(self):
        """Auto-generate section name from internal_key"""
        for record in self:
            if record.internal_key:
                record.section_name = f'#ccp_selection_{record.internal_key}'
            else:
                record.section_name = False

    @api.model
    def get_scanner_by_section_name(self, section_name):
        """Find scanner config by section name"""
        if section_name and section_name.startswith('#ccp_selection_'):
            internal_key = section_name.replace('#ccp_selection_', '')
            return self.search([('internal_key', '=', internal_key)], limit=1)
        return self.env['ccp.scanner.config']

    def get_title(self, lang='en_US'):
        """Get localized title with scanner name substituted"""
        self.ensure_one()
        if lang in ('fr_CA', 'fr_FR', 'fr_BE'):
            template = self.title_template_fr
        else:
            template = self.title_template_en
        return template.replace('{scanner_name}', self.name)

    def get_search_patterns(self, ccp_type, period):
        """Get product search patterns with placeholders substituted"""
        self.ensure_one()
        patterns = []
        if self.product_search_patterns:
            for line in self.product_search_patterns.split('\n'):
                if line.strip():
                    pattern = line.strip()
                    pattern = pattern.replace('{scanner_name}', self.name)
                    pattern = pattern.replace('{ccp_type}', ccp_type)
                    pattern = pattern.replace('{period}', period)
                    patterns.append(pattern)
        return patterns

    _sql_constraints = [
        ('internal_key_unique', 'unique(internal_key)', 'Scanner internal key must be unique!'),
        ('name_unique', 'unique(name)', 'Scanner name must be unique!')
    ]
